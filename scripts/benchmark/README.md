# 性能压测模块 / Performance Benchmarking Module

[English](#english) | [中文](#中文)

---

## English

### Overview

Measures inference performance metrics of Ollama-hosted LLMs, including:

- **TTFT** (Time To First Token) — Latency to generate the first token
- **TPOT** (Time Per Output Token) — Average latency per output token
- **Throughput** — Tokens generated per second
- **Concurrence** — Performance under concurrent requests (1, 5, 10, 20 workers)
- **Success Rate** — Percentage of successful requests

### Project Structure

```
benchmark/
├── bench_config.py         # Configuration (model, prompts, concurrency)
├── benchmark_ollama.py     # Main benchmarking script
└── README.md               # This file
```

### Configuration (`bench_config.py`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `MODEL_NAME` | Model name in Ollama | `qwen3.5:9b` |
| `OLLAMA_BASE_URL` | Ollama API endpoint | `http://127.0.0.1:11434` |
| `NUM_PROMPTS` | Number of requests in single-concurrency test | `50` |
| `CONCURRENCY` | Default concurrency workers | `1` |
| `CONCURRENCY_LEVELS` | Gradient test levels | `[1, 5, 10, 20]` |
| `CONCURRENCY_COOLDOWN` | Seconds between levels | `5` |
| `INPUT_TOKEN_LEN` | Approximate input tokens (for auto-generating prompts) | `128` |
| `OUTPUT_TOKEN_LEN` | `num_predict` for the model | `256` |
| `TEMPERATURE` | Generation temperature | `0.0` |
| `REQUEST_TIMEOUT` | HTTP request timeout (seconds) | `300` |
| `PRESET_PROMPTS` | Custom prompt list (empty = auto-generate) | `[]` |

### Usage

```bash
# From project root
cd /path/to/Intern_CMW

# 1. Edit configuration
vim scripts/benchmark/bench_config.py
#   - Change MODEL_NAME to your model
#   - Adjust NUM_PROMPTS / CONCURRENCY / CONCURRENCY_LEVELS

# 2. Run benchmark
python scripts/benchmark/benchmark_ollama.py
```

### Output Structure

Results are saved to `results/benchmark/{model_name}/`:

```
results/benchmark/{model}/
├── benchmark_summary.json       # Summary metrics (TTFT, TPOT, throughput)
├── concurrency_summary.json     # Gradient concurrency comparison table
└── detailed_results.json        # Per-request raw data (if enabled)
```

Example output in terminal:

```
======================================================================
 Ollama Performance Benchmark
 Model: qwen3.5:9b | Prompts: 50 | Concurrency: 1
======================================================================

 TTFT (First Token Latency):
   Avg:   1.85s
   P50:   1.72s
   P95:   2.41s
   P99:   2.89s

 TPOT (Per-Token Latency):
   Avg:   45ms
   P95:   58ms

 Throughput:
   Tokens/s: 22.3

 Success Rate: 100%

 [Concurrency Test]
 Level | TTFT Avg | TPOT Avg | Throughput | Success
 -------+----------+----------+------------+---------
 1      | 1.85s    | 45ms     | 22.3/s     | 100%
 5      | 3.21s    | 89ms     | 18.7/s     | 98%
 10     | 6.42s    | 156ms    | 12.1/s     | 95%
 20     | 12.80s   | 312ms    | 6.8/s      | 87%
```

### Requirements

- Ollama service running at `OLLAMA_BASE_URL`
- `MODEL_NAME` pulled via `ollama pull <model>`
- Python 3.10+ with `requests` library (in project `requirements.txt`)

### Tips

- Start with `NUM_PROMPTS=5` for a quick sanity check, then scale up
- The script sends an initial warm-up request before measuring (excluded from stats)
- Set `CONCURRENCY_LEVELS = []` if you only want a single-concurrency test
- For models > 13B parameters, reduce concurrency to avoid GPU memory pressure
- **The gradient test runs at `OLLAMA_BASE_URL` sequentially — each level has a cooldown of `CONCURRENCY_COOLDOWN` seconds**

---

## 中文

### 功能概述

测试通过 Ollama 部署的大模型在推理时的性能指标，包括：

- **TTFT**（首 Token 延迟）—— 生成第一个 Token 的时间
- **TPOT**（每 Token 输出耗时）—— 每个输出 Token 的平均延迟
- **吞吐率** —— 每秒生成的 Token 数
- **并发性能** —— 不同并发级别（1、5、10、20）下的表现对比
- **成功率** —— 请求成功比例

### 项目结构

```
benchmark/
├── bench_config.py         # 配置文件（模型、prompt、并发）
├── benchmark_ollama.py     # 压测主脚本
└── README.md               # 本文件
```

### 配置说明（`bench_config.py`）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `MODEL_NAME` | Ollama 中的模型名 | `qwen3.5:9b` |
| `OLLAMA_BASE_URL` | Ollama API 地址 | `http://127.0.0.1:11434` |
| `NUM_PROMPTS` | 单并发测试时的请求数量 | `50` |
| `CONCURRENCY` | 默认并发 worker 数 | `1` |
| `CONCURRENCY_LEVELS` | 并发梯度测试级别 | `[1, 5, 10, 20]` |
| `CONCURRENCY_COOLDOWN` | 不同级别之间的冷却时间（秒） | `5` |
| `INPUT_TOKEN_LEN` | 自动生成 prompt 的近似输入 token 数 | `128` |
| `OUTPUT_TOKEN_LEN` | 模型的 `num_predict`（输出长度） | `256` |
| `TEMPERATURE` | 生成温度 | `0.0` |
| `REQUEST_TIMEOUT` | HTTP 请求超时（秒） | `300` |
| `PRESET_PROMPTS` | 自定义 prompt 列表（空=自动生成） | `[]` |

### 使用方法

```bash
# 进入项目根目录
cd /path/to/Intern_CMW

# 1. 编辑配置
vim scripts/benchmark/bench_config.py
#    - 修改 MODEL_NAME 为你的模型
#    - 调整 NUM_PROMPTS / CONCURRENCY / CONCURRENCY_LEVELS

# 2. 运行压测
python scripts/benchmark/benchmark_ollama.py
```

### 结果输出

结果保存在 `results/benchmark/{模型名}/` 目录：

```
results/benchmark/{model}/
├── benchmark_summary.json       # 汇总指标（TTFT、TPOT、吞吐率）
├── concurrency_summary.json     # 并发梯度对比表
└── detailed_results.json        # 每条请求的原始数据（如启用）
```

终端输出示例：

```
======================================================================
 Ollama 性能压测
 模型: qwen3.5:9b | Prompt 数: 50 | 并发: 1
======================================================================

 TTFT（首 Token 延迟）:
   平均:   1.85s
   P50:    1.72s
   P95:    2.41s
   P99:    2.89s

 TPOT（每 Token 输出耗时）:
   平均:   45ms
   P95:    58ms

 吞吐率:
   Token/秒: 22.3

 成功率: 100%

 [并发梯度测试]
 级别 | TTFT 平均 | TPOT 平均 | 吞吐率   | 成功率
 ----+-----------+----------+----------+--------
 1    | 1.85s     | 45ms      | 22.3/s   | 100%
 5    | 3.21s     | 89ms      | 18.7/s   | 98%
 10   | 6.42s     | 156ms     | 12.1/s   | 95%
 20   | 12.80s    | 312ms     | 6.8/s    | 87%
```

### 运行要求

- Ollama 服务在 `OLLAMA_BASE_URL` 正常运行
- `MODEL_NAME` 已通过 `ollama pull` 下载
- Python 3.10+，并安装 `requests`（已在项目 `requirements.txt` 中）

### 小贴士

- 先用 `NUM_PROMPTS=5` 做快速验证，再扩大规模
- 脚本会先发送一个预热请求（不计入统计）
- 如果只需要单并发测试，设置 `CONCURRENCY_LEVELS = []`
- 对于 > 13B 参数的模型，建议降低并发以避免 GPU 显存压力
- **并发梯度测试按 `CONCURRENCY_LEVELS` 顺序串行执行，每级之间冷却 `CONCURRENCY_COOLDOWN` 秒**
