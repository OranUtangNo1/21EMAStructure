from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class VCSConfig:
    """Configuration for the published Pine VCS workflow."""

    vcs_threshold_candidate: float = 60.0
    vcs_threshold_priority: float = 80.0
    len_short: int = 13
    len_long: int = 63
    len_volume: int = 50
    hl_lookback: int = 63
    sensitivity: float = 2.0
    trend_penalty_weight: float = 1.0
    penalty_factor: float = 0.75
    bonus_max: float = 15.0

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "VCSConfig":
        return cls(**{key: value for key, value in payload.items() if key in cls.__dataclass_fields__})


class VCSCalculator:
    """Estimate contraction quality using the published Pine VCS workflow."""

    _VOLUME_SHORT_PERIOD = 5
    _SMOOTH_SPAN = 3
    _CONSISTENCY_THRESHOLD = 70.0
    _RAW_ATR_WEIGHT = 0.4
    _RAW_STD_WEIGHT = 0.4
    _RAW_VOLUME_WEIGHT = 0.2

    def __init__(self, config: VCSConfig) -> None:
        self.config = config

    def calculate_series(self, history: pd.DataFrame) -> pd.Series:
        close = history["close"].astype(float)
        high = history["high"].astype(float)
        low = history["low"].astype(float)
        volume = history["volume"].astype(float)
        bar_count = pd.Series(np.arange(1, len(history) + 1, dtype=int), index=history.index, dtype=int)

        len_short = bar_count.clip(upper=int(self.config.len_short))
        len_long = bar_count.clip(upper=int(self.config.len_long))
        len_vol = bar_count.clip(upper=int(self.config.len_volume))

        previous_close = close.shift(1)
        true_range = pd.concat(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        tr_short = self._variable_length_sma(true_range, len_short)
        tr_long_avg = self._variable_length_sma(true_range, len_long)
        ratio_atr = tr_short / tr_long_avg.clip(lower=1e-6)

        std_short = self._variable_length_std(close, len_short)
        std_long_avg = self._variable_length_std(close, len_long)
        ratio_std = std_short / std_long_avg.clip(lower=1e-6)

        vol_avg = self._variable_length_sma(volume, len_vol)
        vol_short_avg = volume.rolling(self._VOLUME_SHORT_PERIOD, min_periods=1).mean()
        vol_ratio = vol_short_avg / vol_avg.clip(lower=1.0)

        net_change = (close - close.shift(int(self.config.len_short))).abs()
        total_travel = self._variable_length_sum(true_range, len_short)
        efficiency = net_change / total_travel.clip(lower=1e-6)
        trend_factor = (1.0 - (efficiency * float(self.config.trend_penalty_weight))).clip(lower=0.0)

        low_recent = self._variable_length_lowest(low, len_short)
        bars_before_short = bar_count - int(self.config.len_short)
        low_base = low.rolling(int(self.config.hl_lookback), min_periods=1).min().shift(int(self.config.len_short))
        is_higher_low = pd.Series(True, index=history.index, dtype=bool)
        has_history = bars_before_short > 0
        is_higher_low.loc[has_history] = (low_recent.loc[has_history] >= low_base.loc[has_history]).fillna(False)

        score_atr = (1.0 - ratio_atr.fillna(1.0)).clip(lower=0.0) * float(self.config.sensitivity)
        score_std = (1.0 - ratio_std.fillna(1.0)).clip(lower=0.0) * float(self.config.sensitivity)
        score_vol = (1.0 - vol_ratio.fillna(1.0)).clip(lower=0.0)

        raw_score = (
            score_atr * self._RAW_ATR_WEIGHT
            + score_std * self._RAW_STD_WEIGHT
            + score_vol * self._RAW_VOLUME_WEIGHT
        )
        filtered_score = raw_score * trend_factor
        physics_score = (filtered_score * 100.0).clip(upper=100.0)
        smooth_physics = physics_score.ewm(span=self._SMOOTH_SPAN, adjust=False).mean()

        is_tight = smooth_physics >= self._CONSISTENCY_THRESHOLD
        days_tight = self._consecutive_true_count(is_tight)
        weight_physics = (100.0 - float(self.config.bonus_max)) / 100.0
        weighted_physics_score = smooth_physics * weight_physics
        consistency_score = days_tight.clip(upper=float(self.config.bonus_max))
        total_score = weighted_physics_score + consistency_score
        final_score = total_score.where(is_higher_low, total_score * float(self.config.penalty_factor))
        return final_score.fillna(0.0).clip(0.0, 100.0)

    def add_scores(self, snapshot: pd.DataFrame, histories: dict[str, pd.DataFrame]) -> pd.DataFrame:
        result = snapshot.copy()
        result["vcs"] = np.nan
        for ticker, history in histories.items():
            series = self.calculate_series(history)
            if not series.empty:
                result.loc[ticker, "vcs"] = float(series.iloc[-1])
        return result

    def _consecutive_true_count(self, mask: pd.Series) -> pd.Series:
        counts: list[int] = []
        streak = 0
        for value in mask.fillna(False).astype(bool):
            streak = streak + 1 if value else 0
            counts.append(streak)
        return pd.Series(counts, index=mask.index, dtype=float)

    def _variable_length_sma(self, series: pd.Series, windows: pd.Series) -> pd.Series:
        values: list[float] = []
        for idx, window in enumerate(windows.astype(int).tolist()):
            start = max(0, idx - window + 1)
            values.append(float(series.iloc[start : idx + 1].mean()))
        return pd.Series(values, index=series.index, dtype=float)

    def _variable_length_sum(self, series: pd.Series, windows: pd.Series) -> pd.Series:
        values: list[float] = []
        for idx, window in enumerate(windows.astype(int).tolist()):
            start = max(0, idx - window + 1)
            values.append(float(series.iloc[start : idx + 1].sum()))
        return pd.Series(values, index=series.index, dtype=float)

    def _variable_length_std(self, series: pd.Series, windows: pd.Series) -> pd.Series:
        values: list[float] = []
        for idx, window in enumerate(windows.astype(int).tolist()):
            start = max(0, idx - window + 1)
            values.append(float(series.iloc[start : idx + 1].std(ddof=0)))
        return pd.Series(values, index=series.index, dtype=float)

    def _variable_length_lowest(self, series: pd.Series, windows: pd.Series) -> pd.Series:
        values: list[float] = []
        for idx, window in enumerate(windows.astype(int).tolist()):
            start = max(0, idx - window + 1)
            values.append(float(series.iloc[start : idx + 1].min()))
        return pd.Series(values, index=series.index, dtype=float)
