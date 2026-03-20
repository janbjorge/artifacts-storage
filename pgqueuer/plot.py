from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime

import plotly.graph_objects as go
import plotly.subplots as sp
from plotly.subplots import make_subplots
from utils import grouped_by_driver_strategy, rolling_percentile, merged_pepy
from models import PackageStats


def plot_rate_over_time():
    groups = list(grouped_by_driver_strategy())
    window = 21

    drivers = sorted({driver for (driver, _), _ in groups})
    strategies = sorted({strategy for (_, strategy), _ in groups})
    driver_col = {d: i + 1 for i, d in enumerate(drivers)}
    strategy_row = {s: i + 1 for i, s in enumerate(strategies)}

    colors = {
        "apg": "rgb(31,119,180)",
        "apgpool": "rgb(255,127,14)",
        "psy": "rgb(44,160,44)",
        "mem": "rgb(214,39,40)",
    }

    fig = make_subplots(
        rows=len(strategies),
        cols=len(drivers),
        column_titles=[d.upper() for d in drivers],
        vertical_spacing=0.08,
        horizontal_spacing=0.04,
    )

    for (driver, strategy), results in groups:
        times = [x.created_at for x in results]
        rates = [x.rate for x in results]
        row = strategy_row[strategy]
        col = driver_col[driver]
        color = colors.get(driver, "rgb(99,110,250)")
        r, g, b = color[4:-1].split(",")

        p5 = list(rolling_percentile(rates, window, 5))
        p50 = list(rolling_percentile(rates, window, 50))
        p95 = list(rolling_percentile(rates, window, 95))

        fig.add_trace(
            go.Scatter(
                x=times,
                y=p95,
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            ),
            row=row,
            col=col,
        )

        fig.add_trace(
            go.Scatter(
                x=times,
                y=p5,
                mode="lines",
                line={"width": 0},
                fill="tonexty",
                fillcolor=f"rgba({r},{g},{b},0.15)",
                showlegend=False,
                hoverinfo="skip",
            ),
            row=row,
            col=col,
        )

        fig.add_trace(
            go.Scatter(
                x=times,
                y=p50,
                mode="lines",
                line={"color": color, "width": 2},
                showlegend=False,
                hovertemplate="%{y:.0f} jobs/s<extra></extra>",
            ),
            row=row,
            col=col,
        )

    for strategy, row in strategy_row.items():
        for col in range(1, len(drivers) + 1):
            fig.update_yaxes(
                title_text=f"{strategy.capitalize()} (jobs/s)",
                row=row,
                col=col,
            )
    fig.update_layout(
        height=900,
        width=1600,
        title={"text": "Benchmark Rate Over Time (P5 / P50 / P95)", "x": 0.5},
        template="plotly_white",
        margin={"l": 50, "r": 30, "t": 60, "b": 40},
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
