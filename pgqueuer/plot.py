from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from itertools import accumulate

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import rolling_percentile, plot_inputs


def trailing_mean(values: list[float], window: int) -> list[float]:
    """Trailing moving average, shrinking the window at the start of the series."""
    out = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        out.append(sum(values[start : i + 1]) / (i - start + 1))
    return out


def plot_combined() -> None:
    data, groups = plot_inputs()
    window = 21

    drivers = sorted({driver for (driver, _), _ in groups})
    strategies = sorted({strategy for (_, strategy), _ in groups})
    driver_col = {d: i + 1 for i, d in enumerate(drivers)}
    strategy_row = {s: i + 1 for i, s in enumerate(strategies)}
    n_cols = len(drivers)
    n_rate_rows = len(strategies)

    colors = {
        "apg": "rgb(31,119,180)",
        "apgpool": "rgb(255,127,14)",
        "psy": "rgb(44,160,44)",
        "mem": "rgb(214,39,40)",
    }

    downloads: defaultdict[datetime, defaultdict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for date, vers_counts in data.downloads.items():
        for version, count in vers_counts.items():
            if mv := re.match(r"^\d+\.\d+", version):
                downloads[date][mv.group(0)] += count

    totals = Counter[str]()
    for vers_counts in downloads.values():
        totals.update(vers_counts)

    grand_total = sum(totals.values())
    dates = sorted(downloads.keys())

    def version_sort_key(v: str) -> tuple[int, ...]:
        return tuple(map(int, v.split(".")))

    versions = sorted(
        {v for vc in downloads.values() for v in vc}, key=version_sort_key
    )

    palette = [
        "rgb(31,119,180)", "rgb(255,127,14)", "rgb(44,160,44)",
        "rgb(214,39,40)", "rgb(148,103,189)", "rgb(140,86,75)",
        "rgb(227,119,194)", "rgb(127,127,127)", "rgb(188,189,34)",
        "rgb(23,190,207)",
    ]
    version_colors = {v: palette[i % len(palette)] for i, v in enumerate(versions)}

    daily_totals = [float(sum(downloads[d].values())) for d in dates]
    rate_window = 7
    smoothed_rate = trailing_mean(daily_totals, rate_window)
    cumulative_total = list(accumulate(daily_totals))

    # Adoption: share of daily downloads per version, smoothed. Versions are picked
    # by recent traffic rather than all-time totals, otherwise long-dead versions
    # crowd out the current ones. "Other" carries the remaining versions so the
    # plotted lines sum to 100% on every day.
    n_adoption_versions = 5
    adoption_window = 90
    recent_totals = Counter[str]()
    for d in dates[-adoption_window:]:
        recent_totals.update(downloads[d])
    adoption_versions = sorted(
        (v for v, _ in recent_totals.most_common(n_adoption_versions)),
        key=version_sort_key,
    )

    def smoothed_share(picked: tuple[str, ...]) -> list[float]:
        return trailing_mean(
            [
                sum(downloads[d].get(v, 0) for v in picked) / total * 100 if total else 0.0
                for d, total in zip(dates, daily_totals)
            ],
            rate_window,
        )

    adoption_pct = {version: smoothed_share((version,)) for version in adoption_versions}
    other_versions = tuple(v for v in versions if v not in adoption_versions)
    adoption_other = smoothed_share(other_versions)

    # Release-date proxy: first date each version appears in the download data.
    # Versions that first appear on the very first tracked date are dataset
    # backfill artifacts, not real release signals, so they're excluded.
    remaining = set(versions)
    release_dates: dict[str, datetime] = {}
    for d in dates:
        if not remaining:
            break
        found = [v for v in remaining if downloads[d].get(v, 0) > 0]
        for version in found:
            release_dates[version] = d
            remaining.remove(version)
    if dates:
        release_dates = {v: d for v, d in release_dates.items() if d != dates[0]}

    left_span = max(1, n_cols // 2)
    right_col = left_span + 1
    right_span = max(1, n_cols - left_span)

    download_row_titles = [
        "Daily Download Rate (7-day avg)",
        f"Cumulative Downloads (Total: {grand_total:,})",
        "Daily Downloads by Version",
        f"Version Adoption, Top {len(adoption_versions)} by Recent Traffic (7-day avg share)",
        "Total Downloads by Version",
    ]
    rate_row_titles = [d.upper() for d in drivers] + [None] * n_cols * (n_rate_rows - 1)
    subplot_titles = download_row_titles + rate_row_titles

    split_row: list[dict[str, int] | None] = [None] * n_cols
    split_row[0] = {"colspan": left_span}
    split_row[right_col - 1] = {"colspan": right_span}

    full_row: list[dict[str, int] | None] = [None] * n_cols
    full_row[0] = {"colspan": n_cols}

    specs: list[list[dict[str, int] | None]] = [split_row, list(split_row), full_row]
    specs += [[{} for _ in range(n_cols)] for _ in range(n_rate_rows)]

    n_download_rows = 3
    total_rows = n_download_rows + n_rate_rows
    fig = make_subplots(
        rows=total_rows,
        cols=n_cols,
        subplot_titles=subplot_titles,
        specs=specs,
        vertical_spacing=0.05,
        horizontal_spacing=0.04,
        row_heights=[1.0, 1.2, 0.8] + [1.0] * n_rate_rows,
    )

    for (driver, strategy), results in groups:
        times = [x.created_at for x in results]
        rates = [x.rate for x in results]
        row = strategy_row[strategy] + n_download_rows
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
        for col in range(1, n_cols + 1):
            fig.update_yaxes(
                title_text=f"{strategy.capitalize()} (jobs/s)",
                row=row + n_download_rows,
                col=col,
            )

    # add_vline's annotation path chokes on datetime x-values (plotly 6.5.2), and
    # add_shape/add_annotation revalidate the whole layout array on every call, which
    # is quadratic in the number of markers. Build them once, assign them once.
    rate_rows = range(n_download_rows + 1, n_download_rows + n_rate_rows + 1)
    release_shapes = []
    release_labels = []
    for row in rate_rows:
        for col in range(1, n_cols + 1):
            subplot = fig.get_subplot(row, col)
            xref = subplot.xaxis.plotly_name.replace("axis", "")
            yref = subplot.yaxis.plotly_name.replace("axis", "")
            for version, release_date in release_dates.items():
                release_shapes.append(
                    {
                        "type": "line",
                        "x0": release_date,
                        "x1": release_date,
                        "y0": 0,
                        "y1": 1,
                        "xref": xref,
                        "yref": f"{yref} domain",
                        "line": {"color": "rgba(0,0,0,0.3)", "width": 1, "dash": "dot"},
                    }
                )
                if row == rate_rows[0]:
                    release_labels.append(
                        {
                            "x": release_date,
                            "y": 1,
                            "xref": xref,
                            "yref": f"{yref} domain",
                            "text": f"v{version}",
                            "showarrow": False,
                            "textangle": -90,
                            "font": {"size": 9},
                        }
                    )

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
            row=2,
            col=1,
        )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=smoothed_rate,
            mode="lines",
            name="Daily rate",
            line={"color": "rgb(31,119,180)", "width": 2},
            fill="tozeroy",
            fillcolor="rgba(31,119,180,0.15)",
            showlegend=False,
            hovertemplate="%{y:.0f} downloads/day<extra></extra>",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=cumulative_total,
            mode="lines",
            line={"color": "rgb(44,160,44)", "width": 2},
            fill="tozeroy",
            fillcolor="rgba(44,160,44,0.15)",
            showlegend=False,
            hovertemplate="%{y:,.0f} downloads total<extra></extra>",
        ),
        row=1,
        col=right_col,
    )

    for version, share in adoption_pct.items():
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=share,
                mode="lines",
                line={"color": version_colors[version], "width": 2},
                showlegend=False,
                hovertemplate=f"v{version}: %{{y:.1f}}%<extra></extra>",
            ),
            row=2,
            col=right_col,
        )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=adoption_other,
            mode="lines",
            name=f"Other ({len(other_versions)} versions)",
            line={"color": "rgb(150,150,150)", "width": 1.5, "dash": "dot"},
            hovertemplate="Other: %{y:.1f}%<extra></extra>",
        ),
        row=2,
        col=right_col,
    )

    sorted_totals = sorted(totals.items(), key=lambda i: version_sort_key(i[0]))
    fig.add_trace(
        go.Bar(
            x=[f"v{v}" for v, _ in sorted_totals],
            y=[c for _, c in sorted_totals],
            marker_color=[version_colors[v] for v, _ in sorted_totals],
            showlegend=False,
            hovertemplate="%{x}: %{y}<extra></extra>",
        ),
        row=3,
        col=1,
    )

    fig.update_yaxes(title_text="Downloads/day (avg)", row=1, col=1)
    fig.update_yaxes(title_text="Cumulative downloads", row=1, col=right_col)
    fig.update_yaxes(title_text="Downloads/day", row=2, col=1)
    fig.update_yaxes(title_text="% of daily downloads", row=2, col=right_col)
    fig.update_yaxes(title_text="Total downloads", row=3, col=1)

    fig.update_layout(
        shapes=release_shapes,
        annotations=list(fig.layout.annotations) + release_labels,
        height=320 * total_rows,
        width=1600,
        title={"text": f"Benchmarks & Downloads: {data.id}", "x": 0.5},
        template="plotly_white",
        margin={"l": 60, "r": 30, "t": 60, "b": 40},
        legend={"orientation": "h", "y": -0.02},
    )
    fig.show()


if __name__ == "__main__":
    plot_combined()
