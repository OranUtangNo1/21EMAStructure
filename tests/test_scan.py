from __future__ import annotations

import pandas as pd

from src.dashboard.watchlist import WatchlistViewModelBuilder
from src.scan.rules import (
    AnnotationFilterConfig,
    DuplicateRuleConfig,
    DEFAULT_SCAN_RULE_NAMES,
    SCAN_RULE_DEFINITIONS,
    ScanCardConfig,
    ScanConfig,
    evaluate_annotation_filters,
    evaluate_scan_issues,
    evaluate_scan_rules,
    mature_late_stage_risk,
    stage2_quality_score,
)
from src.scan.runner import ScanRunner


def _annotation_config(*filter_names: str, **kwargs: object) -> ScanConfig:
    return ScanConfig(
        annotation_filters=tuple(
            AnnotationFilterConfig.from_dict({"filter_name": name, "display_name": name})
            for name in filter_names
        ),
        **kwargs,
    )


def test_high_est_eps_growth_annotation_uses_rank_threshold() -> None:
    row = pd.Series({"eps_growth": 45.0, "eps_growth_rank": 95.0})
    config = _annotation_config("High Est. EPS Growth", high_eps_growth_rank_threshold=90.0)
    result = evaluate_annotation_filters(row, config)
    assert result["High Est. EPS Growth"] is True


def test_relative_strength_annotation_uses_app_rs_threshold() -> None:
    row = pd.Series({"rs21": 63.0, "raw_rs21": 63.0, "rsi21": 10.0, "rsi63": 90.0})
    config = _annotation_config("RS 21 >= 63")

    result = evaluate_annotation_filters(row, config)

    assert result["RS 21 >= 63"] is True


def test_trend_base_annotation_uses_existing_indicator_flag() -> None:
    row = pd.Series({"trend_base": True})
    config = _annotation_config("Trend Base")

    result = evaluate_annotation_filters(row, config)

    assert result["Trend Base"] is True


def test_trend_template_scan_requires_price_template_and_rs_confirmation() -> None:
    row = pd.Series({"trend_template_price_score": 7, "raw_rs21": 70.0})
    config = ScanConfig(enabled_scan_rules=("Trend Template",))

    result = evaluate_scan_rules(row, config)

    assert result["Trend Template"] is True


def test_default_scans_are_composed_from_named_issues() -> None:
    assert set(DEFAULT_SCAN_RULE_NAMES).issubset(SCAN_RULE_DEFINITIONS)
    assert all(SCAN_RULE_DEFINITIONS[name].issues for name in DEFAULT_SCAN_RULE_NAMES)


def test_evaluate_scan_issues_exposes_issue_level_results() -> None:
    row = pd.Series(
        {
            "atr_50sma_zone": 1.0,
            "atr_21ema_zone": 0.5,
            "atr_low_to_ema21_high": 0.0,
            "high": 100.0,
            "prev_high": 100.0,
        }
    )
    config = ScanConfig(enabled_scan_rules=("21EMA Pattern H",))

    result = evaluate_scan_issues(row, config)

    assert result["21EMA Pattern H"] == {
        "atr_50sma_zone_between_0_3": True,
        "atr_21ema_zone_between_0_3_1": True,
        "atr_low_to_ema21_high_gte_minus_0_2": True,
        "high_gt_prev_high": False,
    }
    assert evaluate_scan_rules(row, config)["21EMA Pattern H"] is False


def test_stage_annotations_use_template_context_and_rs_confirmation() -> None:
    row = pd.Series({"stage_label": "stage2_candidate", "trend_template_price_score": 5, "raw_rs21": 60.0})
    config = _annotation_config("Stage 2 Confirmed", "Stage 4 Avoid")

    result = evaluate_annotation_filters(row, config)

    assert result["Stage 2 Confirmed"] is True
    assert result["Stage 4 Avoid"] is False


def test_stage2_quality_annotation_uses_composite_quality_score() -> None:
    row = pd.Series(
        {
            "stage_label": "stage2_candidate",
            "trend_template_price_score": 7,
            "raw_rs21": 88.0,
            "raw_rs63": 80.0,
            "sma150_slope_1m_pct": 3.0,
            "sma200_slope_1m_pct": 2.0,
            "dist_from_52w_high": -6.0,
            "dist_from_52w_low": 75.0,
            "ud_volume_ratio": 1.8,
            "pp_count_window": 2,
        }
    )
    config = ScanConfig()

    result = evaluate_annotation_filters(row, config)

    assert stage2_quality_score(row, config) >= config.stage2_quality_min_score
    assert result["Stage 2 Quality Score"] is True


def test_mature_stage_risk_filter_rejects_extended_late_stage_rows() -> None:
    row = pd.Series(
        {
            "stage_label": "stage2_candidate",
            "trend_template_price_score": 7,
            "raw_rs21": 80.0,
            "days_since_stage2_start": 300.0,
            "dist_from_52w_low": 180.0,
            "atr_pct_from_50sma": 3.0,
        }
    )
    config = ScanConfig()

    result = evaluate_annotation_filters(row, config)

    assert mature_late_stage_risk(row, config) is True
    assert result["Mature / Late Stage Risk Filter"] is False


def test_industry_leadership_gate_uses_industry_score_threshold() -> None:
    row = pd.Series({"industry_score": 72.0})
    config = ScanConfig(industry_leadership_min_score=70.0)

    result = evaluate_annotation_filters(row, config)

    assert result["Industry Leadership Gate"] is True


def test_stage4_annotation_uses_indicator_stage_label() -> None:
    row = pd.Series({"stage_label": "stage4_avoid", "trend_template_price_score": 0, "raw_rs21": 10.0})
    config = _annotation_config("Stage 4 Avoid")

    result = evaluate_annotation_filters(row, config)

    assert result["Stage 4 Avoid"] is True


def test_fund_score_annotation_uses_fixed_threshold() -> None:
    row = pd.Series({"fundamental_score": 70.0})
    config = _annotation_config("Fund Score > 70")

    result = evaluate_annotation_filters(row, config)

    assert result["Fund Score > 70"] is True


def test_resistance_tests_annotation_uses_minimum_two_tests() -> None:
    row = pd.Series({"resistance_test_count": 2.0})
    config = _annotation_config("Resistance Tests >= 2")

    result = evaluate_annotation_filters(row, config)

    assert result["Resistance Tests >= 2"] is True


def test_recent_power_gap_annotation_uses_gap_size_and_recency() -> None:
    row = pd.Series({"power_gap_up_pct": 12.0, "days_since_power_gap": 10.0})
    config = ScanConfig()

    result = evaluate_annotation_filters(row, config)

    assert result["Recent Power Gap"] is True


def test_recent_power_gap_annotation_respects_config_thresholds() -> None:
    row = pd.Series({"power_gap_up_pct": 9.0, "days_since_power_gap": 25.0})
    config = ScanConfig(
        power_gap_annotation_min_pct=10.0,
        power_gap_annotation_max_days=20,
    )
    result = evaluate_annotation_filters(row, config)
    assert result["Recent Power Gap"] is False

    relaxed = ScanConfig(
        power_gap_annotation_min_pct=8.0,
        power_gap_annotation_max_days=30,
    )
    relaxed_result = evaluate_annotation_filters(row, relaxed)
    assert relaxed_result["Recent Power Gap"] is True


def test_enabled_scan_rules_can_be_swapped_from_config() -> None:
    row = pd.Series({"rel_volume": 2.0, "daily_change_pct": 1.0, "ud_volume_ratio": 2.0})
    config = ScanConfig(enabled_scan_rules=("Volume Accumulation",))
    result = evaluate_scan_rules(row, config)
    assert set(result) == {"Volume Accumulation"}
    assert result["Volume Accumulation"] is True


def test_vcs_52_high_scan_uses_relaxed_thresholds() -> None:
    row = pd.Series({"vcs": 55.0, "raw_rs21": 30.0, "dist_from_52w_high": -20.0, "trend_base": False})
    config = ScanConfig(enabled_scan_rules=("VCS 52 High",))

    result = evaluate_scan_rules(row, config)

    assert result["VCS 52 High"] is True


def test_vcs_52_high_scan_no_longer_requires_trend_base() -> None:
    row = pd.Series({"vcs": 80.0, "raw_rs21": 90.0, "dist_from_52w_high": -5.0, "trend_base": False})
    config = ScanConfig(enabled_scan_rules=("VCS 52 High",))

    result = evaluate_scan_rules(row, config)

    assert result["VCS 52 High"] is True


def test_pullback_quality_scan_requires_quiet_volume_contraction() -> None:
    row = pd.Series(
        {
            "trend_base": True,
                        "ema21_slope_5d_pct": 0.4,
            "sma50_slope_10d_pct": 0.8,
            "atr_21ema_zone": -0.5,
            "atr_50sma_zone": 1.0,
            "weekly_return": -4.0,
            "dcr_percent": 55.0,
            "drawdown_from_20d_high_pct": 7.0,
            "volume_ma5_to_ma20_ratio": 0.8,
        }
    )
    config = ScanConfig(enabled_scan_rules=("Pullback Quality scan",))

    result = evaluate_scan_rules(row, config)

    assert result["Pullback Quality scan"] is True


def test_reclaim_scan_requires_cross_back_above_ema21_with_volume() -> None:
    row = pd.Series(
        {
            "trend_base": True,
                        "ema21_slope_5d_pct": 0.4,
            "sma50_slope_10d_pct": 0.7,
            "atr_21ema_zone": 0.5,
            "atr_50sma_zone": 1.5,
            "weekly_return": 2.0,
            "dcr_percent": 65.0,
            "drawdown_from_20d_high_pct": 5.0,
            "volume_ratio_20d": 1.2,
            "close_crossed_above_ema21": True,
            "min_atr_21ema_zone_5d": -0.5,
        }
    )
    config = ScanConfig(enabled_scan_rules=("Reclaim scan",))

    result = evaluate_scan_rules(row, config)

    assert result["Reclaim scan"] is True


def test_reclaim_scan_rejects_rows_without_reclaim_cross() -> None:
    row = pd.Series(
        {
            "trend_base": True,
                        "ema21_slope_5d_pct": 0.4,
            "sma50_slope_10d_pct": 0.7,
            "atr_21ema_zone": 0.5,
            "atr_50sma_zone": 1.5,
            "weekly_return": 2.0,
            "dcr_percent": 65.0,
            "drawdown_from_20d_high_pct": 5.0,
            "volume_ratio_20d": 1.2,
            "close_crossed_above_ema21": False,
            "min_atr_21ema_zone_5d": -0.5,
        }
    )
    config = ScanConfig(enabled_scan_rules=("Reclaim scan",))

    result = evaluate_scan_rules(row, config)

    assert result["Reclaim scan"] is False


def test_50sma_reclaim_scan_requires_sma50_cross_and_recent_undercut() -> None:
    row = pd.Series(
        {
            "sma50_slope_10d_pct": 0.5,
            "atr_50sma_zone": 0.6,
            "close_crossed_above_sma50": True,
            "min_atr_50sma_zone_5d": -0.5,
            "dcr_percent": 65.0,
            "volume_ratio_20d": 1.2,
            "drawdown_from_20d_high_pct": 8.0,
        }
    )
    config = ScanConfig(enabled_scan_rules=("50SMA Reclaim",))

    result = evaluate_scan_rules(row, config)

    assert result["50SMA Reclaim"] is True


def test_50sma_reclaim_scan_rejects_without_same_day_cross() -> None:
    row = pd.Series(
        {
            "sma50_slope_10d_pct": 0.5,
            "atr_50sma_zone": 0.6,
            "close_crossed_above_sma50": False,
            "min_atr_50sma_zone_5d": -0.5,
            "dcr_percent": 65.0,
            "volume_ratio_20d": 1.2,
            "drawdown_from_20d_high_pct": 8.0,
        }
    )
    config = ScanConfig(enabled_scan_rules=("50SMA Reclaim",))

    result = evaluate_scan_rules(row, config)

    assert result["50SMA Reclaim"] is False


def test_rs_new_high_scan_uses_rs_flag_and_distance_band() -> None:
    row = pd.Series(
        {
            "rs_ratio_at_52w_high": True,
            "dist_from_52w_high": -12.0,
        }
    )
    config = ScanConfig(enabled_scan_rules=("RS New High",))

    result = evaluate_scan_rules(row, config)

    assert result["RS New High"] is True


def test_rs_new_high_scan_respects_configurable_distance_bounds() -> None:
    row = pd.Series(
        {
            "rs_ratio_at_52w_high": True,
            "dist_from_52w_high": -4.9,
        }
    )
    config = ScanConfig(
        enabled_scan_rules=("RS New High",),
        rs_new_high_price_dist_max=-5.0,
        rs_new_high_price_dist_min=-30.0,
    )
    result = evaluate_scan_rules(row, config)
    assert result["RS New High"] is False

    relaxed = ScanConfig(
        enabled_scan_rules=("RS New High",),
        rs_new_high_price_dist_max=-4.0,
        rs_new_high_price_dist_min=-30.0,
    )
    relaxed_result = evaluate_scan_rules(row, relaxed)
    assert relaxed_result["RS New High"] is True


def test_rs_3y_new_high_scan_uses_long_term_rs_flag_and_distance_band() -> None:
    row = pd.Series(
        {
            "rs_ratio_at_3y_high": True,
            "dist_from_52w_high": -18.0,
        }
    )
    config = ScanConfig(enabled_scan_rules=("RS 3Y New High",))

    result = evaluate_scan_rules(row, config)

    assert result["RS 3Y New High"] is True


def test_rs_3y_new_high_scan_respects_configurable_distance_bounds() -> None:
    row = pd.Series(
        {
            "rs_ratio_at_3y_high": True,
            "dist_from_52w_high": -4.9,
        }
    )
    config = ScanConfig(
        enabled_scan_rules=("RS 3Y New High",),
        rs_3y_new_high_price_dist_max=-5.0,
        rs_3y_new_high_price_dist_min=-35.0,
    )
    result = evaluate_scan_rules(row, config)
    assert result["RS 3Y New High"] is False

    relaxed = ScanConfig(
        enabled_scan_rules=("RS 3Y New High",),
        rs_3y_new_high_price_dist_max=-4.0,
        rs_3y_new_high_price_dist_min=-35.0,
    )
    relaxed_result = evaluate_scan_rules(row, relaxed)
    assert relaxed_result["RS 3Y New High"] is True


def test_rs_leads_price_setup_requires_rs_new_high_before_price_breakout() -> None:
    row = pd.Series(
        {
            "stage_label": "stage2_candidate",
            "trend_template_price_score": 7,
            "raw_rs21": 82.0,
            "raw_rs63": 78.0,
            "sma150_slope_1m_pct": 2.0,
            "sma200_slope_1m_pct": 1.0,
            "dist_from_52w_high": -8.0,
            "dist_from_52w_low": 70.0,
            "ud_volume_ratio": 1.5,
            "pp_count_window": 2,
            "atr_pct_from_50sma": 2.0,
            "rs_ratio_at_52w_high": True,
        }
    )
    config = ScanConfig(enabled_scan_rules=("RS Leads Price Setup",))

    result = evaluate_scan_rules(row, config)

    assert result["RS Leads Price Setup"] is True


def test_fresh_stage2_breakout_requires_recent_stage2_transition_and_breakout_evidence() -> None:
    row = pd.Series(
        {
            "stage_label": "stage2_candidate",
            "trend_template_price_score": 7,
            "raw_rs21": 78.0,
            "days_since_stage2_start": 5.0,
            "stage_base_days_3m": 30.0,
            "close": 105.0,
            "sma50": 100.0,
            "vcp_pivot_breakout": True,
            "volume_ratio_20d": 1.6,
            "dcr_percent": 75.0,
            "atr_pct_from_50sma": 2.0,
        }
    )
    config = ScanConfig(enabled_scan_rules=("Fresh Stage 2 Breakout",))

    result = evaluate_scan_rules(row, config)

    assert result["Fresh Stage 2 Breakout"] is True


def test_21ema_pattern_h_requires_shallow_high_band_support_and_prev_high_break() -> None:
    row = pd.Series(
        {
            "atr_50sma_zone": 1.0,
            "atr_21ema_zone": 0.3,
            "atr_low_to_ema21_high": -0.2,
            "high": 101.0,
            "prev_high": 100.0,
            "weekly_return": 50.0,
            "dcr_percent": 0.0,
        }
    )
    config = ScanConfig(enabled_scan_rules=("21EMA Pattern H",))

    result = evaluate_scan_rules(row, config)

    assert result["21EMA Pattern H"] is True


def test_21ema_pattern_h_rejects_rows_without_prev_high_break() -> None:
    row = pd.Series(
        {
            "atr_50sma_zone": 1.0,
            "atr_21ema_zone": 0.5,
            "atr_low_to_ema21_high": 0.0,
            "high": 100.0,
            "prev_high": 100.0,
        }
    )
    config = ScanConfig(enabled_scan_rules=("21EMA Pattern H",))

    result = evaluate_scan_rules(row, config)

    assert result["21EMA Pattern H"] is False


def test_21ema_pattern_l_requires_low_band_pierce_reclaim_and_prev_high_break() -> None:
    row = pd.Series(
        {
            "atr_50sma_zone": 1.0,
            "atr_21ema_zone": -0.2,
            "atr_low_to_ema21_low": -0.01,
            "atr_21emaL_zone": 0.01,
            "high": 101.0,
            "prev_high": 100.0,
            "weekly_return": 50.0,
            "dcr_percent": 0.0,
        }
    )
    config = ScanConfig(enabled_scan_rules=("21EMA Pattern L",))

    result = evaluate_scan_rules(row, config)

    assert result["21EMA Pattern L"] is True


def test_21ema_pattern_l_rejects_rows_that_do_not_reclaim_low_band() -> None:
    row = pd.Series(
        {
            "atr_50sma_zone": 1.0,
            "atr_21ema_zone": -0.2,
            "atr_low_to_ema21_low": -0.01,
            "atr_21emaL_zone": 0.0,
            "high": 101.0,
            "prev_high": 100.0,
        }
    )
    config = ScanConfig(enabled_scan_rules=("21EMA Pattern L",))

    result = evaluate_scan_rules(row, config)

    assert result["21EMA Pattern L"] is False


def test_pp_count_annotation_triggers_at_two_pocket_pivots() -> None:
    row = pd.Series({"pp_count_window": 2})
    config = _annotation_config("PP Count (20d)")

    result = evaluate_annotation_filters(row, config)

    assert result["PP Count (20d)"] is True


def test_pp_count_scan_uses_scan_threshold() -> None:
    row = pd.Series({"pp_count_window": 3, "trend_base": False})
    config = ScanConfig(enabled_scan_rules=("PP Count",))

    result = evaluate_scan_rules(row, config)

    assert result["PP Count"] is True


def test_pp_count_thresholds_can_be_parameterized_independently() -> None:
    row = pd.Series({"pp_count_window": 2, "trend_base": True})
    config = _annotation_config(
        "PP Count (20d)",
        enabled_scan_rules=("PP Count",),
        pp_count_scan_min=3,
        pp_count_annotation_min=2,
    )

    scan_result = evaluate_scan_rules(row, config)
    annotation_result = evaluate_annotation_filters(row, config)

    assert scan_result["PP Count"] is False
    assert annotation_result["PP Count (20d)"] is True


def test_pocket_pivot_scan_uses_recent_pp_count_threshold() -> None:
    row = pd.Series({"pp_count_window": 1, "close": 1.0, "sma50": 999.0, "pocket_pivot": False})
    config = ScanConfig(enabled_scan_rules=("Pocket Pivot",), pocket_pivot_pp_count_min=1)

    result = evaluate_scan_rules(row, config)

    assert result["Pocket Pivot"] is True


def test_pocket_pivot_scan_respects_configurable_pp_count_minimum() -> None:
    row = pd.Series({"pp_count_window": 1, "close": 1.0, "sma50": 999.0, "pocket_pivot": True})
    config = ScanConfig(enabled_scan_rules=("Pocket Pivot",), pocket_pivot_pp_count_min=2)

    result = evaluate_scan_rules(row, config)

    assert result["Pocket Pivot"] is False


def test_volume_accumulation_scan_uses_ud_ratio_rel_volume_and_positive_day() -> None:
    row = pd.Series({"ud_volume_ratio": 1.5, "rel_volume": 1.0, "daily_change_pct": 0.1})
    config = ScanConfig(enabled_scan_rules=("Volume Accumulation",))

    result = evaluate_scan_rules(row, config)

    assert result["Volume Accumulation"] is True


def test_volume_accumulation_scan_requires_positive_day() -> None:
    row = pd.Series({"ud_volume_ratio": 2.0, "rel_volume": 1.5, "daily_change_pct": 0.0})
    config = ScanConfig(enabled_scan_rules=("Volume Accumulation",))

    result = evaluate_scan_rules(row, config)

    assert result["Volume Accumulation"] is False


def test_vcp_3t_scan_uses_tightening_state_flag() -> None:
    row = pd.Series({"vcp_tightening": True})
    config = ScanConfig(enabled_scan_rules=("VCP 3T",))

    result = evaluate_scan_rules(row, config)

    assert result["VCP 3T"] is True


def test_vcp_3t_scan_rejects_without_tightening_state() -> None:
    row = pd.Series({"vcp_tightening": False})
    config = ScanConfig(enabled_scan_rules=("VCP 3T",))

    result = evaluate_scan_rules(row, config)

    assert result["VCP 3T"] is False


def test_llhl_1st_pivot_scan_requires_rs_and_first_break() -> None:
    row = pd.Series({"raw_rs21": 60.0, "structure_pivot_1st_break": True})
    config = ScanConfig(enabled_scan_rules=("LL-HL Structure 1st Pivot",), llhl_1st_rs21_min=60.0)

    result = evaluate_scan_rules(row, config)

    assert result["LL-HL Structure 1st Pivot"] is True


def test_llhl_2nd_pivot_scan_requires_rs_and_second_break() -> None:
    row = pd.Series({"raw_rs21": 60.0, "structure_pivot_2nd_break": True})
    config = ScanConfig(enabled_scan_rules=("LL-HL Structure 2nd Pivot",), llhl_2nd_rs21_min=60.0)

    result = evaluate_scan_rules(row, config)

    assert result["LL-HL Structure 2nd Pivot"] is True


def test_llhl_ct_break_scan_uses_ct_trendline_break_flag() -> None:
    row = pd.Series({"ct_trendline_break": True})
    config = ScanConfig(enabled_scan_rules=("LL-HL Structure Trend Line Break",))

    result = evaluate_scan_rules(row, config)

    assert result["LL-HL Structure Trend Line Break"] is True


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
            {"ticker": "AAA", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "BBB", "name": "Reclaim scan", "kind": "scan"},
        ]
    )
    config = ScanConfig(card_sections=(ScanCardConfig(scan_name="Reclaim scan", display_name="Volume Expansion"),))

    cards = WatchlistViewModelBuilder(config).build_scan_cards(raw_watchlist, hits)

    assert len(cards) == 1
    assert cards[0].display_name == "Volume Expansion"
    assert list(cards[0].rows["Ticker"]) == ["BBB"]


def test_watchlist_cards_keep_selected_sections_visible_when_a_scan_has_no_hits() -> None:
    raw_watchlist = pd.DataFrame(
        {
            "name": ["Alpha"],
            "hybrid_score": [95.0],
            "overlap_count": [2],
            "vcs": [70.0],
            "earnings_in_7d": [False],
        },
        index=["AAA"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "name": "21EMA Pattern H", "kind": "scan"},
        ]
    )
    config = ScanConfig(
        card_sections=(
            ScanCardConfig(scan_name="Pullback Quality scan", display_name="PB Quality"),
            ScanCardConfig(scan_name="Reclaim scan", display_name="Reclaim"),
        )
    )

    cards = WatchlistViewModelBuilder(config).build_scan_cards(
        raw_watchlist,
        hits,
        selected_scan_names=["Pullback Quality scan", "Reclaim scan"],
    )

    assert [card.scan_name for card in cards] == ["Pullback Quality scan", "Reclaim scan"]
    assert all(card.ticker_count == 0 for card in cards)
    assert all(card.rows.empty for card in cards)
    assert list(cards[0].rows.columns) == ["Ticker", "Name", "Hybrid-RS", "Overlap", "VCS", "Duplicate", "Earnings"]


def test_watchlist_builder_surfaces_annotation_columns() -> None:
    raw_watchlist = pd.DataFrame(
        {
            "name": ["Alpha"],
            "hybrid_score": [95.0],
            "overlap_count": [3],
            "scan_hit_count": [3],
            "annotation_hit_count": [2],
            "duplicate_ticker": [True],
            "hit_scans": ["21EMA Pattern H, Pocket Pivot, VCS 52 High"],
            "annotation_hits": ["RS 21 >= 63, High Est. EPS Growth"],
            "annotation_rs21_gte_63": [True],
            "annotation_high_eps_growth": [True],
            "vcs": [70.0],
            "earnings_in_7d": [False],
        },
        index=["AAA"],
    )

    display = WatchlistViewModelBuilder(
        _annotation_config("RS 21 >= 63", "High Est. EPS Growth")
    ).build(raw_watchlist)

    assert bool(display.iloc[0]["duplicate_ticker"]) is True
    assert bool(display.iloc[0]["backend_duplicate_ticker"]) is True
    assert display.iloc[0]["backend_duplicate_rule"] == "scan_hit_count >= 3 across all enabled scans"
    assert display.iloc[0]["watchlist_candidate_reason"] == "matched_enabled_scan"
    assert display.iloc[0]["matched_scan_rules"] == "21EMA Pattern H, Pocket Pivot, VCS 52 High"
    assert int(display.iloc[0]["scan_hit_count"]) == 3
    assert int(display.iloc[0]["annotation_hit_count"]) == 2
    assert "RS 21 >= 63" in display.iloc[0]["annotation_hits"]
    assert "RS 21 >= 63" in display.iloc[0]["matched_annotation_filters"]
    assert bool(display.iloc[0]["annotation_rs21_gte_63"]) is True
    assert bool(display.iloc[0]["annotation_high_eps_growth"]) is True


def test_watchlist_builder_includes_new_scan_output_fields_when_available() -> None:
    raw_watchlist = pd.DataFrame(
        {
            "name": ["Alpha"],
            "overlap_count": [3],
            "scan_hit_count": [3],
            "annotation_hit_count": [0],
            "duplicate_ticker": [True],
            "hit_scans": ["Pocket Pivot, VCS 52 High, Volume Accumulation"],
            "annotation_hits": [""],
            "vcs": [70.0],
            "dist_from_52w_high": [-12.5],
            "dist_from_52w_low": [18.0],
            "ud_volume_ratio": [1.8],
            "earnings_in_7d": [False],
        },
        index=["AAA"],
    )

    display = WatchlistViewModelBuilder().build(raw_watchlist)

    assert float(display.iloc[0]["dist_from_52w_high"]) == -12.5
    assert float(display.iloc[0]["dist_from_52w_low"]) == 18.0
    assert float(display.iloc[0]["ud_volume_ratio"]) == 1.8


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
            "pp_count_window": [0],
        },
        index=["AAA"],
    )
    runner = ScanRunner(ScanConfig(enabled_scan_rules=("4% bullish",)))

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
            "daily_change_pct": [4.0],
            "from_open_pct": [1.0],
            "hybrid_score": [80.0],
            "vcs": [10.0],
            "rs21": [70.0],
            "raw_rs21": [70.0],
            "raw_rs63": [60.0],
            "rsi21": [60.0],
            "rsi63": [50.0],
            "eps_growth": [50.0],
            "eps_growth_rank": [95.0],
            "trend_base": [False],
            "pp_count_window": [0],
            "pocket_pivot": [False],
        },
        index=["AAA"],
    )
    runner = ScanRunner(
        _annotation_config(
            "RS 21 >= 63",
            "High Est. EPS Growth",
            enabled_scan_rules=("4% bullish",),
            duplicate_min_count=3,
        )
    )

    result = runner.run(snapshot)

    assert len(result.watchlist) == 1
    assert set(result.hits["kind"]) == {"scan"}
    latest = result.watchlist.iloc[0]
    assert bool(latest["annotation_rs21_gte_63"]) is True
    assert bool(latest["annotation_high_eps_growth"]) is True
    assert int(latest["annotation_hit_count"]) == 2
    assert "RS 21 >= 63" in latest["annotation_hits"]
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
            "annotation_rs21_gte_63": [True, True],
            "annotation_high_eps_growth": [True, False],
        },
        index=["AAA", "BBB"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "AAA", "name": "Reclaim scan", "kind": "scan"},
            {"ticker": "AAA", "name": "Pocket Pivot", "kind": "scan"},
            {"ticker": "BBB", "name": "21EMA Pattern H", "kind": "scan"},
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
            {"ticker": "AAA", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "BBB", "name": "Reclaim scan", "kind": "scan"},
        ]
    )
    config = ScanConfig(
        card_sections=(
            ScanCardConfig(scan_name="21EMA Pattern H", display_name="21EMA"),
            ScanCardConfig(scan_name="Reclaim scan", display_name="Reclaim scan"),
        )
    )

    cards = WatchlistViewModelBuilder(config).build_scan_cards(raw_watchlist, hits, selected_scan_names=["21EMA Pattern H"])

    assert len(cards) == 1
    assert cards[0].scan_name == "21EMA Pattern H"
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
            {"ticker": "AAA", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "AAA", "name": "Reclaim scan", "kind": "scan"},
            {"ticker": "AAA", "name": "Pocket Pivot", "kind": "scan"},
            {"ticker": "BBB", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "BBB", "name": "VCS 52 High", "kind": "scan"},
        ]
    )

    duplicate = WatchlistViewModelBuilder().build_duplicate_tickers(
        watchlist,
        hits,
        min_count=2,
        selected_scan_names=["21EMA Pattern H", "Pocket Pivot"],
    )

    assert list(duplicate["Ticker"]) == ["AAA"]
    assert int(duplicate.iloc[0]["Scan Hits"]) == 2
    assert float(duplicate.iloc[0]["Hybrid-RS"]) == 95.0


def test_duplicate_ticker_builder_can_use_required_plus_optional_rule() -> None:
    watchlist = pd.DataFrame(
        {
            "hybrid_score": [95.0, 80.0, 70.0],
            "overlap_count": [3, 2, 2],
            "vcs": [70.0, 60.0, 50.0],
        },
        index=["AAA", "BBB", "CCC"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "AAA", "name": "Pocket Pivot", "kind": "scan"},
            {"ticker": "AAA", "name": "Reclaim scan", "kind": "scan"},
            {"ticker": "BBB", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "BBB", "name": "Pocket Pivot", "kind": "scan"},
            {"ticker": "CCC", "name": "Pocket Pivot", "kind": "scan"},
            {"ticker": "CCC", "name": "Reclaim scan", "kind": "scan"},
        ]
    )
    config = ScanConfig(
        card_sections=(
            ScanCardConfig(scan_name="21EMA Pattern H", display_name="21EMA"),
            ScanCardConfig(scan_name="Pocket Pivot", display_name="Pocket Pivot"),
            ScanCardConfig(scan_name="Reclaim scan", display_name="Reclaim scan"),
            ScanCardConfig(scan_name="VCS 52 High", display_name="VCS 52 High"),
        )
    )
    duplicate = WatchlistViewModelBuilder(config).build_duplicate_tickers(
        watchlist,
        hits,
        min_count=2,
        selected_scan_names=["21EMA Pattern H", "Pocket Pivot", "Reclaim scan", "VCS 52 High"],
        duplicate_rule=DuplicateRuleConfig(
            mode="required_plus_optional_min",
            required_scans=("21EMA Pattern H",),
            optional_scans=("Pocket Pivot", "Reclaim scan", "VCS 52 High"),
            optional_min_hits=2,
        ),
    )

    assert list(duplicate["Ticker"]) == ["AAA"]
    assert int(duplicate.iloc[0]["Scan Hits"]) == 3


def test_duplicate_ticker_builder_can_use_grouped_threshold_rule() -> None:
    watchlist = pd.DataFrame(
        {
            "hybrid_score": [95.0, 80.0, 70.0],
            "overlap_count": [4, 3, 3],
            "vcs": [70.0, 60.0, 50.0],
        },
        index=["AAA", "BBB", "CCC"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "name": "Pullback Quality scan", "kind": "scan"},
            {"ticker": "AAA", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "AAA", "name": "Volume Accumulation", "kind": "scan"},
            {"ticker": "BBB", "name": "Pullback Quality scan", "kind": "scan"},
            {"ticker": "BBB", "name": "21EMA Pattern L", "kind": "scan"},
            {"ticker": "CCC", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "CCC", "name": "Volume Accumulation", "kind": "scan"},
        ]
    )
    config = ScanConfig(
        card_sections=(
            ScanCardConfig(scan_name="Pullback Quality scan", display_name="PB Quality"),
            ScanCardConfig(scan_name="21EMA Pattern H", display_name="21EMA PH"),
            ScanCardConfig(scan_name="21EMA Pattern L", display_name="21EMA PL"),
            ScanCardConfig(scan_name="Volume Accumulation", display_name="RS Accel"),
            ScanCardConfig(scan_name="Volume Accumulation", display_name="Volume Accumulation"),
        )
    )
    rule = DuplicateRuleConfig.from_dict(
        {
            "mode": "grouped_threshold",
            "required_scans": ["Pullback Quality scan"],
            "optional_groups": [
                {
                    "group_name": "21EMA Trigger",
                    "scans": ["21EMA Pattern H", "21EMA Pattern L"],
                    "min_hits": 1,
                },
                {
                    "group_name": "Strength Confirmation",
                    "scans": ["Volume Accumulation", "Volume Accumulation"],
                    "min_hits": 1,
                },
            ],
        }
    )

    duplicate = WatchlistViewModelBuilder(config).build_duplicate_tickers(
        watchlist,
        hits,
        min_count=1,
        selected_scan_names=[
            "Pullback Quality scan",
            "21EMA Pattern H",
            "21EMA Pattern L",
            "Volume Accumulation",
            "Volume Accumulation",
        ],
        duplicate_rule=rule,
    )

    assert list(duplicate["Ticker"]) == ["AAA"]
    assert int(duplicate.iloc[0]["Scan Hits"]) == 3


def test_duplicate_ticker_builder_can_apply_top3_hybridrs_subfilter() -> None:
    watchlist = pd.DataFrame(
        {
            "hybrid_score": [95.0, 99.0, 88.0, 97.0],
            "overlap_count": [2, 2, 2, 2],
            "vcs": [70.0, 80.0, 65.0, 75.0],
        },
        index=["AAA", "BBB", "CCC", "DDD"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "AAA", "name": "Pocket Pivot", "kind": "scan"},
            {"ticker": "BBB", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "BBB", "name": "Pocket Pivot", "kind": "scan"},
            {"ticker": "CCC", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "CCC", "name": "Pocket Pivot", "kind": "scan"},
            {"ticker": "DDD", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "DDD", "name": "Pocket Pivot", "kind": "scan"},
        ]
    )

    duplicate = WatchlistViewModelBuilder().build_duplicate_tickers(
        watchlist,
        hits,
        min_count=2,
        selected_scan_names=["21EMA Pattern H", "Pocket Pivot"],
        selected_duplicate_subfilters=["Top3 HybridRS"],
    )

    assert list(duplicate["Ticker"]) == ["BBB", "DDD", "AAA"]
    assert list(duplicate["Hybrid-RS"]) == [99.0, 97.0, 95.0]


def test_annotation_filters_apply_with_and_semantics() -> None:
    watchlist = pd.DataFrame(
        {
            "annotation_rs21_gte_63": [True, True, False],
            "annotation_high_eps_growth": [True, False, True],
        },
        index=["AAA", "BBB", "CCC"],
    )

    config = _annotation_config("RS 21 >= 63", "High Est. EPS Growth")
    filtered = WatchlistViewModelBuilder(config).filter_by_annotation_filters(
        watchlist,
        ["RS 21 >= 63", "High Est. EPS Growth"],
    )

    assert list(filtered.index) == ["AAA"]


def test_default_scan_config_includes_new_scan_names_and_cards() -> None:
    config = ScanConfig()

    assert {
        "21EMA Pattern H",
        "21EMA Pattern L",
        "Pullback Quality scan",
        "Reclaim scan",
        "50SMA Reclaim",
        "RS New High",
        "RS 3Y New High",
        "Volume Accumulation",
        "LL-HL Structure 1st Pivot",
        "Pocket Pivot",
        "PP Count",
    }.issubset(set(config.enabled_scan_rules))
    assert "21EMA scan V2" not in set(config.enabled_scan_rules)
    assert "PP Count" in set(config.enabled_scan_rules)
    assert {
        "21EMA Pattern H",
        "21EMA Pattern L",
        "Pullback Quality scan",
        "Reclaim scan",
        "50SMA Reclaim",
        "RS New High",
        "RS 3Y New High",
        "Volume Accumulation",
        "LL-HL Structure 1st Pivot",
        "Pocket Pivot",
        "PP Count",
    }.issubset(
        {section.scan_name for section in config.card_sections}
    )
    assert {section.scan_name for section in config.card_sections}.isdisjoint({"21EMA scan V2"})
    assert "PP Count" in {section.scan_name for section in config.card_sections}
    assert {section.filter_name for section in config.annotation_filters} == {
        "Stage 2 Quality Score",
        "Mature / Late Stage Risk Filter",
        "Industry Leadership Gate",
        "Recent Power Gap",
        "Trend Template",
    }


def test_scan_config_startup_selection_defaults_to_all_card_sections() -> None:
    config = ScanConfig(
        card_sections=(
            ScanCardConfig(scan_name="Reclaim scan", display_name="Reclaim scan"),
            ScanCardConfig(scan_name="Pocket Pivot", display_name="Pocket Pivot"),
        )
    )

    assert config.startup_selected_scan_names() == ("Reclaim scan", "Pocket Pivot")


def test_scan_config_can_define_startup_selected_scan_names_from_config() -> None:
    config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "Reclaim scan", "display_name": "Reclaim scan"},
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
            ],
            "default_selected_scan_names": ["Pocket Pivot"],
        }
    )

    assert config.startup_selected_scan_names() == ("Pocket Pivot",)


def test_scan_config_filters_disabled_scans_from_runtime_and_cards() -> None:
    config = ScanConfig.from_dict(
        {
            "enabled_scan_rules": ["Reclaim scan", "Pocket Pivot"],
            "scan_status_map": {
                "Reclaim scan": "disabled",
                "Pocket Pivot": "enabled",
            },
            "card_sections": [
                {"scan_name": "Reclaim scan", "display_name": "Reclaim scan"},
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
            ],
        }
    )

    assert config.enabled_scan_rules == ("Pocket Pivot",)
    assert tuple(section.scan_name for section in config.card_sections) == ("Pocket Pivot",)


def test_scan_config_coerces_misplaced_scan_names_out_of_enabled_annotation_filters() -> None:
    config = ScanConfig.from_dict(
        {
            "enabled_scan_rules": ["Reclaim scan"],
            "enabled_annotation_filters": ["RS 21 >= 63", "LL-HL Structure 1st Pivot"],
            "annotation_filters": [
                {"filter_name": "RS 21 >= 63", "display_name": "RS 21 >= 63"},
            ],
        }
    )

    assert config.enabled_scan_rules == ("Reclaim scan", "LL-HL Structure 1st Pivot")
    assert config.enabled_annotation_filters == ("RS 21 >= 63",)


def test_scan_config_filters_disabled_annotation_filters_from_runtime_and_presets() -> None:
    config = ScanConfig.from_dict(
        {
            "annotation_filter_status_map": {
                "Trend Base": "disabled",
                "RS 21 >= 63": "enabled",
            },
            "enabled_annotation_filters": ["Trend Base", "RS 21 >= 63"],
            "annotation_filters": [
                {"filter_name": "Trend Base", "display_name": "Trend Base"},
                {"filter_name": "RS 21 >= 63", "display_name": "RS 21 >= 63"},
            ],
            "card_sections": [
                {"scan_name": "Reclaim scan", "display_name": "Reclaim scan"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Filter Trim",
                    "selected_scan_names": ["Reclaim scan"],
                    "selected_annotation_filters": ["Trend Base", "RS 21 >= 63"],
                }
            ],
        }
    )

    assert config.enabled_annotation_filters == ("RS 21 >= 63",)
    assert tuple(section.filter_name for section in config.annotation_filters) == ("RS 21 >= 63",)
    assert config.watchlist_presets[0].selected_annotation_filters == ("RS 21 >= 63",)


def test_scan_config_drops_unavailable_startup_selected_scan_names() -> None:
    config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "Reclaim scan", "display_name": "Reclaim scan"},
            ],
            "default_selected_scan_names": ["Pocket Pivot"],
        }
    )

    assert config.startup_selected_scan_names() == ()


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
            {"ticker": "AAA", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "AAA", "name": "Pocket Pivot", "kind": "scan"},
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


def test_default_annotation_filters_are_simplified() -> None:
    config = ScanConfig()

    labels = {section.filter_name: section.display_name for section in config.annotation_filters}

    assert labels == {
        "Stage 2 Quality Score": "Stage 2 Quality",
        "Mature / Late Stage Risk Filter": "Mature Risk Filter",
        "Industry Leadership Gate": "Industry Leadership",
        "Recent Power Gap": "Recent Power Gap",
        "Trend Template": "Trend Template",
    }


def test_legacy_pp_count_annotation_name_remains_accepted() -> None:
    config = ScanConfig.from_dict(
        {
            "annotation_filters": [
                {"filter_name": "3+ Pocket Pivots (20d)", "display_name": "3+ Pocket Pivots (20d)"},
            ]
        }
    )

    assert config.annotation_filters[0].filter_name == "PP Count (20d)"


def test_scan_config_can_parse_builtin_watchlist_presets() -> None:
    config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "VCS 52 High", "display_name": "VCS 52 High"},
                {"scan_name": "Volume Accumulation", "display_name": "Volume Accumulation"},
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "RS Breakout Setup",
                    "selected_scan_names": ["VCS 52 High", "Volume Accumulation", "Pocket Pivot"],
                    "duplicate_threshold": 2,
                    "duplicate_rule": {"mode": "min_count", "min_count": 2},
                    "preset_status": "hidden_enabled",
                }
            ],
        }
    )

    assert len(config.watchlist_presets) == 1
    assert config.watchlist_presets[0].preset_name == "RS Breakout Setup"
    assert config.watchlist_presets[0].selected_scan_names == ("VCS 52 High", "Volume Accumulation", "Pocket Pivot")
    assert config.watchlist_presets[0].to_control_values()["duplicate_threshold"] == 2
    assert config.watchlist_presets[0].duplicate_rule.mode == "min_count"
    assert config.watchlist_presets[0].preset_status == "hidden_enabled"
    assert config.watchlist_presets[0].visible_in_ui is False
    assert config.watchlist_presets[0].export_enabled is True


def test_scan_config_can_parse_preset_csv_export_settings() -> None:
    config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "VCS 52 High", "display_name": "VCS 52 High"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "RS Breakout Setup",
                    "selected_scan_names": ["VCS 52 High"],
                    "duplicate_threshold": 2,
                    "export_enabled": False,
                }
            ],
            "preset_csv_export": {
                "enabled": True,
                "output_dir": "custom_exports",
                "write_details": False,
                "top_ticker_limit": 3,
            },
        }
    )

    assert config.preset_csv_export.enabled is True
    assert config.preset_csv_export.output_dir == "custom_exports"
    assert config.preset_csv_export.write_details is False
    assert config.preset_csv_export.top_ticker_limit == 3
    assert config.watchlist_presets[0].export_enabled is False
    assert config.watchlist_presets[0].preset_status == "disabled"


def test_scan_config_disables_builtin_preset_when_it_uses_disabled_scan() -> None:
    config = ScanConfig.from_dict(
        {
            "scan_status_map": {
                "VCS 52 High": "enabled",
                "Volume Accumulation": "enabled",
                "Pocket Pivot": "disabled",
            },
            "card_sections": [
                {"scan_name": "VCS 52 High", "display_name": "VCS 52 High"},
                {"scan_name": "Volume Accumulation", "display_name": "Volume Accumulation"},
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "RS Breakout Setup",
                    "selected_scan_names": ["VCS 52 High", "Volume Accumulation", "Pocket Pivot"],
                    "duplicate_threshold": 2,
                    "preset_status": "enabled",
                }
            ],
        }
    )

    assert config.watchlist_presets[0].preset_status == "disabled"
    assert config.watchlist_presets[0].visible_in_ui is False
    assert config.watchlist_presets[0].export_enabled is False


def test_scan_config_rejects_preset_duplicate_rule_scans_outside_selected_scans() -> None:
    try:
        ScanConfig.from_dict(
            {
                "card_sections": [
                    {"scan_name": "21EMA Pattern H", "display_name": "21EMA"},
                    {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
                ],
                "watchlist_presets": [
                    {
                        "preset_name": "Rule Preset",
                        "selected_scan_names": ["21EMA Pattern H"],
                        "duplicate_rule": {
                            "mode": "required_plus_optional_min",
                            "required_scans": ["21EMA Pattern H"],
                            "optional_scans": ["Pocket Pivot"],
                            "optional_min_hits": 1,
                        },
                    }
                ],
            }
        )
    except ValueError as exc:
        assert "duplicate_rule" in str(exc)
    else:
        raise AssertionError("Expected invalid preset duplicate_rule to raise ValueError")


def test_scan_config_rejects_unknown_watchlist_preset_status() -> None:
    try:
        ScanConfig.from_dict(
            {
                "card_sections": [
                    {"scan_name": "VCS 52 High", "display_name": "VCS 52 High"},
                ],
                "watchlist_presets": [
                    {
                        "preset_name": "RS Breakout Setup",
                        "selected_scan_names": ["VCS 52 High"],
                        "preset_status": "archive_only",
                    }
                ],
            }
        )
    except ValueError as exc:
        assert "preset_status" in str(exc)
    else:
        raise AssertionError("Expected invalid preset_status to raise ValueError")


def test_scan_config_rejects_unknown_scan_status_name() -> None:
    try:
        ScanConfig.from_dict({"scan_status_map": {"Made Up Scan": "disabled"}})
    except ValueError as exc:
        assert "scan_status_map" in str(exc)
    else:
        raise AssertionError("Expected invalid scan_status_map name to raise ValueError")


def test_scan_config_rejects_unknown_annotation_filter_status_name() -> None:
    try:
        ScanConfig.from_dict({"annotation_filter_status_map": {"Made Up Filter": "disabled"}})
    except ValueError as exc:
        assert "annotation_filter_status_map" in str(exc)
    else:
        raise AssertionError("Expected invalid annotation_filter_status_map name to raise ValueError")



def test_watchlist_preset_export_includes_duplicate_and_card_hit_tickers() -> None:
    watchlist = pd.DataFrame(
        {
            "hybrid_score": [95.0, 80.0, 70.0],
            "overlap_count": [2, 1, 1],
            "vcs": [70.0, 60.0, 55.0],
            "annotation_rs21_gte_63": [True, True, False],
        },
        index=["AAA", "BBB", "CCC"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "AAA", "name": "Pocket Pivot", "kind": "scan"},
            {"ticker": "BBB", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "CCC", "name": "Pocket Pivot", "kind": "scan"},
        ]
    )
    config = ScanConfig(
        card_sections=(
            ScanCardConfig(scan_name="21EMA Pattern H", display_name="21EMA"),
            ScanCardConfig(scan_name="Pocket Pivot", display_name="Pocket Pivot"),
        ),
        annotation_filters=(AnnotationFilterConfig(filter_name="RS 21 >= 63", display_name="RS 21 >= 63"),),
    )

    export_frame = WatchlistViewModelBuilder(config).build_preset_export(
        "Momentum Core",
        watchlist,
        hits,
        selected_scan_names=["21EMA Pattern H", "Pocket Pivot"],
        min_count=2,
        selected_annotation_filters=["RS 21 >= 63"],
    )

    assert list(export_frame.columns) == [
        "Output Target",
        "Preset Name",
        "Duplicate Tickers",
        "21EMA Hit Tickers",
        "Pocket Pivot Hit Tickers",
    ]
    assert export_frame.iloc[0].to_dict() == {
        "Output Target": "Today's Watchlist",
        "Preset Name": "Momentum Core",
        "Duplicate Tickers": "AAA",
        "21EMA Hit Tickers": "AAA, BBB",
        "Pocket Pivot Hit Tickers": "AAA",
    }


def test_watchlist_preset_summary_export_groups_hit_presets_by_ticker() -> None:
    watchlist = pd.DataFrame(
        {
            "hybrid_score": [95.0, 80.0, 70.0],
            "overlap_count": [2, 1, 1],
            "vcs": [70.0, 60.0, 55.0],
            "annotation_rs21_gte_63": [True, True, False],
        },
        index=["AAA", "BBB", "CCC"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "AAA", "name": "Pocket Pivot", "kind": "scan"},
            {"ticker": "BBB", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "CCC", "name": "Pocket Pivot", "kind": "scan"},
        ]
    )
    config = ScanConfig(
        card_sections=(
            ScanCardConfig(scan_name="21EMA Pattern H", display_name="21EMA"),
            ScanCardConfig(scan_name="Pocket Pivot", display_name="Pocket Pivot"),
        ),
        annotation_filters=(AnnotationFilterConfig(filter_name="RS 21 >= 63", display_name="RS 21 >= 63"),),
    )
    custom_presets = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "21EMA Pattern H", "display_name": "21EMA"},
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
            ],
            "annotation_filters": [
                {"filter_name": "RS 21 >= 63", "display_name": "RS 21 >= 63"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Momentum Core",
                    "selected_scan_names": ["21EMA Pattern H", "Pocket Pivot"],
                    "selected_annotation_filters": ["RS 21 >= 63"],
                    "duplicate_threshold": 2,
                },
                {
                    "preset_name": "EMA Follow Through",
                    "selected_scan_names": ["21EMA Pattern H"],
                    "selected_annotation_filters": [],
                    "duplicate_threshold": 1,
                },
            ],
        }
    ).watchlist_presets

    summary = WatchlistViewModelBuilder(config).build_preset_summary_exports(
        custom_presets,
        watchlist,
        hits,
        trade_date="2026-04-09",
        output_date="2026-04-09",
        top_ticker_limit=1,
    )

    assert list(summary["ticker"]) == ["AAA", "BBB"]
    assert summary.iloc[0].to_dict() == {
        "Output Target": "Today's Watchlist",
        "trade_date": "2026-04-09",
        "output_date": "2026-04-09",
        "ticker": "AAA",
        "hit_presets": "Momentum Core, EMA Follow Through",
        "hit_preset_count": 2,
            "selected_scan_names": "21EMA Pattern H, Pocket Pivot",
        "selected_annotation_filters": "RS 21 >= 63",
        "duplicate_thresholds": "2, 1",
        "duplicate_rule_modes": "min_count",
    }
    assert summary.iloc[1].to_dict() == {
        "Output Target": "Today's Watchlist",
        "trade_date": "2026-04-09",
        "output_date": "2026-04-09",
        "ticker": "BBB",
        "hit_presets": "EMA Follow Through",
        "hit_preset_count": 1,
        "selected_scan_names": "21EMA Pattern H",
        "selected_annotation_filters": "",
        "duplicate_thresholds": "1",
        "duplicate_rule_modes": "min_count",
    }
