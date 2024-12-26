# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "plotly",
#     "pydantic",
# ]
# ///
from __future__ import annotations

import plotly.graph_objects as go
from models import BenchmarkResult
from plotly.subplots import make_subplots
from utils import grouped_by_driver, median_filter


def plot_rate_over_time(
    data: list[tuple[str, list[BenchmarkResult]]],
):
    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=(
            "Benchmark Rate Over Time by Driver",
            "Benchmark Rate Over Time by Driver (Median Filter)",
        ),
    )

    for driver, results in data:
        results = [x for x in results if x.github_ref_name == "main"]
        times = [result.created_at for result in results]
        rates = [result.rate for result in results]

        fig.add_trace(
            go.Scatter(
                x=times,
                y=rates,
                mode="lines+markers",
                name=f"{driver} (Raw)",
                legendgroup=f"{driver}_raw",
                showlegend=True,
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=times,
                y=median_filter(rates, 5),
                mode="lines+markers",
                name=f"{driver} (Filtered)",
                legendgroup=f"{driver}_filtered",
                showlegend=True,
            ),
            row=2,
            col=1,
        )

    fig.update_layout(
        height=800,
        title="Benchmark Rate Over Time",
        xaxis_title="Timestamp",
        yaxis_title="Rate",
        template="plotly_white",
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=0,
                y=1.15,
                text="Window: Raw Data",
                showarrow=False,
                font=dict(size=12),
            ),
            dict(
                xref="paper",
                yref="paper",
                x=0,
                y=0.55,
                text="Window: Median Filter",
                showarrow=False,
                font=dict(size=12),
            ),
        ],
    )

    fig.show()


if __name__ == "__main__":
    plot_rate_over_time(list(grouped_by_driver()))
