from __future__ import annotations

import pandas as pd

from src.dashboard.watchlist import WatchlistViewModelBuilder
from src.scan.rules import ScanCardConfig, ScanConfig, evaluate_annotation_filters, evaluate_scan_rules
from src.scan.runner import ScanRunner


def test_high_est_eps_growth_annotation_uses_rank_threshold() -> None:
    row = pd.Series({"eps_growth": 45.0, "eps_growth_rank": 95.0})
    config = ScanConfig(high_eps_growth_rank_threshold=90.0)
    result = evaluate_annotation_filters(row, config)
    assert result["High Est. EPS Growth"] is True


def test_relative_strength_annotation_uses_rsi_not_app_rs() -> None:
    row = pd.Series({"rsi21": 61.0, "rsi63": 55.0, "raw_rs21": 10.0, "raw_rs63": 95.0})
    config = ScanConfig()

    result = evaluate_annotation_filters(row, config)

    assert result["Relative Strength 21 > 63"] is True


def test_enabled_scan_rules_can_be_swapped_from_config() -> None:
    row = pd.Series({"rel_volume": 2.0, "daily_change_pct": 1.0})
    config = ScanConfig(enabled_scan_rules=("Vol Up",))
    result = evaluate_scan_rules(row, config)
    assert set(result) == {"Vol Up"}
    assert result["Vol Up"] is True


def test_near_52w_high_scan_uses_distance_hybrid_and_trend_filters() -> None:
    row = pd.Series({"high_52w": 100.0, "close": 95.0, "hybrid_score": 70.0, "trend_base": True})
    config = ScanConfig(enabled_scan_rules=("Near 52W High",))

    result = evaluate_scan_rules(row, config)

    assert result["Near 52W High"] is True


def test_three_weeks_tight_scan_uses_indicator_flag_vcs_and_trend() -> None:
    row = pd.Series({"three_weeks_tight": True, "vcs": 55.0, "trend_base": True})
    config = ScanConfig(enabled_scan_rules=("Three Weeks Tight",))

    result = evaluate_scan_rules(row, config)

    assert result["Three Weeks Tight"] is True


def test_rs_acceleration_scan_uses_rs_fields_not_rsi_fields() -> None:
    row = pd.Series({"rs21": 75.0, "rs63": 70.0, "rsi21": 10.0, "rsi63": 90.0, "trend_base": True})
    config = ScanConfig(enabled_scan_rules=("RS Acceleration",))

    result = evaluate_scan_rules(row, config)

    assert result["RS Acceleration"] is True


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


def test_watchlist_builder_surfaces_annotation_columns() -> None:
    raw_watchlist = pd.DataFrame(
        {
            "name": ["Alpha"],
            "hybrid_score": [95.0],
            "overlap_count": [3],
            "scan_hit_count": [3],
            "annotation_hit_count": [2],
            "duplicate_ticker": [True],
            "hit_scans": ["Vol Up, VCS, 97 Club"],
            "annotation_hits": ["Relative Strength 21 > 63, High Est. EPS Growth"],
            "vcs": [70.0],
            "earnings_in_7d": [False],
        },
        index=["AAA"],
    )

    display = WatchlistViewModelBuilder().build(raw_watchlist)

    assert bool(display.iloc[0]["duplicate_ticker"]) is True
    assert int(display.iloc[0]["scan_hit_count"]) == 3
    assert int(display.iloc[0]["annotation_hit_count"]) == 2
    assert "Relative Strength 21 > 63" in display.iloc[0]["annotation_hits"]


def test_watchlist_is_empty_when_no_scans_hit_even_if_annotations_exist() -> None:
    snapshot = pd.DataFrame(
        {
            "weekly_return": [0.0],
            "quarterly_return": [0.0],
            "hybrid_score": [50.0],
            "vcs": [0.0],
            "rs21": [0.0],
            "rsi21": [60.0],
            "rsi63": [50.0],
            "eps_growth_rank": [95.0],
            "trend_base": [False],
            "rel_volume": [0.1],
            "daily_change_pct": [-1.0],
            "from_open_pct": [-1.0],
            "pp_count_30d": [0],
        },
        index=["AAA"],
    )
    runner = ScanRunner(ScanConfig())

    result = runner.run(snapshot)

    assert result.hits.empty
    assert result.watchlist.empty


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


def test_runner_attaches_annotation_flags_to_scan_hits() -> None:
    snapshot = pd.DataFrame(
        {
            "weekly_return": [1.0],
            "quarterly_return": [1.0],
            "close": [100.0],
            "sma50": [110.0],
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
            "pocket_pivot": [False],
        },
        index=["AAA"],
    )
    runner = ScanRunner(ScanConfig(duplicate_min_count=3))

    result = runner.run(snapshot)

    assert len(result.watchlist) == 1
    assert set(result.hits["kind"]) == {"scan"}
    latest = result.watchlist.iloc[0]
    assert bool(latest["annotation_rsi21_gt_63"]) is True
    assert bool(latest["annotation_high_eps_growth"]) is True
    assert int(latest["annotation_hit_count"]) == 2
    assert "Relative Strength 21 > 63" in latest["annotation_hits"]
    assert int(latest["scan_hit_count"]) == 1
    assert int(latest["list_overlap_count"]) == 1
    assert latest["hit_lists"] == latest["hit_scans"]
    assert bool(latest["duplicate_ticker"]) is False


def test_duplicate_ticker_builder_uses_scan_hits_only() -> None:
    watchlist = pd.DataFrame(
        {
            "hybrid_score": [95.0, 80.0],
            "overlap_count": [3, 1],
            "vcs": [70.0, 60.0],
            "annotation_rsi21_gt_63": [True, True],
            "annotation_high_eps_growth": [True, False],
        },
        index=["AAA", "BBB"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "name": "21EMA scan", "kind": "scan"},
            {"ticker": "AAA", "name": "Vol Up", "kind": "scan"},
            {"ticker": "AAA", "name": "VCS", "kind": "scan"},
            {"ticker": "BBB", "name": "21EMA scan", "kind": "scan"},
        ]
    )

    duplicate = WatchlistViewModelBuilder().build_duplicate_tickers(watchlist, hits, min_count=3)

    assert list(duplicate["Ticker"]) == ["AAA"]
    assert int(duplicate.iloc[0]["Scan Hits"]) == 3



def test_watchlist_cards_can_be_filtered_by_selected_scan_names() -> None:
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
    config = ScanConfig(
        card_sections=(
            ScanCardConfig(scan_name="21EMA scan", display_name="21EMA"),
            ScanCardConfig(scan_name="Vol Up", display_name="Vol Up"),
        )
    )

    cards = WatchlistViewModelBuilder(config).build_scan_cards(raw_watchlist, hits, selected_scan_names=["21EMA scan"])

    assert len(cards) == 1
    assert cards[0].scan_name == "21EMA scan"
    assert list(cards[0].rows["Ticker"]) == ["AAA"]


def test_duplicate_ticker_builder_respects_selected_scans_and_threshold() -> None:
    watchlist = pd.DataFrame(
        {
            "H": [95.0, 80.0],
            "overlap_count": [3, 2],
            "vcs": [70.0, 60.0],
        },
        index=["AAA", "BBB"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "name": "21EMA scan", "kind": "scan"},
            {"ticker": "AAA", "name": "Vol Up", "kind": "scan"},
            {"ticker": "AAA", "name": "VCS", "kind": "scan"},
            {"ticker": "BBB", "name": "21EMA scan", "kind": "scan"},
            {"ticker": "BBB", "name": "97 Club", "kind": "scan"},
        ]
    )

    duplicate = WatchlistViewModelBuilder().build_duplicate_tickers(
        watchlist,
        hits,
        min_count=2,
        selected_scan_names=["21EMA scan", "VCS"],
    )

    assert list(duplicate["Ticker"]) == ["AAA"]
    assert int(duplicate.iloc[0]["Scan Hits"]) == 2
    assert float(duplicate.iloc[0]["Hybrid-RS"]) == 95.0


def test_annotation_filters_apply_with_and_semantics() -> None:
    watchlist = pd.DataFrame(
        {
            "annotation_rsi21_gt_63": [True, True, False],
            "annotation_high_eps_growth": [True, False, True],
        },
        index=["AAA", "BBB", "CCC"],
    )

    filtered = WatchlistViewModelBuilder().filter_by_annotation_filters(
        watchlist,
        ["Relative Strength 21 > 63", "High Est. EPS Growth"],
    )

    assert list(filtered.index) == ["AAA"]


def test_apply_selected_scan_metrics_zeroes_duplicate_state_when_no_scans_selected() -> None:
    watchlist = pd.DataFrame(
        {
            "hybrid_score": [95.0],
            "overlap_count": [3],
            "duplicate_ticker": [True],
        },
        index=["AAA"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "name": "21EMA scan", "kind": "scan"},
            {"ticker": "AAA", "name": "VCS", "kind": "scan"},
        ]
    )

    projected = WatchlistViewModelBuilder().apply_selected_scan_metrics(
        watchlist,
        hits,
        min_count=2,
        selected_scan_names=[],
    )

    assert int(projected.iloc[0]["selected_scan_hit_count"]) == 0
    assert int(projected.iloc[0]["overlap_count"]) == 0
    assert bool(projected.iloc[0]["duplicate_ticker"]) is False
