from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.dashboard.market import MarketConditionConfig, MarketConditionScorer
from src.indicators.core import IndicatorCalculator, IndicatorConfig


def _make_history(values: list[float], dates: pd.DatetimeIndex, volume_scale: float = 1_000_000) -> pd.DataFrame:
    close = pd.Series(values, index=dates, dtype=float)
    return pd.DataFrame(
        {
            "open": close * 0.995,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "adjusted_close": close,
            "volume": np.linspace(volume_scale, volume_scale * 1.5, len(close)),
        },
        index=dates,
    )


def test_market_dashboard_result_contains_expanded_sections() -> None:
    dates = pd.date_range("2024-01-01", periods=320, freq="B")
    calculator = IndicatorCalculator(IndicatorConfig())

    benchmark_raw = _make_history([100.0 + (i * 0.12) for i in range(320)], dates)
    market_raw = {
        "AAA": _make_history([90.0 + (i * 0.20) for i in range(320)], dates),
        "BBB": _make_history([80.0 + (i * 0.16) for i in range(320)], dates),
        "LDR": _make_history([120.0 - (i * 0.08) for i in range(320)], dates),
        "EXT": _make_history([60.0 - (i * 0.05) for i in range(320)], dates),
        "^VIX": _make_history([18.0 - (i * 0.01) for i in range(320)], dates, volume_scale=100_000),
        "FFF": _make_history([70.0 + (i * 0.18) for i in range(320)], dates),
    }
    market_histories = {ticker: calculator.calculate(history) for ticker, history in market_raw.items()}
    benchmark_history = calculator.calculate(benchmark_raw)
    stock_histories = {
        "NVDA": calculator.calculate(_make_history([50.0 + (i * 0.30) for i in range(320)], dates)),
        "META": calculator.calculate(_make_history([60.0 + (i * 0.22) for i in range(320)], dates)),
    }

    config = MarketConditionConfig.from_dict(
        {
            "market_condition_etf_universe": [
                {"ticker": "AAA", "name": "Alpha"},
                {"ticker": "BBB", "name": "Beta"},
            ],
            "leadership_etfs": [
                {"ticker": "LDR", "name": "Leadership"},
            ],
            "external_etfs": [
                {"ticker": "EXT", "name": "External"},
            ],
            "factor_etfs": [
                {"ticker": "FFF", "name": "Factor"},
            ],
        }
    )
    core_only_config = MarketConditionConfig.from_dict(
        {
            "market_condition_etf_universe": [
                {"ticker": "AAA", "name": "Alpha"},
                {"ticker": "BBB", "name": "Beta"},
            ],
            "factor_etfs": [
                {"ticker": "FFF", "name": "Factor"},
            ],
        }
    )

    result = MarketConditionScorer(config).score(stock_histories, market_histories, benchmark_history)
    core_only_result = MarketConditionScorer(core_only_config).score(stock_histories, market_histories, benchmark_history)

    assert result.score > 0
    assert result.score == core_only_result.score
    assert result.score_1w_ago is not None
    assert result.label_1d_ago is not None
    assert result.label_1w_ago is not None
    assert "pct_above_sma10" in result.component_scores
    assert "safe_haven_score" in result.component_scores
    assert "pct_above_sma200" in result.breadth_summary
    assert "% 1M" in result.performance_overview
    assert "S2W HIGH %" in result.high_vix_summary
    assert "SAFE HAVEN %" in result.high_vix_summary
    assert not result.market_snapshot.empty
    assert list(result.market_snapshot["TICKER"]) == ["AAA", "BBB"]
    assert not result.leadership_snapshot.empty
    assert list(result.leadership_snapshot["TICKER"]) == ["LDR"]
    assert not result.external_snapshot.empty
    assert list(result.external_snapshot["TICKER"]) == ["EXT"]
    assert list(result.market_snapshot.columns) == ["TICKER", "NAME", "PRICE", "DAY %", "VOL vs 50D %", "21EMA POS"]
    assert not result.factors_vs_sp500.empty
    assert list(result.factors_vs_sp500.columns) == ["TICKER", "NAME", "REL 1W %", "REL 1M %", "REL 1Y %"]
    assert not result.s5th_series.empty
    assert list(result.s5th_series.columns) == ["date", "pct_above_sma200"]



def test_market_dashboard_supports_etf_active_and_blended_modes() -> None:
    dates = pd.date_range("2024-01-01", periods=320, freq="B")
    calculator = IndicatorCalculator(IndicatorConfig())

    benchmark_history = calculator.calculate(_make_history([100.0 + (i * 0.10) for i in range(320)], dates))
    market_histories = {
        "AAA": calculator.calculate(_make_history([220.0 - (i * 0.35) for i in range(320)], dates)),
        "BBB": calculator.calculate(_make_history([180.0 - (i * 0.28) for i in range(320)], dates)),
        "^VIX": calculator.calculate(_make_history([15.0 for _ in range(320)], dates, volume_scale=100_000)),
        "SPY": calculator.calculate(_make_history([100.0 + (i * 0.10) for i in range(320)], dates)),
        "TLT": calculator.calculate(_make_history([120.0 - (i * 0.05) for i in range(320)], dates)),
    }
    stock_histories = {
        "UP1": calculator.calculate(_make_history([40.0 + (i * 0.22) for i in range(320)], dates)),
        "UP2": calculator.calculate(_make_history([55.0 + (i * 0.18) for i in range(320)], dates)),
    }

    common_config = {
        "market_condition_etf_universe": [
            {"ticker": "AAA", "name": "Alpha"},
            {"ticker": "BBB", "name": "Beta"},
        ],
    }
    etf_result = MarketConditionScorer(
        MarketConditionConfig.from_dict({**common_config, "calculation_mode": "etf"})
    ).score(stock_histories, market_histories, benchmark_history)
    active_result = MarketConditionScorer(
        MarketConditionConfig.from_dict({**common_config, "calculation_mode": "active_symbols"})
    ).score(stock_histories, market_histories, benchmark_history)
    blended_result = MarketConditionScorer(
        MarketConditionConfig.from_dict(
            {
                **common_config,
                "calculation_mode": "blended",
                "etf_weight": 0.25,
                "active_symbols_weight": 0.75,
            }
        )
    ).score(stock_histories, market_histories, benchmark_history)

    assert etf_result.breadth_summary["pct_above_sma200"] == pytest.approx(0.0)
    assert active_result.breadth_summary["pct_above_sma200"] == pytest.approx(100.0)
    assert blended_result.breadth_summary["pct_above_sma200"] == pytest.approx(75.0)
    assert etf_result.breadth_summary["pct_above_sma10"] == pytest.approx(0.0)
    assert active_result.breadth_summary["pct_above_sma10"] == pytest.approx(100.0)
    assert blended_result.breadth_summary["pct_above_sma10"] == pytest.approx(75.0)
    assert etf_result.score < blended_result.score < active_result.score
    assert blended_result.component_scores["pct_positive_ytd"] > 50.0
    assert blended_result.component_scores["safe_haven_score"] > 50.0


def test_market_dashboard_vix_scoring_is_centered_around_neutral_level() -> None:
    dates = pd.date_range("2024-01-01", periods=320, freq="B")
    calculator = IndicatorCalculator(IndicatorConfig())
    benchmark_history = calculator.calculate(_make_history([100.0 + (i * 0.10) for i in range(320)], dates))
    stock_histories = {
        "UP1": calculator.calculate(_make_history([40.0 + (i * 0.22) for i in range(320)], dates)),
    }
    common_market = {
        "AAA": calculator.calculate(_make_history([120.0 + (i * 0.20) for i in range(320)], dates)),
        "SPY": calculator.calculate(_make_history([100.0 + (i * 0.10) for i in range(320)], dates)),
        "TLT": calculator.calculate(_make_history([120.0 - (i * 0.05) for i in range(320)], dates)),
    }
    config = MarketConditionConfig.from_dict(
        {
            "market_condition_etf_universe": [
                {"ticker": "AAA", "name": "Alpha"},
            ],
        }
    )

    low_vix_result = MarketConditionScorer(config).score(
        stock_histories,
        {**common_market, "^VIX": calculator.calculate(_make_history([12.0 for _ in range(320)], dates, volume_scale=100_000))},
        benchmark_history,
    )
    neutral_vix_result = MarketConditionScorer(config).score(
        stock_histories,
        {**common_market, "^VIX": calculator.calculate(_make_history([17.0 for _ in range(320)], dates, volume_scale=100_000))},
        benchmark_history,
    )
    elevated_vix_result = MarketConditionScorer(config).score(
        stock_histories,
        {**common_market, "^VIX": calculator.calculate(_make_history([25.0 for _ in range(320)], dates, volume_scale=100_000))},
        benchmark_history,
    )

    assert low_vix_result.component_scores["vix_score"] == pytest.approx(75.0)
    assert neutral_vix_result.component_scores["vix_score"] == pytest.approx(50.0)
    assert elevated_vix_result.component_scores["vix_score"] == pytest.approx(10.0)
