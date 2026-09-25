from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Self

from models import BenchmarkResult, PackageStats


@dataclass(frozen=True)
class BenchmarkSnapshot:
    created_at: datetime
    strategy: str
    driver: str
    elapsed: timedelta
    github_ref_name: str
    rate: float
    steps: int
    queued: int | None = None

    @classmethod
    def from_model(cls, model: BenchmarkResult) -> Self:
        return cls(
            created_at=model.created_at,
            strategy=model.strategy,
            driver=model.driver,
            elapsed=model.elapsed,
            github_ref_name=model.github_ref_name,
            rate=model.rate,
            steps=model.steps,
            queued=model.queued,
        )


@dataclass(frozen=True)
class PepySnapshot:
    total_downloads: int
    id: str
    versions: tuple[str, ...]
    downloads: dict[datetime, dict[str, int]]

    @classmethod
    def from_model(cls, model: PackageStats) -> Self:
        return cls(
            total_downloads=model.total_downloads,
            id=model.id,
            versions=tuple(model.versions),
            downloads=model.downloads,
        )


@dataclass(frozen=True)
class DownloadSeries:
    package_id: str
    dates: tuple[datetime, ...]
    versions: tuple[str, ...]
    daily: dict[datetime, dict[str, int]]
    totals: dict[str, int]
    grand_total: int
    smoothed_rate: tuple[float, ...]
    cumulative: tuple[float, ...]
    adoption_versions: tuple[str, ...]
    other_versions: tuple[str, ...]
    adoption_pct: dict[str, tuple[float, ...]]
    adoption_other: tuple[float, ...]
    release_dates: dict[str, datetime]


@dataclass(frozen=True)
class BenchmarkGroup:
    driver: str
    strategy: str
    snapshots: tuple[BenchmarkSnapshot, ...]


@dataclass(frozen=True)
class PlotData:
    downloads: DownloadSeries
    groups: tuple[BenchmarkGroup, ...]
