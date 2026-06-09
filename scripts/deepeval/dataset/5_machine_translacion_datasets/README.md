# 机器翻译评测数据集 / Machine Translation Evaluation Dataset

[English](#english) | [中文](#中文)

---

## English

### Overview

Dataset for evaluating **machine translation quality**. A judge model compares a model-generated translation against a reference translation.

### Files

```
5_machine_translacion_datasets/      # Note: "translacion" is a typo in the project; kept as-is
├── README.md                         # This file
└── translation_datasets.jsonl        # Main dataset (JSONL, ~30 samples)
```

**Note on directory name:** The directory is named `5_machine_translacion_datasets` (missing the second "t" — "translation" → "translacion"). This is a known naming artifact in the project structure and is preserved for backward compatibility. The evaluation scripts use this exact path.

### Dataset Format

Each line is a JSON object:

```json
{
  "query": "源句子（如英文原文）",
  "response": "参考翻译（如人工中文译文）"
}
```

- `query` — The source text (e.g., English sentence)
- `response` — A human-written or high-quality reference translation (e.g., Chinese)

During evaluation:
1. The **generation model** receives `query` and produces its own translation
2. The **judge model** compares the model's translation to the reference `response` and scores it on quality / faithfulness / fluency

### Task Type

- **Task name in `eval_config.py`**: `translation`
- **TASK_TYPE in eval_config.py**: Set to `"translation"` or `"auto"`
- The judge prompt (in `task_prompts.py`) evaluates: faithfulness to source, natural fluency in target language, and completeness

### Usage

```bash
# 1. Configure
vim scripts/deepeval/eval_config.py
#   TASK_TYPE = "translation"
#   DATASET_PATH = "scripts/deepeval/dataset/5_machine_translacion_datasets/translation_datasets.jsonl"

# 2. Run
python scripts/deepeval/llm_judge_eval.py
```

### Results

Output is written to:
```
results/deepeval/{model}/translation/
├── individual_scores.json
├── summary_report.txt
└── statistics.json
```

---

## 中文

### 功能概述

用于评估 **机器翻译质量** 的数据集。裁判模型将被测模型生成的译文与参考译文进行对比。

### 文件列表

```
5_machine_translacion_datasets/      # 注意：目录名中 "translacion" 是拼写遗留（应为 "translation"）
├── README.md                         # 本文件
└── translation_datasets.jsonl        # 主数据集（JSONL，约 30 条）
```

**关于目录名的说明：** 该目录实际名为 `5_machine_translacion_datasets`（缺少第二个 "t"，"translation" → "translacion"）。这是项目结构中的已知命名遗留，为保证与评测脚本路径一致，保留原目录名。

### 数据集格式

每行为一个 JSON 对象：

```json
{
  "query": "源句子（如英文原文）",
  "response": "参考翻译（如人工中文译文）"
}
```

- `query` — 源语言文本（如英文句子）
- `response` — 高质量参考翻译（如人工中文译文）

评测流程：
1. **生成模型** 接收 `query` 并生成翻译
2. **裁判模型** 将生成模型的译文与参考 `response` 对比，就忠实度、流畅度、完整性打分

### 任务类型

- **`eval_config.py` 中的任务名**: `translation`
- **`eval_config.py` 中的 TASK_TYPE**: 设为 `"translation"` 或 `"auto"`
- 裁判提示词（`task_prompts.py`）主要评估：忠实还原原文含义、目标语言自然流畅、信息完整性

### 使用方法

```bash
# 1. 修改配置
vim scripts/deepeval/eval_config.py
#   TASK_TYPE = "translation"
#   DATASET_PATH = "scripts/deepeval/dataset/5_machine_translacion_datasets/translation_datasets.jsonl"

# 2. 运行
python scripts/deepeval/llm_judge_eval.py
```

### 结果输出

结果保存到：
```
results/deepeval/{模型名}/translation/
├── individual_scores.json
├── summary_report.txt
└── statistics.json
```
