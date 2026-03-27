from __future__ import annotations

import pandas as pd

from src.entry.evaluator import EntryCriteriaConfig, EntryEvaluator
from src.risk.exits import ExitRuleEvaluator, RiskModelConfig
from src.risk.position_sizing import PositionSizingCalculator, PositionSizingConfig
from src.structure.pivot import StructurePivotConfig, StructurePivotDetector


def _build_history() -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-01", periods=8)
    return pd.DataFrame(
        {
            "open": [11.0, 10.5, 9.5, 10.5, 10.8, 11.0, 11.4, 11.8],
            "high": [11.5, 10.8, 10.0, 11.0, 11.2, 11.6, 12.0, 12.5],
            "low": [10.5, 9.0, 8.0, 9.2, 8.6, 9.4, 10.0, 10.8],
            "close": [10.8, 9.4, 8.8, 10.6, 9.4, 11.2, 11.8, 12.2],
            "volume": [1000000] * 8,
            "ema21_low": [10.1, 9.5, 8.6, 8.9, 9.2, 9.8, 10.4, 11.0],
            "atr_pct_from_50sma": [1.0, 1.2, 1.5, 2.0, 2.1, 4.0, 6.5, 7.2],
        },
        index=dates,
    )


def test_structure_pivot_detects_ll_hl_breakout() -> None:
    history = _build_history()
    detector = StructurePivotDetector(StructurePivotConfig(lengths=(8,), min_separation_bars=1))
    result = detector.detect(history, "TEST")
    assert result.is_valid is True
    assert result.breakout_active is True
    assert round(float(result.pivot_price), 2) == 11.20


def test_entry_evaluator_passes_strong_candidate() -> None:
    history = _build_history()
    detector = StructurePivotDetector(StructurePivotConfig(lengths=(8,), min_separation_bars=1))
    pivot_result = detector.detect(history, "TEST")
    evaluator = EntryEvaluator(EntryCriteriaConfig())
    row = pd.Series(
        {
            "ema21_low_pct": 4.5,
            "close": 12.2,
            "ema21_low": 11.0,
            "atr_21ema_zone": 0.5,
            "atr_10wma_zone": 0.4,
            "atr_50sma_zone": 1.2,
            "sma50": 10.5,
            "rs21": 92.0,
            "rs63": 90.0,
            "rs126": 88.0,
            "fundamental_score": 78.0,
            "industry_score": 70.0,
            "hybrid_score": 84.0,
            "rel_volume": 1.4,
            "three_weeks_tight": True,
            "vcs": 85.0,
            "overheat": False,
        }
    )
    result = evaluator.evaluate("TEST", row, pivot_result)
    assert result.is_candidate is True
    assert result.candidate_status.startswith("pass")


def test_position_sizing_and_exit_rules() -> None:
    sizing = PositionSizingCalculator(PositionSizingConfig(stop_mode="ema21_low", risk_per_trade_pct=1.0))
    size_result = sizing.calculate("TEST", account_size=100000.0, entry_price=50.0, reference_stop_price=46.0)
    assert size_result.position_size == 250
    assert round(size_result.max_loss_amount, 2) == 1000.0

    history = _build_history()
    exit_result = ExitRuleEvaluator(RiskModelConfig()).evaluate(
        "TEST",
        history=history,
        entry_price=10.0,
        initial_stop=8.0,
    )
    assert exit_result.hit_1r is True
    assert exit_result.hit_3r is False
    assert exit_result.phase == "phase_2"
    assert exit_result.partial_take_profit_signal is True
