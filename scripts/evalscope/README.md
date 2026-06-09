# 基础能力评测模块 / Foundation Capability Evaluation Module

[English](#english) | [中文](#中文)

---

## English

### Overview

Evaluates foundational LLM capabilities using **OpenEvalScope** / **OpenCompass** benchmarks.
This module runs standard benchmarks and aggregates results, giving a broad overview of a model's reasoning, knowledge, coding, reading comprehension, instruction-following, and long-context abilities.

### Project Structure

```
evalscope/
├── configs/
│   ├── eval_tasks.yaml          # Definition of benchmark tasks (enabled/disabled, limits)
│   ├── models.yaml              # Model configurations (model names, gen_kwargs)
│   └── score_mapping.yaml       # Dimension weights and final score aggregation
├── check_ollama.py              # Sanity check: verify Ollama models are reachable
├── run_evalscope.py             # Main: run all enabled benchmark tasks
├── parse_evalscope_results.py   # Parse raw outputs → structured report
└── README.md                    # This file
```

### Supported Benchmarks

| Task | Display Name | Dimension | Metric | Task Type |
|------|-------------|-----------|--------|-----------|
| `mmlu` | 英文通用知识能力 | `general_knowledge` | `acc` | multiple_choice |
| `ceval` | 中文知识能力 | `chinese_knowledge` | `acc` | multiple_choice |
| `mgsm` | 多语言数学推理 | `multilingual_math` | `acc` | math |
| `gsm8k` | 数学推理能力 | `math_reasoning` | `acc` | math |
| `bbh` | BIG-Bench Hard | `reasoning` | `acc` | generation |
| `hellaswag` | 常识推理 | `commonsense_reasoning` | `acc` | multiple_choice |
| `humaneval` | 代码能力 | `coding` | `pass_at_1` | code |
| `race` | 阅读理解 | `reading_comprehension` | `acc` | multiple_choice |
| `conll2003` | 命名实体识别 | `ner` | `f1` | generation |
| `longbench_v2` | 长上下文理解 | `long_context` | `f1` | generation |
| `ifeval` | 指令遵循能力 | `instruction_following` | `strict_loose_acc` | instruction_following |
| `truthfulqa` | 真实性 | `truthfulness` | `mc2` | generation |

**Disabled by default** (set `enabled: true` in `eval_tasks.yaml` to enable):
- `multi_if` — Multi-language instruction following
- `tau2_bench` — Conversational agent benchmark

### Configuration (`configs/eval_tasks.yaml`)

Each task is a YAML entry:

```yaml
- name: mmlu
  display_name: 英文通用知识能力
  dimension: general_knowledge
  dataset: mmlu
  metric: acc
  limit: 5
  enabled: true
  need_judge_model: false
  task_type: multiple_choice
```

Key fields:
- `limit` — Number of samples to run (use small values like 5–50 for quick runs)
- `enabled` — `true` to run this task
- `need_judge_model` — Whether a separate judge model is required for this task
- `task_type` — Influences how the prompt is structured

**Model configuration** (`configs/models.yaml`):

```yaml
model:
  name: qwen3.5:9b
  backend: ollama
  gen_kwargs:
    temperature: 0.0
    max_new_tokens: 2048
    num_ctx: 4096
```

**Score aggregation** (`configs/score_mapping.yaml`):

Controls how individual benchmark scores are weighted into the final aggregate score.

### Usage

```bash
# From project root
cd /path/to/Intern_CMW

# Step 0 (optional but recommended): verify Ollama connectivity
python scripts/evalscope/check_ollama.py

# Step 1: Run all enabled benchmarks
# Edit configs/eval_tasks.yaml to enable/disable individual tasks
python scripts/evalscope/run_evalscope.py

# Step 2: Parse results and generate report
python scripts/evalscope/parse_evalscope_results.py
```

### Output Structure

```
results/evalscope/{model}/
├── raw/                           # Raw per-benchmark output
│   ├── mmlu_raw.json
│   ├── ceval_raw.json
│   └── ...
├── per_benchmark/                 # Individual benchmark reports
│   ├── mmlu_report.json
│   ├── ceval_report.json
│   └── ...
└── summary/                       # Aggregated summary
    ├── full_report.txt            # Human-readable report
    ├── full_report.json           # Structured metrics
    └── radar_chart.png            # (if matplotlib available) radar chart
```

### Tips

- For **quick sanity checks**, set `limit: 5` across all tasks — entire run should finish in minutes
- For **full evaluation**, set `limit: 0` (use all available samples) — this can take hours for large benchmarks
- Ollama must already have the model pulled (`ollama pull <model>`)
- The script uses the HTTP API at `OLLAMA_BASE_URL` — no special Python bindings required
- `humaneval` and `bbh` are particularly compute-intensive; consider setting lower limits for these

---

## 中文

### 功能概述

基于 **EvalScope / OpenCompass** 框架评测大模型的**基础能力**。运行多个标准基准任务，并聚合结果，全面反映模型在推理、知识、代码、阅读理解、指令遵循和长上下文方面的能力。

### 项目结构

```
evalscope/
├── configs/
│   ├── eval_tasks.yaml          # 基准任务定义（启用/禁用、样本数）
│   ├── models.yaml              # 模型配置（模型名、生成参数）
│   └── score_mapping.yaml       # 维度权重与最终分数聚合
├── check_ollama.py              # 健康检查：验证 Ollama 模型可访问
├── run_evalscope.py             # 主脚本：运行所有启用的基准任务
├── parse_evalscope_results.py   # 解析原始输出 → 结构化报告
└── README.md                    # 本文件
```

### 支持的基准任务

| 任务 | 展示名称 | 维度 | 指标 | 任务类型 |
|------|---------|------|------|---------|
| `mmlu` | 英文通用知识能力 | `general_knowledge` | `acc` | 选择题 |
| `ceval` | 中文知识能力 | `chinese_knowledge` | `acc` | 选择题 |
| `mgsm` | 多语言数学推理 | `multilingual_math` | `acc` | 数学 |
| `gsm8k` | 数学推理能力 | `math_reasoning` | `acc` | 数学 |
| `bbh` | BIG-Bench Hard | `reasoning` | `acc` | 生成 |
| `hellaswag` | 常识推理 | `commonsense_reasoning` | `acc` | 选择题 |
| `humaneval` | 代码能力 | `coding` | `pass_at_1` | 代码 |
| `race` | 阅读理解 | `reading_comprehension` | `acc` | 选择题 |
| `conll2003` | 命名实体识别 | `ner` | `f1` | 生成 |
| `longbench_v2` | 长上下文理解 | `long_context` | `f1` | 生成 |
| `ifeval` | 指令遵循能力 | `instruction_following` | `strict_loose_acc` | 指令遵循 |
| `truthfulqa` | 真实性 | `truthfulness` | `mc2` | 生成 |

**默认禁用**（在 `eval_tasks.yaml` 中设 `enabled: true` 以启用）：
- `multi_if` — 多语言指令遵循
- `tau2_bench` — 对话代理基准

### 配置说明（`configs/eval_tasks.yaml`）

每个任务为一条 YAML 记录：

```yaml
- name: mmlu
  display_name: 英文通用知识能力
  dimension: general_knowledge
  dataset: mmlu
  metric: acc
  limit: 5
  enabled: true
  need_judge_model: false
  task_type: multiple_choice
```

关键字段：
- `limit` — 运行的样本数（快速测试时使用 5–50）
- `enabled` — `true` 为运行该任务
- `need_judge_model` — 该任务是否需要独立的裁判模型
- `task_type` — 影响 prompt 构造方式

**模型配置**（`configs/models.yaml`）：

```yaml
model:
  name: qwen3.5:9b
  backend: ollama
  gen_kwargs:
    temperature: 0.0
    max_new_tokens: 2048
    num_ctx: 4096
```

**分数聚合**（`configs/score_mapping.yaml`）：

控制各项基准分数如何加权汇总为最终综合分数。

### 使用方法

```bash
# 在项目根目录
cd /path/to/Intern_CMW

# 第 0 步（建议执行）：验证 Ollama 连接
python scripts/evalscope/check_ollama.py

# 第 1 步：运行所有启用的基准任务
# 修改 configs/eval_tasks.yaml 启用/禁用各任务
python scripts/evalscope/run_evalscope.py

# 第 2 步：解析结果并生成报告
python scripts/evalscope/parse_evalscope_results.py
```

### 结果输出

```
results/evalscope/{模型名}/
├── raw/                           # 各基准原始输出
│   ├── mmlu_raw.json
│   ├── ceval_raw.json
│   └── ...
├── per_benchmark/                 # 各基准的单独报告
│   ├── mmlu_report.json
│   ├── ceval_report.json
│   └── ...
└── summary/                       # 汇总
    ├── full_report.txt            # 可读报告
    ├── full_report.json           # 结构化指标
    └── radar_chart.png            # （如装了 matplotlib）雷达图
```

### 小贴士

- **快速验证**：将所有任务的 `limit` 设为 5 —— 整个评测几分钟内完成
- **完整评测**：将 `limit` 设为 `0`（使用全部样本）—— 大型基准可能需要数小时
- Ollama 中必须已 pull 相应模型（`ollama pull <模型名>`）
- 脚本通过 HTTP API 调用 Ollama，无需额外 Python 绑定
- `humaneval` 和 `bbh` 计算开销较大，建议在这些任务上设置较小的 `limit`
