# RAG 评测模块 / RAG Evaluation Module

[English](#english) | [中文](#中文)

---

## English

### Overview

Evaluates **Retrieval-Augmented Generation (RAG)** quality using the **RAGAS** framework.

Two evaluation modes:

1. **Standard RAG Evaluation** (`run_ragas_eval.py`) — Measures whether a RAG system produces correct, faithful, and relevant answers given retrieved context.
2. **Noise Robustness Evaluation** (`run_noise_robustness.py`) — Measures how model answer quality degrades when inputs are perturbed (typos, synonyms, character insertion/deletion).

### Project Structure

```
ragas/
├── ragas_config.py              # Configuration (models, datasets, metrics, noise)
├── run_ragas_eval.py            # Main: standard RAG evaluation
├── run_noise_robustness.py      # Noise robustness evaluation
├── README.md                    # This file
└── dataset/
    ├── rag_eval_sample.jsonl     # Standard RAG evaluation dataset
    ├── noise_eval_sample.jsonl   # Dataset for noise robustness evaluation
    └── prepare_noise_dataset.py  # Helper to generate noise-perturbed variants
```

### Configuration (`ragas_config.py`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `MODEL_NAME` | Model name in Ollama (the RAG generator being evaluated) | `qwen3.5:9b` |
| `OLLAMA_BASE_URL` | Ollama API endpoint | `http://127.0.0.1:11434` |
| `ENABLED_METRICS` | List of RAGAS metrics to run | `context_relevancy`, `context_precision`, `context_recall`, `context_entities_recall` |
| `DATASET_FILE` | Path to standard evaluation dataset | `dataset/rag_eval_sample.jsonl` |
| `NOISE_DATASET_FILE` | Path to noise evaluation dataset | `dataset/noise_eval_sample.jsonl` |
| `SAMPLE_LIMIT` | Max samples (0 = all) | `0` |
| `USE_OLLAMA_BACKEND` | `True` = use Ollama for scoring; `False` = use OpenAI API | `True` |
| `RAGAS_JUDGE_MODEL` | Model used internally by RAGAS for scoring | `qwen3:32b` |
| `EMBEDDING_MODEL` | Model used for vector similarity by RAGAS | `bge-m3:latest` |
| `LLM_TIMEOUT` | Per-LLM-call timeout (seconds) | `600` |
| `REQUEST_TIMEOUT` | Per-HTTP-request timeout (seconds) | `300` |
| `RAGAS_TIMEOUT` | Overall evaluation timeout (seconds) | `3600` |
| `RAGAS_MAX_WORKERS` | Concurrent workers for RAGAS evaluation | `1` |
| `ENABLE_NOISE_ROBUSTNESS` | Whether to also run noise robustness evaluation | `True` |
| `NOISE_TYPES` | Perturbation types to apply | `typo`, `synonym`, `insert`, `delete` |
| `NOISE_INTENSITY` | Number of perturbations per sample | `3` |
| `NOISE_VARIANTS_PER_TYPE` | Number of variants per perturbation type | `2` |
| `NOISE_METRICS` | Metrics for noise evaluation | `accuracy_drop`, `semantic_similarity`, `answer_consistency` |
| `SIMILARITY_THRESHOLD` | Threshold for "significant" degradation (0–1) | `0.7` |

### Dataset Format

#### Standard RAG Evaluation (`rag_eval_sample.jsonl`)

```json
{
  "question": "用户问题",
  "contexts": ["检索文档 1", "检索文档 2"],
  "answer": "模型生成的回答",
  "ground_truth": "标准答案"
}
```

- `question` — The user query
- `contexts` — List of retrieved documents / passages
- `answer` — The answer produced by the RAG system
- `ground_truth` — Expected correct answer (for `context_recall`, `answer_relevancy`)

#### Noise Robustness Dataset (`noise_eval_sample.jsonl`)

```json
{
  "question": "用户问题",
  "ground_truth": "标准答案"
}
```

Only `question` and `ground_truth` are required; perturbations are applied automatically by the script.

### Metrics Explained

| Metric | Measures | Range | Interpretation |
|--------|---------|-------|----------------|
| `context_relevancy` | How relevant the retrieved context is to the question | 0.0–1.0 | Higher = more relevant context |
| `context_precision` | Fraction of retrieved chunks that are actually useful | 0.0–1.0 | Higher = more precise retrieval |
| `context_recall` | Fraction of ground truth claims covered by the context | 0.0–1.0 | Higher = more thorough retrieval |
| `context_entities_recall` | How well the context covers named entities in ground truth | 0.0–1.0 | Higher = better entity coverage |
| `answer_relevancy` | How directly the generated answer addresses the question | 0.0–1.0 | Higher = more relevant answer |
| `faithfulness` | How faithful the answer is to the context (no hallucination) | 0.0–1.0 | Higher = more faithful |

### Usage

```bash
# From project root
cd /path/to/Intern_CMW

# ---- Standard RAG Evaluation ----
# 1. Check configuration
vim scripts/ragas/ragas_config.py
#   - Set MODEL_NAME, RAGAS_JUDGE_MODEL, EMBEDDING_MODEL
#   - Verify DATASET_FILE points to a valid JSONL

# 2. Run
python scripts/ragas/run_ragas_eval.py

# ---- Noise Robustness Evaluation ----
python scripts/ragas/run_noise_robustness.py
```

### Output Structure

```
results/ragas/{model}/
├── ragas_results.json            # Per-metric aggregate scores
├── ragas_report.txt              # Human-readable report
└── noise_robustness/             # Noise robustness output (if enabled)
    ├── noise_results.json        # Per-noise-type scores
    ├── noise_report.txt          # Degradation analysis
    └── noise_variants.jsonl      # Generated perturbed variants
```

### Requirements

- Ollama service running with `MODEL_NAME`, `RAGAS_JUDGE_MODEL`, `EMBEDDING_MODEL` all pulled
- Python packages: `ragas`, `datasets`, `langchain`, `sentence-transformers`
  (included in project `requirements.txt`)
- For the `EMBEDDING_MODEL`, ensure you have a suitable embedding model pulled in Ollama
  (e.g., `bge-m3:latest`, `nomic-embed-text`, `mxbai-embed-large`)

---

## 中文

### 功能概述

基于 **RAGAS** 框架评测 **检索增强生成（RAG）** 的质量。

提供两种评测模式：

1. **标准 RAG 评测**（`run_ragas_eval.py`）—— 衡量 RAG 系统在给定检索上下文的情况下，是否能生成正确、忠实、相关的回答。
2. **噪声鲁棒性评测**（`run_noise_robustness.py`）—— 衡量输入被扰动（拼写错误、同义词、字符插入/删除）时，模型回答质量的下降程度。

### 项目结构

```
ragas/
├── ragas_config.py              # 配置文件（模型、数据集、指标、噪声）
├── run_ragas_eval.py            # 主脚本：标准 RAG 评测
├── run_noise_robustness.py      # 噪声鲁棒性评测
├── README.md                    # 本文件
└── dataset/
    ├── rag_eval_sample.jsonl     # 标准 RAG 评测数据集
    ├── noise_eval_sample.jsonl   # 噪声鲁棒性评测数据集
    └── prepare_noise_dataset.py  # 生成噪声扰动变体的辅助脚本
```

### 配置说明（`ragas_config.py`）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `MODEL_NAME` | Ollama 中被测 RAG 生成模型的名称 | `qwen3.5:9b` |
| `OLLAMA_BASE_URL` | Ollama API 地址 | `http://127.0.0.1:11434` |
| `ENABLED_METRICS` | 启用的 RAGAS 指标列表 | `context_relevancy`, `context_precision`, `context_recall`, `context_entities_recall` |
| `DATASET_FILE` | 标准评测数据集路径 | `dataset/rag_eval_sample.jsonl` |
| `NOISE_DATASET_FILE` | 噪声评测数据集路径 | `dataset/noise_eval_sample.jsonl` |
| `SAMPLE_LIMIT` | 最多评测样本数（0 = 全部） | `0` |
| `USE_OLLAMA_BACKEND` | `True` = 用 Ollama 评分；`False` = 用 OpenAI API | `True` |
| `RAGAS_JUDGE_MODEL` | RAGAS 内部用于评分的模型 | `qwen3:32b` |
| `EMBEDDING_MODEL` | RAGAS 内部用于向量相似度的模型 | `bge-m3:latest` |
| `LLM_TIMEOUT` | 单次 LLM 调用超时（秒） | `600` |
| `REQUEST_TIMEOUT` | 单次 HTTP 请求超时（秒） | `300` |
| `RAGAS_TIMEOUT` | 整体评测超时（秒） | `3600` |
| `RAGAS_MAX_WORKERS` | RAGAS 评测并发 worker 数 | `1` |
| `ENABLE_NOISE_ROBUSTNESS` | 是否同时运行噪声鲁棒性评测 | `True` |
| `NOISE_TYPES` | 应用的扰动类型 | `typo`, `synonym`, `insert`, `delete` |
| `NOISE_INTENSITY` | 每个样本的扰动次数 | `3` |
| `NOISE_VARIANTS_PER_TYPE` | 每种扰动类型生成的变体数 | `2` |
| `NOISE_METRICS` | 噪声评测使用的指标 | `accuracy_drop`, `semantic_similarity`, `answer_consistency` |
| `SIMILARITY_THRESHOLD` | 视为"严重退化"的语义相似度阈值（0–1） | `0.7` |

### 数据集格式

#### 标准 RAG 数据集（`rag_eval_sample.jsonl`）

```json
{
  "question": "用户问题",
  "contexts": ["检索文档 1", "检索文档 2"],
  "answer": "模型生成的回答",
  "ground_truth": "标准答案"
}
```

- `question` — 用户查询
- `contexts` — 检索到的文档/段落列表
- `answer` — RAG 系统生成的回答
- `ground_truth` — 期望的正确答案（用于 `context_recall`, `answer_relevancy`）

#### 噪声鲁棒性数据集（`noise_eval_sample.jsonl`）

```json
{
  "question": "用户问题",
  "ground_truth": "标准答案"
}
```

只需要 `question` 和 `ground_truth`；脚本会自动在原始问题上应用各类扰动。

### 指标说明

| 指标 | 衡量内容 | 取值范围 | 含义 |
|------|---------|---------|------|
| `context_relevancy` | 检索到的上下文与问题的相关性 | 0.0–1.0 | 越高 = 上下文越相关 |
| `context_precision` | 检索到的上下文中真正有用的片段比例 | 0.0–1.0 | 越高 = 检索越精准 |
| `context_recall` | 标准答案中的关键信息被上下文覆盖的比例 | 0.0–1.0 | 越高 = 检索越全面 |
| `context_entities_recall` | 上下文覆盖标准答案中命名实体的程度 | 0.0–1.0 | 越高 = 实体覆盖越好 |
| `answer_relevancy` | 生成回答与问题的直接相关性 | 0.0–1.0 | 越高 = 回答越切题 |
| `faithfulness` | 回答对上下文的忠实程度（无幻觉） | 0.0–1.0 | 越高 = 回答越忠实 |

### 使用方法

```bash
# 进入项目根目录
cd /path/to/Intern_CMW

# ---- 标准 RAG 评测 ----
# 1. 检查配置
vim scripts/ragas/ragas_config.py
#    - 设置 MODEL_NAME、RAGAS_JUDGE_MODEL、EMBEDDING_MODEL
#    - 确认 DATASET_FILE 指向有效的 JSONL 文件

# 2. 运行
python scripts/ragas/run_ragas_eval.py

# ---- 噪声鲁棒性评测 ----
python scripts/ragas/run_noise_robustness.py
```

### 结果输出

```
results/ragas/{模型名}/
├── ragas_results.json            # 各指标聚合分数
├── ragas_report.txt              # 可读报告
└── noise_robustness/             # 噪声鲁棒性输出（如启用）
    ├── noise_results.json        # 按噪声类型打分
    ├── noise_report.txt          # 退化分析
    └── noise_variants.jsonl      # 生成的扰动变体
```

### 运行要求

- Ollama 服务运行，且已 pull `MODEL_NAME`、`RAGAS_JUDGE_MODEL`、`EMBEDDING_MODEL`
- Python 包：`ragas`, `datasets`, `langchain`, `sentence-transformers`
  （已包含在项目 `requirements.txt` 中）
- 关于 `EMBEDDING_MODEL`：请在 Ollama 中 pull 合适的嵌入模型
  （例如 `bge-m3:latest`, `nomic-embed-text`, `mxbai-embed-large`）
