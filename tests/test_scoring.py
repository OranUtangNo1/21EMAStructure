from __future__ import annotations

import pandas as pd

from src.scoring.fundamental import FundamentalScoreConfig, FundamentalScorer
from src.scoring.hybrid import HybridScoreCalculator, HybridScoreConfig
from src.scoring.rs import RSConfig, RSScorer
from src.scoring.vcs import VCSCalculator, VCSConfig


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



def test_rs_scorer_uses_less_or_equal_count_for_tied_windows() -> None:
    dates = pd.date_range("2025-02-01", periods=5, freq="D")
    benchmark_history = pd.DataFrame({"close": [100.0] * 5}, index=dates)
    histories = {
        "AAA": pd.DataFrame({"close": [1.0, 1.0, 1.0, 1.0, 1.0]}, index=dates),
        "BBB": pd.DataFrame({"close": [2.0, 1.0, 1.0, 1.0, 1.0]}, index=dates),
    }
    snapshot = pd.DataFrame(index=["AAA", "BBB"])

    scorer = RSScorer(RSConfig(rs_lookbacks=(5,)))
    result = scorer.score(snapshot, histories, benchmark_history)

    assert result.loc["AAA", "rs5"] == 100.0
    assert result.loc["BBB", "rs5"] == 80.0


def test_rs_scorer_outputs_rs_ratio_and_52w_high_flags() -> None:
    dates = pd.date_range("2025-01-01", periods=200, freq="D")
    benchmark_history = pd.DataFrame({"close": [100.0] * len(dates)}, index=dates)
    aaa_close = [100.0 + (i * 0.5) for i in range(len(dates))]
    bbb_close = [120.0 - (i * 0.3) for i in range(len(dates))]
    histories = {
        "AAA": pd.DataFrame({"close": aaa_close}, index=dates),
        "BBB": pd.DataFrame({"close": bbb_close}, index=dates),
    }
    snapshot = pd.DataFrame(index=["AAA", "BBB"])

    scorer = RSScorer(RSConfig(rs_lookbacks=(21,)))
    result = scorer.score(snapshot, histories, benchmark_history)

    assert round(float(result.loc["AAA", "rs_ratio"]), 6) == round(aaa_close[-1] / 100.0, 6)
    assert round(float(result.loc["AAA", "rs_ratio_52w_high"]), 6) == round(max([value / 100.0 for value in aaa_close]), 6)
    assert bool(result.loc["AAA", "rs_ratio_at_52w_high"]) is True
    assert bool(result.loc["BBB", "rs_ratio_at_52w_high"]) is False


def test_rs_scorer_respects_rs_new_high_tolerance_and_min_history() -> None:
    long_dates = pd.date_range("2025-01-01", periods=200, freq="D")
    benchmark_history = pd.DataFrame({"close": [100.0] * len(long_dates)}, index=long_dates)
    close_long = [100.0 + (i * 0.4) for i in range(len(long_dates) - 1)] + [100.0 + ((len(long_dates) - 2) * 0.4) * 0.995]
    histories = {"AAA": pd.DataFrame({"close": close_long}, index=long_dates)}
    snapshot = pd.DataFrame(index=["AAA"])

    loose = RSScorer(RSConfig(rs_lookbacks=(21,), rs_new_high_tolerance=1.0)).score(snapshot, histories, benchmark_history)
    strict = RSScorer(RSConfig(rs_lookbacks=(21,), rs_new_high_tolerance=0.1)).score(snapshot, histories, benchmark_history)
    assert bool(loose.loc["AAA", "rs_ratio_at_52w_high"]) is True
    assert bool(strict.loc["AAA", "rs_ratio_at_52w_high"]) is False

    short_dates = pd.date_range("2025-01-01", periods=120, freq="D")
    short_history = {"AAA": pd.DataFrame({"close": [100.0 + i for i in range(len(short_dates))]}, index=short_dates)}
    short_benchmark = pd.DataFrame({"close": [100.0] * len(short_dates)}, index=short_dates)
    short_result = RSScorer(RSConfig(rs_lookbacks=(21,))).score(pd.DataFrame(index=["AAA"]), short_history, short_benchmark)
    assert bool(short_result.loc["AAA", "rs_ratio_at_52w_high"]) is False



def test_vcs_penalizes_broken_higher_low_against_shifted_structure_base() -> None:
    dates = pd.date_range("2025-01-01", periods=80, freq="D")
    base = pd.Series([100.0 + (i * 0.1) for i in range(80)], index=dates, dtype=float)
    low = base - 1.5
    high = base + 1.5
    close = base
    volume = pd.Series([1_200_000] * 80, index=dates, dtype=float)

    healthy_history = pd.DataFrame({"high": high, "low": low, "close": close, "volume": volume}, index=dates)
    broken_low = low.copy()
    broken_low.iloc[-5:] = broken_low.iloc[-5:] - 6.0
    broken_history = pd.DataFrame({"high": high, "low": broken_low, "close": close, "volume": volume}, index=dates)

    calculator = VCSCalculator(
        VCSConfig(
            len_short=10,
            len_long=20,
            len_volume=20,
            hl_lookback=20,
            penalty_factor=0.75,
            bonus_max=15.0,
        )
    )
    healthy_score = float(calculator.calculate_series(healthy_history).iloc[-1])
    broken_score = float(calculator.calculate_series(broken_history).iloc[-1])

    assert 0.0 <= healthy_score <= 100.0
    assert 0.0 <= broken_score <= 100.0
    assert healthy_score > broken_score
