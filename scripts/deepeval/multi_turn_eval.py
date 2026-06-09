#!/usr/bin/env python3
"""
多轮对话能力评测脚本（集成到 deepeval 框架）
评测维度：
- turn_relevancy: 对话相关性
- conversation_completeness: 对话完整性
- knowledge_retention: 知识保持
- role_adherence: 角色保持

评测方式：LLM-as-Judge
输出格式：兼容 EvalScope 风格（summary.json / detailed_results.json / config.json / history.json）
"""
import json
import re
import requests
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# 导入 deepeval 配置
import eval_config as cfg


# ═══════════════════════════════════════════════════════════════
#  评测 Prompt 模板
# ═══════════════════════════════════════════════════════════════

JUDGE_PROMPTS = {
    "turn_relevancy": """你是一位多轮对话质量评测专家。请评测模型最后一轮的回答是否与对话主题相关。

对话历史：
{conversation_history}

最后一轮用户输入：{user_input}
最后一轮模型回答：{model_response}

评分标准（0-10分制，只输出整数或一位小数）：
10分：回答完全围绕用户意图，与对话主题高度相关
7分：回答基本相关，但略有偏离
4分：回答部分相关，有较多无关内容
0分：回答完全偏离主题

⚠️ 重要：只输出一个0-10之间的数字，例如 7 或 7.5。不要输出任何其他内容！""",

    "conversation_completeness": """你是一位多轮对话质量评测专家。请评测模型是否通过多轮对话满足了用户的核心需求。

对话历史：
{conversation_history}

最后一轮模型回答：{model_response}

用户核心需求：{user_goal}

评分标准（0-10分制，只输出整数或一位小数）：
10分：完全满足用户需求，提供了完整、可执行的解决方案
7分：基本满足需求，缺少部分细节
4分：部分满足需求，有明显遗漏
0分：完全没有满足用户需求

⚠️ 重要：只输出一个0-10之间的数字，例如 7 或 7.5。不要输出任何其他内容！""",

    "knowledge_retention": """你是一位多轮对话质量评测专家。请评测模型是否记住并正确使用了对话中用户提到的关键信息。

对话历史（用户提到的关键信息已加粗标记）：
{conversation_history}

需要记住的关键信息：
{key_info}

最后一轮模型回答：{model_response}

评分标准（0-10分制，只输出整数或一位小数）：
10分：完全记住并正确使用了所有关键信息
7分：记住了大部分关键信息，有少量遗漏
4分：只记住了部分信息，有明显遗漏
0分：完全忘记了关键信息，或出现矛盾

⚠️ 重要：只输出一个0-10之间的数字，例如 7 或 7.5。不要输出任何其他内容！""",

    "role_adherence": """你是一位多轮对话质量评测专家。请评测模型是否保持了设定的角色和语言风格。

角色设定：
{role_setting}

对话历史：
{conversation_history}

最后一轮模型回答：{model_response}

评分标准（0-10分制，只输出整数或一位小数）：
10分：完全符合角色设定，语言风格一致
7分：基本符合角色，偶有偏离
4分：部分符合角色，有明显不一致
0分：完全脱离角色，变成普通AI助手

⚠️ 重要：只输出一个0-10之间的数字，例如 7 或 7.5。不要输出任何其他内容！""",
}


DIMENSION_NAMES = {
    "turn_relevancy": "对话相关性",
    "conversation_completeness": "对话完整性",
    "knowledge_retention": "知识保持",
    "role_adherence": "角色保持",
}


# ═══════════════════════════════════════════════════════════════
#  全局错误记录（必须定义在 API 调用函数之前）
# ═══════════════════════════════════════════════════════════════

_LAST_ERROR = ""  # 记录最后一次 API 调用的错误信息


def _set_err(msg: str):
    """设置全局错误信息"""
    global _LAST_ERROR
    _LAST_ERROR = msg


# ═══════════════════════════════════════════════════════════════
#  Ollama API 调用
# ═══════════════════════════════════════════════════════════════

def _ollama_url(endpoint: str) -> str:
    """从配置中构造 Ollama URL。OLLAMA_API_URL 可能是 'http://host:port/api/generate' 或类似。"""
    base = cfg.OLLAMA_API_URL.replace('/api/generate', '').replace('/api/chat', '').rstrip('/')
    return f"{base}/{endpoint.lstrip('/')}"


def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    """多轮消息 → prompt（用于 /api/generate）。带 anti-thinking 前缀。"""
    parts = []
    parts.append("系统提示: 你是一个直接、简洁的助手。禁止输出 <thinking> 标签或任何推理过程，只输出最终答案。")
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "").strip()
        if not content:
            continue
        if role == "system":
            parts.append(f"系统提示: {content}")
        elif role == "assistant":
            parts.append(f"助手: {content}")
        else:
            parts.append(f"用户: {content}")
    return "\n\n".join(parts) + "\n\n助手:"


def _flatten_to_single_turn(messages: List[Dict[str, str]]) -> str:
    """把多轮消息"扁平化"为单轮问答，从根本避免多轮 thinking 死循环。

    格式：
        以下是对话历史（参考材料，不需要你逐条分析）：
        - 用户: xxx
        - 助手: xxx
        ...

        请直接回答最后一个用户的问题：[最后一条用户消息]

        你的答案：
    """
    # 提取最后一条用户消息
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = m.get("content", "").strip()
            break

    # 构建历史摘要（只放非空消息，简化格式）
    history_lines = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "").strip()
        if not content:
            continue
        if role == "assistant":
            history_lines.append(f"- 助手: {content}")
        elif role == "system":
            history_lines.append(f"- [系统] {content}")
        else:
            history_lines.append(f"- 用户: {content}")

    history_text = "\n".join(history_lines)

    prompt = (
        "你是一个直接、简洁的 AI 助手。\n"
        "\n"
        "以下是对话历史（仅作为背景参考，不要逐条分析，不要输出推理过程）：\n"
        "----------------------------------------------------------------\n"
        f"{history_text}\n"
        "----------------------------------------------------------------\n"
        "\n"
        f"请直接回答最后一个用户的问题：{last_user}\n"
        "\n"
        "重要要求：\n"
        "1. 禁止输出 <thinking>、推理分析、或任何内部思考过程\n"
        "2. 只输出最终答案\n"
        "3. 答案要简洁明了\n"
        "\n"
        "你的答案："
    )
    return prompt


def _add_anti_thinking_prefix(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """对 /api/chat 的 messages 数组加 anti-thinking 系统消息。"""
    anti_think = {
        "role": "system",
        "content": "你必须直接回答问题，不要输出任何 <thinking> 标签或推理过程。你的输出只能包含最终答案。"
    }
    return [anti_think] + list(messages)


def _request_with_error(url: str, payload: dict, timeout: int) -> dict:
    """发送 POST 请求到 Ollama，并在失败时返回带详细错误信息的 dict。

    成功返回: {"ok": True, "data": response_json}
    失败返回: {"ok": False, "error": "详细错误信息"}
    """
    try:
        response = requests.post(url, json=payload, timeout=timeout)
    except requests.exceptions.ConnectionError as e:
        return {"ok": False, "error": f"连接失败: {type(e).__name__}: {str(e)[:200]}"}
    except requests.exceptions.Timeout as e:
        return {"ok": False, "error": f"超时 ({timeout}s): {type(e).__name__}: {str(e)[:100]}"}
    except Exception as e:
        return {"ok": False, "error": f"请求异常: {type(e).__name__}: {str(e)[:200]}"}

    # 请求已发出，检查 HTTP 状态
    if response.status_code >= 400:
        body = response.text[:500]
        return {"ok": False, "error": f"HTTP {response.status_code}: {body}"}

    # 解析 JSON
    try:
        data = response.json()
    except Exception as e:
        return {"ok": False, "error": f"响应非 JSON: {type(e).__name__}: {response.text[:300]}"}

    # 检查 Ollama 业务级错误（如 {"error": "..."}）
    if isinstance(data, dict) and "error" in data:
        return {"ok": False, "error": f"Ollama: {str(data['error'])[:300]}"}

    return {"ok": True, "data": data}


def _safe_str(data) -> str:
    """安全字符串转换（处理 None、空字符串等）"""
    if data is None:
        return ""
    return str(data)


def _strip_control(text: str) -> str:
    """清理控制字符和 ANSI 转义序列"""
    if not text:
        return ""
    text = re.sub(r'\x1b\[[A-Za-z]', '', text)
    text = re.sub(r'\x1b\[\[?\d*[A-Za-z]?', '', text)
    return text.strip()


def _extract_answer_from_thinking(thinking: str) -> str:
    """从 Ollama 返回的 thinking 字段中提取模型实际打算输出的答案。

    qwen3.5 的 thinking 字段格式类似：
        Thinking Process:
        1. **Analyze the Request:** ...
        ...
        3. **Formulate the Response:**
           Direct answer: 您的名字叫张三。

    策略：从后往前找 "Direct answer"、"答案"、"Response" 等关键词；
    如果找不到，就取 thinking 最后几行的非推理内容。
    """
    if not thinking:
        return ""

    text = thinking.strip()

    # 候选关键词（中英文混合）
    answer_markers = [
        r"[Dd]irect answer[:：]\s*",
        r"[Dd]irect answer[:：]\s*\*\*",
        r"[Dd]irect response[:：]\s*",
        r"[Aa]nswer[:：]\s*",
        r"[Rr]esponse[:：]\s*",
        r"输出答案[:：]\s*",
        r"最终答案[:：]\s*",
        r"答案[:：]\s*",
        r"Formulate the Response[:：]*[\s\S]*?\n\s*\*\*",
        r"Final Response[:：]\s*",
    ]

    for marker in answer_markers:
        match = re.search(marker + r"(.{5,500})", text)
        if match:
            candidate = match.group(1).strip()
            # 清理 markdown 格式标记
            candidate = re.sub(r'^\*+\s*', '', candidate)
            candidate = re.sub(r'\*+$', '', candidate)
            candidate = candidate.strip("*`\n\r\t ")
            if len(candidate) > 2 and "思考" not in candidate[:10]:
                return candidate

    # 如果没找到明确的答案标记，从 thinking 末尾倒着找一段"看起来像答案"的文本
    # 策略：找 thinking 中最后一个带中文/英文自然语言的段落，且不以数字开头
    lines = [l.strip() for l in text.split("\n")]
    lines = [l for l in lines if l]

    # 从后向前扫，找"看起来像答案"的行（不以数字或 ** 开头，包含中文）
    for line in reversed(lines[-10:]):  # 只看最后 10 行
        stripped = line.strip("*`\t ")
        # 过滤掉纯推理/思考标记的行
        if not stripped or len(stripped) < 4:
            continue
        if re.match(r'^\s*\d+\.?\s*\*\*', stripped):  # 形如 "1. **Analyze"
            continue
        if stripped.startswith("Thinking Process"):
            continue
        # 找到一个候选
        if any('\u4e00' <= ch <= '\u9fff' for ch in stripped):
            return stripped

    # 最后兜底：如果 thinking 很短（< 200 字）直接返回末尾几句
    if len(text) < 400:
        # 取最后一段
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if paragraphs:
            return paragraphs[-1][:300]

    return ""


def _extract_any_answer(data) -> str:
    """从 Ollama 返回的 JSON dict 中穷尽所有字段尝试提取答案。

    检查顺序：
    1. message.content（/api/chat 标准字段）
    2. response（/api/generate 标准字段）
    3. message.thinking（qwen3.5 专用字段，答案可能嵌在推理末尾）
    4. thinking（顶层字段）
    """
    if not isinstance(data, dict):
        return ""

    candidates = []

    # 1) message.content
    msg = data.get("message")
    if isinstance(msg, dict):
        content = _safe_str(msg.get("content", ""))
        cleaned = _strip_control(content)
        if cleaned and cleaned.lower() not in ("", "n/a", "none"):
            candidates.append(cleaned)

        # 2) message.thinking（关键！qwen3.5 的答案可能嵌在这里面）
        thinking_text = _safe_str(msg.get("thinking", ""))
        if thinking_text:
            extracted = _extract_answer_from_thinking(thinking_text)
            if extracted:
                candidates.append(extracted)

    # 3) 顶层 response（/api/generate 用）
    resp = _safe_str(data.get("response", ""))
    cleaned_resp = _strip_control(resp)
    if cleaned_resp:
        candidates.append(cleaned_resp)

    # 4) 顶层 thinking
    top_thinking = _safe_str(data.get("thinking", ""))
    if top_thinking:
        extracted = _extract_answer_from_thinking(top_thinking)
        if extracted:
            candidates.append(extracted)

    # 返回第一个非空候选
    for c in candidates:
        if c:
            return c
    return ""


def _clean_text(text: str) -> str:
    """简单清理控制字符（对裁判模型或普通文本使用）"""
    return _strip_control(text)


def call_ollama_chat(messages: List[Dict[str, str]], model: str, timeout: int = 600,
                    max_retries: int = 1, retry_delay: int = 5) -> str:
    """调用 Ollama 生成回答 —— 4 级回退策略：

    关键发现（2026-06-04 curl 测试）：qwen3.5 返回的 JSON 结构是：
        {"message": {"role": "assistant", "content": "",
                     "thinking": "Thinking Process: ... Direct answer: 您的名字叫张三。"},
         "done_reason": "length", ...}

    当 num_predict 不够大时，content 可能为空，答案嵌在 thinking 末尾。
    因此我们要：1）给足够大的 num_predict；2）同时检查 content 和 thinking 两个字段。

    1) generate: /api/generate + 多轮 prompt（标准方式）
    2) chat:     /api/chat + messages 数组
    3) flatten:  扁平化为单轮问答（把历史作为"参考材料"列出）
    4) minimal:  只留最后一条用户消息，极端 fallback

    返回模型回答字符串。失败时返回 ""。
    """
    _set_err("")
    total_chars = sum(len(m.get("content", "") or "") for m in messages)
    debug_info = f"[{len(messages)}条消息, {total_chars}字]"

    url_generate = _ollama_url('/api/generate')
    url_chat = _ollama_url('/api/chat')

    # 提取最后一条用户消息（给方案 3、4 用）
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = (m.get("content") or "").strip()
            break

    # 定义 4 个方案（name, url, payload_dict） — 答案提取统一用 _extract_any_answer()
    plans = [
        # 方案 1：/api/generate + 多轮 prompt（标准方式）
        ("generate", url_generate,
         {"model": model, "prompt": _messages_to_prompt(messages),
          "stream": False, "keep_alive": "24h",
          "options": {"temperature": 0.0, "num_predict": 8192}}),

        # 方案 2：/api/chat + messages 数组（原生多轮）
        ("chat", url_chat,
         {"model": model, "messages": _add_anti_thinking_prefix(messages),
          "stream": False, "keep_alive": "24h",
          "options": {"temperature": 0.0, "num_predict": 8192}}),

        # 方案 3：扁平化为单轮问答（把多轮历史作为"参考材料"）
        ("flatten", url_generate,
         {"model": model, "prompt": _flatten_to_single_turn(messages),
          "stream": False, "keep_alive": "24h",
          "options": {"temperature": 0.0, "num_predict": 8192}}),
    ]

    # 方案 4：极端极简 fallback — 只留最后一条用户消息
    if last_user:
        plans.append(
            ("minimal", url_generate,
             {"model": model,
              "prompt": f"请直接回答以下问题，不要分析，不要推理。\n\n问题：{last_user}\n\n答案：",
              "stream": False, "keep_alive": "24h",
              "options": {"temperature": 0.0, "num_predict": 4096}})
        )

    for p_idx, (p_name, url, payload) in enumerate(plans):
        result = _request_with_error(url, payload, timeout)

        if result["ok"]:
            data = result["data"]
            # ★ 关键改动：从 content + response + thinking 多字段穷尽提取
            content = _extract_any_answer(data)
            if content:
                return content

            # 空回答 — 打印诊断信息
            eval_count = data.get("eval_count", 0) if isinstance(data, dict) else 0
            done_reason = data.get("done_reason", "?") if isinstance(data, dict) else "?"
            err_msg = f"[{p_name}] 空回答（eval_count={eval_count}, done_reason={done_reason}）"
        else:
            err_msg = f"[{p_name}] {result['error']}"

        _set_err(err_msg)
        print(f"\n    ❌ {err_msg} {debug_info}", flush=True)

        if p_idx < len(plans) - 1:
            next_name = plans[p_idx + 1][0]
            print(f"       → 切换到 {next_name} 方案", flush=True)
            time.sleep(1)

    _set_err(f"所有方案均失败 {debug_info}")
    return ""


# ═══════════════════════════════════════════════════════════════
#  模型回答生成
# ═══════════════════════════════════════════════════════════════

def get_model_response(conversation: List[Dict[str, str]], check_turn: int, model: str) -> str:
    """获取模型在指定轮次的回答（用 /api/chat 原生多轮对话）

    qwen3.5:9b 需要 num_predict >= 2048（thinking 会占用大量 token）
    """
    global _LAST_ERROR
    _LAST_ERROR = ""

    # 构建到 check_turn 的对话历史（包含 check_turn 的用户输入）
    history = conversation[:check_turn]

    # 关键修复：Ollama 要求最后一条消息必须是 user 角色
    # 如果最后一条是 assistant/system，往前裁剪，直到找到 user 消息
    while len(history) > 0 and history[-1]["role"] != "user":
        history = history[:-1]

    if len(history) == 0 or history[-1]["role"] != "user":
        _LAST_ERROR = "对话历史中没有 user 消息"
        print(f"\n    ❌ {_LAST_ERROR}", flush=True)
        return ""

    roles = [m["role"] for m in history]
    print(f"     发送 {len(history)} 条消息, 角色: {roles}", end=" ", flush=True)

    # 用 /api/chat 的 messages 数组（原生多轮对话格式）
    response = call_ollama_chat(history, model=model)
    return response


# ═══════════════════════════════════════════════════════════════
#  评测逻辑
# ═══════════════════════════════════════════════════════════════

def judge_dimension(dimension: str, sample: Dict, model_response: str) -> Dict[str, Any]:
    """使用 LLM-as-Judge 评测指定维度"""
    conversation = sample["conversation"]
    check_turn = sample["check_turn"]

    # 构建对话历史文本（排除最后一轮 user 消息，因为 model_response 就是回答）
    history_text = ""
    for i, turn in enumerate(conversation[:check_turn]):
        role = "用户" if turn["role"] == "user" else "模型"
        if turn["role"] == "system":
            role = "系统"
        history_text += f"[{i}] {role}: {turn['content']}\n"

    # 获取当前轮次的用户输入
    user_input = ""
    if check_turn > 0 and check_turn <= len(conversation):
        turn = conversation[check_turn - 1]
        if turn["role"] == "user":
            user_input = turn["content"]

    # 构建评测 prompt
    if dimension == "turn_relevancy":
        prompt = JUDGE_PROMPTS[dimension].format(
            conversation_history=history_text,
            user_input=user_input,
            model_response=model_response,
        )
    elif dimension == "conversation_completeness":
        # 用户核心需求 = 第一条用户消息（对话的起点）
        user_goal = conversation[0]["content"] if conversation else ""
        prompt = JUDGE_PROMPTS[dimension].format(
            conversation_history=history_text,
            user_goal=user_goal,
            model_response=model_response,
        )
    elif dimension == "knowledge_retention":
        # 提取"关键信息"：用户在对话历史（check_turn 之前）
        # 明确提到的事实性信息（姓名、地点、偏好、设备、预算等）
        # 只取 check_turn-1 轮之前的用户消息，排除最后一条提问
        user_messages_before = []
        for turn in conversation[:check_turn - 1]:
            if turn["role"] == "user":
                user_messages_before.append(f"- {turn['content']}")
        key_info = "\n".join(user_messages_before) if user_messages_before else "无明确关键信息"
        prompt = JUDGE_PROMPTS[dimension].format(
            conversation_history=history_text,
            key_info=key_info,
            model_response=model_response,
        )
    elif dimension == "role_adherence":
        role_setting = ""
        for turn in conversation:
            if turn["role"] == "system":
                role_setting = turn["content"]
                break
        prompt = JUDGE_PROMPTS[dimension].format(
            role_setting=role_setting or "无特定角色设定",
            conversation_history=history_text,
            model_response=model_response,
        )
    else:
        return {"score": 0, "reason": "未知维度"}

    # 调用裁判模型（用 /api/chat 原生多轮对话接口，避免 assistant 消息问题）
    judge_messages = [
        {"role": "user", "content": prompt}
    ]
    judge_response = call_ollama_chat(judge_messages, model=cfg.JUDGE_MODEL)

    # 解析分数
    try:
        match = re.search(r'(\d+(?:\.\d+)?)', judge_response)
        if match:
            score = float(match.group(1))
            # 明确 0-10 分制，除以 10 得到 0-1 分
            score = min(max(score, 0.0), 10.0) / 10.0
            return {"score": score, "raw_output": judge_response}
        else:
            return {"score": 0, "raw_output": judge_response}
    except Exception as e:
        return {"score": 0, "raw_output": f"解析错误: {str(e)[:100]}"}


# ═══════════════════════════════════════════════════════════════
#  数据集加载
# ═══════════════════════════════════════════════════════════════

def load_multi_turn_dataset(dataset_path: Path) -> List[Dict]:
    """加载多轮对话数据集"""
    data = []
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                data.append(item)
            except json.JSONDecodeError:
                continue
    return data


# ═══════════════════════════════════════════════════════════════
#  结果构建与保存（兼容 EvalScope 格式）
# ═══════════════════════════════════════════════════════════════

def build_config(dimension: str, start_time: float, end_time: float) -> Dict[str, Any]:
    """构建 config.json 内容"""
    return {
        'model': cfg.GENERATION_MODEL,
        'judge_model': cfg.JUDGE_MODEL,
        'dataset': str(cfg.DATASET_PATH),
        'task_type': 'multi_turn',
        'task_name': f'多轮对话能力评测 - {DIMENSION_NAMES.get(dimension, dimension)}',
        'eval_dimension': dimension,
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'time_elapsed': round(end_time - start_time, 2),
        'time_elapsed_formatted': f"{end_time - start_time:.2f}s"
    }


def build_summary(results: List[Dict[str, Any]], start_time: float, end_time: float) -> Dict[str, Any]:
    """构建 summary.json 内容"""
    valid_scores = [r['score'] for r in results if r['score'] >= 0]

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
        'time_elapsed': round(end_time - start_time, 2),
        'time_elapsed_formatted': f"{end_time - start_time:.2f}s"
    }


def save_results(output_dir: Path, config: Dict[str, Any], summary: Dict[str, Any],
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

    history.append({
        'timestamp': config['timestamp'],
        'model': config['model'],
        'judge_model': config['judge_model'],
        'task_type': config['task_type'],
        'task_name': config['task_name'],
        'eval_dimension': config['eval_dimension'],
        'overall_score': summary['overall_score'],
        'pass_rate': summary['pass_rate'],
        'time_elapsed': summary['time_elapsed_formatted']
    })

    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def print_summary(config: Dict[str, Any], summary: Dict[str, Any]):
    """打印汇总结果"""
    print("\n" + "=" * 70)
    print(f"评估结果汇总 - {config['task_name']}")
    print("=" * 70)
    print(f"模型: {config['model']}")
    print(f"裁判模型: {config['judge_model']}")
    print(f"评估维度: {config['eval_dimension']}")
    print(f"样本数: {summary['total_samples']}")
    print(f"有效样本: {summary['valid_samples']}")
    print(f"失败样本: {summary['failed_samples']}")
    print("-" * 70)
    print(f"总体得分: {summary['overall_score']:.4f}")
    print(f"最高分:   {summary['max_score']:.4f}")
    print(f"最低分:   {summary['min_score']:.4f}")
    print(f"通过率 (≥0.6): {summary['pass_rate']:.1f}%")
    print("-" * 70)
    print(f"耗时: {summary['time_elapsed_formatted']}")
    print("=" * 70)


# ═══════════════════════════════════════════════════════════════
#  单次维度评测
# ═══════════════════════════════════════════════════════════════

def evaluate_dimension(dataset: List[Dict], dimension: str, output_dir: Path) -> Dict[str, Any]:
    """评测单个维度"""
    # 过滤该维度的样本
    dim_samples = [s for s in dataset if s.get("dimension") == dimension]

    if not dim_samples:
        print(f"❌ 维度 {dimension} 没有样本")
        return None

    print(f"\n{'='*70}")
    print(f"📋 评测维度: {dimension} ({DIMENSION_NAMES.get(dimension, '')})")
    print(f"📊 样本数: {len(dim_samples)}")
    print(f"🤖 被测模型: {cfg.GENERATION_MODEL}")
    print(f"⚖️  裁判模型: {cfg.JUDGE_MODEL}")
    print(f"{'='*70}")

    start_time = time.time()
    detailed_results = []

    for idx, sample in enumerate(dim_samples, 1):
        print(f"\n  [{idx}/{len(dim_samples)}] {sample.get('description', '')}")

        conversation = sample["conversation"]
        check_turn = sample["check_turn"]

        # 获取模型回答
        print(f"     获取模型第 {check_turn} 轮回答...", end=" ", flush=True)
        model_response = get_model_response(conversation, check_turn, cfg.GENERATION_MODEL)

        if not model_response:
            print("❌ 失败", flush=True)
            if _LAST_ERROR:
                print(f"        原因: {_LAST_ERROR}", flush=True)
            print(f"        等待 30 秒让 GPU 内存释放...", flush=True)
            time.sleep(30)
            detailed_results.append({
                'id': idx,
                'description': sample.get('description', ''),
                'score': -1.0,
                'raw_output': _LAST_ERROR or '模型回答为空',
                'model_response': '',
                'expected': sample.get('expected', ''),
            })
            continue

        print(f"完成 ({len(model_response)} 字)")
        print(f"     模型回答: {model_response[:80]}...")

        # 评测
        print(f"     裁判评测中...", end=" ", flush=True)
        judge_result = judge_dimension(dimension, sample, model_response)
        score = judge_result.get("score", 0)
        raw_output = judge_result.get("raw_output", "")

        if score >= 0:
            print(f"得分: {score:.4f}")
        else:
            print(f"失败")

        detailed_results.append({
            'id': idx,
            'description': sample.get('description', ''),
            'score': score,
            'raw_output': raw_output,
            'model_response': model_response,
            'expected': sample.get('expected', ''),
            'conversation': conversation,
            'check_turn': check_turn,
        })

        # 样本间等待，避免连续请求压垮 Ollama（连续 10 秒让 GPU 内存释放）
        if idx < len(dim_samples):
            time.sleep(10)

    end_time = time.time()

    # 构建结果
    config = build_config(dimension, start_time, end_time)
    summary = build_summary(detailed_results, start_time, end_time)

    # 打印汇总
    print_summary(config, summary)

    # 保存结果
    dim_output_dir = output_dir / dimension
    save_results(dim_output_dir, config, summary, detailed_results)
    print(f"\n✅ 结果已保存到: {dim_output_dir}")

    return {
        'dimension': dimension,
        'overall_score': summary['overall_score'],
        'pass_rate': summary['pass_rate'],
        'output_dir': str(dim_output_dir)
    }


# ═══════════════════════════════════════════════════════════════
#  启动健康检查
# ═══════════════════════════════════════════════════════════════

def health_check() -> bool:
    """启动前检查：确认被测模型和裁判模型都能正常响应

    Returns:
        bool: True 表示两个模型都能正常工作，False 表示至少一个有问题
    """
    print(f"\n{'='*70}")
    print("🔍 启动健康检查：验证模型可访问性")
    print(f"{'='*70}")

    test_msg = [{"role": "user", "content": "请用一句话回答：1+1等于几？"}]
    all_ok = True

    for label, model in [("被测模型", cfg.GENERATION_MODEL), ("裁判模型", cfg.JUDGE_MODEL)]:
        print(f"  检查 {label} ({model})...", end=" ", flush=True)
        resp = call_ollama_chat(test_msg, model=model, timeout=300, max_retries=2, retry_delay=10)
        if resp:
            print(f"✅ OK（响应 {len(resp)} 字）", flush=True)
        else:
            all_ok = False
            err = _LAST_ERROR or "未知错误"
            print(f"❌ 失败: {err}", flush=True)

    print()
    if not all_ok:
        print("⚠️  警告：部分模型无法正常响应。评测可能会有大量失败样本。")
        print("    建议：检查 Ollama 服务状态、GPU 显存、模型是否已 pull。")
    else:
        print("✅ 健康检查通过，开始评测...")
    return all_ok


# ═══════════════════════════════════════════════════════════════
#  主函数
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("多轮对话能力评测（Deepeval 集成版）")
    print("=" * 70)

    # --- 健康检查（最先运行） ---
    health_check()

    # 数据集路径
    dataset_path = Path(__file__).parent / "dataset" / "19_multi_turn_datasets" / "multi_turn_dataset.jsonl"

    if not dataset_path.exists():
        print(f"❌ 数据集不存在: {dataset_path}")
        print("请先运行 generate_multi_turn_dataset.py 生成数据集")
        return

    # 加载数据集
    print(f"\n📂 加载数据集: {dataset_path}")
    dataset = load_multi_turn_dataset(dataset_path)
    print(f"   加载 {len(dataset)} 条样本")

    if not dataset:
        print("❌ 数据集为空")
        return

    # 按维度分组统计
    from collections import Counter
    dim_counts = Counter(s.get("dimension", "unknown") for s in dataset)
    print(f"\n📊 维度分布:")
    for dim, count in sorted(dim_counts.items()):
        print(f"   - {dim}: {count} 条 ({DIMENSION_NAMES.get(dim, dim)})")

    # 输出目录
    output_root = cfg.OUTPUT_ROOT / cfg.GENERATION_MODEL / "multi_turn"
    print(f"\n💾 路径验证:")
    print(f"   项目根目录(PROJECT_ROOT): {cfg.PROJECT_ROOT}")
    print(f"   输出根目录(OUTPUT_ROOT):  {cfg.OUTPUT_ROOT}")
    print(f"   本次结果目录:            {output_root}")

    # 评测所有维度
    all_results = []
    for dimension in sorted(DIMENSION_NAMES.keys()):
        if dimension not in dim_counts:
            continue

        result = evaluate_dimension(dataset, dimension, output_root)
        if result:
            all_results.append(result)

    # 总汇总
    if len(all_results) > 1:
        print("\n" + "=" * 70)
        print("多轮对话能力评测总汇总")
        print("=" * 70)

        total_score = 0
        for r in all_results:
            dim_name = DIMENSION_NAMES.get(r['dimension'], r['dimension'])
            print(f"\n{dim_name}:")
            print(f"  总体得分: {r['overall_score']:.4f}")
            print(f"  通过率: {r['pass_rate']:.1f}%")
            total_score += r['overall_score']

        overall_avg = total_score / len(all_results) if all_results else 0
        print(f"\n{'='*70}")
        print(f"总体平均分: {overall_avg:.4f}")
        print(f"{'='*70}")

        # 保存总汇总
        summary_file = output_root / "multi_turn_overall_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'model': cfg.GENERATION_MODEL,
                'judge_model': cfg.JUDGE_MODEL,
                'overall_score': overall_avg,
                'dimensions': all_results,
            }, f, ensure_ascii=False, indent=2)
        print(f"\n💾 总汇总已保存: {summary_file}")

    print("\n🎉 多轮对话评测完成！")


if __name__ == "__main__":
    main()
