from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from models import BenchmarkResult, PackageStats
from results import BenchmarkSnapshot, PepySnapshot


def parse_file[T](item: tuple[Callable[[bytes], T], Path]) -> tuple[Path, T]:
    parse, path = item
    return path, parse(path.read_bytes())


@dataclass
class BenchmarkQueries:
    executor: ThreadPoolExecutor
    root: Path = Path("pgqueuer/benchmark")

    def files(self) -> list[Path]:
        return list(self.root.rglob("*.json"))

    def parse(self, raw: bytes) -> BenchmarkSnapshot:
        return BenchmarkSnapshot.from_model(BenchmarkResult.model_validate_json(raw))

    def load(self) -> list[tuple[Path, BenchmarkSnapshot]]:
        jobs = [(self.parse, path) for path in self.files()]
        if not jobs:
            return []
        return list(self.executor.map(parse_file, jobs))


@dataclass
class PepyQueries:
    executor: ThreadPoolExecutor
    root: Path = Path("pgqueuer/pepy")

    def files(self) -> list[Path]:
        return list(self.root.rglob("*.json"))

    def parse(self, raw: bytes) -> PepySnapshot:
        return PepySnapshot.from_model(PackageStats.model_validate_json(raw))

    def load(self) -> list[tuple[Path, PepySnapshot]]:
        jobs = [(self.parse, path) for path in self.files()]
        if not jobs:
            return []
        return list(self.executor.map(parse_file, jobs))
