# 事实一致性评测数据集 / Faithfulness Evaluation Dataset

[English](#english) | [中文](#中文)

---

## English

### Overview

Dataset for evaluating **factuality / faithfulness** of LLM outputs against provided source context. The goal is to measure whether a model's claims are *entailed by* (supported by) the original source text, versus fabricated / hallucinated.

Typical use case: after a RAG system retrieves a document and generates a response, does the response only contain information supported by the retrieved document?

### Files

```
16_Faithfulness_datasets/
├── README.md                        # This file
└── faithfulness_dataset.jsonl       # Main dataset (JSONL, ~30 samples)
```

### Dataset Format

Each line is a JSON object with the following structure:

```json
{
  "query": "原文段落或检索到的文档，作为事实依据",
  "response": "模型基于上述上下文生成的声明，需要被验证是否忠实"
}
```

- `query` — The source text / passage (ground truth context)
- `response` — A claim, assertion or summary that the model produced

During evaluation, the **judge model** scores the `response` on a 0.0–1.0 scale based on whether every statement in `response` is directly supported by `query`.

### Task Type

- **Task name for `eval_config.py`**: `faithfulness`
- **TASK_TYPE in eval_config.py**: Set to `"faithfulness"` or `"auto"`
- **Judge prompt**: defined in `scripts/deepeval/task_prompts.py` — the judge checks:
  1. Are all claims in the response supported by the context?
  2. Is the response free of fabricated information?
  3. Is the response free of contradictory statements?

### Usage

```bash
# 1. Set up eval_config.py
vim scripts/deepeval/eval_config.py
#   TASK_TYPE = "faithfulness"
#   DATASET_PATH = "scripts/deepeval/dataset/16_Faithfulness_datasets/faithfulness_dataset.jsonl"

# 2. Run evaluation
python scripts/deepeval/llm_judge_eval.py
```

### Results

Output is written to:
```
results/deepeval/{model}/faithfulness/
├── individual_scores.json
├── summary_report.txt
└── statistics.json
```

Expected aggregate scores for a well-performing model: 0.70–0.95. Scores below 0.5 indicate significant hallucination risk.

---

## 中文

### 功能概述

用于评估大模型输出的**事实一致性（faithfulness）**的数据集。核心目标是：模型基于给定上下文生成的声明/回答，是否每一条陈述都能被原文支持（entailed），是否存在编造或幻觉。

典型应用场景：RAG 系统检索到文档后，模型基于检索文档生成回答，验证回答中是否只包含原文支持的信息。

### 文件列表

```
16_Faithfulness_datasets/
├── README.md                        # 本文件
└── faithfulness_dataset.jsonl       # 主数据集（JSONL，约 30 条）
```

### 数据集格式

每行为一个 JSON 对象，结构如下：

```json
{
  "query": "原文段落或检索到的文档，作为事实依据",
  "response": "模型基于上述上下文生成的声明，需要被验证是否忠实"
}
```

- `query` — 源文本 / 文档（作为事实依据的上下文）
- `response` — 模型基于该上下文生成的声明，需要被验证

评测时，**裁判模型** 基于 `query` 对 `response` 打 0.0–1.0 的分数，衡量 `response` 中的每个陈述是否都被 `query` 支持。

### 任务类型

- **`eval_config.py` 中的任务名**: `faithfulness`
- **`eval_config.py` 中的 TASK_TYPE**: 设为 `"faithfulness"` 或 `"auto"`
- **裁判提示词**: 定义在 `scripts/deepeval/task_prompts.py` 中，裁判检查：
  1. response 中的所有声明是否都有上下文支持？
  2. response 是否不包含编造的信息？
  3. response 是否不存在与上下文矛盾的陈述？

### 使用方法

```bash
# 1. 修改 eval_config.py
vim scripts/deepeval/eval_config.py
#   TASK_TYPE = "faithfulness"
#   DATASET_PATH = "scripts/deepeval/dataset/16_Faithfulness_datasets/faithfulness_dataset.jsonl"

# 2. 运行评测
python scripts/deepeval/llm_judge_eval.py
```

### 结果输出

结果保存到：
```
results/deepeval/{模型名}/faithfulness/
├── individual_scores.json
├── summary_report.txt
└── statistics.json
```

表现良好的模型通常聚合得分在 0.70–0.95。得分低于 0.5 提示严重的幻觉风险。
