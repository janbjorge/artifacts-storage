from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime

import plotly.graph_objects as go
import plotly.subplots as sp
from plotly.subplots import make_subplots
from utils import grouped_by_driver_strategy, median_filter, merged_pepy
from models import PackageStats


def plot_rate_over_time():
    data = grouped_by_driver_strategy()
    fig = make_subplots(rows=4, cols=1)

    for (driver, strategy), results in data:
        times = [
            x.created_at
            for x in results
            if x.github_ref_name == "main" and x.strategy == strategy
        ]
        rates = [
            x.rate
            for x in results
            if x.github_ref_name == "main" and x.strategy == strategy
        ]

        fig.add_trace(
            go.Scatter(
                x=times,
                y=rates,
                mode="lines",
                name=f"{driver} {strategy} (Raw)",
                showlegend=False,
            ),
            row=1 if strategy == "throughput" else 3,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=times,
                y=list(median_filter(rates, 21)),
                mode="lines",
                name=f"{driver} {strategy} (Filtered)",
                showlegend=False,
            ),
            row=2 if strategy == "throughput" else 4,
            col=1,
        )

    fig.update_layout(
        height=1200,
        title="Benchmark Rate Over Time",
        template="plotly_white",
    )

    fig.show()


def plot_downloads(data: PackageStats) -> None:
    """Create and display a Plotly figure of the package download stats."""
    downloads: defaultdict[datetime, defaultdict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )

    for date, vers_counts in data.downloads.items():
        for version, count in vers_counts.items():
            if mv := re.match(r"^\d+\.\d+", version):
                downloads[date][mv.group(0)] += count

    accumulated = defaultdict[datetime, int](int)
    tally = 0
    for date in sorted(downloads.keys()):
        tally += sum(downloads[date].values())
        accumulated[date] = tally

    adjusted_downloads_offset = data.total_downloads - max(accumulated.values())
    for date, acc in accumulated.items():
        accumulated[date] += adjusted_downloads_offset

    totals = Counter[str]()
    for vers_counts in downloads.values():
        for version, count in vers_counts.items():
            totals[version] += count

    dates = sorted(downloads.keys())
    versions = sorted(
        {v for vc in downloads.values() for v in vc}, key=lambda x: (len(x), x)
    )

    fig = sp.make_subplots(
        rows=2,
        cols=2,
        specs=[[{"type": "xy"}, {"type": "xy"}], [{"type": "xy", "colspan": 2}, None]],
        subplot_titles=[
            "Downloads by Version",
            "Accumulated Downloads",
            "Version Distribution (Bar)",
        ],
    )

    for version in versions:
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=[downloads[d][version] for d in dates],
                mode="lines",
                name=f"v{version}",
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Scatter(
            x=list(accumulated.keys()),
            y=list(accumulated.values()),
            mode="lines",
            name="Accumulated",
        ),
        row=1,
        col=2,
    )

    def sort_key(v: str) -> tuple[int, ...]:
        return tuple(map(int, v.split(".")))

    xy = [(x, y) for x, y in sorted(totals.items(), key=lambda i: sort_key(i[0]))]

    fig.add_trace(
        go.Bar(
            x=[f"v{x}" for x, _ in xy],
            y=[y for _, y in xy],
            name="Total Downloads",
        ),
        row=2,
        col=1,
    )

    fig.update_xaxes(title_text="Date", row=1, col=1)
    fig.update_xaxes(title_text="Date", row=1, col=2)
    fig.update_xaxes(title_text="Version", row=2, col=1)

    fig.update_yaxes(title_text="Count", row=1, col=1)
    fig.update_yaxes(title_text="Accumulated", row=1, col=2)
    fig.update_yaxes(title_text="Downloads", row=2, col=1)

    fig.update_layout(
        title={"text": f"Downloads Analysis: {data.id}", "x": 0.5},
        template="plotly_white",
        margin={"l": 40, "r": 40, "t": 80, "b": 40},
    )
    fig.show()


if __name__ == "__main__":
    plot_rate_over_time()
    plot_downloads(merged_pepy())
