from __future__ import annotations

from itertools import groupby
from pathlib import Path
from typing import Generator

from models import BenchmarkResult


def loader() -> Generator[tuple[Path, BenchmarkResult], None, None]:
    for file in Path("pgqueuer/benchmark").rglob("*.json"):
        with file.open() as f:
            yield (
                file,
                BenchmarkResult.model_validate_json(f.read()),
            )


def grouped_by_driver(
    github_ref_name: str = "main",
) -> Generator[
    tuple[str, list[BenchmarkResult]],
    None,
    None,
]:
    for driver, group in groupby(
        sorted(
            [x for _, x in loader() if x.github_ref_name == github_ref_name],
            key=lambda x: x.driver,
        ),
        key=lambda x: x.driver,
    ):
        yield (
            driver,
            sorted(group, key=lambda x: x.created_at),
        )


def median_filter(data: list[float], window_size: int) -> Generator[float, None, None]:
    if window_size % 2 == 0 or window_size < 1:
        raise ValueError("Window size must be a positive odd number.")

    half_window = window_size // 2

    for i in range(len(data)):
        window = data[max(0, i - half_window) : min(len(data), i + half_window + 1)]
        median = sorted(window)[len(window) // 2]
        yield median
