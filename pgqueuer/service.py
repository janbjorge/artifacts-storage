from __future__ import annotations

import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from itertools import accumulate, groupby
from pathlib import Path
from statistics import median

from queries import BenchmarkQueries, PepyQueries, parse_file
from results import (
    BenchmarkGroup,
    BenchmarkSnapshot,
    DownloadSeries,
    PepySnapshot,
    PlotData,
)


def trailing_mean(values: list[float], window: int) -> list[float]:
    """Trailing moving average, shrinking the window at the start of the series."""
    out = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        out.append(sum(values[start : i + 1]) / (i - start + 1))
    return out


def version_sort_key(v: str) -> tuple[int, ...]:
    return tuple(map(int, v.split(".")))


def _merge_pepy(stats: list[PepySnapshot]) -> PepySnapshot:
    downloads = defaultdict[datetime, dict[str, list[int]]](
        lambda: defaultdict[str, list[int]](list)
    )
    total_downloads = 0
    for ps in stats:
        total_downloads = max(total_downloads, ps.total_downloads)
        for when, v_dl in ps.downloads.items():
            for v, dl in v_dl.items():
                downloads[when][v].append(dl)

    return PepySnapshot(
        total_downloads=total_downloads,
        id="pgqueuer",
        versions=tuple(set(v for x in downloads.values() for v in x.keys())),
        downloads={
            when: {v: round(median(dl)) for v, dl in dls.items()}
            for when, dls in downloads.items()
        },
    )


def _group_benchmarks(
    results: list[BenchmarkSnapshot],
    github_ref_name: str = "main",
) -> tuple[BenchmarkGroup, ...]:
    groups: list[BenchmarkGroup] = []
    filtered = sorted(
        (x for x in results if x.github_ref_name == github_ref_name),
        key=lambda x: (x.driver, x.strategy),
    )
    for (driver, strategy), group in groupby(
        filtered, key=lambda x: (x.driver, x.strategy)
    ):
        snapshots = tuple(sorted(group, key=lambda x: x.created_at))
        groups.append(
            BenchmarkGroup(driver=driver, strategy=strategy, snapshots=snapshots)
        )
    return tuple(groups)


def _download_series(
    merged: PepySnapshot,
    *,
    rate_window: int,
    n_adoption_versions: int,
    adoption_window: int,
) -> DownloadSeries:
    downloads: defaultdict[datetime, defaultdict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for date, vers_counts in merged.downloads.items():
        for version, count in vers_counts.items():
            if mv := re.match(r"^\d+\.\d+", version):
                downloads[date][mv.group(0)] += count

    daily = {date: dict(vers_counts) for date, vers_counts in downloads.items()}
    totals_counter: Counter[str] = Counter()
    for vers_counts in daily.values():
        totals_counter.update(vers_counts)
    totals = dict(totals_counter)

    grand_total = sum(totals.values())
    dates = tuple(sorted(daily.keys()))
    versions = tuple(
        sorted({v for vc in daily.values() for v in vc}, key=version_sort_key)
    )

    daily_totals = [float(sum(daily[d].values())) for d in dates]
    smoothed_rate = tuple(trailing_mean(daily_totals, rate_window))
    cumulative = tuple(accumulate(daily_totals))

    recent_totals: Counter[str] = Counter()
    for d in dates[-adoption_window:]:
        recent_totals.update(daily[d])
    adoption_versions = tuple(
        sorted(
            (v for v, _ in recent_totals.most_common(n_adoption_versions)),
            key=version_sort_key,
        )
    )

    def smoothed_share(picked: tuple[str, ...]) -> tuple[float, ...]:
        return tuple(
            trailing_mean(
                [
                    sum(daily[d].get(v, 0) for v in picked) / total * 100
                    if total
                    else 0.0
                    for d, total in zip(dates, daily_totals)
                ],
                rate_window,
            )
        )

    adoption_pct = {
        version: smoothed_share((version,)) for version in adoption_versions
    }
    other_versions = tuple(v for v in versions if v not in adoption_versions)
    adoption_other = smoothed_share(other_versions)

    remaining = set(versions)
    release_dates: dict[str, datetime] = {}
    for d in dates:
        if not remaining:
            break
        found = [v for v in remaining if daily[d].get(v, 0) > 0]
        for version in found:
            release_dates[version] = d
            remaining.remove(version)
    if dates:
        release_dates = {v: d for v, d in release_dates.items() if d != dates[0]}

    return DownloadSeries(
        package_id=merged.id,
        dates=dates,
        versions=versions,
        daily=daily,
        totals=totals,
        grand_total=grand_total,
        smoothed_rate=smoothed_rate,
        cumulative=cumulative,
        adoption_versions=adoption_versions,
        other_versions=other_versions,
        adoption_pct=adoption_pct,
        adoption_other=adoption_other,
        release_dates=release_dates,
    )


@dataclass
class PlotService:
    benchmark_root: Path = Path("pgqueuer/benchmark")
    pepy_root: Path = Path("pgqueuer/pepy")
    github_ref_name: str = "main"
    rate_window: int = 7
    n_adoption_versions: int = 5
    adoption_window: int = 90

    def build_plot_data(self) -> PlotData:
        with ThreadPoolExecutor() as pool:
            bench_q = BenchmarkQueries(pool, self.benchmark_root)
            pepy_q = PepyQueries(pool, self.pepy_root)
            jobs = [(bench_q.parse, path) for path in bench_q.files()]
            jobs += [(pepy_q.parse, path) for path in pepy_q.files()]
            loaded = list(pool.map(parse_file, jobs))

        pepy = [model for _, model in loaded if isinstance(model, PepySnapshot)]
        bench = [model for _, model in loaded if isinstance(model, BenchmarkSnapshot)]
        merged = _merge_pepy(pepy)
        return PlotData(
            downloads=_download_series(
                merged,
                rate_window=self.rate_window,
                n_adoption_versions=self.n_adoption_versions,
                adoption_window=self.adoption_window,
            ),
            groups=_group_benchmarks(bench, self.github_ref_name),
        )
