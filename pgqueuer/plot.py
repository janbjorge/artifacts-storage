from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from service import PlotService, version_sort_key
from utils import rolling_percentile


def plot_combined() -> None:
    plot = PlotService().build_plot_data()
    downloads = plot.downloads
    window = 21

    drivers = sorted({g.driver for g in plot.groups})
    strategies = sorted({g.strategy for g in plot.groups})
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

    palette = [
        "rgb(31,119,180)",
        "rgb(255,127,14)",
        "rgb(44,160,44)",
        "rgb(214,39,40)",
        "rgb(148,103,189)",
        "rgb(140,86,75)",
        "rgb(227,119,194)",
        "rgb(127,127,127)",
        "rgb(188,189,34)",
        "rgb(23,190,207)",
    ]
    version_colors = {
        v: palette[i % len(palette)] for i, v in enumerate(downloads.versions)
    }

    left_span = max(1, n_cols // 2)
    right_col = left_span + 1
    right_span = max(1, n_cols - left_span)

    download_row_titles = [
        "Daily Download Rate (7-day avg)",
        f"Cumulative Downloads (Total: {downloads.grand_total:,})",
        "Daily Downloads by Version",
        (
            f"Version Adoption, Top {len(downloads.adoption_versions)} "
            "by Recent Traffic (7-day avg share)"
        ),
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

    for group in plot.groups:
        times = [x.created_at for x in group.snapshots]
        rates = [x.rate for x in group.snapshots]
        row = strategy_row[group.strategy] + n_download_rows
        col = driver_col[group.driver]
        color = colors.get(group.driver, "rgb(99,110,250)")
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
            for version, release_date in downloads.release_dates.items():
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

    for version in downloads.versions:
        fig.add_trace(
            go.Scatter(
                x=downloads.dates,
                y=[downloads.daily[d].get(version, 0) for d in downloads.dates],
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
            x=downloads.dates,
            y=list(downloads.smoothed_rate),
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
            x=downloads.dates,
            y=list(downloads.cumulative),
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

    for version, share in downloads.adoption_pct.items():
        fig.add_trace(
            go.Scatter(
                x=downloads.dates,
                y=list(share),
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
            x=downloads.dates,
            y=list(downloads.adoption_other),
            mode="lines",
            name=f"Other ({len(downloads.other_versions)} versions)",
            line={"color": "rgb(150,150,150)", "width": 1.5, "dash": "dot"},
            hovertemplate="Other: %{y:.1f}%<extra></extra>",
        ),
        row=2,
        col=right_col,
    )

    sorted_totals = sorted(
        downloads.totals.items(), key=lambda i: version_sort_key(i[0])
    )
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
        title={"text": f"Benchmarks & Downloads: {downloads.package_id}", "x": 0.5},
        template="plotly_white",
        margin={"l": 60, "r": 30, "t": 60, "b": 40},
        legend={"orientation": "h", "y": -0.02},
    )
    fig.show()


if __name__ == "__main__":
    plot_combined()
