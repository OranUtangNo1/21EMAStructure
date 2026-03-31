from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd

from src.structure.pivot import StructurePivotResult


class ChartBuilder:
    """Render the main chart with 21EMA Cloud and Structure Pivot overlays."""

    def build(self, symbol: str, history: pd.DataFrame, pivot_result: StructurePivotResult) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(
            go.Candlestick(
                x=history.index,
                open=history["open"],
                high=history["high"],
                low=history["low"],
                close=history["close"],
                name=symbol,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=history.index,
                y=history["ema21_high"],
                mode="lines",
                line=dict(color="rgba(0, 130, 120, 0.55)", width=1),
                name="EMA21 High",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=history.index,
                y=history["ema21_low"],
                mode="lines",
                line=dict(color="rgba(0, 130, 120, 0.55)", width=1),
                fill="tonexty",
                fillcolor="rgba(0, 130, 120, 0.15)",
                name="EMA21 Low",
            )
        )
        fig.add_trace(
            go.Scatter(x=history.index, y=history["sma50"], mode="lines", line=dict(color="#ff8c42", width=1.5), name="SMA50")
        )
        fig.add_trace(
            go.Scatter(x=history.index, y=history["sma200"], mode="lines", line=dict(color="#4c4f69", width=1.5), name="SMA200")
        )

        if pivot_result.is_valid and pivot_result.pivot_price is not None:
            fig.add_hline(
                y=pivot_result.pivot_price,
                line_dash="dot",
                line_color="#d62828",
                annotation_text=f"Pivot {pivot_result.pivot_price:.2f}",
                annotation_position="top right",
            )

        overheat_points = history.loc[history.get("overheat", pd.Series(False, index=history.index))]
        if not overheat_points.empty:
            fig.add_trace(
                go.Scatter(
                    x=overheat_points.index,
                    y=overheat_points["high"] * 1.01,
                    mode="markers",
                    marker=dict(color="#d62828", size=7, symbol="circle"),
                    name="Overheat",
                )
            )

        fig.update_layout(
            template="plotly_white",
            height=680,
            xaxis_title="Date",
            yaxis_title="Price",
            legend=dict(orientation="h"),
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_rangeslider_visible=False,
        )
        return fig
