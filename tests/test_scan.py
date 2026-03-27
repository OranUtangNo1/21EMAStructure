from __future__ import annotations

import pandas as pd

from src.scan.rules import ScanConfig, evaluate_list_rules
from src.scan.runner import ScanRunner


def test_high_est_eps_growth_uses_rank_threshold() -> None:
    row = pd.Series({"eps_growth": 45.0, "eps_growth_rank": 95.0})
    config = ScanConfig(high_eps_growth_rank_threshold=90.0)
    result = evaluate_list_rules(row, config)
    assert result["High Est. EPS Growth"] is True


def test_watchlist_default_sort_prefers_hybrid_score() -> None:
    watchlist = pd.DataFrame(
        {
            "hybrid_score": [80.0, 95.0],
            "overlap_count": [5, 2],
            "vcs": [70.0, 60.0],
            "rs21": [85.0, 90.0],
        },
        index=["AAA", "BBB"],
    )
    runner = ScanRunner(ScanConfig(watchlist_sort_mode="hybrid_score"))
    result = runner._sort_watchlist(watchlist)
    assert list(result.index) == ["BBB", "AAA"]


def test_watchlist_optional_sort_can_prioritize_overlap() -> None:
    watchlist = pd.DataFrame(
        {
            "hybrid_score": [80.0, 95.0],
            "overlap_count": [5, 2],
            "vcs": [70.0, 60.0],
            "rs21": [85.0, 90.0],
        },
        index=["AAA", "BBB"],
    )
    runner = ScanRunner(ScanConfig(watchlist_sort_mode="overlap_then_hybrid"))
    result = runner._sort_watchlist(watchlist)
    assert list(result.index) == ["AAA", "BBB"]


def test_watchlist_cards_use_raw_watchlist_fields() -> None:
    from src.dashboard.watchlist import WatchlistViewModelBuilder

    raw_watchlist = pd.DataFrame(
        {
            "name": ["Alpha", "Beta"],
            "hybrid_score": [95.0, 80.0],
            "overlap_count": [2, 1],
            "vcs": [70.0, 60.0],
            "earnings_in_7d": [False, True],
        },
        index=["AAA", "BBB"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "name": "21EMA scan", "kind": "scan"},
            {"ticker": "BBB", "name": "21EMA scan", "kind": "scan"},
        ]
    )

    cards = WatchlistViewModelBuilder().build_scan_cards(raw_watchlist, hits)

    assert len(cards) == 1
    assert list(cards[0].rows["Ticker"]) == ["AAA", "BBB"]
    assert "Hybrid-RS" in cards[0].rows.columns
