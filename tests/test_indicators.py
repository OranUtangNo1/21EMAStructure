from __future__ import annotations

import pandas as pd

from src.indicators.core import IndicatorCalculator, IndicatorConfig


def test_indicator_formulas_match_docs() -> None:
    dates = pd.date_range("2025-01-01", periods=3, freq="D")
    frame = pd.DataFrame(
        {
            "open": [10.0, 10.0, 11.0],
            "high": [10.0, 11.0, 12.0],
            "low": [10.0, 9.0, 10.0],
            "close": [10.0, 10.0, 12.0],
            "adjusted_close": [10.0, 10.0, 12.0],
            "volume": [1_000_000, 1_000_000, 1_000_000],
        },
        index=dates,
    )
    calculator = IndicatorCalculator(
        IndicatorConfig(
            ema_period=1,
            sma_short_period=2,
            sma_long_period=2,
            atr_period=1,
            adr_period=2,
            relvol_period=2,
            enable_3wt=False,
        )
    )

    result = calculator.calculate(frame)
    latest = result.iloc[-1]

    assert round(float(latest["atr_21ema_zone"]), 6) == 0.0
    assert round(float(latest["atr_21emaH_zone"]), 6) == 0.0
    assert round(float(latest["atr_21emaL_zone"]), 6) == 1.0
    assert round(float(latest["atr_low_to_ema21_high"]), 6) == -1.0
    assert round(float(latest["atr_low_to_ema21_low"]), 6) == 0.0
    assert round(float(latest["prev_high"]), 6) == 11.0
    assert round(float(latest["ema21_low_pct"]), 6) == 20.0
    assert round(float(latest["adr_percent"]), 6) == round((((11.0 / 9.0) + (12.0 / 10.0)) / 2.0 - 1.0) * 100.0, 6)
    assert round(float(latest["atr_pct_from_50sma"]), 6) == round((((12.0 / 11.0) - 1.0) / (2.0 / 12.0)), 6)


def test_indicator_calculator_adds_52_week_high_from_daily_highs() -> None:
    dates = pd.date_range("2025-01-01", periods=252, freq="B")
    frame = pd.DataFrame(
        {
            "open": [90.0] * 252,
            "high": [100.0] * 251 + [125.0],
            "low": [89.0] * 252,
            "close": [95.0] * 252,
            "adjusted_close": [95.0] * 252,
            "volume": [1_000_000] * 252,
        },
        index=dates,
    )
    calculator = IndicatorCalculator(IndicatorConfig(sma_short_period=2, sma_long_period=2, relvol_period=2, enable_3wt=False))

    result = calculator.calculate(frame)

    assert "high_52w" in result.columns
    assert float(result.iloc[-1]["high_52w"]) == 125.0


def test_dist_from_52w_high_is_zero_when_close_matches_52w_high() -> None:
    dates = pd.date_range("2025-01-01", periods=252, freq="B")
    frame = pd.DataFrame(
        {
            "open": [90.0] * 252,
            "high": [100.0] * 251 + [125.0],
            "low": [80.0] * 252,
            "close": [95.0] * 251 + [125.0],
            "adjusted_close": [95.0] * 251 + [125.0],
            "volume": [1_000_000] * 252,
        },
        index=dates,
    )
    calculator = IndicatorCalculator(IndicatorConfig(sma_short_period=2, sma_long_period=2, relvol_period=2, enable_3wt=False))

    result = calculator.calculate(frame)

    assert float(result.iloc[-1]["dist_from_52w_high"]) == 0.0


def test_dist_from_52w_high_is_negative_when_close_is_below_high() -> None:
    dates = pd.date_range("2025-01-01", periods=252, freq="B")
    frame = pd.DataFrame(
        {
            "open": [90.0] * 252,
            "high": [100.0] * 251 + [125.0],
            "low": [80.0] * 252,
            "close": [95.0] * 251 + [112.5],
            "adjusted_close": [95.0] * 251 + [112.5],
            "volume": [1_000_000] * 252,
        },
        index=dates,
    )
    calculator = IndicatorCalculator(IndicatorConfig(sma_short_period=2, sma_long_period=2, relvol_period=2, enable_3wt=False))

    result = calculator.calculate(frame)

    assert round(float(result.iloc[-1]["dist_from_52w_high"]), 6) == -10.0


def test_dist_from_52w_low_is_zero_when_close_matches_52w_low() -> None:
    dates = pd.date_range("2025-01-01", periods=252, freq="B")
    frame = pd.DataFrame(
        {
            "open": [60.0] * 252,
            "high": [65.0] * 252,
            "low": [50.0] * 251 + [40.0],
            "close": [55.0] * 251 + [40.0],
            "adjusted_close": [55.0] * 251 + [40.0],
            "volume": [1_000_000] * 252,
        },
        index=dates,
    )
    calculator = IndicatorCalculator(IndicatorConfig(sma_short_period=2, sma_long_period=2, relvol_period=2, enable_3wt=False))

    result = calculator.calculate(frame)

    assert float(result.iloc[-1]["dist_from_52w_low"]) == 0.0


def test_ud_volume_ratio_is_one_when_up_and_down_volume_totals_match() -> None:
    dates = pd.date_range("2025-01-01", periods=5, freq="D")
    frame = pd.DataFrame(
        {
            "open": [10.0, 10.5, 10.5, 10.5, 10.5],
            "high": [10.2, 11.2, 10.2, 11.2, 10.2],
            "low": [9.8, 10.8, 9.8, 10.8, 9.8],
            "close": [10.0, 11.0, 10.0, 11.0, 10.0],
            "adjusted_close": [10.0, 11.0, 10.0, 11.0, 10.0],
            "volume": [100, 100, 100, 100, 100],
        },
        index=dates,
    )
    calculator = IndicatorCalculator(
        IndicatorConfig(
            ema_period=1,
            sma_short_period=1,
            sma_long_period=1,
            atr_period=1,
            adr_period=1,
            relvol_period=1,
            ud_volume_period=4,
            enable_3wt=False,
        )
    )

    result = calculator.calculate(frame)

    assert round(float(result.iloc[-1]["ud_volume_ratio"]), 6) == 1.0


def test_ud_volume_ratio_handles_all_up_days_without_dividing_by_zero() -> None:
    dates = pd.date_range("2025-01-01", periods=5, freq="D")
    frame = pd.DataFrame(
        {
            "open": [10.0, 10.5, 11.5, 12.5, 13.5],
            "high": [10.2, 11.2, 12.2, 13.2, 14.2],
            "low": [9.8, 10.8, 11.8, 12.8, 13.8],
            "close": [10.0, 11.0, 12.0, 13.0, 14.0],
            "adjusted_close": [10.0, 11.0, 12.0, 13.0, 14.0],
            "volume": [100, 100, 100, 100, 100],
        },
        index=dates,
    )
    calculator = IndicatorCalculator(
        IndicatorConfig(
            ema_period=1,
            sma_short_period=1,
            sma_long_period=1,
            atr_period=1,
            adr_period=1,
            relvol_period=1,
            ud_volume_period=4,
            enable_3wt=False,
        )
    )

    result = calculator.calculate(frame)

    assert float(result.iloc[-1]["ud_volume_ratio"]) == 400.0


def test_ema21_low_pct_uses_below_price_branch_when_under_support() -> None:
    dates = pd.date_range("2025-01-01", periods=2, freq="D")
    frame = pd.DataFrame(
        {
            "open": [10.0, 10.0],
            "high": [10.0, 10.0],
            "low": [10.0, 10.0],
            "close": [10.0, 9.0],
            "adjusted_close": [10.0, 9.0],
            "volume": [1_000_000, 1_000_000],
        },
        index=dates,
    )
    calculator = IndicatorCalculator(IndicatorConfig(ema_period=1, sma_short_period=1, sma_long_period=1, atr_period=1, adr_period=1, relvol_period=1, enable_3wt=False))

    result = calculator.calculate(frame)

    assert round(float(result.iloc[-1]["ema21_low_pct"]), 6) == round(((9.0 - 10.0) / 9.0) * 100.0, 6)


def test_three_weeks_tight_matches_two_consecutive_weekly_close_rules() -> None:
    dates = pd.date_range("2025-01-06", periods=15, freq="B")
    close = [95, 96, 97, 98, 100, 96, 97, 98, 99, 101, 97, 98, 99, 100, 102]
    frame = pd.DataFrame(
        {
            "open": close,
            "high": [value * 1.01 for value in close],
            "low": [value * 0.99 for value in close],
            "close": close,
            "adjusted_close": close,
            "volume": [1_000_000] * len(close),
        },
        index=dates,
    )
    calculator = IndicatorCalculator(IndicatorConfig(sma_short_period=2, sma_long_period=2, relvol_period=2, weekly_short_wma_period=2, weekly_long_wma_period=3, three_weeks_tight_pct_threshold=1.5))

    result = calculator.calculate(frame)

    assert bool(result.iloc[-1]["three_weeks_tight"]) is True


def test_pocket_pivot_uses_highest_total_volume_in_prior_10_days() -> None:
    dates = pd.date_range("2025-01-01", periods=11, freq="D")
    frame = pd.DataFrame(
        {
            "open": [10.0] * 10 + [10.0],
            "high": [10.5] * 10 + [11.5],
            "low": [9.5] * 10 + [9.8],
            "close": [10.2, 10.1, 10.0, 9.9, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 11.0],
            "adjusted_close": [10.2, 10.1, 10.0, 9.9, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 11.0],
            "volume": [100, 120, 140, 160, 500, 180, 190, 200, 210, 220, 300],
        },
        index=dates,
    )
    calculator = IndicatorCalculator(
        IndicatorConfig(
            ema_period=1,
            sma_short_period=1,
            sma_long_period=1,
            atr_period=1,
            adr_period=1,
            relvol_period=1,
            enable_3wt=False,
            pocket_pivot_lookback=10,
        )
    )

    result = calculator.calculate(frame)

    assert bool(result.iloc[-1]["pocket_pivot"]) is False


def test_pocket_pivot_flags_green_candle_when_volume_breaks_prior_10_day_high() -> None:
    dates = pd.date_range("2025-02-01", periods=11, freq="D")
    frame = pd.DataFrame(
        {
            "open": [10.0] * 10 + [10.0],
            "high": [10.4] * 10 + [11.6],
            "low": [9.6] * 10 + [9.9],
            "close": [10.0, 9.9, 10.1, 10.0, 10.2, 10.1, 10.3, 10.2, 10.4, 10.3, 11.2],
            "adjusted_close": [10.0, 9.9, 10.1, 10.0, 10.2, 10.1, 10.3, 10.2, 10.4, 10.3, 11.2],
            "volume": [100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 320],
        },
        index=dates,
    )
    calculator = IndicatorCalculator(
        IndicatorConfig(
            ema_period=1,
            sma_short_period=1,
            sma_long_period=1,
            atr_period=1,
            adr_period=1,
            relvol_period=1,
            enable_3wt=False,
            pocket_pivot_lookback=10,
        )
    )

    result = calculator.calculate(frame)

    assert bool(result.iloc[-1]["pocket_pivot"]) is True


def test_indicator_calculator_adds_rsi_columns() -> None:
    dates = pd.date_range("2025-01-01", periods=90, freq="D")
    close = [100.0 + (i * 0.2) + (5.0 if i > 70 else 0.0) for i in range(90)]
    frame = pd.DataFrame(
        {
            "open": close,
            "high": [value * 1.01 for value in close],
            "low": [value * 0.99 for value in close],
            "close": close,
            "adjusted_close": close,
            "volume": [1_000_000] * len(close),
        },
        index=dates,
    )
    calculator = IndicatorCalculator(IndicatorConfig())

    result = calculator.calculate(frame)

    assert "rsi21" in result.columns
    assert "rsi63" in result.columns
    assert pd.notna(result.iloc[-1]["rsi21"])
    assert pd.notna(result.iloc[-1]["rsi63"])


def test_indicator_calculator_adds_pullback_and_reclaim_fields() -> None:
    dates = pd.date_range("2025-01-01", periods=30, freq="D")
    close = [
        100.0,
        101.0,
        102.0,
        103.0,
        104.0,
        105.0,
        106.0,
        107.0,
        108.0,
        109.0,
        110.0,
        111.0,
        112.0,
        113.0,
        114.0,
        115.0,
        116.0,
        117.0,
        118.0,
        119.0,
        120.0,
        118.0,
        116.0,
        114.0,
        113.0,
        112.0,
        111.0,
        112.0,
        114.0,
        116.0,
    ]
    volume = [
        100.0,
        105.0,
        110.0,
        115.0,
        120.0,
        125.0,
        130.0,
        135.0,
        140.0,
        145.0,
        150.0,
        155.0,
        160.0,
        165.0,
        170.0,
        175.0,
        180.0,
        185.0,
        190.0,
        195.0,
        200.0,
        180.0,
        170.0,
        160.0,
        150.0,
        145.0,
        140.0,
        150.0,
        180.0,
        260.0,
    ]
    frame = pd.DataFrame(
        {
            "open": [value - 0.5 for value in close],
            "high": [value + 1.0 for value in close],
            "low": [value - 1.0 for value in close],
            "close": close,
            "adjusted_close": close,
            "volume": volume,
        },
        index=dates,
    )
    calculator = IndicatorCalculator(
        IndicatorConfig(
            ema_period=3,
            sma_short_period=5,
            sma_long_period=10,
            atr_period=3,
            adr_period=3,
            relvol_period=5,
            enable_3wt=False,
        )
    )

    result = calculator.calculate(frame)
    latest = result.iloc[-1]
    previous = result.iloc[-2]

    expected_rolling_high = frame["close"].iloc[-20:].max()
    expected_drawdown = ((expected_rolling_high - frame["close"].iloc[-1]) / expected_rolling_high) * 100.0
    expected_ema_slope = ((latest["ema21_close"] / result.iloc[-6]["ema21_close"]) - 1.0) * 100.0
    expected_sma_slope = ((latest["sma50"] / result.iloc[-11]["sma50"]) - 1.0) * 100.0
    expected_volume_ma5 = frame["volume"].iloc[-5:].mean()
    expected_volume_ma20 = frame["volume"].iloc[-20:].mean()
    expected_volume_ma5_to_ma20 = expected_volume_ma5 / expected_volume_ma20
    expected_volume_ratio_20d = frame["volume"].iloc[-1] / expected_volume_ma20
    expected_cross = bool(
        frame["close"].iloc[-1] > latest["ema21_close"] and frame["close"].iloc[-2] <= previous["ema21_close"]
    )
    expected_min_atr_21ema_zone_5d = result["atr_21ema_zone"].iloc[-5:].min()

    assert round(float(latest["rolling_20d_close_high"]), 6) == round(float(expected_rolling_high), 6)
    assert round(float(latest["drawdown_from_20d_high_pct"]), 6) == round(float(expected_drawdown), 6)
    assert round(float(latest["ema21_slope_5d_pct"]), 6) == round(float(expected_ema_slope), 6)
    assert round(float(latest["sma50_slope_10d_pct"]), 6) == round(float(expected_sma_slope), 6)
    assert round(float(latest["volume_ma5"]), 6) == round(float(expected_volume_ma5), 6)
    assert round(float(latest["volume_ma20"]), 6) == round(float(expected_volume_ma20), 6)
    assert round(float(latest["volume_ma5_to_ma20_ratio"]), 6) == round(float(expected_volume_ma5_to_ma20), 6)
    assert round(float(latest["volume_ratio_20d"]), 6) == round(float(expected_volume_ratio_20d), 6)
    assert bool(latest["close_crossed_above_ema21"]) is expected_cross
    assert round(float(latest["min_atr_21ema_zone_5d"]), 6) == round(float(expected_min_atr_21ema_zone_5d), 6)


def test_indicator_calculator_adds_resistance_breakout_quality_fields() -> None:
    dates = pd.date_range("2025-01-01", periods=10, freq="D")
    frame = pd.DataFrame(
        {
            "open": [9.8, 10.8, 11.8, 12.8, 13.8, 13.5, 13.6, 13.4, 13.9, 14.2],
            "high": [10.0, 11.0, 12.0, 13.0, 14.0, 13.8, 13.9, 13.7, 14.8, 15.5],
            "low": [9.5, 10.5, 11.5, 12.5, 13.5, 13.2, 13.3, 13.1, 13.5, 14.0],
            "close": [9.8, 10.8, 11.8, 12.8, 13.8, 13.6, 13.7, 13.5, 14.0, 15.2],
            "adjusted_close": [9.8, 10.8, 11.8, 12.8, 13.8, 13.6, 13.7, 13.5, 14.0, 15.2],
            "volume": [1_000_000] * 10,
        },
        index=dates,
    )
    calculator = IndicatorCalculator(
        IndicatorConfig(
            ema_period=2,
            sma_short_period=2,
            sma_long_period=3,
            atr_period=2,
            adr_period=2,
            relvol_period=2,
            enable_3wt=False,
            resistance_test_lookback=5,
            resistance_zone_width_atr=0.5,
            resistance_test_count_window=5,
        )
    )

    result = calculator.calculate(frame)
    latest = result.iloc[-1]

    assert round(float(latest["resistance_level_lookback"]), 6) == 14.8
    assert float(latest["resistance_test_count"]) >= 2.0
    assert round(float(latest["breakout_body_ratio"]), 6) == round((15.2 - 14.2) / (15.5 - 14.0), 6)


def test_indicator_calculator_adds_structure_pivot_fields_from_history() -> None:
    dates = pd.date_range("2025-01-01", periods=8, freq="D")
    frame = pd.DataFrame(
        {
            "open": [11.0, 10.5, 9.5, 10.5, 10.8, 11.0, 11.4, 11.8],
            "high": [11.5, 10.8, 10.0, 11.0, 11.2, 11.6, 12.0, 12.5],
            "low": [10.5, 9.0, 8.0, 9.2, 8.6, 9.4, 10.0, 10.8],
            "close": [10.8, 9.4, 8.8, 10.6, 9.4, 11.2, 11.8, 12.2],
            "adjusted_close": [10.8, 9.4, 8.8, 10.6, 9.4, 11.2, 11.8, 12.2],
            "volume": [1_000_000] * 8,
        },
        index=dates,
    )
    calculator = IndicatorCalculator(
        IndicatorConfig(
            ema_period=2,
            sma_short_period=2,
            sma_long_period=3,
            atr_period=2,
            adr_period=2,
            relvol_period=2,
            enable_3wt=False,
            structure_pivot_min_length=1,
            structure_pivot_max_length=1,
            structure_pivot_priority_mode="tightest",
        )
    )

    result = calculator.calculate(frame)
    latest = result.iloc[-1]

    assert bool(latest["structure_pivot_long_active"]) is True
    assert bool(latest["structure_pivot_long_breakout"]) is True
    assert bool(latest["structure_pivot_long_breakout_first_day"]) is False
    assert bool(latest["structure_pivot_long_breakout_gap_up"]) is False
    assert round(float(latest["structure_pivot_long_pivot_price"]), 6) == 11.0
    assert float(latest["structure_pivot_long_length"]) == 1.0
    assert round(float(latest["structure_pivot_long_ll_price"]), 6) == 8.0
    assert round(float(latest["structure_pivot_long_hl_price"]), 6) == 8.6
    assert round(float(latest["structure_pivot_hl_price"]), 6) == 8.6
    assert round(float(latest["structure_pivot_swing_high"]), 6) == 11.0
    assert round(float(latest["structure_pivot_1st_pivot"]), 6) == 10.0832
    assert round(float(latest["structure_pivot_2nd_pivot"]), 6) == 11.0
    assert bool(latest["structure_pivot_1st_break"]) is False
    assert bool(latest["structure_pivot_2nd_break"]) is False
    assert pd.isna(latest["ct_trendline_value"])
    assert bool(latest["ct_trendline_break"]) is False


def test_indicator_calculator_flags_first_day_structure_pivot_breakout() -> None:
    dates = pd.date_range("2025-01-01", periods=6, freq="D")
    frame = pd.DataFrame(
        {
            "open": [11.0, 10.5, 9.5, 10.5, 10.8, 11.0],
            "high": [11.5, 10.8, 10.0, 11.0, 11.2, 11.6],
            "low": [10.5, 9.0, 8.0, 9.2, 8.6, 9.4],
            "close": [10.8, 9.4, 8.8, 10.6, 9.4, 11.2],
            "adjusted_close": [10.8, 9.4, 8.8, 10.6, 9.4, 11.2],
            "volume": [1_000_000] * 6,
        },
        index=dates,
    )
    calculator = IndicatorCalculator(
        IndicatorConfig(
            ema_period=2,
            sma_short_period=2,
            sma_long_period=3,
            atr_period=2,
            adr_period=2,
            relvol_period=2,
            enable_3wt=False,
            structure_pivot_min_length=1,
            structure_pivot_max_length=1,
            structure_pivot_priority_mode="tightest",
        )
    )

    result = calculator.calculate(frame)
    latest = result.iloc[-1]

    assert bool(latest["structure_pivot_long_breakout"]) is True
    assert bool(latest["structure_pivot_long_breakout_first_day"]) is True
    assert bool(latest["structure_pivot_long_breakout_gap_up"]) is False


def test_indicator_calculator_computes_ct_break_only_when_long_structure_is_inactive() -> None:
    dates = pd.date_range("2025-03-01", periods=8, freq="D")
    frame = pd.DataFrame(
        {
            "open": [11.5, 10.8, 9.8, 10.8, 8.8, 9.6, 8.2, 8.9],
            "high": [12.0, 11.0, 10.0, 11.0, 9.0, 10.0, 8.0, 10.0],
            "low": [10.5, 9.0, 8.0, 9.0, 7.0, 8.0, 6.5, 7.5],
            "close": [11.0, 9.5, 8.7, 10.0, 7.8, 9.2, 9.2, 9.4],
            "adjusted_close": [11.0, 9.5, 8.7, 10.0, 7.8, 9.2, 9.2, 9.4],
            "volume": [1_000_000] * 8,
        },
        index=dates,
    )
    calculator = IndicatorCalculator(
        IndicatorConfig(
            ema_period=2,
            sma_short_period=2,
            sma_long_period=3,
            atr_period=2,
            adr_period=2,
            relvol_period=2,
            enable_3wt=False,
            structure_pivot_min_length=1,
            structure_pivot_max_length=1,
        )
    )

    result = calculator.calculate(frame)
    latest = result.iloc[-1]

    assert bool(latest["structure_pivot_long_active"]) is False
    assert round(float(latest["ct_trendline_value"]), 6) == 9.0
    assert bool(latest["ct_trendline_break"]) is True


def test_structure_pivot_priority_mode_accepts_legacy_aliases() -> None:
    calculator = IndicatorCalculator(IndicatorConfig(enable_3wt=False))

    assert calculator._normalize_structure_pivot_priority_mode("tightest") == "tightest"
    assert calculator._normalize_structure_pivot_priority_mode("Tightest Structure") == "tightest"
    assert calculator._normalize_structure_pivot_priority_mode("longest") == "longest"
    assert calculator._normalize_structure_pivot_priority_mode("Longest Length") == "longest"
    assert calculator._normalize_structure_pivot_priority_mode("shortest") == "shortest"
    assert calculator._normalize_structure_pivot_priority_mode("Shortest Length") == "shortest"


def test_indicator_calculator_adds_sma50_reclaim_support_fields() -> None:
    dates = pd.date_range("2025-01-01", periods=8, freq="D")
    close = [10.0, 10.0, 10.0, 9.0, 9.0, 9.0, 9.0, 11.0]
    frame = pd.DataFrame(
        {
            "open": [value - 0.2 for value in close],
            "high": [value + 0.5 for value in close],
            "low": [value - 0.5 for value in close],
            "close": close,
            "adjusted_close": close,
            "volume": [1_000_000] * len(close),
        },
        index=dates,
    )
    calculator = IndicatorCalculator(
        IndicatorConfig(
            ema_period=2,
            sma_short_period=3,
            sma_long_period=5,
            atr_period=2,
            adr_period=2,
            relvol_period=2,
            enable_3wt=False,
        )
    )

    result = calculator.calculate(frame)

    assert bool(result.iloc[-1]["close_crossed_above_sma50"]) is True
    assert bool(result.iloc[-2]["close_crossed_above_sma50"]) is False
    assert round(float(result.iloc[-1]["min_atr_50sma_zone_5d"]), 6) == round(float(result["atr_50sma_zone"].iloc[-5:].min()), 6)


def test_indicator_calculator_keeps_sma50_reclaim_support_fields_nan_before_sma50_warmup() -> None:
    dates = pd.date_range("2025-01-01", periods=30, freq="D")
    close = [100.0 + i for i in range(30)]
    frame = pd.DataFrame(
        {
            "open": close,
            "high": [value + 1.0 for value in close],
            "low": [value - 1.0 for value in close],
            "close": close,
            "adjusted_close": close,
            "volume": [1_000_000] * len(close),
        },
        index=dates,
    )
    calculator = IndicatorCalculator(IndicatorConfig(enable_3wt=False))

    result = calculator.calculate(frame)

    assert bool(result["close_crossed_above_sma50"].any()) is False
    assert bool(result["min_atr_50sma_zone_5d"].isna().all()) is True


def test_indicator_calculator_adds_power_gap_context_fields_with_threshold_control() -> None:
    dates = pd.date_range("2025-01-01", periods=6, freq="D")
    close = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    frame = pd.DataFrame(
        {
            "open": [100.0, 112.0, 102.0, 103.0, 120.0, 106.0],
            "high": [value + 1.0 for value in close],
            "low": [value - 1.0 for value in close],
            "close": close,
            "adjusted_close": close,
            "volume": [1_000_000] * len(close),
        },
        index=dates,
    )
    calculator = IndicatorCalculator(
        IndicatorConfig(
            ema_period=2,
            sma_short_period=2,
            sma_long_period=2,
            atr_period=2,
            adr_period=2,
            relvol_period=2,
            enable_3wt=False,
            power_gap_threshold=10.0,
        )
    )

    result = calculator.calculate(frame)

    assert pd.isna(result.iloc[0]["days_since_power_gap"])
    assert round(float(result.iloc[1]["days_since_power_gap"]), 6) == 0.0
    assert round(float(result.iloc[2]["days_since_power_gap"]), 6) == 1.0
    assert round(float(result.iloc[4]["days_since_power_gap"]), 6) == 0.0
    assert round(float(result.iloc[5]["days_since_power_gap"]), 6) == 1.0
    assert round(float(result.iloc[2]["power_gap_up_pct"]), 6) == round(float(result.iloc[1]["power_gap_up_pct"]), 6)
    assert round(float(result.iloc[5]["power_gap_up_pct"]), 6) == round(float(result.iloc[4]["power_gap_up_pct"]), 6)

    stricter = IndicatorCalculator(
        IndicatorConfig(
            ema_period=2,
            sma_short_period=2,
            sma_long_period=2,
            atr_period=2,
            adr_period=2,
            relvol_period=2,
            enable_3wt=False,
            power_gap_threshold=15.0,
        )
    ).calculate(frame)
    assert pd.isna(stricter.iloc[1]["days_since_power_gap"])
    assert round(float(stricter.iloc[4]["days_since_power_gap"]), 6) == 0.0
