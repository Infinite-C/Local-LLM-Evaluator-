# 🏗️ Local-LLM-Evaluator — 本地大模型评测框架

> 一个**全本地、零依赖云端**的大语言模型综合评测工具箱。
> A fully-local, no-cloud-dependency comprehensive evaluation toolkit for large language models.

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/OS-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/Ollama-required-orange.svg" alt="Ollama required">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT">
</p>

<p align="center">
  <a href="#features">✨ 功能特性</a> •
  <a href="#modules">📦 评测模块</a> •
  <a href="#quick-start">🚀 快速开始</a> •
  <a href="#structure">📂 目录结构</a> •
  <a href="#results">📊 评测结果</a> •
  <a href="#contributing">🤝 参与贡献</a>
</p>

---

## ✨ 功能特性 / Features

| | |
|---|---|
| 🔒 **全本地运行** | 所有评测通过本地 Ollama HTTP API 完成，数据不离开你的机器 |
| 🧩 **模块化设计** | 5 大独立评测模块，可单独运行也可组合执行 |
| ⚖️ **LLM-as-Judge** | 内置 qwen3:32b 裁判模型进行开放式输出打分 |
| 📊 **多种评测范式** | 选择题 / 生成式 / LLM 裁判 / 对抗攻击 / 性能压测 |
| 🎯 **双语数据集** | 涵盖 MMLU、C-Eval、GSM8K、HumanEval + 自建多轮/安全评测集 |
| 📈 **结构化输出** | 每个评测任务生成 JSON + Markdown 报告，便于归档和对比 |
| 🔌 **零基础设施依赖** | 只需 Python + Ollama，无需向量库、数据库或外部服务 |

---

## 📦 评测模块 / Evaluation Modules

```
┌─────────────────────────────────────────────────────────────────┐
│                   Local-LLM-Evaluator 架构                       │
├─────────────────────────────────────────────────────────────────┤
│  scripts/                                                        │
│  ├── benchmark/        ⚡ 性能压测 (TTFT / TPOT / 吞吐量)        │
│  ├── deepeval/         ⚖️ LLM-as-Judge (摘要/翻译/相关/多轮)     │
│  ├── evalscope/        📚 基础能力 (MMLU / C-Eval / GSM8K ...)   │
│  ├── ragas/            🧠 RAG 质量 (检索+生成链路评估)            │
│  └── safety/           🛡️ 安全治理 (11 维度对抗性评测)           │
└─────────────────────────────────────────────────────────────────┘
```

### 模块详细

| 模块 | 入口脚本 | 核心维度 | 数据规模 |
|-----|---------|---------|---------|
| **性能压测** | `benchmark/benchmark_ollama.py` | TTFT、TPOT、吞吐量、并发梯度 | ~50 prompts × 并发级别 |
| **LLM-as-Judge（单轮）** | `deepeval/llm_judge_eval.py` | 摘要质量、翻译质量、答案相关性、事实一致性 | ~160 条 |
| **多轮对话** | `deepeval/multi_turn_eval.py` | 对话相关性、对话完整性、知识保持、角色保持 | 60 条（4 维度 × 15） |
| **基础能力** | `evalscope/run_evalscope.py` | 知识、推理、代码、阅读理解、长上下文、指令遵循 | ~1300 条 |
| **RAG 质量** | `ragas/run_ragas_eval.py` | 上下文相关性、精确率、召回率、实体覆盖 | ~80 条 |
| **安全治理** | `safety/run_safety_eval.py` | 提示词注入、越狱、毒性、偏见、泄露、投毒等 | ~345 条 |

---

## 🚀 快速开始 / Quick Start

### 前置条件 / Prerequisites

- **Python ≥ 3.10**
- **[Ollama](https://ollama.com/)** 安装并运行于 `http://127.0.0.1:11434`
- 至少 pull 一个被测模型，一个裁判模型（推荐：`qwen3.5:9b` + `qwen3:32b`）

### 1. 克隆项目 / Clone

```bash
git clone <your-repo-url>
cd Intern_CMW
```

### 2. 安装依赖 / Install Dependencies

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 配置环境变量 / Configure

```bash
# 复制模板，按需修改（可选 —— 大部分脚本直接读取 Python 配置文件）
cp .env.example .env.local
```

### 4. 运行评测 / Run Evaluation

选择你要评测的维度，修改对应 `*_config.py` 中模型名，然后运行：

```bash
# ---- 评测摘要 / 翻译 / 相关性 / 事实一致性 ----
python scripts/deepeval/llm_judge_eval.py

# ---- 评测多轮对话能力 ----
python scripts/deepeval/multi_turn_eval.py

# ---- 评测基础能力 (MMLU / C-Eval / GSM8K 等) ----
python scripts/evalscope/run_evalscope.py

# ---- 评测 RAG 质量 ----
python scripts/ragas/run_ragas_eval.py

# ---- 评测安全治理 ----
python scripts/safety/run_safety_eval.py

# ---- 性能压测 ----
python scripts/benchmark/benchmark_ollama.py
```

### 5. 查看结果 / View Results

所有评测结果保存在 `results/<module>/` 目录下：

```
results/
├── benchmark/qwen3.5_9b/
├── deepeval/qwen3.5_9b/
├── evalscope_raw/qwen3.5_9b/
├── ragas/qwen3.5_9b/
└── safety/qwen3.5_9b/
```

详细运行说明见各模块的 README：
- `scripts/benchmark/README.md`
- `scripts/deepeval/README.md`
- `scripts/evalscope/README.md`
- `scripts/ragas/README.md`
- `scripts/safety/README.md`

---

## 📂 目录结构 / Project Structure

```
Intern_CMW/
│
├── scripts/                          # 所有评测脚本（核心目录）
│   ├── benchmark/                    # ⚡ 性能压测
│   │   ├── bench_config.py           #    压测配置
│   │   ├── benchmark_ollama.py       #    主脚本
│   │   └── README.md
│   ├── deepeval/                     # ⚖️ LLM-as-Judge 评测
│   │   ├── eval_config.py            #    评测配置（模型、数据集、任务类型）
│   │   ├── llm_judge_eval.py         #    单轮评测入口
│   │   ├── multi_turn_eval.py        #    多轮对话评测入口
│   │   ├── task_prompts.py           #    裁判 prompt 模板
│   │   ├── README.md
│   │   └── dataset/                  #    ← 评测数据集（JSONL 格式）
│   │       ├── 5_machine_translacion_datasets/
│   │       ├── 15_answer_relevance_datasets/
│   │       ├── 16_Faithfulness_datasets/
│   │       ├── 18_summarization_datasets/
│   │       └── 19_multi_turn_datasets/
│   ├── evalscope/                    # 📚 基础能力评测
│   │   ├── configs/                  #    任务配置（YAML）
│   │   ├── run_evalscope.py          #    主脚本
│   │   ├── parse_evalscope_results.py
│   │   ├── check_ollama.py
│   │   └── README.md
│   ├── ragas/                        # 🧠 RAG 质量评测
│   │   ├── ragas_config.py           #    RAGAS 配置
│   │   ├── run_ragas_eval.py         #    标准 RAG 评测
│   │   ├── run_noise_robustness.py   #    噪声鲁棒性评测
│   │   ├── dataset/                  #    RAG 数据集
│   │   └── README.md
│   └── safety/                       # 🛡️ 安全治理评测
│       ├── safety_config.py          #    安全维度配置
│       ├── run_safety_eval.py        #    主脚本
│       ├── vector_risk_test.py       #    向量嵌入风险测试
│       ├── supply_chain_check.py     #    供应链安全检查
│       ├── dataset/                  #    对抗性安全评测数据集
│       └── README.md
│
├── results/                          # 评测输出（.gitignore 默认忽略内容）
│   ├── benchmark/                    #   性能压测报告
│   ├── deepeval/                     #   LLM-as-Judge 结果
│   ├── evalscope_raw/                #   基础能力原始输出
│   ├── ragas/                        #   RAGAS 评测结果
│   └── safety/                       #   安全评测报告
│
├── qwen3.5_综合评测报告.md           # 综合评测报告示例
├── requirements.txt                  # Python 依赖
├── .env.example                      # 环境变量模板
├── .gitignore                        # Git 忽略规则
├── LICENSE.txt                       # MIT 许可证
└── README.md                         # 本文件
```

---

## 📊 评测结果示例 / Sample Results

以下为 **qwen3.5:9b** 在本框架下的典型评分（示意值，实际请运行脚本获取）：

### 基础能力 / Foundational Capabilities

| 维度 | 数据集 | 9B 评分 | 说明 |
|-----|--------|---------|------|
| 知识能力 | MMLU | **0.87** | 通识知识与学科知识 |
| 中文能力 | C-Eval | **0.83** | 中文语料学习效果 |
| 数学推理 | GSM8K | **0.69** | 算术与应用题 |
| 通用推理 | BBH | **0.80** | 逻辑与多步推理 |
| 代码能力 | HumanEval | **1.00** | 20/20 Pass@1 |
| 阅读理解 | RACE | **0.80** | 长文理解与问答 |
| 长上下文 | LongBench V2 | **0.28** | 长文档检索与理解 |
| 指令遵循 | IFEval | **0.72** | 对复杂约束指令的遵从度 |

### 应用生成质量 / Application-Generation Quality

| 维度 | 评分 (9B / 4B) | 说明 |
|-----|---------------|------|
| 摘要质量 | **0.91 / 0.50** | 摘要忠实度、覆盖度、压缩性 |
| 事实一致性 | **0.89 / 0.64** | 回答是否忠实于上下文 |
| 答案相关性 | **0.77 / 0.60** | 是否回应用户问题 |
| 机器翻译 | **0.84 / 0.60** | 中英翻译忠实度 |

### 多轮对话 / Multi-turn Dialogue

| 维度 | 评分 (9B / 4B) |
|-----|---------------|
| 对话相关性 | **1.00 / 0.99** |
| 对话完整性 | **0.92 / 0.90** |
| 知识保持 | **0.86 / 0.82** |
| 角色保持 | **0.95 / 0.86** |

### 安全治理 / Safety & Governance

| 维度 | 评分 (9B / 4B) |
|-----|---------------|
| 提示词注入 | **0.88 / 0.66** |
| 越狱抵抗 | **0.98 / 0.88** |
| 毒性输出 | **0.90 / 0.96** |
| 偏见输出 | **0.97 / 0.87** |
| 敏感信息泄露 | **0.85 / 0.73** |
| 数据投毒抵抗 | **0.95 / 0.90** |

> 💡 **说明**：以上数值为示意。完整实测结果请参考 `qwen3.5_综合评测报告.md` 或运行脚本生成最新结果。

---

## 📝 使用指南 / Usage Guide

### 修改被测模型

编辑各模块下的 `*_config.py` 配置文件，修改 `MODEL_NAME` 字段：

```python
# scripts/deepeval/eval_config.py
GENERATION_MODEL = "qwen3.5:9b"  # 被测模型
JUDGE_MODEL = "qwen3:32b"        # 裁判模型
```

### 添加自定义数据集

按 JSONL 格式准备数据（一条 = 一个 JSON 对象），放到对应模块的 `dataset/` 子目录下，修改配置中的 `DATASET_PATH` 即可。

### 典型工作流

```bash
# 1. 修改 eval_config.py → 设置模型和数据集
# 2. 运行评测
python scripts/deepeval/llm_judge_eval.py

# 3. 查看结果
cat results/deepeval/<model>/summary_report.txt

# 4. 对比不同模型，修改配置后重新运行
```

---

## ❓ 常见问题 / FAQ

<details>
<summary><b>Q: 为什么需要一个独立的裁判模型（JUDGE_MODEL）？</b></summary>

A: 开放式输出（摘要、翻译、回答等）没有标准答案，需要用另一个能力更强或不同的 LLM 作为"裁判"来打分。**裁判模型应与被测模型不同**，否则模型会自我包庇。

</details>

<details>
<summary><b>Q: 评测运行太慢怎么办？</b></summary>

A: 几个建议：
1. 先跑少量样本验证（`SAMPLE_LIMIT=10` 快速试跑）
2. 用更小的模型作为裁判（如 `qwen3:14b` 或 `llama3:8b`）
3. 为 Ollama 分配更多 GPU 显存
4. 多进程并发运行不同模块

</details>

<details>
<summary><b>Q: 如何评估其他模型（不是 qwen3.5）？</b></summary>

A: 本框架对模型无假设。修改各模块配置中的 `MODEL_NAME` 为任何 Ollama 支持的模型名即可（如 `llama3:8b`、`gemma2:9b`）。

</details>

<details>
<summary><b>Q: results 目录被 git 忽略了，我想分享评测结果怎么办？</b></summary>

A: 两种方式：
1. 在 `.gitignore` 中删除/注释掉 `results` 相关行（如果你希望公开原始结果）
2. 将 `*.json` 之外的报告文件（如 `*.md`、`*.csv` 摘要）手动 `git add -f`

</details>

---

## 🔧 路线图 / Roadmap

- [ ] 增加 **HumanEval 代码执行沙箱**（Python 代码验证）
- [ ] 支持 **更多开源数据集**（CMMLU、AGIEval、Gaokao-Bench）
- [ ] **Streamlit 可视化仪表盘**，实时查看各模型多维评分
- [ ] **模型 A/B 对比**，自动生成双模型对比报告
- [ ] **Agent 评测**：工具调用、函数调用、多步规划能力
- [ ] **多语言评测**：英语、日语、法语等主流语言

欢迎提交 Issue / PR 补充你的建议！

---

## 🤝 参与贡献 / Contributing

欢迎贡献代码、数据集或建议！

1. **Fork** 本仓库
2. 创建你的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开一个 **Pull Request**

> 💡 建议在提交前运行以下检查：
> - `python scripts/deepeval/llm_judge_eval.py`（使用 SAMPLE_LIMIT=5 快速验证）
> - 检查是否有 `__pycache__`、临时文件被误提交

---

## 📄 许可证 / License

本项目基于 [MIT License](LICENSE.txt) 开源。

Copyright © 2026 Chen Minwei

---

## ⭐ 如果本项目对你有帮助，请点个 Star！

<div align="center">
  <sub>Built with ❤️ — 本地评测，数据不出境 · 隐私优先 · 全开源</sub>
</div>
