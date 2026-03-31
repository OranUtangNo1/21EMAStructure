from __future__ import annotations

import pandas as pd

from src.dashboard.watchlist import WatchlistViewModelBuilder
from src.scan.rules import ScanCardConfig, ScanConfig, evaluate_list_rules, evaluate_scan_rules
from src.scan.runner import ScanRunner


def test_high_est_eps_growth_uses_rank_threshold() -> None:
    row = pd.Series({"eps_growth": 45.0, "eps_growth_rank": 95.0})
    config = ScanConfig(high_eps_growth_rank_threshold=90.0)
    result = evaluate_list_rules(row, config)
    assert result["High Est. EPS Growth"] is True


def test_relative_strength_list_uses_rsi_not_app_rs() -> None:
    row = pd.Series({"rsi21": 61.0, "rsi63": 55.0, "raw_rs21": 10.0, "raw_rs63": 95.0})
    config = ScanConfig(enabled_list_rules=("Relative Strength 21 > 63",))

    result = evaluate_list_rules(row, config)

    assert result["Relative Strength 21 > 63"] is True


def test_enabled_scan_rules_can_be_swapped_from_config() -> None:
    row = pd.Series({"rel_volume": 2.0, "daily_change_pct": 1.0})
    config = ScanConfig(enabled_scan_rules=("Vol Up",))
    result = evaluate_scan_rules(row, config)
    assert set(result) == {"Vol Up"}
    assert result["Vol Up"] is True


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


def test_watchlist_cards_follow_configured_card_sections() -> None:
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
            {"ticker": "BBB", "name": "Vol Up", "kind": "scan"},
        ]
    )
    config = ScanConfig(card_sections=(ScanCardConfig(scan_name="Vol Up", display_name="Volume Expansion"),))

    cards = WatchlistViewModelBuilder(config).build_scan_cards(raw_watchlist, hits)

    assert len(cards) == 1
    assert cards[0].display_name == "Volume Expansion"
    assert list(cards[0].rows["Ticker"]) == ["BBB"]


def test_watchlist_builder_preserves_duplicate_columns() -> None:
    raw_watchlist = pd.DataFrame(
        {
            "name": ["Alpha"],
            "hybrid_score": [95.0],
            "overlap_count": [3],
            "scan_hit_count": [3],
            "list_overlap_count": [1],
            "duplicate_ticker": [True],
            "hit_scans": ["Vol Up, VCS, 97 Club"],
            "hit_lists": ["High Est. EPS Growth"],
            "vcs": [70.0],
            "earnings_in_7d": [False],
        },
        index=["AAA"],
    )

    display = WatchlistViewModelBuilder().build(raw_watchlist)

    assert bool(display.iloc[0]["duplicate_ticker"]) is True
    assert int(display.iloc[0]["scan_hit_count"]) == 3
    assert int(display.iloc[0]["list_overlap_count"]) == 1


def test_watchlist_has_no_hard_limit_when_no_hits() -> None:
    snapshot = pd.DataFrame(
        {
            "weekly_return": [0.0] * 12,
            "quarterly_return": [0.0] * 12,
            "hybrid_score": list(range(12)),
            "vcs": [0.0] * 12,
            "rs21": [0.0] * 12,
        },
        index=[f"T{i:02d}" for i in range(12)],
    )
    runner = ScanRunner(ScanConfig())

    result = runner.run(snapshot)

    assert result.hits.empty
    assert len(result.watchlist) == 12


def test_card_sections_reject_list_sources() -> None:
    try:
        ScanConfig.from_dict(
            {
                "card_sections": [
                    {
                        "scan_name": "High Est. EPS Growth",
                        "source_kind": "list",
                    }
                ]
            }
        )
    except ValueError as exc:
        assert "scan-based cards only" in str(exc)
    else:
        raise AssertionError("Expected list-based card sections to be rejected")


def test_watchlist_excludes_list_only_symbols() -> None:
    snapshot = pd.DataFrame(
        {
            "weekly_return": [5.0],
            "quarterly_return": [15.0],
            "close": [100.0],
            "ema21_low": [90.0],
            "ema21_low_pct": [4.0],
            "atr_21ema_zone": [-2.0],
            "rel_volume": [0.5],
            "daily_change_pct": [1.0],
            "from_open_pct": [1.0],
            "hybrid_score": [50.0],
            "vcs": [10.0],
            "rs21": [60.0],
            "raw_rs21": [70.0],
            "raw_rs63": [60.0],
            "rsi21": [40.0],
            "rsi63": [45.0],
            "eps_growth": [99.0],
            "trend_base": [False],
            "pp_count_30d": [0],
        },
        index=["AAA"],
    )
    runner = ScanRunner(ScanConfig(high_eps_growth_rank_threshold=50.0))

    result = runner.run(snapshot)

    assert result.watchlist.empty
    assert not result.hits.empty
    assert set(result.hits["kind"]) == {"list"}


def test_duplicate_ticker_uses_scan_overlap_not_list_overlap() -> None:
    snapshot = pd.DataFrame(
        {
            "weekly_return": [1.0],
            "quarterly_return": [1.0],
            "close": [100.0],
            "sma50": [90.0],
            "ema21_low": [95.0],
            "ema21_low_pct": [5.0],
            "atr_21ema_zone": [2.0],
            "atr_50sma_zone": [2.0],
            "dcr_percent": [10.0],
            "rel_volume": [2.0],
            "daily_change_pct": [1.0],
            "from_open_pct": [1.0],
            "hybrid_score": [80.0],
            "vcs": [10.0],
            "rs21": [60.0],
            "raw_rs21": [70.0],
            "raw_rs63": [60.0],
            "rsi21": [60.0],
            "rsi63": [50.0],
            "eps_growth": [50.0],
            "eps_growth_rank": [95.0],
            "trend_base": [False],
            "pp_count_30d": [0],
        },
        index=["AAA"],
    )
    runner = ScanRunner(ScanConfig(duplicate_min_count=3))

    result = runner.run(snapshot)

    assert len(result.watchlist) == 1
    latest = result.watchlist.iloc[0]
    assert int(latest["scan_hit_count"]) == 1
    assert int(latest["list_overlap_count"]) >= 3
    assert int(latest["overlap_count"]) == 1
    assert bool(latest["duplicate_ticker"]) is False


def test_duplicate_ticker_builder_uses_scan_hits_only() -> None:
    watchlist = pd.DataFrame(
        {
            "hybrid_score": [95.0, 80.0],
            "overlap_count": [3, 1],
            "vcs": [70.0, 60.0],
        },
        index=["AAA", "BBB"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "name": "21EMA scan", "kind": "scan"},
            {"ticker": "AAA", "name": "Vol Up", "kind": "scan"},
            {"ticker": "AAA", "name": "VCS", "kind": "scan"},
            {"ticker": "AAA", "name": "High Est. EPS Growth", "kind": "list"},
            {"ticker": "BBB", "name": "21EMA scan", "kind": "scan"},
            {"ticker": "BBB", "name": "High Est. EPS Growth", "kind": "list"},
            {"ticker": "BBB", "name": "Relative Strength 21 > 63", "kind": "list"},
            {"ticker": "BBB", "name": "Vol Up Gainers", "kind": "list"},
        ]
    )

    duplicate = WatchlistViewModelBuilder().build_duplicate_tickers(watchlist, hits, min_count=3)

    assert list(duplicate["Ticker"]) == ["AAA"]
    assert int(duplicate.iloc[0]["Scan Hits"]) == 3

