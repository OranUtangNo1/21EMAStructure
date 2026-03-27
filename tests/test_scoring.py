from __future__ import annotations

import pandas as pd

from src.scoring.fundamental import FundamentalScoreConfig, FundamentalScorer
from src.scoring.hybrid import HybridScoreCalculator, HybridScoreConfig
from src.scoring.rs import RSConfig, RSScorer


def test_hybrid_score_renormalizes_missing_weights() -> None:
    snapshot = pd.DataFrame(
        {
            "rs21": [90.0],
            "rs63": [80.0],
            "rs126": [70.0],
            "fundamental_score": [None],
            "industry_score": [60.0],
        },
        index=["AAA"],
    )
    calculator = HybridScoreCalculator(HybridScoreConfig(hybrid_missing_value_policy="renormalize_weights"))
    result = calculator.score(snapshot)
    assert round(result.loc["AAA", "hybrid_score"], 2) == 71.25


def test_hybrid_score_default_fills_missing_with_neutral_50() -> None:
    snapshot = pd.DataFrame(
        {
            "rs21": [90.0],
            "rs63": [80.0],
            "rs126": [70.0],
            "fundamental_score": [None],
            "industry_score": [60.0],
        },
        index=["AAA"],
    )
    calculator = HybridScoreCalculator(HybridScoreConfig())
    result = calculator.score(snapshot)
    assert round(result.loc["AAA", "hybrid_score"], 2) == 67.0


def test_fundamental_score_fill_neutral_returns_value() -> None:
    snapshot = pd.DataFrame(
        {
            "eps_growth": [60.0, None, 10.0],
            "revenue_growth": [40.0, 25.0, 5.0],
        },
        index=["AAA", "BBB", "CCC"],
    )
    scorer = FundamentalScorer(FundamentalScoreConfig(missing_fundamental_policy="fill_neutral"))
    result = scorer.score(snapshot)
    assert result["fundamental_score"].between(0, 100).all()
    assert result.loc["AAA", "fundamental_score"] > result.loc["CCC", "fundamental_score"]


def test_rs_scorer_uses_symbol_own_ratio_history_percentile() -> None:
    dates = pd.date_range("2025-01-01", periods=30, freq="D")
    benchmark_history = pd.DataFrame({"close": [100.0] * 30}, index=dates)
    histories = {
        "AAA": pd.DataFrame({"close": list(range(1, 31))}, index=dates),
        "BBB": pd.DataFrame({"close": list(range(30, 0, -1))}, index=dates),
    }
    snapshot = pd.DataFrame(index=["AAA", "BBB"])

    scorer = RSScorer(RSConfig(rs_lookbacks=(5, 21)))
    result = scorer.score(snapshot, histories, benchmark_history)

    assert result.loc["AAA", "rs5"] == 100.0
    assert result.loc["AAA", "rs21"] == 100.0
    assert result.loc["BBB", "rs5"] == 20.0
    assert abs(result.loc["BBB", "rs21"] - ((1.0 / 21.0) * 100.0)) < 1e-12
    assert result.loc["AAA", "raw_rs5"] == result.loc["AAA", "rs5"]
    assert result.loc["BBB", "raw_rs21"] == result.loc["BBB", "rs21"]
