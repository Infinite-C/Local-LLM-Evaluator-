#!/usr/bin/env python3
"""
安全治理能力评测配置文件
修改这里即可切换模型、评测维度、探针类型等

基于 garak (NVIDIA) 框架进行安全评测
"""
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
#  🤖 模型配置
# ═══════════════════════════════════════════════════════════════

# 被测模型名称（Ollama 模型名）
MODEL_NAME = "qwen3.5:9b"

# Ollama API 地址
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

# ═══════════════════════════════════════════════════════════════
#  🛡️ 评测维度配置
# ═══════════════════════════════════════════════════════════════

# 启用的安全评测维度
ENABLED_DIMENSIONS = {
    "prompt_injection": {
        "enabled": True,
        "description": "提示词注入 - 是否被恶意提示改变行为或泄露信息",
        "probes": ["promptinject", "encoding"],
        "detector": "same_as_prompt",
    },
    "jailbreak": {
        "enabled": True,
        "description": "越狱抵抗 - 是否被诱导绕过安全限制",
        "probes": ["dan"],
        "detector": "same_as_prompt",
    },
    "toxicity": {
        "enabled": True,
        "description": "毒性输出 - 是否输出攻击性、辱骂性、有害内容",
        "probes": ["realtoxicityprompts", "continuation"],
        "detector": "toxicity",
    },
    "bias": {
        "enabled": True,
        "description": "偏见输出 - 是否涉及性别、年龄、地域、职业等偏见",
        "probes": ["lmrc"],
        "detector": "same_as_prompt",
    },
    "misinformation": {
        "enabled": True,
        "description": "错误信息与误导 - 是否生成错误、误导性或过度自信的信息",
        "probes": ["misleading", "snowball"],
        "detector": "same_as_prompt",
    },
    "data_leakage": {
        "enabled": True,
        "description": "敏感信息泄露 - 是否泄露隐私、密钥、系统提示、内部数据",
        "probes": ["leakreplay"],
        "detector": "same_as_prompt",
    },
    "malware": {
        "enabled": True,
        "description": "滥用风险 - 是否协助生成恶意代码或有害工具",
        "probes": ["malwaregen"],
        "detector": "same_as_prompt",
    },
    "xss": {
        "enabled": True,
        "description": "不安全输出处理 - 输出是否可能被下游系统误执行（XSS/SQL注入/命令注入）",
        "probes": [],  # 使用自定义测试集
        "detector": "same_as_prompt",
    },
    # ═══════════════════════════════════════════════════════════════
    #  新增维度（需要自定义评测脚本）
    # ═══════════════════════════════════════════════════════════════
    "vector_embedding_risk": {
        "enabled": True,
        "description": "向量与嵌入风险 - RAG向量库是否存在越权检索、污染或泄露风险",
        "probes": [],  # 需要自定义脚本测试
        "eval_type": "script",  # 标记为脚本评测
        "script": "vector_risk_test.py",
    },
    "supply_chain_risk": {
        "enabled": True,
        "description": "供应链风险 - 模型、数据、插件、工具链是否存在供应链安全问题",
        "probes": [],  # 需要自定义脚本测试
        "eval_type": "script",  # 标记为脚本评测
        "script": "supply_chain_check.py",
    },
    "data_model_poisoning": {
        "enabled": True,
        "description": "数据与模型投毒 - 训练、微调、知识库或检索数据是否被污染",
        "probes": [],  # 使用自定义测试集
        "detector": "same_as_prompt",
    },
}

# ═══════════════════════════════════════════════════════════════
#  📁 数据集配置
# ═══════════════════════════════════════════════════════════════

# 脚本所在目录
SCRIPT_DIR = Path(__file__).resolve().parents[0]

# 数据集目录
DATASET_DIR = SCRIPT_DIR / "dataset"

# 自定义安全评测数据集（JSONL 格式）
# 格式: {"dimension": "prompt_injection", "prompt": "...", "expected_behavior": "refuse"}
# 可用数据集:
#   - safety_eval_sample.jsonl (原始数据集，每个维度约3-4条)
#   - safety_eval_extended.jsonl (扩展数据集，每个维度50条，共9维度450条)
#   - safety_eval_advanced.jsonl (高级数据集，难度分级：基础30%+进阶40%+专家30%，共5维度250条)
#
# 数据集选择建议：
#   - 快速测试: safety_eval_sample.jsonl
#   - 全面评测: safety_eval_extended.jsonl
#   - 深度安全测试: safety_eval_advanced.jsonl (更复杂的攻击样本)
# 只测新维度时，使用 advanced 数据集（包含 data_model_poisoning）
CUSTOM_DATASET_FILE = DATASET_DIR / "safety_eval_advanced.jsonl"

# ═══════════════════════════════════════════════════════════════
#  📂 输出配置
# ═══════════════════════════════════════════════════════════════

# 项目根目录
PROJECT_ROOT = SCRIPT_DIR.parents[1]

# 输出目录（按模型名分目录，与 ragas 保持一致）
# 模型名中的特殊字符（如 . 和 :）替换为下划线
MODEL_DIR_NAME = MODEL_NAME.replace(".", "_").replace(":", "_")
OUTPUT_DIR = PROJECT_ROOT / "results" / "safety" / MODEL_DIR_NAME

# ═══════════════════════════════════════════════════════════════
#  ⚙️ 评测参数
# ═══════════════════════════════════════════════════════════════

# 样本数量限制（0 表示全部）
SAMPLE_LIMIT = 0

# 每个探针的生成次数（garak 默认 10 次）
GENERATIONS_PER_PROBE = 5

# 请求超时时间（秒）
REQUEST_TIMEOUT = 300

# 评测模式
# "garak": 使用 garak 框架（需要 pip install garak）
# "custom": 使用自定义 LLM-as-Judge 评测（使用 Ollama）
EVAL_MODE = "custom"

# 裁判模型（用于 LLM-as-Judge 模式）
JUDGE_MODEL = "qwen3:32b"

# 生成温度
TEMPERATURE = 0.0
