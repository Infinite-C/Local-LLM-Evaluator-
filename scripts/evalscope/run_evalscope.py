#!/usr/bin/env python3
import subprocess
import yaml
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/evalscope/
PROJECT_ROOT = SCRIPT_DIR.parents[1]  # Intern_CMW/
RAW_DIR = PROJECT_ROOT / "results" / "evalscope_raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def safe_name(name):
    return name.replace(":", "_").replace("/", "_")

def run_evalscope(model, task):
    model_name = model["name"]
    dataset = task["dataset"]
    task_name = task["name"]
    limit = task["limit"]

    output_dir = RAW_DIR / safe_name(model_name) / task_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # ========== 构建 dataset_args ==========
    dataset_args = {}
    
    # 优先使用任务中显式定义的 dataset_args（支持 local_path、subset_list、字段映射等）
    if "dataset_args" in task and task["dataset_args"] is not None:
        dataset_args = task["dataset_args"]
    else:
        # 兼容旧的写法：如果只有 subset_list，则生成简单的 dataset_args
        if "subset_list" in task:
            dataset_args[dataset] = {"subset_list": task["subset_list"]}
    
    # 针对 gsm8k 和 ifeval 的特殊过滤（移除 内的内容）
    if dataset in ("gsm8k", "ifeval"):
        # 确保该数据集的配置存在
        if dataset not in dataset_args:
            dataset_args[dataset] = {}
        dataset_args[dataset]["filters"] = {"remove_until": "</think>"}

    # ========== 生成配置 ==========
    
    task_type = task.get("task_type", "")

    # 如果任务配置了自定义 generation_config，优先使用
    if "generation_config" in task:
        gen_config = json.dumps(task["generation_config"])
    elif dataset == "ifeval":
        gen_config = '{"temperature": 0, "max_tokens": 32768}'
    elif task_type == "multiple_choice":
    # 选择题：只需要输出选项字母，限制极短
        gen_config = '{"temperature": 0, "max_tokens": 2048}'
    elif task_type == "math":
    # 数学题：需要一定长度推导
        gen_config = '{"temperature": 0, "max_tokens": 8192}'
    elif task_type == "code":
    # 代码题：需要较长输出
        gen_config = '{"temperature": 0, "max_tokens": 16384}'
    elif task_type == "instruction_following":
        gen_config = '{"temperature": 0, "max_tokens": 8192}'
    else:
        gen_config = '{"temperature": 0, "max_tokens": 8192}'
        

    # ========== 构建命令 ==========
    cmd = [
        "evalscope", "eval",
        "--model", model_name,
        "--api-url", model["api_base"],
        "--api-key", model.get("api_key", "ollama"),
        "--eval-type", "openai_api",
        "--datasets", dataset,
        "--limit", str(limit),
        "--work-dir", str(output_dir)
    ]

    if dataset_args:
        cmd += ["--dataset-args", json.dumps(dataset_args)]
    
    cmd += ["--generation-config", gen_config]

    # 裁判模型
    if task.get("need_judge_model", False):
        if "judge_model_args" not in task:
            print(f"⚠️ 任务 {task_name} 需要裁判模型但未配置 judge_model_args，跳过")
            return
        judge_args = task["judge_model_args"]
        cmd += ["--judge-model-args", json.dumps(judge_args)]

    # 针对 humaneval 任务启用沙箱
    if dataset == "humaneval":
        cmd += ["--use-sandbox", "--sandbox-type", "docker"]

    print(f"\n[执行] {model_name} - {task['display_name']} ({dataset})")
    print("命令:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, timeout=None)
        print(f"[完成] {model_name} - {task_name}")
    except Exception as e:
        print(f"[失败] {model_name} - {task_name}: {e}")

def main():
    models = [m for m in load_yaml(SCRIPT_DIR / "configs" / "models.yaml")["models"] if m.get("enabled", True)]
    tasks = [t for t in load_yaml(SCRIPT_DIR / "configs" / "eval_tasks.yaml")["tasks"] if t.get("enabled", True)]

    for model in models:
        for task in tasks:
            run_evalscope(model, task)

if __name__ == "__main__":
    main()