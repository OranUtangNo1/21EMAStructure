from __future__ import annotations

import numpy as np
import pandas as pd

from src.dashboard.radar import RadarConfig, RadarViewModelBuilder
from src.indicators.core import IndicatorCalculator, IndicatorConfig


def _make_history(values: list[float], dates: pd.DatetimeIndex) -> pd.DataFrame:
    close = pd.Series(values, index=dates, dtype=float)
    return pd.DataFrame(
        {
            "open": close * 0.995,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "adjusted_close": close,
            "volume": np.linspace(1_000_000, 2_000_000, len(close)),
        },
        index=dates,
    )


def test_radar_builder_builds_etf_based_tables() -> None:
    dates = pd.date_range("2025-01-01", periods=260, freq="B")
    benchmark_history = _make_history([100.0 + (i * 0.02) for i in range(260)], dates)
    raw_histories = {
        "XLK": _make_history([100.0 + (i * 0.18) for i in range(260)], dates),
        "SMH": _make_history([90.0 + (i * 0.25) for i in range(260)], dates),
    }

    calculator = IndicatorCalculator(IndicatorConfig())
    etf_histories = {ticker: calculator.calculate(history) for ticker, history in raw_histories.items()}
    config = RadarConfig.from_dict(
        {
            "sector_etfs": [{"ticker": "XLK", "name": "Technology"}],
            "industry_etfs": [{"ticker": "SMH", "name": "Semiconductors", "major_stocks": ["NVDA", "AVGO", "AMD"]}],
            "top_movers_count": 3,
        }
    )

    result = RadarViewModelBuilder(config).build(etf_histories, benchmark_history)

    assert not result.sector_leaders.empty
    assert not result.industry_leaders.empty
    assert not result.top_daily.empty
    assert not result.top_weekly.empty
    assert list(result.sector_leaders.columns) == ["RS", "1D", "1W", "1M", "TICKER", "NAME", "DAY %", "WK %", "MTH %", "RS DAY%", "RS WK%", "RS MTH%", "52W HIGH"]
    assert "MAJOR STOCKS" in result.industry_leaders.columns
    assert result.industry_leaders.iloc[0]["MAJOR STOCKS"] == "NVDA, AVGO, AMD"
