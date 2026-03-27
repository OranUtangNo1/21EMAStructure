from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.utils import weighted_moving_average


@dataclass(slots=True)
class IndicatorConfig:
    """Configuration for core technical indicators."""

    ema_period: int = 21
    sma_short_period: int = 50
    sma_long_period: int = 200
    atr_period: int = 14
    adr_period: int = 20
    adr_formula: str = "hl_pct"
    dcr_formula: str = "closing_range"
    relvol_period: int = 50
    weekly_short_wma_period: int = 10
    weekly_long_wma_period: int = 30
    three_weeks_tight_threshold_pct: float = 1.5
    enable_3wt: bool = True
    atr_21ema_good_min: float = -0.5
    atr_21ema_good_max: float = 1.0
    atr_50sma_good_max: float = 3.0
    ema21_low_pct_full_max: float = 5.0
    ema21_low_pct_reduce_max: float = 8.0
    atr_pct_from_50sma_overheat: float = 7.0
    show_overheat_dot: bool = True
    pp_count_window_days: int = 30
    pocket_pivot_lookback: int = 10

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "IndicatorConfig":
        return cls(**{key: value for key, value in payload.items() if key in cls.__dataclass_fields__})


class IndicatorCalculator:
    """Calculate the daily indicator stack used across the platform."""

    def __init__(self, config: IndicatorConfig) -> None:
        self.config = config

    def calculate(self, frame: pd.DataFrame) -> pd.DataFrame:
        df = frame.copy().sort_index()
        if df.empty:
            return df

        required = ["open", "high", "low", "close", "volume"]
        missing = [column for column in required if column not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        df["ema21_high"] = df["high"].ewm(span=self.config.ema_period, adjust=False).mean()
        df["ema21_low"] = df["low"].ewm(span=self.config.ema_period, adjust=False).mean()
        df["ema21_close"] = df["close"].ewm(span=self.config.ema_period, adjust=False).mean()
        df["ema21_cloud_width"] = df["ema21_high"] - df["ema21_low"]
        df["sma50"] = df["close"].rolling(self.config.sma_short_period).mean()
        df["sma200"] = df["close"].rolling(self.config.sma_long_period).mean()
        df["avg_volume_50d"] = df["volume"].rolling(self.config.relvol_period).mean()

        weekly = df.resample("W-FRI").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        })
        weekly["wma10_weekly"] = weighted_moving_average(weekly["close"], self.config.weekly_short_wma_period)
        weekly["wma30_weekly"] = weighted_moving_average(weekly["close"], self.config.weekly_long_wma_period)
        weekly["three_weeks_tight"] = self._calculate_three_weeks_tight(weekly) if self.config.enable_3wt else False
        df["wma10_weekly"] = weekly["wma10_weekly"].reindex(df.index, method="ffill")
        df["wma30_weekly"] = weekly["wma30_weekly"].reindex(df.index, method="ffill")
        weekly_tight = weekly["three_weeks_tight"].astype(bool).reindex(df.index, method="ffill")
        df["three_weeks_tight"] = weekly_tight.eq(True)

        previous_close = df["close"].shift(1)
        true_range = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - previous_close).abs(),
                (df["low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        df["atr"] = true_range.ewm(alpha=1 / self.config.atr_period, adjust=False).mean()

        if self.config.adr_formula == "hl_pct":
            daily_range_pct = (df["high"] - df["low"]) / df["close"].replace(0, np.nan) * 100.0
        else:
            daily_range_pct = (df["high"] / df["low"].replace(0, np.nan) - 1.0) * 100.0
        df["adr_percent"] = daily_range_pct.rolling(self.config.adr_period).mean()

        range_width = (df["high"] - df["low"]).replace(0, np.nan)
        df["dcr_percent"] = ((df["close"] - df["low"]) / range_width * 100.0).fillna(50.0)
        df["rel_volume"] = df["volume"] / df["avg_volume_50d"].replace(0, np.nan)

        df["daily_change_pct"] = df["close"].pct_change() * 100.0
        df["from_open_pct"] = (df["close"] - df["open"]) / df["open"].replace(0, np.nan) * 100.0
        df["weekly_return"] = df["close"].pct_change(5) * 100.0
        df["monthly_return"] = df["close"].pct_change(21) * 100.0
        df["quarterly_return"] = df["close"].pct_change(63) * 100.0

        df["atr_21ema_zone"] = (df["close"] - df["ema21_low"]) / df["atr"].replace(0, np.nan)
        df["atr_10wma_zone"] = (df["close"] - df["wma10_weekly"]) / df["atr"].replace(0, np.nan)
        df["atr_50sma_zone"] = (df["close"] - df["sma50"]) / df["atr"].replace(0, np.nan)
        df["ema21_low_pct"] = (df["close"] - df["ema21_low"]) / df["close"].replace(0, np.nan) * 100.0
        df["atr_pct_from_50sma"] = (df["close"] - df["sma50"]) / df["sma50"].replace(0, np.nan) * 100.0
        df["overheat"] = df["atr_pct_from_50sma"] >= self.config.atr_pct_from_50sma_overheat

        df["atr_21ema_label"] = df["atr_21ema_zone"].apply(
            lambda value: self._zone_label(value, self.config.atr_21ema_good_min, self.config.atr_21ema_good_max)
        )
        df["atr_50sma_label"] = df["atr_50sma_zone"].apply(
            lambda value: self._upper_bound_label(value, self.config.atr_50sma_good_max)
        )
        df["ema21_low_size_bucket"] = df["ema21_low_pct"].apply(self._size_bucket)

        df["pocket_pivot"] = self._calculate_pocket_pivot(df)
        df["pp_count_30d"] = df["pocket_pivot"].rolling(self.config.pp_count_window_days).sum().fillna(0).astype(int)
        df["trend_base"] = (df["close"] > df["sma50"]) & (df["wma10_weekly"] > df["wma30_weekly"])
        return df

    def _calculate_three_weeks_tight(self, weekly: pd.DataFrame) -> pd.Series:
        close_range_pct = (
            (weekly["close"].rolling(3).max() - weekly["close"].rolling(3).min())
            / weekly["close"].rolling(3).mean().replace(0, np.nan)
            * 100.0
        )
        weekly_changes = weekly["close"].pct_change().abs() * 100.0
        max_change = weekly_changes.rolling(3).max()
        return ((close_range_pct <= self.config.three_weeks_tight_threshold_pct) & (max_change <= self.config.three_weeks_tight_threshold_pct)).fillna(False)

    def _calculate_pocket_pivot(self, df: pd.DataFrame) -> pd.Series:
        down_volume = df["volume"].where(df["close"] <= df["close"].shift(1))
        max_down_volume = down_volume.rolling(self.config.pocket_pivot_lookback).max().shift(1)
        green_candle = df["close"] > df["open"]
        return (green_candle & (df["volume"] > max_down_volume) & (df["close"] > df["close"].shift(1))).fillna(False)

    def _zone_label(self, value: float, lower: float, upper: float) -> str:
        if pd.isna(value):
            return "unknown"
        if value < lower:
            return "below"
        if value <= upper:
            return "good"
        return "extended"

    def _upper_bound_label(self, value: float, upper: float) -> str:
        if pd.isna(value):
            return "unknown"
        return "good" if value <= upper else "extended"

    def _size_bucket(self, value: float) -> str:
        if pd.isna(value):
            return "unknown"
        if value <= self.config.ema21_low_pct_full_max:
            return "full"
        if value <= self.config.ema21_low_pct_reduce_max:
            return "reduced"
        return "avoid"
