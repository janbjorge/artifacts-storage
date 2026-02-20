# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx",
#     "pydantic",
# ]
# ///

from __future__ import annotations

import os

import httpx
from models import PackageStats


def pepy_api_key() -> str:
    """Return PEPY API key from env var PEPY_API_KEY."""
    if key := os.environ.get("PEPY_API_KEY"):
        return key
    raise RuntimeError("Missing env: `PEPY_API_KEY`")


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
