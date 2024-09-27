# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "plotly",
#     "pydantic",
# ]
# ///
from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import grouped_by_driver, median_filter


def plot_rate_over_time():
    data = grouped_by_driver()
    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=(
            "Benchmark Rate Over Time by Driver",
            "Benchmark Rate Over Time by Driver (Median Filter)",
        ),
    )

    for driver, results in data:
        times = [x.created_at for x in results if x.github_ref_name == "main"]
        rates = [x.rate for x in results if x.github_ref_name == "main"]

        fig.add_trace(
            go.Scatter(
                x=times,
                y=rates,
                mode="lines",
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
                y=list(median_filter(rates, 21)),
                mode="lines",
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
    )

    fig.show()


if __name__ == "__main__":
    plot_rate_over_time()
