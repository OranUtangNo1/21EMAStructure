from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.dashboard.preset_diagnostics import build_preset_diagnostics
from src.scan.rules import ScanConfig
from src.watchlist_presets import ResolvedWatchlistPreset


def _diagnostic_config() -> ScanConfig:
    return ScanConfig.from_dict(
        {
            "enabled_scan_rules": ["VCS 52 High", "Pocket Pivot", "Volume Accumulation"],
            "card_sections": [
                {"scan_name": "VCS 52 High"},
                {"scan_name": "Pocket Pivot"},
                {"scan_name": "Volume Accumulation"},
            ],
            "annotation_filters": [
                {"filter_name": "Stage 2 Quality Score"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Accumulation Breakout",
                    "selected_scan_names": ["VCS 52 High", "Pocket Pivot", "Volume Accumulation"],
                    "selected_annotation_filters": ["Stage 2 Quality Score"],
                    "duplicate_threshold": 1,
                    "duplicate_rule": {
                        "mode": "grouped_threshold",
                        "required_scans": ["VCS 52 High"],
                        "optional_groups": [
                            {
                                "group_name": "Demand Confirmation",
                                "scans": ["Pocket Pivot", "Volume Accumulation"],
                                "min_hits": 1,
                            }
                        ],
                    },
                    "preset_status": "enabled",
                }
            ],
        }
    )


def _diagnostic_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    watchlist = pd.DataFrame(
        {
            "annotation_stage2_quality_score": [True, True, False],
            "hybrid_score": [90.0, 80.0, 70.0],
            "overlap_count": [2, 1, 1],
            "vcs": [80.0, 75.0, 60.0],
        },
        index=["AAA", "BBB", "CCC"],
    )
    scan_hits = pd.DataFrame(
        [
            {"ticker": "AAA", "kind": "scan", "name": "VCS 52 High"},
            {"ticker": "AAA", "kind": "scan", "name": "Pocket Pivot"},
            {"ticker": "BBB", "kind": "scan", "name": "VCS 52 High"},
            {"ticker": "CCC", "kind": "scan", "name": "Pocket Pivot"},
        ]
    )
    return watchlist, scan_hits


def test_build_preset_diagnostics_emits_normalized_funnel_tables() -> None:
    config = _diagnostic_config()
    watchlist, scan_hits = _diagnostic_inputs()
    presets = [ResolvedWatchlistPreset("Accumulation Breakout", "Built-in", config.watchlist_presets[0])]

    artifact = build_preset_diagnostics(
        config_path="config/default.yaml",
        scan_config=config,
        watchlist=watchlist,
        scan_hits=scan_hits,
        presets=presets,
        trade_date=pd.Timestamp("2026-04-10"),
    )

    steps = artifact.preset_steps
    assert list(steps["step_type"]) == ["annotation_filter", "required_scans_all", "scan_group_min"]
    assert list(steps["input_ticker_count"]) == [3, 2, 2]
    assert list(steps["pass_ticker_count"]) == [2, 2, 1]
    assert list(steps["output_ticker_count"]) == [2, 2, 1]
    assert list(steps["rejected_ticker_count"]) == [1, 0, 1]
    assert list(steps["rejection_rate"]) == [1 / 3, 0.0, 0.5]
    assert list(artifact.preset_hits["ticker"]) == ["AAA"]
    assert artifact.preset_hits.iloc[0]["selected_scan_names"] == "Pocket Pivot|VCS 52 High"

    ticker_steps = artifact.preset_ticker_steps
    bbb_group = ticker_steps.loc[(ticker_steps["ticker"] == "BBB") & (ticker_steps["step_name"] == "Demand Confirmation")].iloc[0]
    assert bool(bbb_group["input_eligible"]) is True
    assert bool(bbb_group["step_pass"]) is False
    assert bool(bbb_group["cumulative_pass"]) is False
