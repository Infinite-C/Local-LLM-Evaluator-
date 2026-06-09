#!/usr/bin/env python3
"""
评测配置文件 - 统一配置入口
修改这里即可切换数据集、模型、评测任务类型等

支持的任务类型（TASK_TYPE）：
- summary: 摘要质量评估
- answer_relevancy: 答案相关性评估
- translation: 机器翻译质量评估
- faithfulness: 事实一致性评估
- contextual_relevancy: 上下文相关性评估
"""
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
#  ⚙️ 核心配置（修改这里即可切换任务）
# ═══════════════════════════════════════════════════════════════

# 评测任务类型（设为 "auto" 则根据数据集文件名自动识别）
# 手动可选: summary, answer_relevancy, translation, faithfulness, contextual_relevancy
TASK_TYPE = "auto"

# 评估维度名称（设为 "auto" 则与自动识别的 TASK_TYPE 保持一致）
EVAL_DIMENSION = "auto"

# ═══════════════════════════════════════════════════════════════
#  📁 数据集配置
# ═══════════════════════════════════════════════════════════════

# 从 eval_config.py 的位置精确计算各级目录
# __file__  = /data/chenweihang/Intern_CMW/scripts/deepeval/eval_config.py
# .parents[0] = /data/chenweihang/Intern_CMW/scripts/deepeval  (SCRIPT_DIR)
# .parents[1] = /data/chenweihang/Intern_CMW/scripts            (SCRIPTS_DIR)
# .parents[2] = /data/chenweihang/Intern_CMW                    (PROJECT_ROOT)
_FILE_PATH = Path(__file__).resolve()
SCRIPT_DIR = _FILE_PATH.parents[0]       # scripts/deepeval/
PROJECT_ROOT = _FILE_PATH.parents[2]     # Intern_CMW/

# 数据集根目录
DATASET_ROOT = SCRIPT_DIR / "dataset"

# ── 方式一：读取单个文件 ──
# 数据集文件名（单独一个文件时使用）
DATASET_NAME = "my_summary_set.jsonl"

# 完整数据集路径（当 DATASET_DIR 为 None 时使用）
DATASET_PATH = DATASET_ROOT / DATASET_NAME

# ── 方式二：读取单个目录 ──
# 设置为目录路径，程序会自动读取目录下所有 .jsonl 文件并合并
# 设置为 None 则使用 DATASET_PATH 单文件模式
DATASET_DIR = None   # 例如: Path("/data/chenweihang/Intern_CMW/dataset/answer_relevancy_datasets")

# ── 方式三：读取多个目录（批量评测） ──
# 设置为目录路径列表，程序会依次评测每个目录，每个目录输出一个结果
# 设置为空列表 [] 则使用 DATASET_DIR 或 DATASET_PATH 模式
DATASET_DIRS = []    # 例如: [Path(".../dataset1"), Path(".../dataset2")]

# ── 方式四：智能批量评测（混合模式） ──
# 指定一个父目录，程序会自动扫描其下的所有子目录：
# - 如果子目录下有多个 .jsonl 文件 → 合并评测（输出到该子目录名）
# - 如果子目录下只有1个 .jsonl 文件 → 单独评测（输出到该子目录名）
# 设置为空列表 [] 则禁用此模式
DATASET_BATCH_DIRS = [Path("/data/chenweihang/Intern_CMW/dataset")]

# 评测样本数量（设为 0 表示使用全部数据）
SAMPLE_LIMIT = 0

# ═══════════════════════════════════════════════════════════════
#  🤖 模型配置
# ═══════════════════════════════════════════════════════════════

# 生成模型（用于生成摘要/回答/翻译的模型）
GENERATION_MODEL = "qwen3.5:4b"

# 裁判模型（用于评估生成结果质量的模型）
JUDGE_MODEL = "qwen3:32b"

# Ollama API 地址（一般不需要修改）
OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"

# ═══════════════════════════════════════════════════════════════
#  📂 输出配置
# ═══════════════════════════════════════════════════════════════

# 输出根目录（固定为项目根目录下的 results/deepeval/）
# 例如: /data/chenweihang/Intern_CMW/results/deepeval
# （PROJECT_ROOT 已在文件顶部定义，从 __file__ 精确计算）
OUTPUT_ROOT = PROJECT_ROOT / "results" / "deepeval"

# 输出目录自动生成为：OUTPUT_ROOT / GENERATION_MODEL / EVAL_DIMENSION
# 例如：/data/chenweihang/Intern_CMW/results/deepeval/qwen3.5:9b/summary_quality/

# ═══════════════════════════════════════════════════════════════
#  🔧 高级配置
# ═══════════════════════════════════════════════════════════════

# API 请求超时时间（秒）
API_TIMEOUT = 120

# 生成摘要的温度参数（0.0-1.0，越低越确定性）
GENERATION_TEMPERATURE = 0.3

# 评估的温度参数（建议设为 0.0 保证稳定性）
JUDGE_TEMPERATURE = 0.0

# 最大生成 token 数
MAX_TOKENS_GENERATION = 8192
MAX_TOKENS_JUDGE = 16384

# 是否在生成失败时重试
ENABLE_RETRY = True

# 重试时使用的简化 prompt（通用，适用于所有任务类型）
RETRY_PROMPT = "请处理以下内容：\n\n{input_text}\n\n结果："
RETRY_SYSTEM_MSG = "直接输出结果，不要解释。"

# ═══════════════════════════════════════════════════════════════
#  📋 快速配置示例（复制到上方对应位置即可使用）
# ═══════════════════════════════════════════════════════════════

# 示例1：摘要质量评估
# TASK_TYPE = "summary"
# EVAL_DIMENSION = "summary_quality"
# DATASET_NAME = "my_summary_set.jsonl"

# 示例2：答案相关性评估
# TASK_TYPE = "answer_relevancy"
# EVAL_DIMENSION = "answer_relevancy"
# DATASET_NAME = "qa_dataset.jsonl"

# 示例3：机器翻译评估（英译中）
# TASK_TYPE = "translation"
# EVAL_DIMENSION = "translation_en_zh"
# DATASET_NAME = "translation_test_50.jsonl"

# 示例4：事实一致性评估
# TASK_TYPE = "faithfulness"
# EVAL_DIMENSION = "faithfulness"
# DATASET_NAME = "faithfulness_test_50.jsonl"

# 示例5：上下文相关性评估
# TASK_TYPE = "contextual_relevancy"
# EVAL_DIMENSION = "contextual_relevancy"
# DATASET_NAME = "rag_dataset.jsonl"

# 示例6：使用更大的模型
# GENERATION_MODEL = "qwen3:32b"
# JUDGE_MODEL = "qwen3:72b"
