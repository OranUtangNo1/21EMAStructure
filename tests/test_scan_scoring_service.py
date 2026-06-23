from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.dashboard.watchlist import WatchlistViewModelBuilder
from src.scan.runner import ScanRunner
from src.scan.rules import ScanConfig
from src.services.scan_scoring_service import ScanScoringService
from src.services.scan_service import ScanService


def test_scan_scoring_service_restores_fields_required_by_presets() -> None:
    service = ScanScoringService.from_config()
    stock_history = _history(multiplier=0.012)
    benchmark_history = _history(multiplier=0.001)
    snapshot = _snapshot(stock_history)
    universe = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "name": "Alpha",
                "sector": "Technology",
                "industry": "Software",
                "market_cap": 1_000_000_000.0,
                "eps_growth": 30.0,
                "revenue_growth": 20.0,
            }
        ]
    )

    result = service.score(
        snapshot,
        {"AAA": stock_history},
        benchmark_history,
        universe_snapshot=universe,
    )

    assert result.index.tolist() == ["AAA"]
    assert result.loc["AAA", "raw_rs21"] == pytest.approx(100.0)
    assert result.loc["AAA", "industry"] == "Software"
    assert result.loc["AAA", "industry_score"] == pytest.approx(100.0)
    assert result.loc["AAA", "fundamental_score"] == pytest.approx(100.0)
    assert pd.notna(result.loc["AAA", "hybrid_score"])
    assert pd.notna(result.loc["AAA", "vcs"])
    assert bool(result.loc["AAA", "rs_ratio_at_52w_high"])


def test_scored_snapshot_can_produce_stage2_preset_hit() -> None:
    scoring_service = ScanScoringService.from_config()
    stock_history = _history(multiplier=0.012)
    benchmark_history = _history(multiplier=0.001)
    snapshot = _snapshot(stock_history)
    universe = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "industry": "Software",
                "market_cap": 1_000_000_000.0,
                "eps_growth": 30.0,
                "revenue_growth": 20.0,
            }
        ]
    )
    scored = scoring_service.score(
        snapshot,
        {"AAA": stock_history},
        benchmark_history,
        universe_snapshot=universe,
    )
    config = ScanConfig.from_dict(
        {
            "enabled_scan_rules": ["Pocket Pivot"],
            "annotation_filters": [
                {"filter_name": "Stage 2 Quality Score"},
                {"filter_name": "Mature / Late Stage Risk Filter"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Stage 2 Pocket Pivot",
                    "selected_scan_names": ["Pocket Pivot"],
                    "selected_annotation_filters": [
                        "Stage 2 Quality Score",
                        "Mature / Late Stage Risk Filter",
                    ],
                    "duplicate_threshold": 1,
                }
            ],
        }
    )
    scan_service = ScanService(
        indicator_service=None,
        scan_config=config,
        scan_runner=ScanRunner(config),
        preset_builder=WatchlistViewModelBuilder(config),
    )

    result = scan_service.run_from_snapshot(scored, date_key="2026-06-22")

    assert result.preset["ticker"].tolist() == ["AAA"]
    assert result.preset["hit_presets"].tolist() == ["Stage 2 Pocket Pivot"]
    watchlist = result.scan_run_result.watchlist
    assert bool(watchlist.loc["AAA", "annotation_stage2_quality_score"])
    assert bool(watchlist.loc["AAA", "annotation_mature_late_stage_risk_filter"])


def test_scan_scoring_service_fails_fast_without_rs_inputs() -> None:
    service = ScanScoringService.from_config()

    with pytest.raises(RuntimeError, match="no raw_rs21 values"):
        service.score(_snapshot(_history()), {"AAA": _history()}, pd.DataFrame())


def _history(*, multiplier: float = 0.005) -> pd.DataFrame:
    dates = pd.bdate_range("2025-11-10", periods=160)
    close = pd.Series(100.0 * (1.0 + np.arange(len(dates)) * multiplier), index=dates)
    return pd.DataFrame(
        {
            "open": close * 0.995,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "adjusted_close": close,
            "volume": np.linspace(1_000_000.0, 2_000_000.0, len(dates)),
        },
        index=dates,
    )


def _snapshot(history: pd.DataFrame) -> pd.DataFrame:
    latest = history.iloc[-1]
    return pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "trade_date": history.index[-1],
                "close": latest["close"],
                "stage_label": "stage2_candidate",
                "trend_template_price_score": 7,
                "sma150_slope_1m_pct": 5.0,
                "sma200_slope_1m_pct": 3.0,
                "dist_from_52w_high": -5.0,
                "dist_from_52w_low": 80.0,
                "ud_volume_ratio": 2.0,
                "pp_count_window": 3,
                "weekly_return": 5.0,
                "quarterly_return": 15.0,
                "days_since_stage2_start": 30.0,
                "atr_pct_from_50sma": 1.0,
            }
        ]
    ).set_index("ticker", drop=False)
