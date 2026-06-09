# DeepEval 评测模块 / DeepEval Evaluation Module

[English](#english) | [中文](#中文)

---

## English

### Overview

LLM-as-Judge quality evaluation using Ollama. Two independent entry scripts:

1. **`llm_judge_eval.py`** — Single-turn evaluation (summary quality, translation, answer relevance, faithfulness)
2. **`multi_turn_eval.py`** — Multi-turn conversation capability evaluation (turn relevancy, conversation completeness, knowledge retention, role adherence)

Both scripts follow the same pattern:
1. Read a dataset (JSONL)
2. For each sample, prompt the **generation model** (`GENERATION_MODEL`) to produce an answer
3. Prompt the **judge model** (`JUDGE_MODEL`) to score the answer on a 0–1 scale
4. Output per-sample results + aggregate statistics

### Project Structure

```
deepeval/
├── eval_config.py            # Main configuration (model, dataset, task type)
├── llm_judge_eval.py         # Entry: single-turn evaluation
├── multi_turn_eval.py        # Entry: multi-turn conversation evaluation
├── task_prompts.py           # Judge prompt templates per task
├── README.md                 # This file
└── dataset/
    ├── 5_machine_translation_datasets/   # Translation quality datasets
    ├── 15_answer_relevance_datasets/     # Answer relevance datasets
    ├── 16_Faithfulness_datasets/         # Faithfulness / fact consistency datasets
    ├── 18_summarization_datasets/        # Summary quality datasets
    └── 19_multi_turn_datasets/           # Multi-turn conversation datasets
```

### Configuration (`eval_config.py`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `TASK_TYPE` | `summary` / `translation` / `answer_relevancy` / `faithfulness` / `contextual_relevancy` / `auto` (auto-detect from dataset filename) | `auto` |
| `EVAL_DIMENSION` | Dimension display name, `auto` to match `TASK_TYPE` | `auto` |
| `GENERATION_MODEL` | Ollama model name for generating answers | `qwen3.5:9b` |
| `JUDGE_MODEL` | Ollama model name for judging / scoring | `qwen3:32b` |
| `OLLAMA_API_URL` | Ollama API endpoint | `http://127.0.0.1:11434/api/generate` |
| `DATASET_PATH` | Dataset file (JSONL) — used when `DATASET_DIR` is `None` | `my_summary_set.jsonl` |
| `DATASET_DIR` | Directory of multiple JSONL files — runs evaluation on each | `None` |
| `DATASET_DIRS` | List of directories — batch evaluation | `[]` |
| `TEMPERATURE` | Generation temperature | `0.0` |
| `MAX_TOKENS` | `num_predict` for generation | `2048` |
| `SAMPLE_LIMIT` | Max samples per dataset (0 = all) | `0` |
| `TIMEOUT` | Per-request timeout (seconds) | `600` |
| `OUTPUT_DIR` | Output root directory | `PROJECT_ROOT/results/deepeval/{model}/{dimension}/` |

### Usage

#### 1. Single-Turn Evaluation (`llm_judge_eval.py`)

```bash
# From project root
cd /path/to/Intern_CMW

# Edit configuration: set TASK_TYPE and path to your dataset
vim scripts/deepeval/eval_config.py
#   TASK_TYPE = "summary"                      # Or "auto" to detect from filename
#   DATASET_PATH = "scripts/deepeval/dataset/18_summarization_datasets/summary_dataset.jsonl"
#   GENERATION_MODEL = "qwen3.5:9b"
#   JUDGE_MODEL = "qwen3:32b"

# Run
python scripts/deepeval/llm_judge_eval.py
```

Supported task types and their judge prompts are defined in `task_prompts.py`:

| Task | Dataset field | Typical dataset |
|------|--------------|-----------------|
| `summary` | `query` → text to summarize; `response` → reference summary | `18_summarization_datasets/summary_dataset.jsonl` |
| `translation` | `query` → source text; `response` → reference translation | `5_machine_translation_datasets/translation_datasets.jsonl` |
| `answer_relevancy` | `query` → question; `response` → expected answer | `15_answer_relevance_datasets/*` |
| `faithfulness` | `query` → passage; `response` → claim to validate | `16_Faithfulness_datasets/faithfulness_dataset.jsonl` |

#### 2. Multi-Turn Conversation Evaluation (`multi_turn_eval.py`)

```bash
# From project root (no TASK_TYPE needed — it iterates all 4 dimensions)
python scripts/deepeval/multi_turn_eval.py
```

This script reads `dataset/19_multi_turn_datasets/multi_turn_dataset.jsonl` and evaluates:

| Dimension | Samples | What is tested |
|-----------|---------|----------------|
| `turn_relevancy` | 15 | Whether each turn's response answers the current user query in context |
| `conversation_completeness` | 15 | Whether assistant responses help advance the conversation to completion |
| `knowledge_retention` | 15 | Whether the model remembers facts from earlier turns (user name, location, preferences, project details, etc.) |
| `role_adherence` | 15 | Whether the model maintains a consistent persona / role (doctor, teacher, lawyer, fitness coach, etc.) |

**Per-sample flow:**
1. Send the entire `conversation` history (up to the penultimate turn) to the generation model
2. The model generates a response at the target turn
3. The judge model scores the response on a 0–1 scale

### Dataset Format

#### Single-turn JSONL

```json
{"query": "全文/源句...", "response": "参考答案/摘要/翻译..."}
```

#### Multi-turn JSONL

```json
{
  "dimension": "knowledge_retention",
  "description": "记住用户姓名",
  "conversation": [
    {"role": "user", "content": "我叫张三，今年28岁。"},
    {"role": "assistant", "content": "您好张三，很高兴认识您！"},
    {"role": "user", "content": "我叫什么名字？"}
  ],
  "check_turn": 3,
  "expected": "模型应回答用户姓名为'张三'"
}
```

### Output Structure

```
results/deepeval/{model}/
├── summary/                   # llm_judge_eval.py output
│   ├── individual_scores.json   # Per-sample: score, prompt, model_answer
│   ├── summary_report.txt      # Human-readable report
│   └── statistics.json         # Aggregate: mean, median, stddev
└── multi_turn/                # multi_turn_eval.py output
    ├── turn_relevancy/
    │   ├── per_sample_results.json
    │   └── summary.json
    ├── conversation_completeness/
    │   ├── per_sample_results.json
    │   └── summary.json
    ├── knowledge_retention/
    │   ├── per_sample_results.json
    │   └── summary.json
    └── role_adherence/
        ├── per_sample_results.json
        └── summary.json
```

### Example Terminal Output

```
======================================================================
 评测维度: knowledge_retention (知识保持)
 样本数: 15
 被测模型: qwen3.5:4b
 裁判模型: qwen3:32b
======================================================================

  [1/15] 记住用户姓名
     获取模型回答...       完成 (89字)
     裁判评测中... 得分: 1.0000

  [2/15] 记住居住地点
     获取模型回答...       完成 (112字)
     裁判评测中... 得分: 1.0000
...

======================================================================
 汇总: knowledge_retention
======================================================================
  平均得分: 0.8672
  中位得分: 1.0000
  标准差:   0.1289
  最高分:   1.0000
  最低分:   0.5000
  成功/总数: 15/15
```

### Troubleshooting

**Q: Model returns empty response?**
A: qwen3.5 models have a "thinking" internal mode that may fill the output token budget without producing visible content. `multi_turn_eval.py` has multiple fallbacks: extracting answers from `thinking` field, flattening multi-turn prompts into single-turn queries, and retrying with only the last user message. If you see repeated failures, check that `MAX_TOKENS` in config is ≥ 2048.

**Q: Judge model scores seem random?**
A: Ensure `TEMPERATURE = 0.0` and that you're using a strong judge model (e.g., `qwen3:32b`). Smaller models as judges produce inconsistent scores.

**Q: Out-of-memory on GPU?**
A: The generation model and judge model are both loaded in Ollama. Consider using smaller models, or running on a GPU with ≥ 24GB VRAM when evaluating with `qwen3.5:9b` + `qwen3:32b`.

---

## 中文

### 功能概述

使用 Ollama 进行 **LLM-as-Judge** 质量评测。包含两个独立的入口脚本：

1. **`llm_judge_eval.py`** — 单轮任务评测（摘要、翻译、答案相关性、事实一致性）
2. **`multi_turn_eval.py`** — 多轮对话能力评测（对话相关性、对话完整性、知识保持、角色保持）

两个脚本遵循相同的流程：
1. 读取数据集（JSONL 格式）
2. 对每个样本，调用 **生成模型** (`GENERATION_MODEL`) 生成回答
3. 调用 **裁判模型** (`JUDGE_MODEL`) 对回答打分（0–1 分）
4. 输出每个样本的详细结果 + 聚合统计

### 项目结构

```
deepeval/
├── eval_config.py            # 主配置（模型、数据集、任务类型）
├── llm_judge_eval.py         # 入口：单轮评测
├── multi_turn_eval.py        # 入口：多轮对话评测
├── task_prompts.py           # 各任务的裁判 prompt 模板
├── README.md                 # 本文件
└── dataset/
    ├── 5_machine_translation_datasets/   # 机器翻译数据集
    ├── 15_answer_relevance_datasets/     # 答案相关性数据集
    ├── 16_Faithfulness_datasets/         # 事实一致性数据集
    ├── 18_summarization_datasets/        # 摘要质量数据集
    └── 19_multi_turn_datasets/           # 多轮对话数据集
```

### 配置说明（`eval_config.py`）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `TASK_TYPE` | `summary` / `translation` / `answer_relevancy` / `faithfulness` / `contextual_relevancy` / `auto`（根据数据集文件名自动识别） | `auto` |
| `EVAL_DIMENSION` | 维度展示名，`auto` 时与 `TASK_TYPE` 保持一致 | `auto` |
| `GENERATION_MODEL` | 生成回答的 Ollama 模型名 | `qwen3.5:9b` |
| `JUDGE_MODEL` | 担任裁判、用于打分的 Ollama 模型名 | `qwen3:32b` |
| `OLLAMA_API_URL` | Ollama API 地址 | `http://127.0.0.1:11434/api/generate` |
| `DATASET_PATH` | 单文件数据集路径（`DATASET_DIR` 为 `None` 时生效） | `my_summary_set.jsonl` |
| `DATASET_DIR` | 目录，将自动读取目录下所有 `.jsonl` 文件并合并评测 | `None` |
| `DATASET_DIRS` | 多个目录列表，顺序执行批量评测 | `[]` |
| `TEMPERATURE` | 生成温度 | `0.0` |
| `MAX_TOKENS` | 生成时的 `num_predict` | `2048` |
| `SAMPLE_LIMIT` | 每个数据集最多评测的样本数（0 = 全部） | `0` |
| `TIMEOUT` | 单次请求超时（秒） | `600` |
| `OUTPUT_DIR` | 输出根目录 | `PROJECT_ROOT/results/deepeval/{model}/{dimension}/` |

### 使用方法

#### 1. 单轮评测（`llm_judge_eval.py`）

```bash
# 在项目根目录
cd /path/to/Intern_CMW

# 编辑配置：设置任务类型和数据集路径
vim scripts/deepeval/eval_config.py
#   TASK_TYPE = "summary"                      # 或设为 "auto" 根据文件名识别
#   DATASET_PATH = "scripts/deepeval/dataset/18_summarization_datasets/summary_dataset.jsonl"
#   GENERATION_MODEL = "qwen3.5:9b"
#   JUDGE_MODEL = "qwen3:32b"

# 运行
python scripts/deepeval/llm_judge_eval.py
```

支持的任务类型及对应的数据集：

| 任务 | 数据字段 | 典型数据集 |
|------|---------|------------|
| `summary` | `query` → 待摘要文本；`response` → 参考摘要 | `18_summarization_datasets/summary_dataset.jsonl` |
| `translation` | `query` → 源文本；`response` → 参考翻译 | `5_machine_translation_datasets/translation_datasets.jsonl` |
| `answer_relevancy` | `query` → 问题；`response` → 期望答案 | `15_answer_relevance_datasets/*` |
| `faithfulness` | `query` → 原文段落；`response` → 待验证的声明 | `16_Faithfulness_datasets/faithfulness_dataset.jsonl` |

#### 2. 多轮对话评测（`multi_turn_eval.py`）

```bash
# 在项目根目录（无需设置 TASK_TYPE — 脚本自动遍历 4 个维度）
python scripts/deepeval/multi_turn_eval.py
```

脚本读取 `dataset/19_multi_turn_datasets/multi_turn_dataset.jsonl` 并评测以下 4 个维度：

| 维度 | 样本数 | 测试内容 |
|------|--------|---------|
| `turn_relevancy`（对话相关性） | 15 | 模型每轮回答是否回应当前轮的用户查询 |
| `conversation_completeness`（对话完整性） | 15 | 模型回答是否有助于对话走向完成 |
| `knowledge_retention`（知识保持） | 15 | 模型是否记住前文提到的事实（姓名、地点、偏好、项目细节等） |
| `role_adherence`（角色保持） | 15 | 模型是否维持一致的角色设定（医生、老师、律师、健身教练等） |

**每个样本的执行流程：**
1. 将完整对话历史（到倒数第二轮为止）发送给生成模型
2. 模型在目标轮次生成回答
3. 裁判模型对回答打分（0–1 分）

### 数据集格式

#### 单轮 JSONL

```json
{"query": "文本/源句...", "response": "参考答案/摘要/翻译..."}
```

#### 多轮 JSONL

```json
{
  "dimension": "knowledge_retention",
  "description": "记住用户姓名",
  "conversation": [
    {"role": "user", "content": "我叫张三，今年28岁。"},
    {"role": "assistant", "content": "您好张三，很高兴认识您！"},
    {"role": "user", "content": "我叫什么名字？"}
  ],
  "check_turn": 3,
  "expected": "模型应回答用户姓名为'张三'"
}
```

### 结果输出

```
results/deepeval/{模型名}/
├── summary/                   # llm_judge_eval.py 的输出
│   ├── individual_scores.json   # 每个样本：分数、prompt、模型回答
│   ├── summary_report.txt      # 可读报告
│   └── statistics.json         # 聚合：均值、中位数、标准差
└── multi_turn/                # multi_turn_eval.py 的输出
    ├── turn_relevancy/
    │   ├── per_sample_results.json
    │   └── summary.json
    ├── conversation_completeness/
    │   ├── per_sample_results.json
    │   └── summary.json
    ├── knowledge_retention/
    │   ├── per_sample_results.json
    │   └── summary.json
    └── role_adherence/
        ├── per_sample_results.json
        └── summary.json
```

### 终端输出示例

```
======================================================================
 评测维度: knowledge_retention (知识保持)
 样本数: 15
 被测模型: qwen3.5:4b
 裁判模型: qwen3:32b
======================================================================

  [1/15] 记住用户姓名
     获取模型回答...       完成 (89字)
     裁判评测中... 得分: 1.0000

  [2/15] 记住居住地点
     获取模型回答...       完成 (112字)
     裁判评测中... 得分: 1.0000
...

======================================================================
 汇总: knowledge_retention
======================================================================
  平均得分: 0.8672
  中位得分: 1.0000
  标准差:   0.1289
  最高分:   1.0000
  最低分:   0.5000
  成功/总数: 15/15
```

### 常见问题

**Q: 模型返回空回答？**
A: qwen3.5 系列模型会生成内部 thinking 文本，可能占满输出 token 预算而未生成可见内容。`multi_turn_eval.py` 已内置多重兜底：从 `thinking` 字段提取答案、将多轮对话展平为单轮查询、以及仅保留最后一条用户消息重试。如持续失败，请确认配置中的 `MAX_TOKENS` ≥ 2048。

**Q: 裁判模型打分随机？**
A: 请确保 `TEMPERATURE = 0.0`，且使用能力较强的裁判模型（如 `qwen3:32b`）。较小模型作为裁判时打分一致性较差。

**Q: GPU 显存不足？**
A: 生成模型 + 裁判模型都在 Ollama 中加载。如同时跑 `qwen3.5:9b` + `qwen3:32b`，建议 ≥ 24GB 显存的 GPU；否则请使用更小的模型。
