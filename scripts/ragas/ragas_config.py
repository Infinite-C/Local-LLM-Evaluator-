#!/usr/bin/env python3
"""
RAGAS RAG 评测配置文件
修改这里即可切换模型、数据集、评测指标等
"""
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
#  🤖 模型配置
# ═══════════════════════════════════════════════════════════════

# 被测模型（Ollama 模型名）
MODEL_NAME = "qwen3.5:9b"

# Ollama API 地址
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

# ═══════════════════════════════════════════════════════════════
#  📊 评测指标配置
# ═══════════════════════════════════════════════════════════════

# 启用的 RAGAS 指标
# 可选: context_relevancy, context_precision, context_recall, answer_relevancy
ENABLED_METRICS = [
    "context_relevancy",      # 检索内容是否与用户问题相关
    "context_precision",      # 检索内容中有效证据占比
    "context_recall",         # 关键证据是否被检索出来
    "context_entities_recall", # 关键实体、事实、名称是否被检索覆盖
    # "answer_relevancy",     # RAG 生成答案是否回应用户问题（注释掉）
]

# ═══════════════════════════════════════════════════════════════
#  📁 数据集配置
# ═══════════════════════════════════════════════════════════════

# 脚本所在目录
SCRIPT_DIR = Path(__file__).resolve().parents[0]

# 数据集目录
DATASET_DIR = SCRIPT_DIR / "dataset"

# 数据集文件（JSONL 格式）
# 格式: {"question": "问题", "contexts": ["检索文档1", "检索文档2"], "answer": "生成答案", "ground_truth": "标准答案"}
DATASET_FILE = DATASET_DIR / "rag_eval_sample.jsonl"

# 噪声鲁棒性评测专用数据集（只需要 question 和 ground_truth）
# 格式: {"question": "问题", "ground_truth": "标准答案"}
NOISE_DATASET_FILE = DATASET_DIR / "noise_eval_sample.jsonl"

# ═══════════════════════════════════════════════════════════════
#  📂 输出配置
# ═══════════════════════════════════════════════════════════════

# 项目根目录（scripts 的上级）
PROJECT_ROOT = SCRIPT_DIR.parents[1]

# 输出目录（统一放在项目根目录的 results/ragas/{model_name}/ 下）
# 模型名中的特殊字符（如 . 和 :）替换为下划线
MODEL_DIR_NAME = MODEL_NAME.replace(".", "_").replace(":", "_")
OUTPUT_DIR = PROJECT_ROOT / "results" / "ragas" / MODEL_DIR_NAME

# ═══════════════════════════════════════════════════════════════
#  ⚙️ 评测参数
# ═══════════════════════════════════════════════════════════════

# 样本数量限制（0 表示全部）
SAMPLE_LIMIT = 0

# 是否使用 Ollama 作为 RAGAS 的 LLM 后端
# True: 使用 Ollama
# False: 使用 RAGAS 默认的 OpenAI API（需要设置 OPENAI_API_KEY）
USE_OLLAMA_BACKEND = True

# Ollama 评测模型（用于 RAGAS 内部评分）
RAGAS_JUDGE_MODEL = "qwen3:32b"

# Ollama Embedding 模型（用于 RAGAS 的向量计算）
EMBEDDING_MODEL = "bge-m3:latest"

# ═══════════════════════════════════════════════════════════════
#  ⏱️ 超时配置
# ═══════════════════════════════════════════════════════════════

# LLM 调用超时时间（秒）
# RAGAS 评测每个样本需要多次 LLM 调用，建议设置较长时间
LLM_TIMEOUT = 600  # 10分钟（qwen3:32b 推理慢，需要更长超时）

# 单个请求超时时间（秒）
REQUEST_TIMEOUT = 300  # 5分钟

# RAGAS 评测结果解析超时（秒）
# 由于 RAGAS 会并发执行多个任务，可能需要等待较长时间
RAGAS_TIMEOUT = 3600  # 60分钟（总超时）

# RAGAS 内部并发 worker 数量
# 本地 Ollama 推理能力有限，并发太高会导致超时
# 建议: 1（最稳定）~ 3（稍快但可能超时）
RAGAS_MAX_WORKERS = 1

# ═══════════════════════════════════════════════════════════════
#  🔊 噪声鲁棒性评测配置
# ═══════════════════════════════════════════════════════════════

# 是否启用噪声鲁棒性评测
ENABLE_NOISE_ROBUSTNESS = True

# 噪声扰动类型（可多选）
# 可选: typo, synonym, insert, delete, swap, keyboard
NOISE_TYPES = [
    "typo",       # 拼写错误（字符替换）
    "synonym",    # 同义词替换
    "insert",     # 随机插入字符/词
    "delete",     # 随机删除字符/词
]

# 噪声强度（每个样本应用的扰动次数）
NOISE_INTENSITY = 3

# 每种噪声类型生成的变体数量
NOISE_VARIANTS_PER_TYPE = 2

# 噪声评测指标
# 可选: accuracy_drop, semantic_similarity, answer_consistency
NOISE_METRICS = [
    "accuracy_drop",         # 准确率下降幅度
    "semantic_similarity",   # 语义相似度（与原答案对比）
    "answer_consistency",    # 答案一致性（多次扰动答案是否一致）
]

# 语义相似度阈值（低于此值视为严重退化）
SIMILARITY_THRESHOLD = 0.7
