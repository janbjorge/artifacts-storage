from __future__ import annotations

from itertools import groupby
from datetime import datetime
from pathlib import Path
from typing import Generator
from statistics import median
from collections import defaultdict

from models import BenchmarkResult, PackageStats


def benchmark_loader() -> Generator[tuple[Path, BenchmarkResult], None, None]:
    for file in Path("pgqueuer/benchmark").rglob("*.json"):
        with file.open() as f:
            yield (
                file,
                BenchmarkResult.model_validate_json(f.read()),
            )


def pepy_loader() -> Generator[tuple[Path, PackageStats], None, None]:
    for file in Path("pgqueuer/pepy").rglob("*.json"):
        with file.open() as f:
            yield (
                file,
                PackageStats.model_validate_json(f.read()),
            )


def merged_pepy() -> PackageStats:
    downloads = defaultdict[datetime, dict[str, list[int]]](
        lambda: defaultdict[str, list[int]](list)
    )
    for _, ps in pepy_loader():
        for when, v_dl in ps.downloads.items():
            for v, dl in v_dl.items():
                downloads[when][v].append(dl)

    return PackageStats(
        total_downloads=max(x.total_downloads for _, x in pepy_loader()),
        id="pgqueuer",
        versions=list(set(v for x in downloads.values() for v in x.keys())),
        downloads={
            when: {v: round(median(dl)) for v, dl in dls.items()}
            for when, dls in downloads.items()
        },
    )


def grouped_by_driver_strategy(
    github_ref_name: str = "main",
) -> Generator[
    tuple[tuple[str, str], list[BenchmarkResult]],
    None,
    None,
]:
    for driver_strategy, group in groupby(
        sorted(
            [x for _, x in benchmark_loader() if x.github_ref_name == github_ref_name],
            key=lambda x: (x.driver, x.strategy),
        ),
        key=lambda x: (x.driver, x.strategy),
    ):
        yield (
            driver_strategy,
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
