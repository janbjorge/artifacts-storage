from __future__ import annotations

import matplotlib.pyplot as plt
from models import BenchmarkResult
from utils import grouped_by_driver, median_filter


def plot_rate_over_time(
    data: list[tuple[str, list[BenchmarkResult]]],
    output_file: str,
):
    plt.figure(figsize=(10, 6))
    plt.subplot(211)
    for driver, results in data:
        results = [x for x in results if x.github_ref_name == "main"]
        times = [result.created_at for result in results]
        rates = [result.rate for result in results]
        plt.plot(times, rates, marker="o", label=driver)

    plt.xlabel("Timestamp")
    plt.ylabel("Rate")
    plt.title("Benchmark Rate Over Time by Driver")
    plt.legend()
    plt.grid(True)

    plt.subplot(212)
    for driver, results in data:
        results = [x for x in results if x.github_ref_name == "main"]
        times = [result.created_at for result in results]
        rates = [result.rate for result in results]
        plt.plot(times, median_filter(rates, 5), marker="o", label=driver)

    plt.xlabel("Timestamp")
    plt.ylabel("Rate")
    plt.title("Benchmark Rate Over Time by Driver(Median filter)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_file, dpi=200)


if __name__ == "__main__":
    plot_rate_over_time(list(grouped_by_driver()), "benchmark_rate.png")
