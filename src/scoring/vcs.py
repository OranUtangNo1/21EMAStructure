from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class VCSConfig:
    """Configuration for the initial VCS hypothesis."""

    vcs_threshold_candidate: float = 60.0
    vcs_threshold_priority: float = 80.0
    len_short: int = 13
    len_long: int = 63
    len_volume: int = 50
    sensitivity: float = 2.0
    trend_penalty_weight: float = 1.0
    bonus_max: float = 15.0

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "VCSConfig":
        return cls(**{key: value for key, value in payload.items() if key in cls.__dataclass_fields__})


class VCSCalculator:
    """Estimate contraction quality as a supporting score, not a standalone signal."""

    def __init__(self, config: VCSConfig) -> None:
        self.config = config

    def calculate_series(self, history: pd.DataFrame) -> pd.Series:
        returns = history["close"].pct_change()
        short_vol = returns.rolling(self.config.len_short).std()
        long_vol = returns.rolling(self.config.len_long).std().replace(0, np.nan)
        short_range = ((history["high"] - history["low"]) / history["close"].replace(0, np.nan)).rolling(self.config.len_short).mean()
        long_range = ((history["high"] - history["low"]) / history["close"].replace(0, np.nan)).rolling(self.config.len_long).mean().replace(0, np.nan)
        short_volume = history["volume"].rolling(self.config.len_short).mean()
        long_volume = history["volume"].rolling(self.config.len_volume).mean().replace(0, np.nan)

        vol_component = (1.0 - (short_vol / long_vol).clip(0, 2) / 2.0) * 40.0
        range_component = (1.0 - (short_range / long_range).clip(0, 2) / 2.0) * 45.0
        volume_bonus = (1.0 - (short_volume / long_volume).clip(0, 2) / 2.0) * self.config.bonus_max
        trend_penalty = np.where(history["close"] < history["sma50"], 15.0 * self.config.trend_penalty_weight, 0.0)
        vcs = (vol_component + range_component) * min(self.config.sensitivity, 2.0) / 2.0 + volume_bonus + 5.0 - trend_penalty
        return vcs.clip(0.0, 100.0)

    def add_scores(self, snapshot: pd.DataFrame, histories: dict[str, pd.DataFrame]) -> pd.DataFrame:
        result = snapshot.copy()
        result["vcs"] = np.nan
        for ticker, history in histories.items():
            series = self.calculate_series(history)
            if not series.empty:
                result.loc[ticker, "vcs"] = float(series.iloc[-1])
        return result
