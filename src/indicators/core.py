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
    adr_formula: str = "sma_high_low_ratio"
    dcr_formula: str = "closing_range"
    relvol_period: int = 50
    ud_volume_period: int = 50
    rsi_short_period: int = 21
    rsi_long_period: int = 63
    weekly_short_wma_period: int = 10
    weekly_long_wma_period: int = 30
    three_weeks_tight_pct_threshold: float = 1.5
    enable_3wt: bool = True
    atr_21ema_good_min: float = -0.5
    atr_21ema_good_max: float = 1.0
    atr_50sma_good_max: float = 3.0
    ema21_low_pct_full_max: float = 5.0
    ema21_low_pct_reduce_max: float = 8.0
    atr_pct_from_50sma_overheat: float = 7.0
    show_overheat_dot: bool = True
    pp_count_window_days: int = 20
    pocket_pivot_lookback: int = 10
    structure_pivot_min_length: int = 2
    structure_pivot_max_length: int = 10
    structure_pivot_priority_mode: str = "tightest"
    resistance_test_lookback: int = 20
    resistance_zone_width_atr: float = 0.5
    resistance_test_count_window: int = 20

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "IndicatorConfig":
        values = {key: value for key, value in payload.items() if key in cls.__dataclass_fields__}
        if "three_weeks_tight_pct_threshold" not in values and "three_weeks_tight_threshold_pct" in payload:
            values["three_weeks_tight_pct_threshold"] = payload["three_weeks_tight_threshold_pct"]
        if "adr_formula" in values and values["adr_formula"] == "hl_pct":
            values["adr_formula"] = "sma_high_low_ratio"
        return cls(**values)


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
        df["high_52w"] = df["high"].rolling(252).max()
        df["low_52w"] = df["low"].rolling(252).min()
        df["dist_from_52w_high"] = ((df["close"] / df["high_52w"].replace(0, np.nan)) - 1.0) * 100.0
        df["dist_from_52w_low"] = ((df["close"] / df["low_52w"].replace(0, np.nan)) - 1.0) * 100.0
        df["avg_volume_50d"] = df["volume"].rolling(self.config.relvol_period).mean()

        weekly = df.resample("W-FRI").agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        weekly["wma10_weekly"] = weighted_moving_average(weekly["close"], self.config.weekly_short_wma_period)
        weekly["wma30_weekly"] = weighted_moving_average(weekly["close"], self.config.weekly_long_wma_period)
        weekly["three_weeks_tight"] = self._calculate_three_weeks_tight(weekly) if self.config.enable_3wt else False
        df["wma10_weekly"] = weekly["wma10_weekly"].reindex(df.index, method="ffill")
        df["wma30_weekly"] = weekly["wma30_weekly"].reindex(df.index, method="ffill")
        weekly_tight = weekly["three_weeks_tight"].astype(bool).reindex(df.index, method="ffill")
        df["three_weeks_tight"] = weekly_tight.eq(True)

        previous_close = df["close"].shift(1)
        up_volume = df["volume"].where(df["close"] >= previous_close, 0.0)
        down_volume = df["volume"].where(df["close"] < previous_close, 0.0)
        rolling_up_volume = up_volume.rolling(self.config.ud_volume_period).sum()
        rolling_down_volume = down_volume.rolling(self.config.ud_volume_period).sum()
        df["ud_volume_ratio"] = rolling_up_volume / rolling_down_volume.clip(lower=1.0)

        true_range = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - previous_close).abs(),
                (df["low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        df["atr"] = true_range.ewm(alpha=1 / self.config.atr_period, adjust=False).mean()

        if self.config.adr_formula == "sma_high_low_ratio":
            high_low_ratio = df["high"] / df["low"].replace(0, np.nan)
            df["adr_percent"] = (high_low_ratio.rolling(self.config.adr_period).mean() - 1.0) * 100.0
        elif self.config.adr_formula == "hl_pct":
            daily_range_pct = (df["high"] - df["low"]) / df["close"].replace(0, np.nan) * 100.0
            df["adr_percent"] = daily_range_pct.rolling(self.config.adr_period).mean()
        else:
            daily_range_pct = (df["high"] / df["low"].replace(0, np.nan) - 1.0) * 100.0
            df["adr_percent"] = daily_range_pct.rolling(self.config.adr_period).mean()

        range_width = (df["high"] - df["low"]).replace(0, np.nan)
        df["dcr_percent"] = ((df["close"] - df["low"]) / range_width * 100.0).fillna(50.0)
        df["rel_volume"] = df["volume"] / df["avg_volume_50d"].replace(0, np.nan)
        df["volume_ma5"] = df["volume"].rolling(5).mean()
        df["volume_ma20"] = df["volume"].rolling(20).mean()
        df["volume_ma5_to_ma20_ratio"] = df["volume_ma5"] / df["volume_ma20"].replace(0, np.nan)
        df["volume_ratio_20d"] = df["volume"] / df["volume_ma20"].replace(0, np.nan)

        df["daily_change_pct"] = df["close"].pct_change(fill_method=None) * 100.0
        df["rsi21"] = self._calculate_rsi(df["close"], self.config.rsi_short_period)
        df["rsi63"] = self._calculate_rsi(df["close"], self.config.rsi_long_period)
        df["from_open_pct"] = (df["close"] - df["open"]) / df["open"].replace(0, np.nan) * 100.0
        df["weekly_return"] = df["close"].pct_change(5, fill_method=None) * 100.0
        df["monthly_return"] = df["close"].pct_change(21, fill_method=None) * 100.0
        df["quarterly_return"] = df["close"].pct_change(63, fill_method=None) * 100.0
        df["rolling_20d_close_high"] = df["close"].rolling(20).max()
        df["drawdown_from_20d_high_pct"] = (
            (df["rolling_20d_close_high"] - df["close"]) / df["rolling_20d_close_high"].replace(0, np.nan) * 100.0
        )
        df["resistance_level_lookback"] = df["high"].rolling(self.config.resistance_test_lookback).max().shift(1)
        resistance_zone_threshold = df["atr"] * self.config.resistance_zone_width_atr
        tested_resistance = (df["high"] >= (df["resistance_level_lookback"] - resistance_zone_threshold)) & (
            df["close"] < df["resistance_level_lookback"]
        )
        df["resistance_test_count"] = tested_resistance.rolling(
            self.config.resistance_test_count_window,
            min_periods=self.config.resistance_test_count_window,
        ).sum()
        df["breakout_body_ratio"] = (df["close"] - df["open"]) / range_width

        atr = df["atr"].replace(0, np.nan)
        df["atr_21ema_zone"] = (df["close"] - df["ema21_close"]) / atr
        df["atr_21emaH_zone"] = (df["close"] - df["ema21_high"]) / atr
        df["atr_21emaL_zone"] = (df["close"] - df["ema21_low"]) / atr
        df["atr_low_to_ema21_high"] = (df["low"] - df["ema21_high"]) / atr
        df["atr_low_to_ema21_low"] = (df["low"] - df["ema21_low"]) / atr
        df["atr_10wma_zone"] = (df["close"] - df["wma10_weekly"]) / atr
        df["atr_50sma_zone"] = (df["close"] - df["sma50"]) / atr
        df["prev_high"] = df["high"].shift(1)
        df["min_atr_21ema_zone_5d"] = df["atr_21ema_zone"].rolling(5).min()
        df["close_crossed_above_ema21"] = (df["close"] > df["ema21_close"]) & (
            df["close"].shift(1) <= df["ema21_close"].shift(1)
        )
        df["ema21_slope_5d_pct"] = ((df["ema21_close"] / df["ema21_close"].shift(5)) - 1.0) * 100.0
        df["sma50_slope_10d_pct"] = ((df["sma50"] / df["sma50"].shift(10)) - 1.0) * 100.0

        above_ema21_low = df["close"] >= df["ema21_low"]
        df["ema21_low_pct"] = np.where(
            above_ema21_low,
            (df["close"] - df["ema21_low"]) / df["ema21_low"].replace(0, np.nan) * 100.0,
            (df["close"] - df["ema21_low"]) / df["close"].replace(0, np.nan) * 100.0,
        )

        gain_from_ma_pct = (df["close"] / df["sma50"].replace(0, np.nan)) - 1.0
        atr_pct_daily = atr / df["close"].replace(0, np.nan)
        df["atr_pct_from_50sma"] = gain_from_ma_pct / atr_pct_daily.replace(0, np.nan)
        df["overheat"] = df["atr_pct_from_50sma"] >= self.config.atr_pct_from_50sma_overheat

        df["atr_21ema_label"] = df["atr_21ema_zone"].apply(
            lambda value: self._zone_label(value, self.config.atr_21ema_good_min, self.config.atr_21ema_good_max)
        )
        df["atr_50sma_label"] = df["atr_50sma_zone"].apply(
            lambda value: self._upper_bound_label(value, self.config.atr_50sma_good_max)
        )
        df["ema21_low_size_bucket"] = df["ema21_low_pct"].apply(self._size_bucket)

        df["pocket_pivot"] = self._calculate_pocket_pivot(df)
        df["pp_count_window"] = df["pocket_pivot"].rolling(self.config.pp_count_window_days).sum().fillna(0).astype(int)
        df["trend_base"] = (df["close"] > df["sma50"]) & (df["wma10_weekly"] > df["wma30_weekly"])
        structure_fields = self._calculate_structure_pivot_snapshot(df)
        for column_name, value in structure_fields.items():
            if isinstance(value, bool):
                df[column_name] = False
            else:
                df[column_name] = np.nan
            df.iloc[-1, df.columns.get_loc(column_name)] = value
        return df

    def _calculate_rsi(self, close: pd.Series, period: int) -> pd.Series:
        delta = close.diff()
        gains = delta.clip(lower=0.0)
        losses = -delta.clip(upper=0.0)
        avg_gain = gains.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        avg_loss = losses.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        rsi = rsi.where(~((avg_gain == 0) & (avg_loss == 0)), 50.0)
        rsi = rsi.where(~((avg_gain > 0) & (avg_loss == 0)), 100.0)
        rsi = rsi.where(~((avg_gain == 0) & (avg_loss > 0)), 0.0)
        return rsi

    def _calculate_three_weeks_tight(self, weekly: pd.DataFrame) -> pd.Series:
        close = weekly["close"]
        diff_0_1 = (close - close.shift(1)).abs() / close.shift(1).replace(0, np.nan) * 100.0
        diff_1_2 = (close.shift(1) - close.shift(2)).abs() / close.shift(2).replace(0, np.nan) * 100.0
        return ((diff_0_1 <= self.config.three_weeks_tight_pct_threshold) & (diff_1_2 <= self.config.three_weeks_tight_pct_threshold)).fillna(False)

    def _calculate_pocket_pivot(self, df: pd.DataFrame) -> pd.Series:
        prior_volume_high = df["volume"].rolling(self.config.pocket_pivot_lookback).max().shift(1)
        green_candle = df["close"] > df["open"]
        return (green_candle & (df["volume"] > prior_volume_high)).fillna(False)

    def _calculate_structure_pivot_snapshot(self, df: pd.DataFrame) -> dict[str, float | bool]:
        long_state = self._detect_structure_pivot_state(df, is_long=True)
        short_state = self._detect_structure_pivot_state(df, is_long=False)
        return {
            "structure_pivot_long_active": bool(long_state["active"]),
            "structure_pivot_long_breakout": bool(long_state["breakout"]),
            "structure_pivot_long_breakout_first_day": bool(long_state["breakout_first_day"]),
            "structure_pivot_long_breakout_gap_up": bool(long_state["breakout_gap_up"]),
            "structure_pivot_long_pivot_price": long_state["pivot_price"],
            "structure_pivot_long_length": long_state["length"],
            "structure_pivot_long_ll_price": long_state["prior_price"],
            "structure_pivot_long_hl_price": long_state["current_price"],
            "structure_pivot_short_active": bool(short_state["active"]),
            "structure_pivot_short_breakdown": bool(short_state["breakout"]),
            "structure_pivot_short_breakdown_first_day": bool(short_state["breakout_first_day"]),
            "structure_pivot_short_breakdown_gap_down": bool(short_state["breakout_gap_up"]),
            "structure_pivot_short_pivot_price": short_state["pivot_price"],
            "structure_pivot_short_length": short_state["length"],
            "structure_pivot_short_hh_price": short_state["prior_price"],
            "structure_pivot_short_lh_price": short_state["current_price"],
        }

    def _detect_structure_pivot_state(self, df: pd.DataFrame, *, is_long: bool) -> dict[str, float | bool]:
        min_length = max(int(self.config.structure_pivot_min_length), 1)
        max_length = max(int(self.config.structure_pivot_max_length), min_length)
        lows = df["low"].reset_index(drop=True)
        highs = df["high"].reset_index(drop=True)
        closes = df["close"].reset_index(drop=True)
        states = [
            {
                "length": length,
                "prev_price": np.nan,
                "prev_idx": None,
                "curr_price": np.nan,
                "curr_idx": None,
                "is_setup": False,
                "break_val": np.nan,
            }
            for length in range(min_length, max_length + 1)
        ]

        for current_bar in range(len(df)):
            for state in states:
                length = int(state["length"])
                center = current_bar - length
                if center - length < 0 or center + length > current_bar:
                    pass
                else:
                    pivot_price = self._pivot_price_at(lows, highs, center=center, length=length, is_long=is_long)
                    if pd.notna(pivot_price):
                        current_price = state["curr_price"]
                        setup_cond = bool(pd.notna(current_price) and ((pivot_price > current_price) if is_long else (pivot_price < current_price)))
                        state["prev_price"] = current_price
                        state["prev_idx"] = state["curr_idx"]
                        state["curr_price"] = float(pivot_price)
                        state["curr_idx"] = center
                        state["is_setup"] = setup_cond
                        state["break_val"] = np.nan
                        if setup_cond and state["prev_idx"] is not None:
                            start = int(state["prev_idx"]) + 1
                            end = center - 1
                            if end >= start:
                                if is_long:
                                    state["break_val"] = float(highs.iloc[start : end + 1].max())
                                else:
                                    state["break_val"] = float(lows.iloc[start : end + 1].min())

                curr_idx = state["curr_idx"]
                curr_price = state["curr_price"]
                if not state["is_setup"] or curr_idx is None or pd.isna(curr_price):
                    continue
                if is_long and float(lows.iloc[current_bar]) < float(curr_price):
                    state["is_setup"] = False
                if not is_long and float(highs.iloc[current_bar]) > float(curr_price):
                    state["is_setup"] = False

        winner = self._select_structure_pivot_winner(states, is_long=is_long)
        if winner is None:
            return {
                "active": False,
                "breakout": False,
                "breakout_first_day": False,
                "breakout_gap_up": False,
                "pivot_price": np.nan,
                "length": np.nan,
                "prior_price": np.nan,
                "current_price": np.nan,
            }

        pivot_price = float(winner["break_val"])
        latest_close = float(closes.iloc[-1])
        previous_close = float(closes.iloc[-2]) if len(closes) >= 2 and pd.notna(closes.iloc[-2]) else float("nan")
        latest_open = float(df["open"].iloc[-1])
        breakout = latest_close > pivot_price if is_long else latest_close < pivot_price
        breakout_first_day = bool(
            breakout
            and pd.notna(previous_close)
            and (previous_close <= pivot_price if is_long else previous_close >= pivot_price)
        )
        breakout_gap_up = bool(breakout_first_day and latest_open > pivot_price) if is_long else bool(
            breakout_first_day and latest_open < pivot_price
        )
        return {
            "active": True,
            "breakout": bool(breakout),
            "breakout_first_day": breakout_first_day,
            "breakout_gap_up": breakout_gap_up,
            "pivot_price": pivot_price,
            "length": float(winner["length"]),
            "prior_price": float(winner["prev_price"]),
            "current_price": float(winner["curr_price"]),
        }

    def _pivot_price_at(
        self,
        lows: pd.Series,
        highs: pd.Series,
        *,
        center: int,
        length: int,
        is_long: bool,
    ) -> float:
        if is_long:
            series = lows
            current = float(series.iloc[center])
            left = series.iloc[center - length : center]
            right = series.iloc[center + 1 : center + length + 1]
            if bool((current < left).all() and (current <= right).all()):
                return current
        else:
            series = highs
            current = float(series.iloc[center])
            left = series.iloc[center - length : center]
            right = series.iloc[center + 1 : center + length + 1]
            if bool((current > left).all() and (current >= right).all()):
                return current
        return float("nan")

    def _select_structure_pivot_winner(
        self,
        states: list[dict[str, object]],
        *,
        is_long: bool,
    ) -> dict[str, object] | None:
        candidates = [state for state in states if bool(state["is_setup"]) and pd.notna(state["break_val"])]
        if not candidates:
            return None

        mode = self._normalize_structure_pivot_priority_mode(self.config.structure_pivot_priority_mode)
        if mode == "longest":
            return max(candidates, key=lambda item: int(item["length"]))
        if mode == "shortest":
            return min(candidates, key=lambda item: int(item["length"]))
        if is_long:
            return min(candidates, key=lambda item: (float(item["break_val"]), -int(item["length"])))
        return max(candidates, key=lambda item: (float(item["break_val"]), int(item["length"])))

    def _normalize_structure_pivot_priority_mode(self, raw_mode: object) -> str:
        mode = str(raw_mode).strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "tightest": "tightest",
            "tightest_structure": "tightest",
            "longest": "longest",
            "longest_length": "longest",
            "shortest": "shortest",
            "shortest_length": "shortest",
        }
        return aliases.get(mode, "tightest")

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
