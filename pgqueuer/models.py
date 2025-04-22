from __future__ import annotations

from datetime import timedelta, datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field


class BenchmarkResult(BaseModel):
    created_at: AwareDatetime
    driver: Literal["apg", "apgpool", "psy"]
    elapsed: timedelta
    github_ref_name: str
    rate: float
    steps: int
    queued: int | None = None


class PackageStats(BaseModel):
    """Represent package download statistics from PEPY."""

    total_downloads: int = Field(..., description="Total downloads of all versions")
    id: str = Field(..., description="Package name")
    versions: list[str] = Field(..., description="List of available versions")
    downloads: dict[datetime, dict[str, int]] = Field(
        ..., description="Daily download counts per version"
    )

    class Config:
        extra = "forbid"
