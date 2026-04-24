from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.utils import normalize_series


@dataclass(slots=True)
class RSConfig:
    """Configuration for benchmark-relative strength scoring."""

    benchmark_symbol: str = "SPY"
    rs_lookbacks: tuple[int, ...] = (5, 21, 63, 126)
    rs_normalization_method: str = "percentile"
    rs_strong_threshold: float = 80.0
    rs_weak_threshold: float = 39.0
    rs_new_high_tolerance: float = 1.0

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "RSConfig":
        lookbacks = tuple(int(value) for value in payload.get("rs_lookbacks", [5, 21, 63, 126]))
        return cls(
            benchmark_symbol=str(payload.get("benchmark_symbol", "SPY")),
            rs_lookbacks=lookbacks,
            rs_normalization_method=str(payload.get("rs_normalization_method", "percentile")),
            rs_strong_threshold=float(payload.get("rs_strong_threshold", 80.0)),
            rs_weak_threshold=float(payload.get("rs_weak_threshold", 39.0)),
            rs_new_high_tolerance=float(payload.get("rs_new_high_tolerance", 1.0)),
        )


class RSScorer:
    """Score symbols versus a benchmark using Pine-style percentile rank within each symbol's own ratio history."""

    def __init__(self, config: RSConfig) -> None:
        self.config = config

    def score(
        self,
        snapshot: pd.DataFrame,
        histories: dict[str, pd.DataFrame],
        benchmark_history: pd.DataFrame,
    ) -> pd.DataFrame:
        result = snapshot.copy()
        if benchmark_history.empty or "close" not in benchmark_history:
            return self._append_empty_columns(result)

        benchmark_close = benchmark_history["close"].sort_index().replace(0, np.nan)
        raw_scores: dict[str, dict[str, float]] = {}
        current_ratios: dict[str, float] = {}
        current_ratio_52w_highs: dict[str, float] = {}
        current_ratio_at_52w_highs: dict[str, bool] = {}

        for ticker, history in histories.items():
            raw_scores[ticker] = {}
            current_ratios[ticker] = np.nan
            current_ratio_52w_highs[ticker] = np.nan
            current_ratio_at_52w_highs[ticker] = False
            if history.empty or "close" not in history:
                self._fill_missing_scores(raw_scores[ticker])
                continue

            aligned = pd.concat([history["close"], benchmark_close], axis=1, join="inner").dropna()
            if aligned.empty:
                self._fill_missing_scores(raw_scores[ticker])
                continue

            ratio = aligned.iloc[:, 0] / aligned.iloc[:, 1]
            ratio = ratio.replace([np.inf, -np.inf], np.nan).dropna()
            if ratio.empty:
                self._fill_missing_scores(raw_scores[ticker])
                continue

            current_ratios[ticker] = float(ratio.iloc[-1])
            ratio_52w_high = ratio.rolling(252, min_periods=126).max().iloc[-1]
            current_ratio_52w_highs[ticker] = float(ratio_52w_high) if pd.notna(ratio_52w_high) else np.nan
            if pd.notna(ratio_52w_high):
                threshold = float(ratio_52w_high) * (1.0 - self.config.rs_new_high_tolerance / 100.0)
                current_ratio_at_52w_highs[ticker] = float(ratio.iloc[-1]) >= threshold
            for lookback in self.config.rs_lookbacks:
                raw_scores[ticker][f"raw_rs{lookback}"] = self._score_ratio_window(ratio, lookback)

        raw_frame = pd.DataFrame.from_dict(raw_scores, orient="index")
        for lookback in self.config.rs_lookbacks:
            column = f"raw_rs{lookback}"
            values = raw_frame[column] if column in raw_frame.columns else pd.Series(np.nan, index=result.index, dtype=float)
            result[column] = values.reindex(result.index)
            result[f"rs{lookback}"] = result[column]

        result["price_ratio"] = pd.Series(current_ratios, dtype=float).reindex(result.index)
        result["rs_ratio"] = pd.Series(current_ratios, dtype=float).reindex(result.index)
        result["rs_ratio_52w_high"] = pd.Series(current_ratio_52w_highs, dtype=float).reindex(result.index)
        result["rs_ratio_at_52w_high"] = pd.Series(current_ratio_at_52w_highs, dtype=bool).reindex(result.index).fillna(False)
        return result

    def _append_empty_columns(self, snapshot: pd.DataFrame) -> pd.DataFrame:
        result = snapshot.copy()
        for lookback in self.config.rs_lookbacks:
            result[f"raw_rs{lookback}"] = np.nan
            result[f"rs{lookback}"] = np.nan
        result["price_ratio"] = np.nan
        result["rs_ratio"] = np.nan
        result["rs_ratio_52w_high"] = np.nan
        result["rs_ratio_at_52w_high"] = False
        return result

    def _fill_missing_scores(self, raw_score_row: dict[str, float]) -> None:
        for lookback in self.config.rs_lookbacks:
            raw_score_row[f"raw_rs{lookback}"] = np.nan

    def _score_ratio_window(self, ratio: pd.Series, lookback: int) -> float:
        if len(ratio) < lookback:
            return float("nan")
        window = ratio.tail(lookback).dropna()
        if window.empty:
            return float("nan")
        if self.config.rs_normalization_method == "percentile":
            current = float(window.iloc[-1])
            return float((window.le(current).sum() / len(window)) * 100.0)
        ranked = normalize_series(window, self.config.rs_normalization_method)
        if ranked.empty:
            return float("nan")
        value = ranked.iloc[-1]
        return float(value) if pd.notna(value) else float("nan")
