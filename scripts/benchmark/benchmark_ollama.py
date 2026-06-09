#!/usr/bin/env python3
"""
Ollama 性能压测脚本
支持指标：
- TTFT (Time to First Token)：首 token 延迟
- TPOT (Time Per Output Token)：每 token 平均生成时间
- End-to-End Latency：总响应延迟
- Throughput：吞吐量 (tokens/s)
- 并发压测：多用户同时请求

用法：
    python benchmark_ollama.py

输出：
    results/benchmark/{model_name}/
    ├── benchmark_results.json   详细结果
    ├── benchmark_summary.json   汇总统计
    └── benchmark_report.txt     可读报告
"""
import asyncio
import json
import random
import re
import string
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import aiohttp
import sys

# 添加脚本所在目录到路径
SCRIPT_DIR = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(SCRIPT_DIR))

import bench_config as cfg


# ═══════════════════════════════════════════════════════════════
#  Prompt 生成
# ═══════════════════════════════════════════════════════════════

def generate_random_prompt(target_len: int = 128) -> str:
    """生成随机 prompt，近似达到目标 token 长度"""
    # 中文一个字约 1 token，英文一个词约 1-2 token
    # 混合生成
    base = cfg.RANDOM_PROMPT_PREFIX
    # 用随机中文字符和标点填充
    chars = "这是一段用于测试大语言模型性能的随机文本内容包含各种常见汉字和标点符号，"
    current_len = len(base)
    while current_len < target_len:
        chunk = ''.join(random.choices(chars, k=min(50, target_len - current_len)))
        base += chunk
        current_len = len(base)
    return base


def prepare_prompts() -> List[str]:
    """准备测试 prompt 列表"""
    if cfg.PRESET_PROMPTS and len(cfg.PRESET_PROMPTS) > 0:
        prompts = cfg.PRESET_PROMPTS[:cfg.NUM_PROMPTS]
        # 如果不够，用随机 prompt 补充
        while len(prompts) < cfg.NUM_PROMPTS:
            prompts.append(generate_random_prompt(cfg.INPUT_TOKEN_LEN))
        return prompts

    return [generate_random_prompt(cfg.INPUT_TOKEN_LEN) for _ in range(cfg.NUM_PROMPTS)]


# ═══════════════════════════════════════════════════════════════
#  单次请求测试（Streaming）
# ═══════════════════════════════════════════════════════════════

async def send_single_request(
    session: aiohttp.ClientSession,
    prompt: str,
    request_id: int,
    semaphore: Optional[asyncio.Semaphore] = None
) -> Dict[str, Any]:
    """
    发送单个 streaming 请求，记录 TTFT、TPOT、总延迟等。
    """
    url = f"{cfg.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": cfg.MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "options": {
            "temperature": cfg.TEMPERATURE,
            "num_predict": cfg.OUTPUT_TOKEN_LEN,
        }
    }

    result = {
        "request_id": request_id,
        "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
        "prompt_length": len(prompt),
        "success": False,
        "error": None,
        "ttft": -1.0,          # Time to First Token (秒)
        "tpot": -1.0,           # Time Per Output Token (秒)
        "e2e_latency": -1.0,    # End-to-End Latency (秒)
        "output_tokens": 0,
        "output_length": 0,
        "tokens_per_second": 0.0,
        "start_time": 0.0,
        "end_time": 0.0,
    }

    if semaphore:
        await semaphore.acquire()

    try:
        start_time = time.perf_counter()

        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=cfg.REQUEST_TIMEOUT)) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                result["error"] = f"HTTP {resp.status}: {error_text[:200]}"
                return result

            first_token_time = None
            token_count = 0
            full_response = ""

            async for line in resp.content:
                line = line.decode('utf-8', errors='ignore').strip()
                if not line:
                    continue

                # Ollama streaming 格式：每行一个 JSON
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg = chunk.get("message", {})
                content = msg.get("content", "") or msg.get("thinking", "")
                if not content:
                    # 检查是否是最终响应
                    if chunk.get("done", False):
                        break
                    continue

                # 记录首 token 时间
                if first_token_time is None:
                    first_token_time = time.perf_counter()

                full_response += content
                token_count += 1

            end_time = time.perf_counter()

            # 计算指标
            if first_token_time is not None:
                ttft = first_token_time - start_time
                total_gen_time = end_time - first_token_time
                e2e = end_time - start_time

                result["success"] = True
                result["ttft"] = round(ttft, 4)
                result["tpot"] = round(total_gen_time / token_count, 4) if token_count > 0 else 0.0
                result["e2e_latency"] = round(e2e, 4)
                result["output_tokens"] = token_count
                result["output_length"] = len(full_response)
                result["tokens_per_second"] = round(token_count / total_gen_time, 2) if total_gen_time > 0 else 0.0
                result["start_time"] = round(start_time, 4)
                result["end_time"] = round(end_time, 4)
            else:
                result["error"] = "未收到任何 token"

    except asyncio.TimeoutError:
        result["error"] = f"请求超时（{cfg.REQUEST_TIMEOUT}s）"
    except Exception as e:
        result["error"] = str(e)[:200]
    finally:
        if semaphore:
            semaphore.release()

    return result


# ═══════════════════════════════════════════════════════════════
#  并发压测
# ═══════════════════════════════════════════════════════════════

async def run_benchmark(concurrency: int = None, prompts: List[str] = None) -> List[Dict[str, Any]]:
    """执行压测，可指定并发数和 prompt 列表"""
    if concurrency is None:
        concurrency = cfg.CONCURRENCY
    if prompts is None:
        prompts = prepare_prompts()
    semaphore = asyncio.Semaphore(concurrency) if concurrency > 0 else None

    print(f"\n{'='*70}")
    print(f"Ollama 性能压测")
    print(f"{'='*70}")
    print(f"模型: {cfg.MODEL_NAME}")
    print(f"请求数: {len(prompts)}")
    print(f"并发数: {concurrency}")
    print(f"请求速率: {cfg.REQUEST_RATE if cfg.REQUEST_RATE > 0 else '不限制'} req/s")
    print(f"输入长度: ~{cfg.INPUT_TOKEN_LEN} tokens")
    print(f"输出长度: ~{cfg.OUTPUT_TOKEN_LEN} tokens")
    print(f"温度: {cfg.TEMPERATURE}")
    print(f"{'='*70}\n")

    connector = aiohttp.TCPConnector(limit=concurrency * 2)
    async with aiohttp.ClientSession(connector=connector) as session:
        # 预热请求
        print("🔥 预热中（1次请求）...")
        warmup = await send_single_request(session, "你好", 0, semaphore)
        if warmup["success"]:
            print(f"   预热成功: TTFT={warmup['ttft']:.3f}s, 输出{warmup['output_tokens']} tokens")
        else:
            print(f"   ⚠️ 预热失败: {warmup['error']}")
            print("   继续执行压测...")

        # 正式压测
        print(f"\n🚀 开始压测（{len(prompts)} 个请求）...")
        overall_start = time.perf_counter()

        tasks = []
        for i, prompt in enumerate(prompts):
            # 控制请求速率
            if cfg.REQUEST_RATE > 0:
                delay = 1.0 / cfg.REQUEST_RATE
                await asyncio.sleep(delay)

            task = send_single_request(session, prompt, i + 1, semaphore)
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        overall_end = time.perf_counter()
        total_wall_time = overall_end - overall_start

    print(f"\n✅ 压测完成，总耗时: {total_wall_time:.2f}s")
    return list(results), total_wall_time


# ═══════════════════════════════════════════════════════════════
#  结果统计与输出
# ═══════════════════════════════════════════════════════════════

def compute_statistics(values: List[float]) -> Dict[str, float]:
    """计算统计指标：mean, median, P90, P95, P99, min, max"""
    if not values:
        return {}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    return {
        "mean": round(sum(sorted_vals) / n, 4),
        "median": round(sorted_vals[n // 2], 4),
        "p90": round(sorted_vals[int(n * 0.9)], 4),
        "p95": round(sorted_vals[int(n * 0.95)], 4),
        "p99": round(sorted_vals[min(int(n * 0.99), n - 1)], 4),
        "min": round(sorted_vals[0], 4),
        "max": round(sorted_vals[-1], 4),
    }


def build_summary(results: List[Dict[str, Any]], total_wall_time: float) -> Dict[str, Any]:
    """构建汇总统计"""
    success_results = [r for r in results if r["success"]]
    failed_results = [r for r in results if not r["success"]]

    ttft_values = [r["ttft"] for r in success_results]
    tpot_values = [r["tpot"] for r in success_results]
    e2e_values = [r["e2e_latency"] for r in success_results]
    tps_values = [r["tokens_per_second"] for r in success_results]
    total_output_tokens = sum(r["output_tokens"] for r in success_results)

    return {
        "model": cfg.MODEL_NAME,
        "timestamp": datetime.now().isoformat(),
        "config": {
            "num_prompts": cfg.NUM_PROMPTS,
            "concurrency": cfg.CONCURRENCY,
            "request_rate": cfg.REQUEST_RATE,
            "input_token_len": cfg.INPUT_TOKEN_LEN,
            "output_token_len": cfg.OUTPUT_TOKEN_LEN,
            "temperature": cfg.TEMPERATURE,
        },
        "total_requests": len(results),
        "successful_requests": len(success_results),
        "failed_requests": len(failed_results),
        "total_wall_time": round(total_wall_time, 4),
        "total_output_tokens": total_output_tokens,
        # 吞吐量
        "throughput_requests_per_sec": round(len(success_results) / total_wall_time, 2),
        "throughput_tokens_per_sec": round(total_output_tokens / total_wall_time, 2),
        # TTFT 统计
        "ttft": compute_statistics(ttft_values),
        # TPOT 统计
        "tpot": compute_statistics(tpot_values),
        # 端到端延迟统计
        "e2e_latency": compute_statistics(e2e_values),
        # 吞吐量统计
        "tokens_per_second": compute_statistics(tps_values),
    }


def print_report(summary: Dict[str, Any]):
    """打印可读报告"""
    print("\n" + "=" * 70)
    print(f"性能压测报告 - {summary['model']}")
    print(f"时间: {summary['timestamp']}")
    print("=" * 70)

    print(f"\n📊 基本统计")
    print(f"  总请求数:     {summary['total_requests']}")
    print(f"  成功请求:     {summary['successful_requests']}")
    print(f"  失败请求:     {summary['failed_requests']}")
    print(f"  总耗时:       {summary['total_wall_time']:.2f}s")
    print(f"  总输出 tokens: {summary['total_output_tokens']}")

    print(f"\n🚀 吞吐量")
    print(f"  请求吞吐:     {summary['throughput_requests_per_sec']:.2f} req/s")
    print(f"  Token 吞吐:   {summary['throughput_tokens_per_sec']:.2f} tokens/s")

    def print_stat_block(name: str, stats: Dict[str, float], unit: str = "s"):
        if not stats:
            print(f"\n  {name}: 无数据")
            return
        print(f"\n  {name} ({unit})")
        print(f"    Mean:   {stats['mean']:.4f}")
        print(f"    Median: {stats['median']:.4f}")
        print(f"    P90:    {stats['p90']:.4f}")
        print(f"    P95:    {stats['p95']:.4f}")
        print(f"    P99:    {stats['p99']:.4f}")
        print(f"    Min:    {stats['min']:.4f}")
        print(f"    Max:    {stats['max']:.4f}")

    print(f"\n⏱️  延迟指标")
    print_stat_block("TTFT (首 token 延迟)", summary.get("ttft", {}), "s")
    print_stat_block("TPOT (每 token 时间)", summary.get("tpot", {}), "s")
    print_stat_block("E2E (端到端延迟)", summary.get("e2e_latency", {}), "s")
    print_stat_block("Tokens/s (单请求吞吐)", summary.get("tokens_per_second", {}), "tokens/s")

    print("\n" + "=" * 70)


def save_results(results: List[Dict[str, Any]], summary: Dict[str, Any]):
    """保存结果到文件"""
    output_dir = cfg.OUTPUT_DIR / cfg.MODEL_NAME.replace(":", "_")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 详细结果
    with open(output_dir / "benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 汇总统计
    with open(output_dir / "benchmark_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 可读报告
    report_lines = []
    report_lines.append(f"性能压测报告 - {summary['model']}")
    report_lines.append(f"时间: {summary['timestamp']}")
    report_lines.append("=" * 50)
    report_lines.append(f"总请求数: {summary['total_requests']}")
    report_lines.append(f"成功请求: {summary['successful_requests']}")
    report_lines.append(f"失败请求: {summary['failed_requests']}")
    report_lines.append(f"总耗时: {summary['total_wall_time']:.2f}s")
    report_lines.append(f"总输出 tokens: {summary['total_output_tokens']}")
    report_lines.append(f"请求吞吐: {summary['throughput_requests_per_sec']:.2f} req/s")
    report_lines.append(f"Token 吞吐: {summary['throughput_tokens_per_sec']:.2f} tokens/s")

    for metric_name, stats in [("TTFT", summary.get("ttft", {})),
                                ("TPOT", summary.get("tpot", {})),
                                ("E2E", summary.get("e2e_latency", {}))]:
        if stats:
            report_lines.append(f"\n{metric_name} (s):")
            report_lines.append(f"  Mean={stats['mean']:.4f}  Median={stats['median']:.4f}  "
                               f"P90={stats['p90']:.4f}  P95={stats['p95']:.4f}  P99={stats['p99']:.4f}")

    with open(output_dir / "benchmark_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    return output_dir


# ═══════════════════════════════════════════════════════════════
#  并发梯度压测
# ═══════════════════════════════════════════════════════════════

def print_concurrency_comparison(all_summaries: List[Dict[str, Any]]):
    """打印并发梯度对比表格"""
    if not all_summaries:
        return

    print("\n" + "=" * 90)
    print(f"并发能力对比报告 - {all_summaries[0]['model']}")
    print("=" * 90)

    # 表头
    header = f"{'并发数':>6} | {'成功率':>6} | {'TTFT(s)':>10} | {'TPOT(s)':>10} | {'E2E(s)':>10} | {'吞吐(req/s)':>11} | {'吞吐(tok/s)':>11} | {'失败':>4}"
    print(header)
    print("-" * 90)

    for s in all_summaries:
        conc = s['config']['concurrency']
        success_rate = f"{s['successful_requests']/s['total_requests']*100:.0f}%" if s['total_requests'] > 0 else "N/A"
        ttft = f"{s['ttft']['mean']:.4f}" if s.get('ttft') else "N/A"
        tpot = f"{s['tpot']['mean']:.4f}" if s.get('tpot') else "N/A"
        e2e = f"{s['e2e_latency']['mean']:.4f}" if s.get('e2e_latency') else "N/A"
        rps = f"{s['throughput_requests_per_sec']:.2f}"
        tps = f"{s['throughput_tokens_per_sec']:.2f}"
        failed = s['failed_requests']

        print(f"{conc:>6} | {success_rate:>6} | {ttft:>10} | {tpot:>10} | {e2e:>10} | {rps:>11} | {tps:>11} | {failed:>4}")

    print("-" * 90)

    # 趋势分析
    if len(all_summaries) >= 2:
        first = all_summaries[0]
        last = all_summaries[-1]
        print("\n📈 趋势分析:")
        c_first = first['config']['concurrency']
        c_last = last['config']['concurrency']

        if first.get('ttft') and last.get('ttft'):
            ttft_ratio = last['ttft']['mean'] / first['ttft']['mean'] if first['ttft']['mean'] > 0 else 0
            print(f"  TTFT: 并发{c_first}→{c_last}, 延迟变化 {ttft_ratio:.2f}x ({'恶化' if ttft_ratio > 1.2 else '稳定' if ttft_ratio < 1.2 else '改善'})")

        if first.get('tpot') and last.get('tpot'):
            tpot_ratio = last['tpot']['mean'] / first['tpot']['mean'] if first['tpot']['mean'] > 0 else 0
            print(f"  TPOT: 并发{c_first}→{c_last}, 延迟变化 {tpot_ratio:.2f}x ({'恶化' if tpot_ratio > 1.2 else '稳定' if tpot_ratio < 1.2 else '改善'})")

        rps_first = first['throughput_requests_per_sec']
        rps_last = last['throughput_requests_per_sec']
        if rps_first > 0:
            print(f"  吞吐: 并发{c_first}→{c_last}, req/s 从 {rps_first:.2f} → {rps_last:.2f} ({rps_last/rps_first:.2f}x)")

        if first['failed_requests'] == 0 and last['failed_requests'] > 0:
            print(f"  ⚠️  并发{c_last}时出现 {last['failed_requests']} 个失败请求，可能已达性能瓶颈")
        elif last['failed_requests'] == 0:
            print(f"  ✅ 所有并发级别均无失败请求")

    print("=" * 90)


def save_concurrency_results(all_summaries: List[Dict[str, Any]], all_results_map: Dict[int, List[Dict]]):
    """保存并发梯度压测结果"""
    model_dir = cfg.OUTPUT_DIR / cfg.MODEL_NAME.replace(":", "_")
    model_dir.mkdir(parents=True, exist_ok=True)

    with open(model_dir / "concurrency_summary.json", "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, ensure_ascii=False, indent=2)

    for conc, results in all_results_map.items():
        conc_dir = model_dir / f"concurrency_{conc}"
        conc_dir.mkdir(parents=True, exist_ok=True)
        with open(conc_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    return model_dir


# ═══════════════════════════════════════════════════════════════
#  主函数
# ═══════════════════════════════════════════════════════════════

async def main():
    concurrency_levels = getattr(cfg, 'CONCURRENCY_LEVELS', [])
    cooldown = getattr(cfg, 'CONCURRENCY_COOLDOWN', 5)

    if concurrency_levels:
        # ── 并发梯度压测模式 ──
        print(f"\n{'#'*70}")
        print(f"# 并发梯度压测模式")
        print(f"# 模型: {cfg.MODEL_NAME}")
        print(f"# 并发级别: {concurrency_levels}")
        print(f"# 每轮请求数: {cfg.NUM_PROMPTS}")
        print(f"{'#'*70}")

        # 预先生成统一的 prompt 列表，确保每轮用相同输入
        shared_prompts = prepare_prompts()

        all_summaries = []
        all_results_map = {}

        for i, conc in enumerate(concurrency_levels):
            if i > 0:
                print(f"\n⏳ 冷却 {cooldown}s...")
                await asyncio.sleep(cooldown)

            print(f"\n{'▶'*70}")
            print(f"▶ 第 {i+1}/{len(concurrency_levels)} 轮：并发数 = {conc}")
            print(f"{'▶'*70}")

            results, wall_time = await run_benchmark(concurrency=conc, prompts=shared_prompts)
            summary = build_summary(results, wall_time)
            summary['config']['concurrency'] = conc
            print_report(summary)

            all_summaries.append(summary)
            all_results_map[conc] = results

        # 打印对比表格
        print_concurrency_comparison(all_summaries)

        # 保存结果
        output_dir = save_concurrency_results(all_summaries, all_results_map)
        print(f"\n📁 结果已保存到: {output_dir}")
    else:
        # ── 单次压测模式 ──
        results, wall_time = await run_benchmark()
        summary = build_summary(results, wall_time)
        print_report(summary)
        output_dir = save_results(results, summary)
        print(f"\n📁 结果已保存到: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
