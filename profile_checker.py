"""效能分析脚本。

执行 ``python profile_checker.py`` 会做两件事：

1. 用 cProfile 对正式实现跑一次 10000 道题的生成，输出耗时最高的函数排名，
   并把结果写入 ``profile.prof``（可用 ``python -m pstats profile.prof`` 继续查看）；
2. 对「朴素实现」与「正式实现」分别计时，结果写入 ``benchmark.csv``，
   便于绘制优化前后的对比图。
"""

from __future__ import annotations

import cProfile
import csv
import io
import pstats
import time
from pathlib import Path

from arithmetic.generator import ExerciseGenerator

from baseline_naive import benchmark as benchmark_naive

PROFILE_COUNT = 10000
RANGE_LIMIT = 10

NAIVE_SIZES = (200, 500, 1000, 2000, 5000)
FAST_SIZES = (1000, 5000, 10000)


def profile_fast_generator() -> pstats.Stats:
    """对正式实现做一次 cProfile 采样。"""
    profiler = cProfile.Profile()
    profiler.enable()
    ExerciseGenerator(RANGE_LIMIT, seed=20250920).generate(PROFILE_COUNT)
    profiler.disable()
    profiler.dump_stats("profile.prof")
    return pstats.Stats(profiler)


def print_hot_functions(stats: pstats.Stats, limit: int = 12) -> None:
    """打印累计耗时最高的函数。"""
    stream = io.StringIO()
    stats.stream = stream
    stats.sort_stats("cumulative").print_stats(limit)
    print(stream.getvalue())


def print_time_top_functions(profile_path: str = "profile.prof", limit: int = 5) -> None:
    """按 tottime（函数自身耗时）排序，找出真正的瓶颈函数。"""
    stats = pstats.Stats(profile_path)
    stats.sort_stats("tottime").print_stats(limit)


def benchmark_implementations() -> dict[int, dict[str, float]]:
    """对两种实现计时，返回 {题目数: {"朴素": 秒, "正式": 秒}}。"""
    results: dict[int, dict[str, float]] = {}
    for size in NAIVE_SIZES:
        elapsed, _ = benchmark_naive(size, range_limit=RANGE_LIMIT)
        results.setdefault(size, {})["朴素实现"] = elapsed
        print(f"朴素实现 -n {size}: {elapsed:8.3f} 秒")

    for size in FAST_SIZES:
        started = time.perf_counter()
        ExerciseGenerator(RANGE_LIMIT, seed=20250920).generate(size)
        elapsed = time.perf_counter() - started
        results.setdefault(size, {})["正式实现"] = elapsed
        print(f"正式实现 -n {size}: {elapsed:8.3f} 秒")

    return results


def write_benchmark_csv(results: dict[int, dict[str, float]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["题目个数", "实现", "耗时（秒）"])
        for size in sorted(results):
            for name, elapsed in results[size].items():
                writer.writerow([size, name, f"{elapsed:.4f}"])


def main() -> None:
    print("=" * 68)
    print(f"cProfile：正式实现生成 {PROFILE_COUNT} 道题目，按累计耗时排序")
    print("=" * 68)
    stats = profile_fast_generator()
    print_hot_functions(stats)

    print("=" * 68)
    print("按函数自身耗时（tottime）排序，定位真正的瓶颈")
    print("=" * 68)
    print_time_top_functions()

    print("=" * 68)
    print("两种实现的耗时对比")
    print("=" * 68)
    results = benchmark_implementations()
    write_benchmark_csv(results, Path("benchmark.csv"))
    print("对比数据已写入 benchmark.csv")


if __name__ == "__main__":
    main()
