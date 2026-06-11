from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.dashboard.market import MarketConditionConfig, MarketConditionScorer
from src.indicators.core import IndicatorCalculator, IndicatorConfig


def _make_history(
    values: list[float],
    dates: pd.DatetimeIndex,
    volume_scale: float = 1_000_000,
    volumes: list[float] | None = None,
) -> pd.DataFrame:
    close = pd.Series(values, index=dates, dtype=float)
    volume_values = volumes if volumes is not None else np.linspace(volume_scale, volume_scale * 1.5, len(close))
    return pd.DataFrame(
        {
            "open": close * 0.995,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "adjusted_close": close,
            "volume": volume_values,
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
        "^VIX9D": _make_history([17.0 - (i * 0.012) for i in range(320)], dates, volume_scale=100_000),
        "^VIX3M": _make_history([20.0 - (i * 0.005) for i in range(320)], dates, volume_scale=100_000),
        "FFF": _make_history([70.0 + (i * 0.18) for i in range(320)], dates),
        "IWO": _make_history([95.0 + (i * 0.24) for i in range(320)], dates),
        "IWN": _make_history([92.0 + (i * 0.08) for i in range(320)], dates),
        "HYG": _make_history([74.0 + (i * 0.04) for i in range(320)], dates),
        "LQD": _make_history([108.0 + (i * 0.01) for i in range(320)], dates),
        "IEF": _make_history([96.0 - (i * 0.005) for i in range(320)], dates),
        "BAMLH0A0HYM2": _make_history([4.2 - (i * 0.002) for i in range(320)], dates, volume_scale=0),
        "SPY": _make_history([100.0 + (i * 0.12) for i in range(320)], dates),
        "QQQ": _make_history([110.0 + (i * 0.14) for i in range(320)], dates),
        "RSP": _make_history([98.0 + (i * 0.10) for i in range(320)], dates),
        "XLK": _make_history([100.0 + (i * 0.22) for i in range(320)], dates),
        "XLP": _make_history([100.0 + (i * 0.04) for i in range(320)], dates),
    }
    market_histories = {ticker: calculator.calculate(history) for ticker, history in market_raw.items()}
    benchmark_history = calculator.calculate(benchmark_raw)
    stock_histories = {
        "NVDA": calculator.calculate(_make_history([50.0 + (i * 0.30) for i in range(320)], dates)),
        "META": calculator.calculate(_make_history([60.0 + (i * 0.22) for i in range(320)], dates)),
        "LAG": calculator.calculate(_make_history([120.0 - (i * 0.12) for i in range(320)], dates)),
    }

    config = MarketConditionConfig.from_dict(
        {
            "market_condition_etf_universe": [
                {"ticker": "XLK", "name": "Technology"},
                {"ticker": "XLP", "name": "Consumer Staples"},
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
                {"ticker": "XLK", "name": "Technology"},
                {"ticker": "XLP", "name": "Consumer Staples"},
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
    assert result.breadth_momentum_summary["A20"] == pytest.approx(result.breadth_summary["pct_above_sma20"])
    assert "A20 DELTA 10D" in result.breadth_momentum_summary
    assert result.breadth_momentum_summary["A20 MOMENTUM FLAG"] in {-1.0, 0.0, 1.0}
    assert result.breadth_internal_summary["UNIVERSE COUNT"] == pytest.approx(3.0)
    assert result.breadth_internal_summary["ADVANCERS"] == pytest.approx(2.0)
    assert result.breadth_internal_summary["DECLINERS"] == pytest.approx(1.0)
    assert result.breadth_internal_summary["ADVANCE DECLINE NET"] == pytest.approx(1.0)
    assert result.breadth_internal_summary["NEW HIGH 52W COUNT"] == pytest.approx(2.0)
    assert result.breadth_internal_summary["NEW LOW 52W COUNT"] == pytest.approx(1.0)
    assert result.breadth_internal_summary["NET NEW HIGH LOW"] == pytest.approx(1.0)
    assert result.breadth_internal_summary["STAGE2 %"] >= 0.0
    assert "MCCLELLAN OSCILLATOR" in result.breadth_internal_summary
    assert "ZWEIG BREADTH THRUST" in result.breadth_internal_summary
    assert "1W" in result.metric_deltas["breadth_internal:AD LINE"]
    assert "pct_positive_1m" in result.participation_summary
    assert "1D" in result.metric_deltas["pct_above_sma20"]
    assert "1W" in result.metric_deltas["VIX"]
    assert "1W" in result.metric_deltas["VIX 252D PCTL"]
    assert "1M" in result.metric_deltas["risk_on:REL 1M %"]
    assert "% 1M" in result.performance_overview
    assert "S2W HIGH %" in result.high_vix_summary
    assert "SAFE HAVEN %" in result.high_vix_summary
    assert "VIX 252D PCTL" in result.high_vix_summary
    assert "VIX PEAK DAYS" in result.high_vix_summary
    assert "VIX PEAK RATIO %" in result.high_vix_summary
    assert result.risk_on_ratio_summary["REL 1M %"] > 0.0
    assert result.risk_on_ratio_summary["ABOVE MA COUNT"] == pytest.approx(3.0)
    assert result.risk_on_ratio_summary["MA COUNT"] == pytest.approx(3.0)
    assert result.volatility_term_structure["RATIO"] < 1.0
    assert result.volatility_term_structure["INVERSION FLAG"] == pytest.approx(0.0)
    assert result.volatility_term_structure["VIX9D/VIX RATIO"] < 1.0
    assert result.volatility_term_structure["FRONT INVERSION FLAG"] == pytest.approx(0.0)
    assert result.volatility_term_structure["FULL BACKWARDATION FLAG"] == pytest.approx(0.0)
    assert result.credit_risk_proxy["HYG/LQD REL 1M %"] > 0.0
    assert result.credit_risk_proxy["HYG/IEF REL 1M %"] > 0.0
    assert result.credit_risk_proxy["HY OAS"] < 4.2
    assert result.credit_risk_proxy["HY OAS DELTA 5D BPS"] < 0.0
    assert result.credit_risk_proxy["CREDIT RISK-OFF FLAG"] == pytest.approx(0.0)
    assert "SPY RALLY ATTEMPT DAY" in result.index_state_summary
    assert "QQQ DISTRIBUTION DAY COUNT" in result.index_state_summary
    assert result.drawdown_summary["SPY DD 252D %"] == pytest.approx(0.0)
    assert result.drawdown_summary["SPY T_DD"] == pytest.approx(0.0)
    assert not result.market_snapshot.empty
    assert list(result.market_snapshot["TICKER"]) == ["XLK", "XLP"]
    assert result.leadership_snapshot.empty
    assert "LDR" not in MarketConditionScorer(config).required_symbols()
    assert not result.sector_relative_strength.empty
    assert {"REL 1W %", "REL 1M %", "REL 3M %", "RANK 1M", "RANK DELTA 1W", "RANK DELTA 1M"}.issubset(result.sector_relative_strength.columns)
    assert not result.external_snapshot.empty
    assert list(result.external_snapshot["TICKER"]) == ["EXT"]
    assert list(result.market_snapshot.columns) == ["TICKER", "NAME", "PRICE", "DAY %", "VOL vs 50D %", "21EMA POS"]
    assert not result.factors_vs_sp500.empty
    assert list(result.factors_vs_sp500.columns) == ["TICKER", "NAME", "REL 1W %", "REL 1M %", "REL 1Y %"]
    assert {"RSP/SPY", "QQQ/SPY"}.issubset(set(result.style_pair_summary["PAIR"]))
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


def test_market_dashboard_required_symbols_include_risk_on_ratio_pair() -> None:
    config = MarketConditionConfig.from_dict({})
    required_symbols = MarketConditionScorer(config).required_symbols()

    assert "IWO" in required_symbols
    assert "IWN" in required_symbols
    assert "RSP" in required_symbols
    assert "^VIX9D" in required_symbols
    assert "^VIX3M" in required_symbols
    assert "HYG" in required_symbols
    assert "LQD" in required_symbols
    assert "IEF" in required_symbols
    assert "SPY" in required_symbols
    assert "QQQ" in required_symbols
    assert MarketConditionScorer(config).required_fred_series() == ["BAMLH0A0HYM2"]


def test_market_dashboard_index_state_detects_ftd_and_distribution_days() -> None:
    dates = pd.date_range("2026-01-01", periods=30, freq="B")
    calculator = IndicatorCalculator(IndicatorConfig())
    close_values = [
        100.0,
        98.0,
        96.0,
        94.0,
        90.0,
        90.5,
        91.0,
        92.0,
        94.0,
        94.5,
        95.0,
        95.5,
        96.0,
        96.5,
        97.0,
        97.5,
        98.0,
        98.5,
        99.0,
        98.6,
        99.2,
        98.8,
        99.4,
        99.0,
        99.6,
        99.2,
        99.8,
        99.4,
        100.0,
        100.2,
    ]
    volumes = [
        100,
        95,
        90,
        85,
        80,
        82,
        84,
        86,
        120,
        100,
        101,
        102,
        103,
        104,
        105,
        106,
        107,
        108,
        109,
        130,
        110,
        132,
        112,
        134,
        114,
        136,
        116,
        138,
        118,
        119,
    ]
    index_history = calculator.calculate(_make_history(close_values, dates, volumes=volumes))
    config = MarketConditionConfig.from_dict(
        {
            "market_condition_etf_universe": [{"ticker": "SPY", "name": "S&P 500"}],
                "index_state": {"symbols": ["SPY"], "rally_low_lookback": 30, "distribution_pressure_count": 5},
        }
    )

    active_up = calculator.calculate(_make_history([50.0 + (i * 0.20) for i in range(30)], dates))
    active_down = calculator.calculate(_make_history([80.0 - (i * 0.05) for i in range(30)], dates))
    result = MarketConditionScorer(config).score(
        {"AAA": index_history, "UP": active_up, "DOWN": active_down},
        {
            "SPY": index_history,
            "^VIX": calculator.calculate(_make_history([15.0 for _ in range(30)], dates, volume_scale=100_000)),
        },
        index_history,
    )

    assert result.index_state_summary["SPY RALLY ATTEMPT DAY"] == pytest.approx(25.0)
    assert result.index_state_summary["SPY FTD FLAG"] == pytest.approx(1.0)
    assert result.index_state_summary["SPY FTD AGE DAYS"] == pytest.approx(21.0)
    assert result.index_state_summary["SPY FTD GAIN %"] == pytest.approx(round((94.0 / 92.0 - 1.0) * 100.0, 3))
    assert result.index_state_summary["SPY FTD VOLUME RATIO"] == pytest.approx(round(120.0 / 86.0, 3))
    assert result.index_state_summary["SPY FTD ADVANCE RATIO"] == pytest.approx(round(2.0 / 3.0, 3))
    assert 0.0 <= result.index_state_summary["SPY FTD QUALITY SCORE"] <= 100.0
    assert result.index_state_summary["SPY DISTRIBUTION DAY COUNT"] == pytest.approx(5.0)
    assert result.index_state_summary["SPY UNDER PRESSURE FLAG"] == pytest.approx(1.0)


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
