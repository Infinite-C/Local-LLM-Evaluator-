#!/usr/bin/env python3
"""
噪声鲁棒性评测脚本
测试模型在输入有噪声/扰动时的稳定性

用法:
    python run_noise_robustness.py

输出:
    results/ragas/noise_robustness/
    ├── noise_results.json       详细结果
    └── noise_report.txt         可读报告
"""
import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path


def convert_to_serializable(obj):
    """将 numpy 类型转换为可 JSON 序列化的 Python 类型"""
    import numpy as np
    if isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(v) for v in obj]
    return obj
from typing import List, Dict, Any

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(SCRIPT_DIR))

import ragas_config as cfg

# ═══════════════════════════════════════════════════════════════
#  噪声扰动函数
# ═══════════════════════════════════════════════════════════════

# 常见拼写错误映射（键盘邻近键）
KEYBOARD_NEARBY = {
    'a': ['q', 's', 'z'],
    'b': ['v', 'n', 'g'],
    'c': ['x', 'd', 'f'],
    'd': ['s', 'f', 'e'],
    'e': ['w', 'r', 'd'],
    'f': ['d', 'g', 'r'],
    'g': ['f', 'h', 't'],
    'h': ['g', 'j', 'y'],
    'i': ['u', 'o', 'k'],
    'j': ['h', 'k', 'u'],
    'k': ['j', 'l', 'i'],
    'l': ['k', 'o', 'p'],
    'm': ['n', 'b'],
    'n': ['m', 'b', 'h'],
    'o': ['i', 'p', 'l'],
    'p': ['o', 'l'],
    'q': ['a', 'w'],
    'r': ['e', 't', 'f'],
    's': ['a', 'd', 'w'],
    't': ['r', 'y', 'g'],
    'u': ['y', 'i', 'j'],
    'v': ['c', 'b', 'f'],
    'w': ['q', 'e', 's'],
    'x': ['z', 'c', 's'],
    'y': ['t', 'u', 'h'],
    'z': ['x', 'a', 's'],
}

# 中文常见错别字映射
CHINESE_TYPO_MAP = {
    '的': ['得', '地'],
    '是': ['事', '时'],
    '有': ['又', '友'],
    '在': ['再', '才'],
    '了': ['乐', '辽'],
    '不': ['布', '步'],
    '人': ['认', '任'],
    '这': ['着', '者'],
    '中': ['种', '重'],
    '大': ['达', '打'],
    '来': ['莱', '赖'],
    '去': ['趣', '取'],
    '我': ['窝', '握'],
    '你': ['泥', '拟'],
    '他': ['塔', '踏'],
}

# 同义词映射（简单版）
SYNONYM_MAP = {
    # 英文
    'good': ['great', 'excellent', 'nice', 'fine'],
    'bad': ['poor', 'terrible', 'awful', 'badly'],
    'big': ['large', 'huge', 'enormous', 'massive'],
    'small': ['tiny', 'little', 'mini', 'petite'],
    'fast': ['quick', 'rapid', 'speedy', 'swift'],
    'slow': ['gradual', 'leisurely', 'unhurried'],
    'important': ['significant', 'crucial', 'essential', 'key'],
    'help': ['assist', 'aid', 'support', 'facilitate'],
    'make': ['create', 'produce', 'generate', 'build'],
    'use': ['utilize', 'employ', 'apply', 'leverage'],
    # 中文
    '好': ['优秀', '出色', '棒', '佳'],
    '坏': ['差', '糟糕', '恶劣', '不良'],
    '大': ['巨大', '庞大', '宏伟', '大型'],
    '小': ['微小', '细小', '迷你', '小型'],
    '快': ['迅速', '快速', '敏捷', '疾速'],
    '慢': ['缓慢', '迟缓', '徐缓'],
    '重要': ['关键', '核心', '紧要', '要紧'],
    '帮助': ['协助', '支援', '辅助', '助力'],
}


def apply_typo(text: str, intensity: int = 1) -> str:
    """应用拼写错误扰动"""
    chars = list(text)
    positions = random.sample(range(len(chars)), min(intensity, len(chars)))
    
    for pos in positions:
        char = chars[pos].lower()
        if char in KEYBOARD_NEARBY:
            replacement = random.choice(KEYBOARD_NEARBY[char])
            chars[pos] = replacement if chars[pos].islower() else replacement.upper()
        elif char in CHINESE_TYPO_MAP:
            chars[pos] = random.choice(CHINESE_TYPO_MAP[char])
    
    return ''.join(chars)


def apply_synonym(text: str, intensity: int = 1) -> str:
    """应用同义词替换"""
    words = re.findall(r'\w+|[^\w\s]', text)
    word_positions = [i for i, w in enumerate(words) if w.lower() in SYNONYM_MAP or w in SYNONYM_MAP]
    
    if not word_positions:
        return text
    
    positions = random.sample(word_positions, min(intensity, len(word_positions)))
    
    for pos in positions:
        word = words[pos]
        key = word.lower() if word.lower() in SYNONYM_MAP else word
        if key in SYNONYM_MAP:
            synonym = random.choice(SYNONYM_MAP[key])
            words[pos] = synonym if word.islower() else synonym.capitalize()
    
    return ''.join(words)


def apply_insert(text: str, intensity: int = 1) -> str:
    """应用随机插入扰动"""
    chars = list(text)
    noise_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*'
    
    for _ in range(intensity):
        pos = random.randint(0, len(chars))
        noise = random.choice(noise_chars)
        chars.insert(pos, noise)
    
    return ''.join(chars)


def apply_delete(text: str, intensity: int = 1) -> str:
    """应用随机删除扰动"""
    if len(text) <= intensity:
        return text
    
    chars = list(text)
    positions = random.sample(range(len(chars)), intensity)
    
    for pos in sorted(positions, reverse=True):
        chars.pop(pos)
    
    return ''.join(chars)


def apply_swap(text: str, intensity: int = 1) -> str:
    """应用字符交换扰动"""
    if len(text) < 2:
        return text
    
    chars = list(text)
    for _ in range(intensity):
        pos1 = random.randint(0, len(chars) - 2)
        pos2 = pos1 + 1
        chars[pos1], chars[pos2] = chars[pos2], chars[pos1]
    
    return ''.join(chars)


NOISE_FUNCTIONS = {
    "typo": apply_typo,
    "synonym": apply_synonym,
    "insert": apply_insert,
    "delete": apply_delete,
    "swap": apply_swap,
}


def generate_noisy_variants(text: str, noise_types: List[str], variants_per_type: int, intensity: int) -> Dict[str, List[str]]:
    """生成多种噪声变体"""
    variants = {}
    
    for noise_type in noise_types:
        if noise_type not in NOISE_FUNCTIONS:
            continue
        
        noise_func = NOISE_FUNCTIONS[noise_type]
        type_variants = []
        
        for _ in range(variants_per_type):
            noisy_text = noise_func(text, intensity)
            type_variants.append(noisy_text)
        
        variants[noise_type] = type_variants
    
    return variants


# ═══════════════════════════════════════════════════════════════
#  模型调用
# ═══════════════════════════════════════════════════════════════

def call_ollama(prompt: str, model: str = None) -> str:
    """调用 Ollama 模型"""
    import requests

    model = model or cfg.MODEL_NAME
    url = f"{cfg.OLLAMA_BASE_URL}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=600)  # 增加到10分钟
        response.raise_for_status()
        result = response.json()
        return result.get("response", "")
    except Exception as e:
        print(f"  ⚠️ Ollama 调用失败: {e}")
        return ""


def get_embedding(text: str) -> List[float]:
    """获取文本向量（用于语义相似度计算）"""
    import requests
    
    url = f"{cfg.OLLAMA_BASE_URL}/api/embeddings"
    payload = {
        "model": cfg.EMBEDDING_MODEL,
        "prompt": text,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result.get("embedding", [])
    except Exception as e:
        print(f"  ⚠️ Embedding 获取失败: {e}")
        return []


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算余弦相似度"""
    if not vec1 or not vec2:
        return 0.0
    
    import numpy as np
    
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


# ═══════════════════════════════════════════════════════════════
#  评测流程
# ═══════════════════════════════════════════════════════════════

def load_dataset(file_path: Path, limit: int = 0) -> List[Dict]:
    """加载评测数据集"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if limit > 0 and i >= limit:
                break
            item = json.loads(line.strip())
            data.append(item)
    return data


def evaluate_noise_robustness(sample: Dict) -> Dict[str, Any]:
    """评测单个样本的噪声鲁棒性
    
    流程：
    1. 用干净问题调用模型 → 得到基线答案
    2. 对问题施加噪声扰动 → 生成多个噪声变体
    3. 用每个噪声变体调用模型 → 得到噪声答案
    4. 对比基线答案 vs 噪声答案 → 计算鲁棒性指标
    """
    question = sample.get("question", "")
    ground_truth = sample.get("ground_truth", "")
    
    results = {
        "original_question": question,
        "ground_truth": ground_truth,
        "noise_results": {},
        "metrics": {},
    }
    
    # 第一步：用干净问题调用模型，获取基线答案
    print("    → 生成基线答案...")
    baseline_answer = call_ollama(question)
    results["baseline_answer"] = baseline_answer
    
    if not baseline_answer:
        print("    ⚠️ 基线答案为空，跳过该样本")
        results["metrics"]["robustness_score"] = 0.0
        results["metrics"]["passed"] = False
        results["metrics"]["error"] = "baseline_answer_empty"
        return results
    
    # 预先获取基线答案的向量（避免重复计算）
    baseline_emb = get_embedding(baseline_answer)
    
    # 第二步：生成噪声变体
    noisy_variants = generate_noisy_variants(
        question,
        cfg.NOISE_TYPES,
        cfg.NOISE_VARIANTS_PER_TYPE,
        cfg.NOISE_INTENSITY
    )
    
    # 第三步：对每种噪声类型进行评测
    all_similarities = []
    all_answers = []
    
    for noise_type, variants in noisy_variants.items():
        type_results = []
        
        for i, noisy_question in enumerate(variants):
            # 调用模型获取噪声输入下的答案
            noisy_answer = call_ollama(noisy_question)
            
            # 计算与基线答案的语义相似度
            if "semantic_similarity" in cfg.NOISE_METRICS and baseline_emb:
                noisy_emb = get_embedding(noisy_answer)
                similarity = cosine_similarity(baseline_emb, noisy_emb)
            else:
                similarity = 0.0
            
            type_results.append({
                "noisy_question": noisy_question,
                "noisy_answer": noisy_answer,
                "similarity": similarity,
            })
            
            all_similarities.append(similarity)
            all_answers.append(noisy_answer)
        
        results["noise_results"][noise_type] = type_results
    
    # 第四步：计算综合指标
    if all_similarities:
        results["metrics"]["avg_similarity"] = sum(all_similarities) / len(all_similarities)
        results["metrics"]["min_similarity"] = min(all_similarities)
        results["metrics"]["max_similarity"] = max(all_similarities)
    
    # 答案一致性（所有噪声答案之间的相似度）
    if "answer_consistency" in cfg.NOISE_METRICS and len(all_answers) > 1:
        consistency_scores = []
        for i in range(len(all_answers)):
            for j in range(i + 1, len(all_answers)):
                emb_i = get_embedding(all_answers[i])
                emb_j = get_embedding(all_answers[j])
                consistency_scores.append(cosine_similarity(emb_i, emb_j))
        
        if consistency_scores:
            results["metrics"]["answer_consistency"] = sum(consistency_scores) / len(consistency_scores)
    
    # 鲁棒性评分（相似度越高越鲁棒）
    robustness_score = results["metrics"].get("avg_similarity", 0.0)
    results["metrics"]["robustness_score"] = robustness_score
    
    # 是否通过阈值
    results["metrics"]["passed"] = robustness_score >= cfg.SIMILARITY_THRESHOLD
    
    return results


def run_evaluation():
    """运行完整评测"""
    print("=" * 70)
    print(f"模型: {cfg.MODEL_NAME}")
    print(f"噪声类型: {cfg.NOISE_TYPES}")
    print(f"噪声强度: {cfg.NOISE_INTENSITY}")
    print(f"数据集: {cfg.NOISE_DATASET_FILE}")
    print("=" * 70)

    # 检查数据集是否存在
    if not cfg.NOISE_DATASET_FILE.exists():
        print(f"\n❌ 噪声评测数据集不存在: {cfg.NOISE_DATASET_FILE}")
        print("请创建数据集或从 RAGAS 数据集转换:")
        print(f"  python -c \"import json; [print(json.dumps({{'question': d['question'], 'ground_truth': d['ground_truth']}})) for d in open('{cfg.DATASET_FILE}')]\" > {cfg.NOISE_DATASET_FILE}")
        return None

    # 加载数据集
    print("\n📂 加载数据集...")
    samples = load_dataset(cfg.NOISE_DATASET_FILE, cfg.SAMPLE_LIMIT)
    print(f"   加载 {len(samples)} 条样本")
    
    # 评测每个样本
    print("\n🔄 开始噪声鲁棒性评测...")
    all_results = []
    
    for i, sample in enumerate(samples):
        print(f"\n  [{i+1}/{len(samples)}] 评测样本...")
        result = evaluate_noise_robustness(sample)
        all_results.append(result)
        
        # 显示中间结果
        score = result["metrics"].get("robustness_score", 0)
        passed = result["metrics"].get("passed", False)
        status = "✅" if passed else "❌"
        print(f"    鲁棒性评分: {score:.3f} {status}")
    
    # 计算总体统计
    print("\n📊 计算总体统计...")
    total_scores = [r["metrics"].get("robustness_score", 0) for r in all_results]
    passed_count = sum(1 for r in all_results if r["metrics"].get("passed", False))
    
    summary = {
        "model": cfg.MODEL_NAME,
        "noise_types": cfg.NOISE_TYPES,
        "noise_intensity": cfg.NOISE_INTENSITY,
        "total_samples": len(all_results),
        "passed_samples": passed_count,
        "pass_rate": passed_count / len(all_results) if all_results else 0,
        "avg_robustness_score": sum(total_scores) / len(total_scores) if total_scores else 0,
        "min_robustness_score": min(total_scores) if total_scores else 0,
        "max_robustness_score": max(total_scores) if total_scores else 0,
        "timestamp": datetime.now().isoformat(),
    }
    
    # 保存结果
    output_dir = cfg.OUTPUT_DIR / "noise_robustness"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 详细结果
    results_file = output_dir / "noise_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(
            convert_to_serializable({
                "summary": summary,
                "details": all_results,
            }),
            f, ensure_ascii=False, indent=2
        )
    print(f"\n✅ 详细结果已保存: {results_file}")
    
    # 可读报告
    report_file = output_dir / "noise_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("噪声鲁棒性评测报告\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"模型: {cfg.MODEL_NAME}\n")
        f.write(f"噪声类型: {', '.join(cfg.NOISE_TYPES)}\n")
        f.write(f"噪声强度: {cfg.NOISE_INTENSITY}\n")
        f.write(f"评测时间: {summary['timestamp']}\n\n")
        f.write("-" * 70 + "\n")
        f.write("总体统计\n")
        f.write("-" * 70 + "\n")
        f.write(f"总样本数: {summary['total_samples']}\n")
        f.write(f"通过样本数: {summary['passed_samples']}\n")
        f.write(f"通过率: {summary['pass_rate']:.2%}\n")
        f.write(f"平均鲁棒性评分: {summary['avg_robustness_score']:.3f}\n")
        f.write(f"最低鲁棒性评分: {summary['min_robustness_score']:.3f}\n")
        f.write(f"最高鲁棒性评分: {summary['max_robustness_score']:.3f}\n\n")
        f.write("-" * 70 + "\n")
        f.write("各样本详情\n")
        f.write("-" * 70 + "\n")
        
        for i, result in enumerate(all_results):
            f.write(f"\n样本 {i+1}:\n")
            f.write(f"  原问题: {result['original_question'][:50]}...\n")
            f.write(f"  基线答案: {result.get('baseline_answer', '')[:50]}...\n")
            f.write(f"  鲁棒性评分: {result['metrics'].get('robustness_score', 0):.3f}\n")
            f.write(f"  通过: {'是' if result['metrics'].get('passed', False) else '否'}\n")
            
            for noise_type, type_results in result.get("noise_results", {}).items():
                f.write(f"\n  [{noise_type}] 噪声变体:\n")
                for j, tr in enumerate(type_results):
                    f.write(f"    变体{j+1}: {tr['noisy_question'][:40]}...\n")
                    f.write(f"    相似度: {tr['similarity']:.3f}\n")
    
    print(f"✅ 可读报告已保存: {report_file}")
    
    # 打印摘要
    print("\n" + "=" * 70)
    print("评测完成！")
    print("=" * 70)
    print(f"通过率: {summary['pass_rate']:.2%}")
    print(f"平均鲁棒性评分: {summary['avg_robustness_score']:.3f}")
    print(f"阈值: {cfg.SIMILARITY_THRESHOLD}")
    print("=" * 70)
    
    return summary


def main():
    """主入口"""
    if not cfg.ENABLE_NOISE_ROBUSTNESS:
        print("噪声鲁棒性评测已禁用（ENABLE_NOISE_ROBUSTNESS = False）")
        return
    
    # 检查依赖
    try:
        import numpy
        import requests
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请安装: pip install numpy requests")
        sys.exit(1)
    
    run_evaluation()


if __name__ == "__main__":
    main()