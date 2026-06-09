#!/usr/bin/env python3
"""
评测任务 Prompt 模板库
定义各种评测任务的评估标准、prompt 模板和指标维度
"""
from typing import Dict, List, Any


# ═══════════════════════════════════════════════════════════════
#  任务配置定义
# ═══════════════════════════════════════════════════════════════

TASK_CONFIGS = {
    "summary": {
        "name": "摘要质量评估",
        "description": "评估生成摘要的信息完整性、简洁性、流畅性和准确性",
        "metrics": ["completeness", "conciseness", "fluency", "accuracy"],
        "metric_weights": {
            "completeness": 0.4,
            "conciseness": 0.2,
            "fluency": 0.2,
            "accuracy": 0.2
        },
        "prompt_template": """你是一个摘要质量评估专家。请根据原文和参考摘要，对生成的摘要评分（0-10分）。
评分标准：
- 信息完整性（40%）：是否涵盖原文关键信息
- 简洁性（20%）：是否无冗余
- 流畅性（20%）：语言是否通顺
- 准确性（20%）：是否有错误或曲解

只输出一个数字，不要输出任何解释或思考过程。

原文：{input_text}
参考摘要：{reference}
生成摘要：{generated}

分数：""",
        "system_msg": "你是一个评估助手。只输出0-10之间的一个数字，例如8.5。不要输出任何其他文字，包括思考过程。",
        "generation_prompt": "请用50-100字总结以下内容：\n\n{input_text}\n\n摘要：",
        "generation_system": "你是一个摘要助手，直接输出摘要，不要输出思考过程。"
    },
    
    "answer_relevancy": {
        "name": "答案相关性评估",
        "description": "评估回答是否与问题相关，是否准确回答了问题",
        "metrics": ["relevancy", "completeness", "accuracy", "helpfulness"],
        "metric_weights": {
            "relevancy": 0.4,
            "completeness": 0.2,
            "accuracy": 0.2,
            "helpfulness": 0.2
        },
        "prompt_template": """你是一个答案质量评估专家。请根据问题和参考答案，对生成的回答评分（0-10分）。
评分标准：
- 相关性（40%）：是否直接回答了问题，没有跑题
- 完整性（20%）：是否涵盖了问题的所有要点
- 准确性（20%）：信息是否正确无误
- 有帮助性（20%）：回答是否对用户有实际帮助

只输出一个数字，不要输出任何解释或思考过程。

问题：{input_text}
参考答案：{reference}
生成回答：{generated}

分数：""",
        "system_msg": "你是一个评估助手。只输出0-10之间的一个数字，例如8.5。不要输出任何其他文字，包括思考过程。",
        "generation_prompt": "请回答以下问题：\n\n{input_text}\n\n回答：",
        "generation_system": "你是一个问答助手，直接回答问题，不要输出思考过程。"
    },
    
    "translation": {
        "name": "机器翻译质量评估",
        "description": "评估翻译的准确性、流畅性、术语一致性和语法正确性",
        "metrics": ["accuracy", "fluency", "terminology", "grammar"],
        "metric_weights": {
            "accuracy": 0.4,
            "fluency": 0.3,
            "terminology": 0.2,
            "grammar": 0.1
        },
        "prompt_template": """你是一个机器翻译质量评估专家。请根据原文和参考译文，对机器翻译结果评分（0-10分）。
评分标准：
- 准确性（40%）：是否准确传达原文意思，无错译漏译
- 流畅性（30%）：译文是否自然通顺，符合目标语言习惯
- 术语一致性（20%）：专业术语翻译是否准确一致
- 语法正确性（10%）：是否存在语法错误

只输出一个数字，不要输出任何解释或思考过程。

原文：{input_text}
参考译文：{reference}
机器翻译结果：{generated}

分数：""",
        "system_msg": "你是一个评估助手。只输出0-10之间的一个数字，例如8.5。不要输出任何其他文字，包括思考过程。",
        "generation_prompt": "请将以下内容翻译成与原文不同的语言（如果原文是中文则翻译成英文，如果原文是英文则翻译成中文，如果是其他语言则翻译成英文）:\n\n{input_text}\n\n翻译:",
        "generation_system": "你是一个翻译助手，直接输出翻译结果，不要输出思考过程。"
    },
    
    "faithfulness": {
        "name": "事实一致性评估",
        "description": "评估生成内容是否忠实于原文，是否存在幻觉或错误信息",
        "metrics": ["factuality", "consistency", "no_hallucination", "completeness"],
        "metric_weights": {
            "factuality": 0.4,
            "consistency": 0.3,
            "no_hallucination": 0.2,
            "completeness": 0.1
        },
        "prompt_template": """你是一个事实一致性评估专家。请判断生成的摘要是否忠实于原文，是否存在错误或虚构的事实。
评分标准（0-10分）：
- 完全一致，无错误（9-10分）
- 基本一致，有轻微偏差（7-8分）
- 部分一致，存在错误（4-6分）
- 严重不一致，捏造事实（0-3分）

只输出一个数字。

原文：{input_text}
参考摘要：{reference}
生成摘要：{generated}

分数：""",
        "system_msg": "你是一个评估助手。只输出0-10之间的一个数字。不要输出任何其他文字。",
        "generation_prompt": "请仔细阅读以下内容，判断其中陈述的事实是否正确，并给出简要判断结论：\n\n{input_text}\n\n事实判断：",
        "generation_system": "你是一个事实核查助手。请基于常识和知识，逐一判断内容中的事实陈述是否正确，直接输出判断结论..."
    },
    
    "contextual_relevancy": {
        "name": "上下文相关性评估",
        "description": "评估回答是否充分利用了上下文信息",
        "metrics": ["context_usage", "relevancy", "completeness", "accuracy"],
        "metric_weights": {
            "context_usage": 0.4,
            "relevancy": 0.3,
            "completeness": 0.2,
            "accuracy": 0.1
        },
        "prompt_template": """你是一个上下文相关性评估专家。请评估生成的回答是否充分利用了上下文信息来回答问题。
评分标准（0-10分）：
- 上下文利用（40%）：是否充分使用了提供的上下文信息
- 相关性（30%）：回答是否与问题和上下文相关
- 完整性（20%）：是否涵盖了问题的所有要点
- 准确性（10%）：信息是否准确

只输出一个数字。

上下文：{input_text}
问题：{reference}
生成回答：{generated}

分数：""",
        "system_msg": "你是一个评估助手。只输出0-10之间的一个数字。不要输出任何其他文字。",
        "generation_prompt": "请根据以下上下文回答问题：\n\n上下文：{input_text}\n\n请回答上下文中的问题。",
        "generation_system": "你是一个问答助手，基于提供的上下文回答问题。"
    }
}


# ═══════════════════════════════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════════════════════════════

def get_task_config(task_type: str) -> Dict[str, Any]:
    """获取指定任务的配置"""
    if task_type not in TASK_CONFIGS:
        raise ValueError(f"未知的任务类型: {task_type}。支持的类型: {list(TASK_CONFIGS.keys())}")
    return TASK_CONFIGS[task_type]


def list_supported_tasks() -> List[str]:
    """列出所有支持的任务类型"""
    return list(TASK_CONFIGS.keys())


def get_task_info(task_type: str) -> Dict[str, str]:
    """获取任务的简要信息"""
    config = get_task_config(task_type)
    return {
        "name": config["name"],
        "description": config["description"],
        "metrics": ", ".join(config["metrics"])
    }


def print_all_tasks():
    """打印所有支持的任务类型"""
    print("=" * 70)
    print("支持的评测任务类型")
    print("=" * 70)
    for task_type, config in TASK_CONFIGS.items():
        print(f"\n【{task_type}】{config['name']}")
        print(f"  描述: {config['description']}")
        print(f"  评估维度: {', '.join(config['metrics'])}")
    print("=" * 70)


# ═══════════════════════════════════════════════════════════════
#  自动识别：根据数据集文件名/路径推断任务类型
# ═══════════════════════════════════════════════════════════════

# 文件名关键词 → 任务类型的映射（优先级从上到下）
_KEYWORD_TO_TASK = [
    ("faithfulness",          "faithfulness"),
    ("faithful",              "faithfulness"),
    ("hallucination",         "faithfulness"),
    ("translation",           "translation"),
    ("translate",             "translation"),
    ("trans_",                "translation"),
    ("answer_relevancy",      "answer_relevancy"),
    ("relevancy",             "answer_relevancy"),
    ("relevant",              "answer_relevancy"),
    ("qa_",                   "answer_relevancy"),
    ("question_answer",       "answer_relevancy"),
    ("contextual_relevancy",  "contextual_relevancy"),
    ("context_relevancy",     "contextual_relevancy"),
    ("rag",                   "contextual_relevancy"),
    ("contextual",            "contextual_relevancy"),
    ("summary",               "summary"),
    ("summarization",         "summary"),
    ("summarize",             "summary"),
]

DEFAULT_TASK = "summary"


def auto_detect_task_type(dataset_path) -> str:
    """
    根据数据集文件名或路径自动推断任务类型。
    匹配规则：将文件名转为小写后，按优先级匹配关键词。
    如果都没有匹配到，返回 DEFAULT_TASK。
    """
    name = str(dataset_path).lower()
    for keyword, task_type in _KEYWORD_TO_TASK:
        if keyword in name:
            return task_type
    return DEFAULT_TASK
