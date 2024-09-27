from __future__ import annotations

from datetime import timedelta
from typing import Literal

from pydantic import AwareDatetime, BaseModel


class BenchmarkResult(BaseModel):
    created_at: AwareDatetime
    driver: Literal["apg", "apgpool", "psy"]
    elapsed: timedelta
    github_ref_name: str
    rate: float
    steps: int
    queued: int | None = None
