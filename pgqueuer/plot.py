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

    def version_sort_key(v: str) -> tuple[int, ...]:
        return tuple(map(int, v.split(".")))

    versions = sorted(
        {v for vc in downloads.values() for v in vc}, key=version_sort_key
    )

    # Stable color per version
    palette = [
        "rgb(31,119,180)", "rgb(255,127,14)", "rgb(44,160,44)",
        "rgb(214,39,40)", "rgb(148,103,189)", "rgb(140,86,75)",
        "rgb(227,119,194)", "rgb(127,127,127)", "rgb(188,189,34)",
        "rgb(23,190,207)",
    ]
    version_colors = {v: palette[i % len(palette)] for i, v in enumerate(versions)}

    # Daily download rate (7-day rolling average)
    acc_dates = sorted(accumulated.keys())
    acc_values = [accumulated[d] for d in acc_dates]
    daily_rate = [0.0] * len(acc_values)
    for i in range(1, len(acc_values)):
        daily_rate[i] = float(acc_values[i] - acc_values[i - 1])
    window = 7
    smoothed_rate = []
    for i in range(len(daily_rate)):
        start = max(0, i - window + 1)
        smoothed_rate.append(sum(daily_rate[start : i + 1]) / (i - start + 1))

    fig = make_subplots(
        rows=3,
        cols=1,
        vertical_spacing=0.08,
        subplot_titles=[
            "Daily Downloads by Version",
            "Daily Download Rate (7-day avg)",
            "Total Downloads by Version",
        ],
        row_heights=[0.45, 0.25, 0.30],
    )

    # Row 1: Stacked area by version
    for version in versions:
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=[downloads[d][version] for d in dates],
                mode="lines",
                name=f"v{version}",
                stackgroup="versions",
                line={"color": version_colors[version], "width": 0.5},
                hovertemplate=f"v{version}: %{{y}}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    # Row 2: Daily download rate
    fig.add_trace(
        go.Scatter(
            x=acc_dates,
            y=smoothed_rate,
            mode="lines",
            name="Daily rate",
            line={"color": "rgb(31,119,180)", "width": 2},
            fill="tozeroy",
            fillcolor="rgba(31,119,180,0.15)",
            showlegend=False,
            hovertemplate="%{y:.0f} downloads/day<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Row 3: Bar chart of total downloads per version
    sorted_totals = sorted(totals.items(), key=lambda i: version_sort_key(i[0]))
    fig.add_trace(
        go.Bar(
            x=[f"v{v}" for v, _ in sorted_totals],
            y=[c for _, c in sorted_totals],
            marker_color=[version_colors[v] for v, _ in sorted_totals],
            showlegend=False,
            hovertemplate="v%{x}: %{y}<extra></extra>",
        ),
        row=3,
        col=1,
    )

    fig.update_yaxes(title_text="Downloads/day", row=1, col=1)
    fig.update_yaxes(title_text="Downloads/day (avg)", row=2, col=1)
    fig.update_yaxes(title_text="Total downloads", row=3, col=1)

    fig.update_layout(
        height=900,
        width=1600,
        title={"text": f"Downloads Analysis: {data.id}", "x": 0.5},
        template="plotly_white",
        margin={"l": 60, "r": 30, "t": 60, "b": 40},
        legend={"orientation": "h", "y": -0.05},
    )
    fig.show()


if __name__ == "__main__":
    plot_rate_over_time()
    plot_downloads(merged_pepy())
