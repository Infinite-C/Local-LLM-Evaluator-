#!/usr/bin/env python3
"""
统一 LLM-as-Judge 评测框架（EvalScope 风格输出格式）
- 支持多种评测任务：摘要、答案相关性、翻译、事实一致性等
- 通过修改 eval_config.py 的 TASK_TYPE 即可切换任务
- 从 task_prompts.py 自动加载对应任务的 prompt 模板和评估指标
- 支持批量评测多个数据集目录（智能合并模式）
- 输出目录结构：results/deepeval/{模型名}/{评估维度}/
  ├── detailed_results.json   每个样本的详细评测结果
  ├── summary.json            汇总统计
  ├── config.json             评测配置
  └── history.json            历史运行记录（追加，不覆盖）
"""
import json
import re
import requests
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# 导入配置文件和任务模板
import eval_config as cfg
from task_prompts import get_task_config, list_supported_tasks, print_all_tasks, auto_detect_task_type


# ──────────────────────────── 数据加载 ────────────────────────────

def load_dataset(dataset_path: Path = None, dataset_dir: Path = None, limit: int = 0) -> List[Dict]:
    """
    加载数据集。
    - dataset_dir 不为 None：读取目录下所有 .jsonl 文件并合并
    - 否则读取单个 dataset_path 文件
    limit=0 表示使用全部数据
    返回列表，每个元素包含 input_text、reference_summary、id、source_file
    """
    data = []
    global_id = 0

    if dataset_dir is not None:
        # 读取目录下所有 .jsonl 文件
        jsonl_files = sorted(dataset_dir.glob("*.jsonl"))
        if not jsonl_files:
            raise FileNotFoundError(f"目录中没有找到 .jsonl 文件: {dataset_dir}")

        for jsonl_file in jsonl_files:
            file_data = []
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    item = json.loads(line)
                    file_data.append({
                        'input_text': item['query'],
                        'reference_summary': item['response'],
                        'id': global_id,
                        'source_file': jsonl_file.name
                    })
                    global_id += 1
                    if limit > 0 and global_id >= limit:
                        break
            data.extend(file_data)
            if limit > 0 and global_id >= limit:
                break
    else:
        # 读取单个文件
        if dataset_path is None:
            raise ValueError("dataset_path 和 dataset_dir 不能同时为 None")
        source_file = dataset_path.name
        with open(dataset_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if limit > 0 and i >= limit:
                    break
                item = json.loads(line.strip())
                data.append({
                    'input_text': item['query'],
                    'reference_summary': item['response'],
                    'id': i,
                    'source_file': source_file
                })

    return data


# ──────────────────────────── 内容生成 ────────────────────────────

def generate_content_once(model_name: str, input_text: str,
                          prompt_template: str, system_msg: str) -> str:
    """单次生成内容的内部函数"""
    url = cfg.OLLAMA_API_URL
    prompt = prompt_template.format(input_text=input_text)
    payload = {
        "model": model_name,
        "prompt": prompt,
        "system": system_msg,
        "stream": False,
        "options": {
            "temperature": cfg.GENERATION_TEMPERATURE,
            "num_predict": cfg.MAX_TOKENS_GENERATION,
        }
    }
    try:
        resp = requests.post(url, json=payload, timeout=cfg.API_TIMEOUT)
        resp.raise_for_status()
        content = resp.json().get('response', '').strip()
        return content
    except Exception as e:
        print(f"生成失败: {e}")
        return ""


def generate_content(model_name: str, input_text: str, task_config: Dict[str, Any]) -> str:
    """生成内容，带重试逻辑，根据任务类型使用对应 prompt"""
    gen_prompt = task_config.get('generation_prompt', "请回答：\n\n{input_text}\n\n回答：")
    gen_system = task_config.get('generation_system', "你是一个助手，直接输出结果，不要输出思考过程。")

    content = generate_content_once(model_name, input_text, gen_prompt, gen_system)

    # 重试逻辑
    if not content and cfg.ENABLE_RETRY:
        print("    [重试] 第一次生成为空，使用简化 prompt 重试...")
        content = generate_content_once(model_name, input_text,
                                        cfg.RETRY_PROMPT, cfg.RETRY_SYSTEM_MSG)

    if not content:
        return ""

    # 后处理：去除思考标签
    content = re.sub(r'💭.*?💭', '', content, flags=re.DOTALL)
    content = re.sub(r'思考.*?\n', '', content, flags=re.DOTALL)
    return content


# ──────────────────────────── 质量评估 ────────────────────────────

def evaluate_content(generated: str, reference: str, input_text: str,
                     task_config: Dict[str, Any]) -> Dict[str, Any]:
    """调用裁判模型对内容进行打分，使用任务特定的 prompt"""
    if not generated:
        metrics = {m: 0.0 for m in task_config['metrics']}
        return {
            'score': 0.0,
            'raw_output': '',
            'metrics': metrics
        }

    prompt_template = task_config['prompt_template']
    system_msg = task_config['system_msg']
    metric_weights = task_config['metric_weights']

    prompt = prompt_template.format(
        input_text=input_text[:500],
        reference=reference,
        generated=generated
    )

    payload = {
        "model": cfg.JUDGE_MODEL,
        "prompt": prompt,
        "system": system_msg,
        "stream": False,
        "options": {
            "temperature": cfg.JUDGE_TEMPERATURE,
            "num_predict": cfg.MAX_TOKENS_JUDGE,
        }
    }
    try:
        resp = requests.post(cfg.OLLAMA_API_URL, json=payload, timeout=cfg.API_TIMEOUT)
        resp.raise_for_status()
        output = resp.json().get('response', '').strip()
        raw_output = output

        # 去除思考标签
        output = re.sub(r'💭.*?💭', '', output, flags=re.DOTALL)
        output = re.sub(r'思考[：:].*?\n', '', output)
        # 提取数字
        match = re.search(r'(\d+(?:\.\d+)?)', output)
        if match:
            score = float(match.group(1))
            score = min(max(score, 0.0), 10.0) / 10.0
            metrics = {}
            for metric, weight in metric_weights.items():
                metrics[metric] = score * weight
            return {
                'score': score,
                'raw_output': raw_output,
                'metrics': metrics
            }
        else:
            print(f"  裁判模型输出无法解析: {output[:200]}")
            return {'score': -1.0, 'raw_output': raw_output, 'metrics': {}}
    except Exception as e:
        print(f"  评估调用失败: {e}")
        return {'score': -1.0, 'raw_output': str(e), 'metrics': {}}


# ──────────────────────── 结果构建与保存 ──────────────────────────

def build_config(task_config: Dict[str, Any], task_type: str, eval_dimension: str,
                 start_time: float, end_time: float) -> Dict[str, Any]:
    """构建 config.json 内容"""
    return {
        'model': cfg.GENERATION_MODEL,
        'judge_model': cfg.JUDGE_MODEL,
        'dataset': str(cfg.DATASET_PATH),
        'sample_limit': cfg.SAMPLE_LIMIT,
        'task_type': task_type,
        'task_name': task_config['name'],
        'eval_dimension': eval_dimension,
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'time_elapsed': round(end_time - start_time, 2),
        'time_elapsed_formatted': f"{end_time - start_time:.2f}s"
    }


def build_summary(results: List[Dict[str, Any]], task_config: Dict[str, Any],
                  start_time: float, end_time: float) -> Dict[str, Any]:
    """构建 summary.json 内容"""
    valid_scores = [r['score'] for r in results if r['score'] >= 0]

    valid_metrics = [r['metrics'] for r in results if r['metrics']]
    avg_metrics = {}
    if valid_metrics:
        for key in task_config['metrics']:
            values = [m.get(key, 0) for m in valid_metrics if key in m]
            avg_metrics[key] = round(sum(values) / len(values), 4) if values else 0.0

    return {
        'total_samples': len(results),
        'valid_samples': len(valid_scores),
        'failed_samples': len(results) - len(valid_scores),
        'overall_score': round(sum(valid_scores) / len(valid_scores), 4) if valid_scores else 0.0,
        'max_score': round(max(valid_scores), 4) if valid_scores else 0.0,
        'min_score': round(min(valid_scores), 4) if valid_scores else 0.0,
        'pass_rate': round(
            sum(1 for s in valid_scores if s >= 0.6) / len(valid_scores) * 100, 1
        ) if valid_scores else 0.0,
        'metrics': avg_metrics,
        'time_elapsed': round(end_time - start_time, 2),
        'time_elapsed_formatted': f"{end_time - start_time:.2f}s"
    }


def build_history_entry(config: Dict[str, Any],
                        summary: Dict[str, Any]) -> Dict[str, Any]:
    """构建单条历史记录"""
    return {
        'timestamp': config['timestamp'],
        'model': config['model'],
        'judge_model': config['judge_model'],
        'task_type': config['task_type'],
        'task_name': config['task_name'],
        'eval_dimension': config['eval_dimension'],
        'sample_limit': config['sample_limit'],
        'overall_score': summary['overall_score'],
        'pass_rate': summary['pass_rate'],
        'time_elapsed': summary['time_elapsed_formatted']
    }


def save_results(output_dir: Path,
                 config: Dict[str, Any],
                 summary: Dict[str, Any],
                 detailed_results: List[Dict[str, Any]]):
    """保存结果到 4 个文件"""
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / 'config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    with open(output_dir / 'detailed_results.json', 'w', encoding='utf-8') as f:
        json.dump(detailed_results, f, ensure_ascii=False, indent=2)

    with open(output_dir / 'summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # history.json（追加模式）
    history_file = output_dir / 'history.json'
    history: List[Dict[str, Any]] = []
    if history_file.exists():
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append(build_history_entry(config, summary))

    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


# ──────────────────────────── 打印汇总 ────────────────────────────

def print_summary(config: Dict[str, Any], summary: Dict[str, Any]):
    """打印汇总结果"""
    print("\n" + "=" * 70)
    print(f"评估结果汇总 - {config['task_name']}")
    print("=" * 70)
    print(f"模型: {config['model']}")
    print(f"裁判模型: {config['judge_model']}")
    print(f"任务类型: {config['task_type']}")
    print(f"评估维度: {config['eval_dimension']}")
    print(f"数据集: {config['dataset']}")
    print(f"样本数: {summary['total_samples']}")
    print(f"有效样本: {summary['valid_samples']}")
    print(f"失败样本: {summary['failed_samples']}")
    print("-" * 70)
    print(f"总体得分: {summary['overall_score']:.4f}")
    print(f"最高分:   {summary['max_score']:.4f}")
    print(f"最低分:   {summary['min_score']:.4f}")
    print(f"通过率 (≥0.6): {summary['pass_rate']:.1f}%")
    print("-" * 70)
    print("各维度得分:")
    for metric, score in summary['metrics'].items():
        print(f"  - {metric}: {score:.4f}")
    print("-" * 70)
    print(f"耗时: {summary['time_elapsed_formatted']}")
    print("=" * 70)


# ──────────────────────────── 单次评测 ────────────────────────────

def run_evaluation(dataset_path_or_dir: Path, data_mode: str, dataset_index: int = 0, total_datasets: int = 1) -> Dict[str, Any]:
    """
    执行单次评测，返回汇总信息。
    """
    # ── 自动识别任务类型 ──
    task_type = cfg.TASK_TYPE
    eval_dimension = cfg.EVAL_DIMENSION

    if task_type == "auto":
        task_type = auto_detect_task_type(dataset_path_or_dir)

    if eval_dimension == "auto":
        eval_dimension = task_type

    # ── 获取任务配置 ──
    try:
        task_config = get_task_config(task_type)
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        return None

    # ── 输出目录 ──
    if data_mode == "dir":
        eval_dimension = dataset_path_or_dir.name
    OUTPUT_DIR = cfg.OUTPUT_ROOT / cfg.GENERATION_MODEL / eval_dimension

    # ── 打印配置信息 ──
    if total_datasets > 1:
        print(f"\n{'='*70}")
        print(f"[{dataset_index}/{total_datasets}] 评测数据集: {dataset_path_or_dir.name}")
        print(f"{'='*70}")
    print(f"📋 任务类型: {task_type} ({task_config['name']})")
    print(f"📁 数据集: {dataset_path_or_dir} ({'目录' if data_mode == 'dir' else '文件'})")
    print(f"🤖 生成模型: {cfg.GENERATION_MODEL}")
    print(f"⚖️  裁判模型: {cfg.JUDGE_MODEL}")
    print(f"📝 样本数量: {cfg.SAMPLE_LIMIT if cfg.SAMPLE_LIMIT > 0 else '全部'}")
    print(f"📂 输出目录: {OUTPUT_DIR}")

    # ── 开始计时 ──
    start_time = time.time()

    # ── 加载数据 ──
    if data_mode == "dir":
        dataset = load_dataset(dataset_dir=dataset_path_or_dir, limit=cfg.SAMPLE_LIMIT)
        jsonl_files = list(dataset_path_or_dir.glob("*.jsonl"))
        print(f"\n✅ 从目录加载 {len(dataset)} 条数据（共 {len(jsonl_files)} 个文件）")
    else:
        dataset = load_dataset(dataset_path=dataset_path_or_dir, limit=cfg.SAMPLE_LIMIT)
        print(f"\n✅ 加载 {len(dataset)} 条数据")

    # ── 生成内容 ──
    print(f"\n🔄 生成内容 (模型: {cfg.GENERATION_MODEL})...")
    generated_results = []
    for i, item in enumerate(dataset):
        print(f"  [{i+1}/{len(dataset)}] 生成中...", end=' ', flush=True)
        generated = generate_content(cfg.GENERATION_MODEL, item['input_text'], task_config)
        print(f"完成 ({len(generated)} 字)")
        generated_results.append({
            'id': item['id'],
            'input_text': item['input_text'],
            'generated_summary': generated,
            'reference_summary': item['reference_summary'],
            'source_file': item.get('source_file', '')
        })

    # ── 评估 ──
    print(f"\n🔄 评估质量 (裁判: {cfg.JUDGE_MODEL})...")
    detailed_results = []
    for i, res in enumerate(generated_results):
        print(f"  [{i+1}/{len(generated_results)}] 评估中...", end=' ', flush=True)
        eval_info = evaluate_content(
            res['generated_summary'],
            res['reference_summary'],
            res['input_text'],
            task_config
        )

        result_item = {
            'id': res['id'],
            'input_text': (res['input_text'][:200] + "..."
                           if len(res['input_text']) > 200
                           else res['input_text']),
            'generated_summary': res['generated_summary'],
            'reference_summary': res['reference_summary'],
            'score': eval_info['score'],
            'raw_output': eval_info['raw_output'],
            'metrics': eval_info['metrics'],
            'summary_length': len(res['generated_summary']),
            'reference_length': len(res['reference_summary']),
            'source_file': res.get('source_file', '')
        }

        if eval_info['score'] >= 0:
            print(f"得分: {eval_info['score']:.4f}")
        else:
            print(f"失败: {eval_info['score']}")

        detailed_results.append(result_item)

    # ── 结束计时 ──
    end_time = time.time()

    # ── 构建结果 ──
    config = build_config(task_config, task_type, eval_dimension, start_time, end_time)
    summary = build_summary(detailed_results, task_config, start_time, end_time)

    # ── 打印汇总 ──
    print_summary(config, summary)

    # ── 保存结果 ──
    save_results(OUTPUT_DIR, config, summary, detailed_results)
    print(f"\n✅ 结果已保存到: {OUTPUT_DIR}")

    return {
        'dataset': str(dataset_path_or_dir),
        'task_type': task_type,
        'eval_dimension': eval_dimension,
        'overall_score': summary['overall_score'],
        'pass_rate': summary['pass_rate'],
        'output_dir': str(OUTPUT_DIR)
    }


# ──────────────────────── 智能批量扫描 ──────────────────────────

def scan_batch_dirs(parent_dir: Path) -> List[tuple]:
    """
    扫描父目录下的所有子目录，返回 (子目录路径, 模式) 列表
    模式: "single_file" 或 "merged_dir"
    """
    results = []
    if not parent_dir.exists() or not parent_dir.is_dir():
        print(f"❌ 父目录不存在: {parent_dir}")
        return results

    for subdir in sorted(parent_dir.iterdir()):
        if not subdir.is_dir():
            continue

        jsonl_files = list(subdir.glob("*.jsonl"))
        if not jsonl_files:
            print(f"⚠️  跳过空目录: {subdir.name}")
            continue

        if len(jsonl_files) == 1:
            results.append((subdir, "single_file", jsonl_files[0]))
            print(f"  📁 {subdir.name}: 单文件 ({jsonl_files[0].name})")
        else:
            results.append((subdir, "merged_dir", None))
            print(f"  📁 {subdir.name}: 合并 {len(jsonl_files)} 个文件")

    return results


# ──────────────────────────── 主函数 ──────────────────────────────

def main():
    print("=" * 70)
    print("统一 LLM-as-Judge 评测框架")
    print("=" * 70)

    # ── 确定运行模式 ──
    # 优先级：DATASET_BATCH_DIRS > DATASET_DIRS > DATASET_DIR > DATASET_PATH
    if cfg.DATASET_BATCH_DIRS and len(cfg.DATASET_BATCH_DIRS) > 0:
        # 方式四：智能批量评测（混合模式）
        run_mode = "smart_batch"
        all_datasets = []
        for parent_dir in cfg.DATASET_BATCH_DIRS:
            print(f"\n🔍 扫描目录: {parent_dir}")
            subdirs = scan_batch_dirs(parent_dir)
            all_datasets.extend(subdirs)
        datasets = all_datasets
    elif cfg.DATASET_DIRS and len(cfg.DATASET_DIRS) > 0:
        # 方式三：批量评测多个目录
        run_mode = "batch_dirs"
        datasets = [(ds, "dir", None) for ds in cfg.DATASET_DIRS]
    elif cfg.DATASET_DIR is not None:
        # 方式二：评测单个目录
        run_mode = "single_dir"
        datasets = [(cfg.DATASET_DIR, "dir", None)]
    else:
        # 方式一：评测单个文件
        run_mode = "single_file"
        datasets = [(cfg.DATASET_PATH.parent, "single_file", cfg.DATASET_PATH)]

    if not datasets:
        print("❌ 没有有效的数据集，退出")
        return

    total_datasets = len(datasets)
    print(f"\n📊 共 {total_datasets} 个数据集待评测")

    # ── 执行评测 ──
    all_results = []
    for idx, (ds_dir, ds_mode, ds_file) in enumerate(datasets, 1):
        if ds_mode == "single_file":
            result = run_evaluation(ds_file, "file", idx, total_datasets)
        elif ds_mode == "merged_dir" or ds_mode == "dir":
            result = run_evaluation(ds_dir, "dir", idx, total_datasets)
        else:
            continue

        if result:
            all_results.append(result)

    # ── 批量评测汇总 ──
    if total_datasets > 1 and all_results:
        print("\n" + "=" * 70)
        print("批量评测汇总")
        print("=" * 70)
        for i, r in enumerate(all_results, 1):
            print(f"{i}. {Path(r['dataset']).name}")
            print(f"   任务类型: {r['task_type']} | 维度: {r['eval_dimension']}")
            print(f"   总体得分: {r['overall_score']:.4f} | 通过率: {r['pass_rate']:.1f}%")
            print(f"   输出目录: {r['output_dir']}")
        print("=" * 70)

    print("\n🎉 评测完成！")


if __name__ == "__main__":
    main()
