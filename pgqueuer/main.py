from __future__ import annotations

from datetime import timedelta
from itertools import groupby
from pathlib import Path
from typing import Generator, Literal

import matplotlib.pyplot as plt
from pydantic import AwareDatetime, BaseModel


class BenchmarkResult(BaseModel):
    created_at: AwareDatetime
    driver: Literal["apg", "apgpool", "psy"]
    elapsed: timedelta
    github_ref_name: str
    rate: float
    steps: int


def loader() -> Generator[BenchmarkResult, None, None]:
    for file in Path("pgqueuer/benchmark").rglob("*.json"):
        with file.open() as f:
            yield BenchmarkResult.model_validate_json(f.read())


def grouped() -> (
    Generator[
        tuple[str, list[BenchmarkResult]],
        None,
        None,
    ]
):
    for driver, group in groupby(
        sorted(loader(), key=lambda x: x.driver),
        key=lambda x: x.driver,
    ):
        yield (
            driver,
            sorted(group, key=lambda x: x.created_at),
        )


def plot_rate_over_time(data: list[tuple[str, list[BenchmarkResult]]]):
    plt.figure(figsize=(10, 6))
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
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    plot_rate_over_time(list(grouped()))
