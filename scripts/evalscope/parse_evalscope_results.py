#!/usr/bin/env python3
"""
Parse EvalScope evaluation results into normalized scores.
Supports all datasets defined in eval_tasks.yaml
"""
import json
import re
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "results" / "evalscope_raw"
NORM = BASE / "results" / "normalized"
NORM.mkdir(parents=True, exist_ok=True)


def clean(text):
    """Clean model output by removing thinking tags and filler words."""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'^(?:嗯|首先|接下来|好的|让我想想).*?(?=答案|最终|选|所以|Answer)', '', text, flags=re.DOTALL)
    return text


# ==================== Extraction Functions ====================

def extract_mc(text):
    """Extract multiple choice answer (A-D) from text."""
    cleaned = clean(text)
    patterns = [
        r'答案[：:]\s*([A-D])',
        r'最终答案[：:]\s*([A-D])',
        r'正确答案[：:]\s*([A-D])',
        r'所以\s*选\s*([A-D])',
        r'选([A-D])',
        r'Answer\s*:\s*([A-D])',
        r'ANSWER\s*:\s*([A-D])',
        r'\b([A-D])\b\s*是正确的',
        r'\b([A-D])\b(?!.*[A-D])'
    ]
    for pat in patterns:
        matches = list(re.finditer(pat, cleaned, re.IGNORECASE))
        if matches:
            return matches[-1].group(1).upper()
    letters = re.findall(r'\b([A-D])\b', cleaned)
    return letters[-1].upper() if letters else ""


def extract_math(text):
    """Extract numeric answer from math problems."""
    cleaned = clean(text)
    boxed = re.search(r'\\boxed\{([\d.]+)\}', cleaned)
    if boxed:
        return boxed.group(1)
    patterns = [
        r'答案[：:]\s*([\d.]+)',
        r'最终答案[：:]\s*([\d.]+)',
        r'Answer\s*:\s*([\d.]+)',
        r'结果为\s*([\d.]+)',
        r'等于\s*([\d.]+)'
    ]
    for pat in patterns:
        matches = list(re.finditer(pat, cleaned, re.IGNORECASE))
        if matches:
            return matches[-1].group(1)
    nums = re.findall(r'\b(\d+\.?\d*)\b', cleaned)
    return nums[-1] if nums else ""


def extract_code(text):
    """Extract code completion from model output (for HumanEval)."""
    # HumanEval uses pass@k metric from EvalScope, we keep raw output
    return text.strip()


def extract_generation(text):
    """For generation tasks (BBH, CoNLL2003, LongBench, etc.), keep raw output."""
    return text.strip()


def extract_ifeval(text):
    """IFEval is evaluated by EvalScope internally, keep raw output."""
    return text.strip()


def extract_truthfulqa(text):
    """Extract answer for TruthfulQA (multiple choice format)."""
    cleaned = clean(text)
    # Try to extract letter answer first
    letters = re.findall(r'\b([A-D])\b', cleaned)
    if letters:
        return letters[-1].upper()
    # Try to extract "True" or "False"
    if re.search(r'\b(true|yes|correct)\b', cleaned, re.IGNORECASE):
        return "True"
    if re.search(r'\b(false|no|incorrect)\b', cleaned, re.IGNORECASE):
        return "False"
    return cleaned[:100]  # Return truncated text if no clear answer


# ==================== Target Normalization ====================

def normalize_target(target, dataset):
    """Normalize reference answer based on dataset type."""
    if dataset in ('mmlu', 'ceval', 'hellaswag', 'race'):
        return target.strip()[0] if target else ""
    elif dataset in ('gsm8k', 'mgsm'):
        m = re.search(r'(\d+\.?\d*)', str(target))
        return m.group(1) if m else target.strip()
    elif dataset == 'truthfulqa':
        # TruthfulQA uses mc2 metric, target is usually a letter or boolean
        return target.strip()
    else:
        return target.strip()


# ==================== Dataset Detection ====================

def detect_dataset(fname):
    """
    Detect dataset type from filename.
    Returns (dataset_type, extraction_function) or (None, None) if unsupported.
    """
    # Multiple choice datasets
    if fname.startswith("mmlu_"):
        return "mmlu", extract_mc
    elif fname.startswith("ceval_"):
        return "ceval", extract_mc
    elif fname.startswith("hellaswag_"):
        return "hellaswag", extract_mc
    elif fname.startswith("race_"):
        return "race", extract_mc
    elif fname.startswith("truthful_qa_"):
        return "truthfulqa", extract_truthfulqa
    
    # Math datasets
    elif fname == "gsm8k_main":
        return "gsm8k", extract_math
    elif fname.startswith("mgsm_"):
        return "mgsm", extract_math
    
    # Code datasets
    elif fname.startswith("humaneval_"):
        return "humaneval", extract_code
    
    # Instruction following
    elif fname.startswith("ifeval_"):
        return "ifeval", extract_ifeval
    
    # Generation tasks (BBH, CoNLL2003, LongBench, etc.)
    elif fname.startswith("bbh_"):
        return "bbh", extract_generation
    elif fname.startswith("conll2003_"):
        return "conll2003", extract_generation
    elif fname.startswith("longbench_v2_"):
        return "longbench_v2", extract_generation
    elif fname.startswith("alpaca_eval_"):
        return "alpaca_eval", extract_generation
    elif fname.startswith("drop_"):
        return "drop", extract_generation
    elif fname.startswith("multi_if_"):
        return "multi_if", extract_generation
    elif fname.startswith("tau2_bench_"):
        return "tau2_bench", extract_generation
    elif fname.startswith("hle_"):
        return "hle", extract_generation
    elif fname.startswith("civilcomments_") or fname.startswith("bias_"):
        return "bias", extract_generation
    
    # Custom datasets (general_qa pattern)
    elif any(x in fname for x in ['squad_', 'nq_', 'rag_', 'multilingual_', 'my_summary_set']):
        return "custom", extract_generation
    
    else:
        return None, None


# ==================== Model Output Extraction ====================

def get_model_output(data):
    """Extract model output from EvalScope result format."""
    if 'prediction' in data and data['prediction']:
        return data['prediction']
    if 'model_output' in data:
        mo = data['model_output']
        if 'choices' in mo and mo['choices']:
            msg = mo['choices'][0].get('message', {})
            content = msg.get('content')
            if isinstance(content, list):
                for item in content:
                    if item.get('type') == 'text':
                        return item.get('text', '')
            elif isinstance(content, str):
                return content
    return ""


# ==================== File Processing ====================

def process_file(file_path):
    """
    Process a single prediction file.
    Returns (key, accuracy, total, correct, parse_rate, samples) or None.
    """
    parts = file_path.parts
    try:
        pred_idx = parts.index('predictions')
        model_name = parts[pred_idx + 1]
        task_name = parts[pred_idx - 1]
    except (ValueError, IndexError):
        return None

    fname = file_path.stem
    dataset, extract_func = detect_dataset(fname)
    
    if dataset is None:
        print(f"[跳过] 不支持的数据集: {fname}")
        return None

    total = 0
    correct = 0
    parse_ok = 0
    samples = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            total += 1
            raw = get_model_output(data)
            target = data.get('target', '')
            
            # Extract answer using dataset-specific function
            extracted = extract_func(raw)
            norm = normalize_target(target, dataset)
            
            # For generation tasks without simple string matching, 
            # we consider it "parsed" if we got some output
            is_generation = dataset in ['bbh', 'conll2003', 'longbench_v2', 'humaneval', 
                                         'alpaca_eval', 'drop', 'multi_if', 'tau2_bench',
                                         'hle', 'bias', 'custom']
            
            if is_generation:
                # For generation tasks, use EvalScope's built-in judgment if available
                is_correct = data.get('judgment', False) if 'judgment' in data else False
                # If no judgment, check if extracted matches target (for simple cases)
                if not is_correct and extracted and norm:
                    is_correct = (extracted.lower() == norm.lower())
            else:
                is_correct = (extracted == norm) if extracted else False
            
            if is_correct:
                correct += 1
            if extracted or is_generation:
                parse_ok += 1
                
            samples.append({
                "model": model_name,
                "dataset": task_name,
                "dimension": task_name,
                "sample_id": f"{task_name}_{data.get('idx', total)}",
                "question": data.get('prompt', '')[:500],
                "raw_output": raw[:2000],
                "cleaned_output": raw,
                "extracted_answer": extracted,
                "reference_answer": norm,
                "is_correct": is_correct,
                "score": 1.0 if is_correct else 0.0,
                "parse_status": "success" if (extracted or is_generation) else "failed",
                "error_type": "none" if (extracted or is_generation) else "parse_failed"
            })
    
    acc = correct / total if total else 0
    parse_rate = parse_ok / total if total else 0
    return (model_name, task_name), acc, total, correct, parse_rate, samples


# ==================== Main ====================

def main():
    """Main entry point: process all prediction files and generate reports."""
    agg = defaultdict(lambda: {"total": 0, "correct": 0, "parse_success": 0, "samples": []})
    skipped = []
    
    for jsonl in RAW.rglob("*.jsonl"):
        if "reviews" in jsonl.parts:
            continue
        result = process_file(jsonl)
        if result is None:
            skipped.append(jsonl.name)
            continue
        key, acc, total, correct, parse_rate, samples = result
        agg[key]["total"] += total
        agg[key]["correct"] += correct
        agg[key]["parse_success"] += int(parse_rate * total)
        agg[key]["samples"].extend(samples)
        print(f"处理 {key[0]} / {key[1]} (来自 {jsonl.parent.name}/{jsonl.name})")

    if not agg:
        print("未找到任何预测文件！请确认 results/evalscope_raw 下存在 .jsonl 文件。")
        return

    if skipped:
        print(f"\n[注意] 跳过了 {len(skipped)} 个不支持的文件")

    # Write scores.csv
    csv_path = NORM / "scores.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["model", "dataset", "dimension", "metric", "score", "total", 
                        "correct", "parse_success_rate", "format_error_rate", 
                        "timeout_rate", "ambiguous_rate", "run_time", "source_file"])
        for (model_name, task_name), stats in agg.items():
            total = stats["total"]
            correct = stats["correct"]
            acc = correct / total if total else 0
            parse_rate = stats["parse_success"] / total if total else 0
            dimension = task_name
            writer.writerow([model_name, task_name, dimension, "acc", acc, total, 
                           correct, parse_rate, 0.0, 0.0, 0.0, 
                           datetime.now().isoformat(), "evalscope"])

    # Write sample_outputs.jsonl
    jsonl_path = NORM / "sample_outputs.jsonl"
    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for stats in agg.values():
            for sample in stats["samples"]:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')

    print(f"\n✅ 解析完成！")
    print(f"   scores.csv: {csv_path}")
    print(f"   sample_outputs.jsonl: {jsonl_path}")
    print(f"   共处理 {len(agg)} 个模型/数据集组合")


if __name__ == "__main__":
    main()
