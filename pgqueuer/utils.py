from __future__ import annotations

from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor
from itertools import groupby
from datetime import datetime
from pathlib import Path
from statistics import median
from collections import defaultdict

from models import BenchmarkResult, PackageStats


def _parse_file[T](item: tuple[Callable[[bytes], T], Path]) -> tuple[Path, T]:
    parse, path = item
    return path, parse(path.read_bytes())


def _load_json_files[T](
    root: Path, parse: Callable[[bytes], T]
) -> list[tuple[Path, T]]:
    files = [(parse, path) for path in root.rglob("*.json")]
    if not files:
        return []
    with ThreadPoolExecutor() as pool:
        return list(pool.map(_parse_file, files))


def benchmark_loader() -> Generator[tuple[Path, BenchmarkResult], None, None]:
    yield from _load_json_files(
        Path("pgqueuer/benchmark"), BenchmarkResult.model_validate_json
    )


def pepy_loader() -> Generator[tuple[Path, PackageStats], None, None]:
    yield from _load_json_files(Path("pgqueuer/pepy"), PackageStats.model_validate_json)


def _merge_pepy(stats: list[PackageStats]) -> PackageStats:
    downloads = defaultdict[datetime, dict[str, list[int]]](
        lambda: defaultdict[str, list[int]](list)
    )
    total_downloads = 0
    for ps in stats:
        total_downloads = max(total_downloads, ps.total_downloads)
        for when, v_dl in ps.downloads.items():
            for v, dl in v_dl.items():
                downloads[when][v].append(dl)

    return PackageStats(
        total_downloads=total_downloads,
        id="pgqueuer",
        versions=list(set(v for x in downloads.values() for v in x.keys())),
        downloads={
            when: {v: round(median(dl)) for v, dl in dls.items()}
            for when, dls in downloads.items()
        },
    )


def merged_pepy() -> PackageStats:
    return _merge_pepy([ps for _, ps in pepy_loader()])


def _grouped_by_driver_strategy(
    results: list[BenchmarkResult],
    github_ref_name: str = "main",
) -> Generator[
    tuple[tuple[str, str], list[BenchmarkResult]],
    None,
    None,
]:
    for driver_strategy, group in groupby(
        sorted(
            [x for x in results if x.github_ref_name == github_ref_name],
            key=lambda x: (x.driver, x.strategy),
        ),
        key=lambda x: (x.driver, x.strategy),
    ):
        yield (
            driver_strategy,
            sorted(group, key=lambda x: x.created_at),
        )


def grouped_by_driver_strategy(
    github_ref_name: str = "main",
) -> Generator[
    tuple[tuple[str, str], list[BenchmarkResult]],
    None,
    None,
]:
    yield from _grouped_by_driver_strategy(
        [x for _, x in benchmark_loader()],
        github_ref_name,
    )


def plot_inputs() -> tuple[
    PackageStats,
    list[tuple[tuple[str, str], list[BenchmarkResult]]],
]:
    """Load pepy and benchmark JSON in one default thread pool, then merge/group."""
    jobs: list[tuple[Callable[[bytes], object], Path]] = [
        (BenchmarkResult.model_validate_json, path)
        for path in Path("pgqueuer/benchmark").rglob("*.json")
    ]
    jobs.extend(
        (PackageStats.model_validate_json, path)
        for path in Path("pgqueuer/pepy").rglob("*.json")
    )
    with ThreadPoolExecutor() as pool:
        loaded = list(pool.map(_parse_file, jobs))
    pepy = [model for _, model in loaded if isinstance(model, PackageStats)]
    bench = [model for _, model in loaded if isinstance(model, BenchmarkResult)]
    return _merge_pepy(pepy), list(_grouped_by_driver_strategy(bench))


def median_filter(data: list[float], window_size: int) -> Generator[float, None, None]:
    if window_size % 2 == 0 or window_size < 1:
        raise ValueError("Window size must be a positive odd number.")

    half_window = window_size // 2

    for i in range(len(data)):
        window = data[max(0, i - half_window) : min(len(data), i + half_window + 1)]
        median = sorted(window)[len(window) // 2]
        yield median


def rolling_percentile(
    data: list[float],
    window_size: int,
    percentile: float,
) -> Generator[float, None, None]:
    if window_size < 1:
        raise ValueError("Window size must be a positive integer.")
    if not 0 <= percentile <= 100:
        raise ValueError("Percentile must be between 0 and 100.")

    half_window = window_size // 2

    for i in range(len(data)):
        window = sorted(data[max(0, i - half_window) : min(len(data), i + half_window + 1)])
        idx = (len(window) - 1) * percentile / 100
        lo = int(idx)
        hi = min(lo + 1, len(window) - 1)
        frac = idx - lo
        yield window[lo] + (window[hi] - window[lo]) * frac
