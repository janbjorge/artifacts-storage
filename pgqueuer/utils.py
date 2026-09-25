from __future__ import annotations

from collections.abc import Generator


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
        window = sorted(
            data[max(0, i - half_window) : min(len(data), i + half_window + 1)]
        )
        idx = (len(window) - 1) * percentile / 100
        lo = int(idx)
        hi = min(lo + 1, len(window) - 1)
        frac = idx - lo
        yield window[lo] + (window[hi] - window[lo]) * frac
