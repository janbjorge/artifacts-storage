# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pydantic",
#     "httpx",
# ]
# ///

from __future__ import annotations

import os
from datetime import datetime

import httpx
from pydantic import BaseModel, Field


def pepy_api_key() -> str:
    """Return PEPY API key from env var PEPY_API_KEY."""
    if key := os.environ.get("PEPY_API_KEY"):
        return key
    raise RuntimeError("Missing env: `PEPY_API_KEY`")


class PackageStats(BaseModel):
    """Represent package download statistics from PEPY."""

    total_downloads: int = Field(
        ...,
        description="Total downloads of all versions",
    )
    id: str = Field(
        ...,
        description="Package name",
    )
    versions: list[str] = Field(
        ...,
        description="List of available versions",
    )
    downloads: dict[datetime, dict[str, int]] = Field(
        ...,
        description="Daily download counts per version",
    )


def fetch() -> PackageStats:
    """Fetch and return package stats from PEPY."""
    return PackageStats.model_validate_json(
        httpx.get(
            "https://api.pepy.tech/api/v2/projects/pgqueuer",
            headers={"X-API-Key": pepy_api_key()},
        ).content
    )


if __name__ == "__main__":
    print(fetch().model_dump_json(), flush=True)
