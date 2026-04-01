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
