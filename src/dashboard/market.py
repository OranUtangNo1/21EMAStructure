from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass(slots=True)
class MarketConditionConfig:
    """Configurable scoring model for the market dashboard."""

    component_weights: dict[str, float]
    bullish_threshold: float = 80.0
    positive_threshold: float = 60.0
    neutral_threshold: float = 40.0
    negative_threshold: float = 20.0

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "MarketConditionConfig":
        return cls(
            component_weights=dict(payload.get("component_weights", {})),
            bullish_threshold=float(payload.get("bullish_threshold", 80.0)),
            positive_threshold=float(payload.get("positive_threshold", 60.0)),
            neutral_threshold=float(payload.get("neutral_threshold", 40.0)),
            negative_threshold=float(payload.get("negative_threshold", 20.0)),
        )


@dataclass(slots=True)
class MarketConditionResult:
    """Summary object for the market dashboard page."""

    trade_date: pd.Timestamp | None
    score: float
    label: str
    component_scores: dict[str, float]
    breadth_summary: dict[str, float]
    vix_close: float | None
    update_time: str


class MarketConditionScorer:
    """Score the tape using breadth plus an optional VIX component."""

    def __init__(self, config: MarketConditionConfig) -> None:
        self.config = config

    def score(
        self,
        snapshot: pd.DataFrame,
        benchmark_history: pd.DataFrame,
        vix_history: pd.DataFrame | None = None,
    ) -> MarketConditionResult:
        if snapshot.empty:
            return MarketConditionResult(
                trade_date=None,
                score=0.0,
                label="No Data",
                component_scores={},
                breadth_summary={},
                vix_close=None,
                update_time=datetime.now().isoformat(timespec="seconds"),
            )

        component_scores = {
            "pct_above_ema21": float((snapshot["close"] >= snapshot["ema21_low"]).mean() * 100.0),
            "pct_above_sma50": float((snapshot["close"] >= snapshot["sma50"]).mean() * 100.0),
            "pct_above_sma200": float((snapshot["close"] >= snapshot["sma200"]).mean() * 100.0),
            "pct_sma50_gt_sma200": float((snapshot["sma50"] >= snapshot["sma200"]).mean() * 100.0),
        }
        vix_close = None
        if vix_history is not None and not vix_history.empty:
            vix_close = float(vix_history["close"].iloc[-1])
            component_scores["vix_score"] = max(0.0, min(100.0, 100.0 - max(vix_close - 12.0, 0.0) * 4.0))
        else:
            component_scores["vix_score"] = 50.0

        score = 0.0
        for name, weight in self.config.component_weights.items():
            score += component_scores.get(name, 50.0) * weight
        label = self._label(score)
        breadth_summary = {
            "Above EMA21 %": round(component_scores["pct_above_ema21"], 2),
            "Above SMA50 %": round(component_scores["pct_above_sma50"], 2),
            "Above SMA200 %": round(component_scores["pct_above_sma200"], 2),
            "SMA50 > SMA200 %": round(component_scores["pct_sma50_gt_sma200"], 2),
        }
        trade_date = pd.to_datetime(snapshot["trade_date"]).max()
        return MarketConditionResult(
            trade_date=trade_date,
            score=round(score, 2),
            label=label,
            component_scores={key: round(value, 2) for key, value in component_scores.items()},
            breadth_summary=breadth_summary,
            vix_close=round(vix_close, 2) if vix_close is not None else None,
            update_time=datetime.now().isoformat(timespec="seconds"),
        )

    def _label(self, score: float) -> str:
        if score >= self.config.bullish_threshold:
            return "Bullish"
        if score >= self.config.positive_threshold:
            return "Positive"
        if score >= self.config.neutral_threshold:
            return "Neutral"
        if score >= self.config.negative_threshold:
            return "Cautious"
        return "Risk-off"
