#!/usr/bin/env python3
"""
从 RAGAS 数据集提取噪声评测数据集

噪声评测只需要 question 和 ground_truth，不需要 contexts 和 answer

用法:
    python prepare_noise_dataset.py
    
输出:
    noise_eval_sample.jsonl
"""
import json
from pathlib import Path

# 路径配置
SCRIPT_DIR = Path(__file__).resolve().parents[0]
RAGAS_DATASET = SCRIPT_DIR / "rag_eval_sample.jsonl"
NOISE_DATASET = SCRIPT_DIR / "noise_eval_sample.jsonl"


def extract_for_noise_eval(input_file: Path, output_file: Path):
    """从 RAGAS 数据集提取噪声评测所需字段"""
    print(f"📂 读取 RAGAS 数据集: {input_file}")
    
    samples = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line.strip())
            # 只保留噪声评测需要的字段
            noise_sample = {
                "question": item.get("question", ""),
                "ground_truth": item.get("ground_truth", ""),
            }
            samples.append(noise_sample)
    
    print(f"   提取 {len(samples)} 条样本")
    
    # 保存噪声评测数据集
    print(f"💾 保存噪声评测数据集: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')
    
    print(f"✅ 完成！")
    print(f"\n噪声评测数据集格式示例:")
    print(json.dumps(samples[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if not RAGAS_DATASET.exists():
        print(f"❌ RAGAS 数据集不存在: {RAGAS_DATASET}")
        exit(1)
    
    extract_for_noise_eval(RAGAS_DATASET, NOISE_DATASET)
