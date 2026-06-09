#!/usr/bin/env python3
"""
RAGAS RAG 评测脚本
基于 RAGAS 框架评测 RAG 系统的检索质量和生成质量

用法:
    python run_ragas_eval.py

输出:
    results/ragas/{model_name}/
    ├── ragas_results.json       详细结果
    └── ragas_report.txt         可读报告
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from functools import wraps

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(SCRIPT_DIR))

import ragas_config as cfg

# 检查 RAGAS 是否安装
try:
    from ragas import evaluate
    from ragas.metrics import (
        ContextRelevance,
        ContextPrecision,
        ContextRecall,
        context_entity_recall,  # 小写，RAGAS 0.2.x 风格
        AnswerRelevancy,
    )
    from datasets import Dataset
except ImportError as e:
    print(f"❌ 缺少依赖: {e}")
    print("请安装: pip install ragas datasets")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════
#  重试机制
# ═══════════════════════════════════════════════════════════════

# 重试配置
RETRY_CONFIG = {
    'max_retries': 3,           # 最大重试次数
    'retry_delay': 5,            # 重试间隔（秒）
    'retry_backoff': 2.0,        # 退避系数（指数退避）
    'timeout_error_types': ['TimeoutError', 'asyncio.exceptions.TimeoutError'],
}

def retry_on_timeout(max_retries=3, delay=5, backoff=2.0):
    """超时重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_type = type(e).__name__
                    error_str = str(e)
                    
                    # 检查是否是超时错误
                    is_timeout = (
                        error_type in RETRY_CONFIG['timeout_error_types'] or
                        'timeout' in error_str.lower() or
                        'Timeout' in error_type
                    )
                    
                    if is_timeout and attempt < max_retries:
                        last_exception = e
                        print(f"\n  ⚠️ 超时 (attempt {attempt + 1}/{max_retries + 1}): {error_str[:100]}...")
                        print(f"     等待 {current_delay}s 后重试...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        # 非超时错误或已达到最大重试次数
                        raise
            
            # 如果所有重试都失败
            raise last_exception
        
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════
#  Ollama 后端配置
# ═══════════════════════════════════════════════════════════════

def create_ollama_llm():
    """创建 Ollama LLM 实例供 RAGAS 使用（带重试和长超时）"""
    if not cfg.USE_OLLAMA_BACKEND:
        return None

    try:
        from langchain_ollama import ChatOllama
        print("  使用 langchain-ollama 后端")
    except ImportError:
        from langchain_community.chat_models import ChatOllama
        print("  使用 langchain_community 后端（建议升级: pip install langchain-ollama）")

    # 设置较长的超时（qwen3:32b 推理慢，需要更多时间）
    llm_timeout = max(cfg.LLM_TIMEOUT, 600)  # 至少 600 秒
    chat_ollama = ChatOllama(
        model=cfg.RAGAS_JUDGE_MODEL,
        base_url=cfg.OLLAMA_BASE_URL,
        temperature=0.0,
        timeout=llm_timeout,
        num_ctx=4096,       # 限制上下文长度，加速推理
        num_predict=512,    # 限制输出长度
    )

    from ragas.llms import LangchainLLMWrapper
    llm = LangchainLLMWrapper(chat_ollama)

    print(f"✅ 已配置 Ollama LLM 后端: {cfg.RAGAS_JUDGE_MODEL}")
    print(f"   LLM 超时时间: {llm_timeout}s")
    print(f"   num_ctx: 4096, num_predict: 512")
    return llm


def create_ollama_embeddings():
    """创建 Ollama Embedding 实例供 RAGAS 使用"""
    try:
        from langchain_ollama import OllamaEmbeddings
        print(f"  使用 langchain-ollama Embeddings 后端")
    except ImportError:
        from langchain_community.embeddings import OllamaEmbeddings
        print(f"  使用 langchain_community Embeddings 后端")

    # 注意：OllamaEmbeddings 不支持 timeout 参数
    embeddings = OllamaEmbeddings(
        model=cfg.EMBEDDING_MODEL,
        base_url=cfg.OLLAMA_BASE_URL,
    )

    from ragas.embeddings import LangchainEmbeddingsWrapper
    wrapped = LangchainEmbeddingsWrapper(embeddings)

    print(f"✅ 已配置 Ollama Embedding 后端: {cfg.EMBEDDING_MODEL}")
    return wrapped


# ═══════════════════════════════════════════════════════════════
#  数据加载
# ═══════════════════════════════════════════════════════════════

def load_dataset(file_path: Path, limit: int = 0) -> list:
    """加载 RAG 评测数据集"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if limit > 0 and i >= limit:
                break
            item = json.loads(line.strip())
            if all(k in item for k in ['question', 'contexts', 'answer', 'ground_truth']):
                data.append(item)
            else:
                print(f"  ⚠️ 跳过不完整样本 (行 {i+1})")
    return data


def convert_to_ragas_format(data: list) -> Dataset:
    """转换为 RAGAS 数据集格式"""
    return Dataset.from_dict({
        'question': [d['question'] for d in data],
        'contexts': [d['contexts'] for d in data],
        'answer': [d['answer'] for d in data],
        'ground_truth': [d['ground_truth'] for d in data],
    })


# ═══════════════════════════════════════════════════════════════
#  评测执行
# ═══════════════════════════════════════════════════════════════

def get_metrics():
    """获取启用的评测指标"""
    metric_map = {
        'context_relevancy': ContextRelevance,
        'context_precision': ContextPrecision,
        'context_recall': ContextRecall,
        'context_entities_recall': context_entity_recall,  # 小写
        'answer_relevancy': AnswerRelevancy,
    }

    metrics = []
    for name in cfg.ENABLED_METRICS:
        if name in metric_map:
            # context_entity_recall 是已实例化的对象，不需要 ()
            if name == 'context_entities_recall':
                metric = metric_map[name]
            else:
                metric = metric_map[name]()
            metrics.append(metric)
        else:
            print(f"  ⚠️ 未知指标: {name}")

    return metrics


def run_evaluation():
    """执行 RAGAS 评测"""
    print("\n" + "=" * 70)
    print("RAGAS RAG 评测")
    print("=" * 70)
    print(f"模型: {cfg.MODEL_NAME}")
    print(f"评测指标: {', '.join(cfg.ENABLED_METRICS)}")
    print(f"数据集: {cfg.DATASET_FILE}")
    print(f"样本限制: {cfg.SAMPLE_LIMIT if cfg.SAMPLE_LIMIT > 0 else '无限制'}")
    print("=" * 70 + "\n")

    # ═══════════════════════════════════════════════════════════
    #  关键：限制并发数，防止 Ollama 被打爆
    # ═══════════════════════════════════════════════════════════
    import os
    # 限制 RAGAS 内部并发 worker 数量（默认会开很多并行 Job）
    # 设为 1 = 串行执行，最稳定；设为 2-3 = 轻微并行
    max_workers = getattr(cfg, 'RAGAS_MAX_WORKERS', 1)
    os.environ["RAGAS_MAX_WORKERS"] = str(max_workers)
    # 同时限制 asyncio 的默认并发
    os.environ["DEFAULT_MAX_WORKERS"] = str(max_workers)
    print(f"🔧 并发控制: max_workers = {max_workers}")
    print(f"   （本地 Ollama 推荐设为 1-3，避免超时）")

    # 创建 Ollama LLM 后端
    llm = create_ollama_llm()

    # 创建 Ollama Embedding 后端
    embeddings = create_ollama_embeddings()

    # 加载数据
    print("📂 加载数据集...")
    raw_data = load_dataset(cfg.DATASET_FILE, cfg.SAMPLE_LIMIT)
    print(f"   加载 {len(raw_data)} 条样本")

    if len(raw_data) == 0:
        print("❌ 数据集为空")
        return None

    # 转换为 RAGAS 格式
    dataset = convert_to_ragas_format(raw_data)

    # 获取评测指标
    metrics = get_metrics()
    print(f"\n📊 评测指标 ({len(metrics)} 个):")
    for m in metrics:
        print(f"   - {m.name}")

    # 执行评测
    print("\n🔄 开始评测...")
    print(f"   重试机制: 最多 {RETRY_CONFIG['max_retries']} 次 (退避: {RETRY_CONFIG['retry_delay']}s × {RETRY_CONFIG['retry_backoff']}x)")
    print(f"   并发数: {max_workers} (降低并发以避免 Ollama 超时)")
    start_time = time.time()
    
    last_error = None
    for attempt in range(RETRY_CONFIG['max_retries'] + 1):
        try:
            # 构建 evaluate 参数
            eval_kwargs = {
                "dataset": dataset,
                "metrics": metrics,
            }
            # 传入 LLM 后端（如果配置了）
            if llm is not None:
                eval_kwargs["llm"] = llm
            # 传入 Embedding 后端（如果配置了）
            if embeddings is not None:
                eval_kwargs["embeddings"] = embeddings

            result = evaluate(**eval_kwargs)

            elapsed = time.time() - start_time
            print(f"\n✅ 评测完成，耗时: {elapsed:.2f}s")

            return result

        except Exception as e:
            error_type = type(e).__name__
            error_str = str(e)
            
            # 检查是否是超时错误
            is_timeout = (
                error_type in RETRY_CONFIG['timeout_error_types'] or
                'timeout' in error_str.lower() or
                'Timeout' in error_type
            )
            
            last_error = e
            
            if is_timeout and attempt < RETRY_CONFIG['max_retries']:
                delay = RETRY_CONFIG['retry_delay'] * (RETRY_CONFIG['retry_backoff'] ** attempt)
                print(f"\n  ⚠️ 超时 (attempt {attempt + 1}/{RETRY_CONFIG['max_retries'] + 1}): {error_str[:100]}")
                print(f"     等待 {delay:.1f}s 后重试...")
                time.sleep(delay)
            else:
                import traceback
                print(f"\n❌ 评测失败: {e}")
                traceback.print_exc()
                return None

    # 所有重试都失败
    print(f"\n❌ 评测失败，已重试 {RETRY_CONFIG['max_retries']} 次")
    return None


# ═══════════════════════════════════════════════════════════════
#  结果保存与报告
# ═══════════════════════════════════════════════════════════════

def save_results(result):
    """保存评测结果"""
    output_dir = cfg.OUTPUT_DIR / "ragas_eval"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 转换为 DataFrame 再转字典
    df = result.to_pandas()
    result_dict = df.to_dict(orient='records')

    # 获取实际的列名（RAGAS 输出的列名可能和配置名不同）
    actual_columns = list(df.columns) if len(df) > 0 else []

    # 计算平均分
    summary = {}
    for col in actual_columns:
        if col in ('question', 'contexts', 'answer', 'ground_truth'):
            continue
        scores = df[col].dropna().tolist()
        if scores:
            try:
                summary[col] = {
                    'mean': sum(scores) / len(scores),
                    'count': len(scores),
                }
            except (TypeError, ValueError):
                pass

    # 保存详细结果
    output = {
        'model': cfg.MODEL_NAME,
        'judge_model': cfg.RAGAS_JUDGE_MODEL,
        'timestamp': datetime.now().isoformat(),
        'configured_metrics': cfg.ENABLED_METRICS,
        'actual_metrics': actual_columns,
        'summary': summary,
        'details': result_dict,
    }

    with open(output_dir / "ragas_results.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    # 生成可读报告
    report_lines = [
        f"RAGAS RAG 评测报告",
        f"被测模型: {cfg.MODEL_NAME}",
        f"裁判模型: {cfg.RAGAS_JUDGE_MODEL}",
        f"时间: {datetime.now().isoformat()}",
        "=" * 50,
        "",
        "评测指标平均分:",
    ]
    for metric, stats in summary.items():
        report_lines.append(f"  {metric}: {stats['mean']:.4f} (n={stats['count']})")

    report_lines.append("")
    report_lines.append("=" * 50)

    with open(output_dir / "ragas_report.txt", 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    print(f"\n📁 结果已保存到: {output_dir}")
    print("\n📊 评测指标平均分:")
    for metric, stats in summary.items():
        print(f"   {metric}: {stats['mean']:.4f}")


def main():
    """主函数"""
    # 检查数据集是否存在
    if not cfg.DATASET_FILE.exists():
        print(f"❌ 数据集不存在: {cfg.DATASET_FILE}")
        print("请创建数据集或修改 ragas_config.py 中的 DATASET_FILE")
        sys.exit(1)

    # 执行评测
    result = run_evaluation()
    if result is not None:
        save_results(result)


if __name__ == "__main__":
    main()
