from pathlib import Path

import pandas as pd

from app.main import (
    _build_builtin_watchlist_presets,
    _build_entry_signal_connection_candidate_display,
    _build_signal_entry_performance_display,
    _build_tracking_detail_display,
    _build_tracking_ranking_display,
    _build_watchlist_control_values,
    _build_duplicate_role_state,
    _read_watchlist_preset_values,
    _resolve_duplicate_role_controls,
    _resolve_selected_watchlist_preset_name,
    _watchlist_controls_equal,
    build_watchlist_preset_hit_frames,
    export_watchlist_preset_csvs,
    load_artifacts,
    watchlist_preference_namespace,
)
from src.pipeline import PlatformArtifacts
from src.scan.rules import ScanConfig
from src.signals.rules import EntrySignalConfig
from src.ui_preferences import UserPreferenceStore


def _minimal_entry_signal_config(preset_sources: list[str]) -> EntrySignalConfig:
    return EntrySignalConfig.from_dict(
        {
            "definitions": {
                "accumulation_breakout_entry": {
                    "display_name": "Accumulation Breakout Entry",
                    "signal_version": "1.0",
                    "pool": {
                        "preset_sources": preset_sources,
                        "detection_window_days": 5,
                    },
                    "setup_maturity": {"indicators": {"setup": {"weight": 1.0}}},
                    "timing": {"indicators": {"timing": {"weight": 1.0}}},
                    "risk_reward": {
                        "stop": {
                            "reference": "low",
                            "atr_buffer": 0.25,
                            "min_distance_atr": 0.5,
                            "structural_penalty": 0.8,
                        },
                        "reward": {"primary": "high"},
                        "scoring": {"breakpoints": [[1.0, 50.0], [2.0, 100.0]]},
                    },
                    "entry_strength": {
                        "weights": {
                            "setup_maturity": 0.3,
                            "timing": 0.35,
                            "risk_reward": 0.35,
                        },
                        "floor_gate": {
                            "min_axis_threshold": 20.0,
                            "capped_strength": 30.0,
                        },
                    },
                    "display": {
                        "thresholds": {
                            "signal_detected": 55.0,
                            "approaching": 38.0,
                            "tracking": 0.0,
                        },
                    },
                },
            },
        }
    )


def test_watchlist_controls_equal_treats_duplicate_threshold_as_material() -> None:
    left = {
        "selected_scan_names": ["Pocket Pivot", "VCS 52 High"],
        "selected_annotation_filters": ["RS 21 >= 63"],
        "selected_duplicate_subfilters": ["Top3 HybridRS"],
        "duplicate_threshold": 2,
    }
    right = {
        "selected_scan_names": ["Pocket Pivot", "VCS 52 High"],
        "selected_annotation_filters": ["RS 21 >= 63"],
        "selected_duplicate_subfilters": ["Top3 HybridRS"],
        "duplicate_threshold": 1,
    }

    assert _watchlist_controls_equal(left, right) is False


def test_watchlist_controls_equal_accepts_equivalent_values() -> None:
    left = {
        "selected_scan_names": ["Pocket Pivot"],
        "selected_annotation_filters": [],
        "selected_duplicate_subfilters": [],
        "duplicate_threshold": 1,
    }
    right = {
        "selected_scan_names": ["Pocket Pivot"],
        "selected_annotation_filters": [],
        "selected_duplicate_subfilters": [],
        "duplicate_threshold": 1,
    }

    assert _watchlist_controls_equal(left, right) is True


def test_tracking_ranking_display_uses_readable_columns_and_hides_benchmark_return() -> None:
    ranking = pd.DataFrame(
        [
            {
                "preset_name": "Pullback Trigger",
                "market_env": "bull",
                "avg_return_pct": 3.25,
                "benchmark_avg_pct": 1.0,
                "excess_avg_pct": 2.25,
                "max_return_pct": 8.0,
                "min_return_pct": -1.5,
                "win_rate": 0.75,
                "detection_count": 35,
            }
        ]
    )

    display = _build_tracking_ranking_display(ranking)

    assert list(display.columns) == [
        "Tier",
        "Preset",
        "Market",
        "Avg Return (%)",
        "Excess vs Benchmark (%)",
        "Max Return (%)",
        "Min Return (%)",
        "Win Rate (%)",
        "Detections",
    ]
    assert "benchmark_avg_pct" not in display.columns
    assert display.iloc[0]["Tier"] == "Core"
    assert display.iloc[0]["Win Rate (%)"] == "75.0%"
    assert display.iloc[0]["Excess vs Benchmark (%)"] == "+2.25%"


def test_tracking_ranking_display_keeps_small_samples_observing() -> None:
    ranking = pd.DataFrame(
        [
            {
                "preset_name": "Pullback Trigger",
                "market_env": "bull",
                "avg_return_pct": 12.0,
                "benchmark_avg_pct": 1.0,
                "excess_avg_pct": 11.0,
                "max_return_pct": 18.0,
                "min_return_pct": 2.0,
                "win_rate": 0.9,
                "detection_count": 29,
            }
        ]
    )

    display = _build_tracking_ranking_display(ranking)

    assert display.iloc[0]["Tier"] == "Observing"


def test_entry_signal_connection_candidate_display_keeps_fresh_stage2_measurement_only() -> None:
    ranking = pd.DataFrame(
        [
            {
                "preset_name": "Fresh Stage 2 Breakout",
                "market_env": "bull",
                "avg_return_pct": 4.5,
                "benchmark_avg_pct": 1.0,
                "excess_avg_pct": 3.5,
                "max_return_pct": 11.0,
                "min_return_pct": -2.0,
                "win_rate": 0.62,
                "detection_count": 35,
            }
        ]
    )
    signal_config = _minimal_entry_signal_config(["Accumulation Breakout", "RS Breakout Setup"])

    display = _build_entry_signal_connection_candidate_display(
        ranking,
        signal_config,
        horizon_days=21,
        benchmark_ticker="SPY",
    )

    assert display.iloc[0]["Decision"] == "Connection Candidate"
    assert display.iloc[0]["Connection Status"] == "Measurement Only"
    assert display.iloc[0]["Target Signal"] == "Accumulation Breakout Entry"
    assert display.iloc[0]["Avg 21D Return (%)"] == "+4.50%"
    assert display.iloc[0]["Excess vs SPY (%)"] == "+3.50%"


def test_entry_signal_connection_candidate_display_detects_existing_connection() -> None:
    ranking = pd.DataFrame(
        [
            {
                "preset_name": "Fresh Stage 2 Breakout",
                "market_env": "bull",
                "avg_return_pct": 1.0,
                "benchmark_avg_pct": 0.5,
                "excess_avg_pct": 0.5,
                "max_return_pct": 5.0,
                "min_return_pct": -3.0,
                "win_rate": 0.5,
                "detection_count": 10,
            }
        ]
    )
    signal_config = _minimal_entry_signal_config(["Fresh Stage 2 Breakout"])

    display = _build_entry_signal_connection_candidate_display(
        ranking,
        signal_config,
        horizon_days=21,
        benchmark_ticker="SPY",
    )

    assert display.iloc[0]["Decision"] == "Already Connected"
    assert display.iloc[0]["Connection Status"] == "Connected"


def test_signal_entry_performance_display_formats_entry_ready_outcomes() -> None:
    performance = pd.DataFrame(
        [
            {
                "action_bucket": "Entry Ready",
                "signal_name": "orderly_pullback_entry",
                "market_env": "bull",
                "event_count": 30,
                "ticker_count": 25,
                "avg_return_21d": 4.2,
                "win_rate_21d": 0.6,
                "tp1_count": 14,
                "sl_count": 8,
                "timeout_count": 8,
                "ambiguous_count": 0,
                "tp1_rate": 0.467,
                "sl_rate": 0.267,
                "avg_outcome_r": 0.35,
                "avg_days_to_first_outcome": 6.5,
                "avg_max_gain_21d": 9.5,
                "avg_max_drawdown_21d": -3.2,
                "first_event_date": "2026-04-01",
                "last_event_date": "2026-05-01",
            }
        ]
    )

    display = _build_signal_entry_performance_display(performance)

    assert display.iloc[0]["Tier"] == "Positive"
    assert display.iloc[0]["Signal"] == "Orderly Pullback Entry"
    assert display.iloc[0]["Avg 21D Return (%)"] == "+4.20%"
    assert display.iloc[0]["21D Win Rate (%)"] == "60.0%"
    assert display.iloc[0]["TP1 Rate (%)"] == "46.7%"
    assert display.iloc[0]["SL Rate (%)"] == "26.7%"


def test_tracking_detail_display_shows_only_returns_through_selected_horizon() -> None:
    detail = pd.DataFrame(
        [
            {
                "hit_date": "2026-04-01",
                "preset_name": "Pullback Trigger",
                "market_env": "bull",
                "ticker": "AAA",
                "status": "active",
                "close_at_hit": 100.0,
                "close_at_1d": 101.0,
                "close_at_5d": 105.0,
                "close_at_10d": 110.0,
                "close_at_20d": 120.0,
                "close_at_21d": 121.0,
                "return_1d": 1.0,
                "return_5d": 5.0,
                "return_10d": 10.0,
                "return_20d": 20.0,
                "return_21d": 21.0,
                "rs21_at_hit": 88.0,
                "vcs_at_hit": 70.0,
                "hybrid_score_at_hit": 91.0,
                "duplicate_hit_count": 3,
                "excess_return_pct": 2.5,
                "benchmark_return_pct": 2.5,
                "hit_scans": "21EMA Pattern H",
                "matched_filters": "Trend Base",
            }
        ]
    )

    display = _build_tracking_detail_display(detail, selected_horizon=5, benchmark_ticker="SPY")

    assert "benchmark_return_pct" not in display.columns
    assert display.iloc[0]["1D Return (%)"] == "+1.00%"
    assert display.iloc[0]["5D Return (%)"] == "+5.00%"
    assert display.iloc[0]["10D Return (%)"] == "-"
    assert "20D Return (%)" not in display.columns
    assert display.iloc[0]["21D Return (%)"] == "-"
    assert display.iloc[0]["Excess vs SPY (%)"] == "+2.50%"


def test_resolve_selected_watchlist_preset_name_requires_available_preset() -> None:
    presets = {"RS Breakout Setup": {"selected_scan_names": ["VCS 52 High"]}}

    assert _resolve_selected_watchlist_preset_name(" RS Breakout Setup ", presets) == "RS Breakout Setup"
    assert _resolve_selected_watchlist_preset_name("Missing Preset", presets) == ""
    assert _resolve_selected_watchlist_preset_name("", presets) == ""


def test_duplicate_role_controls_read_required_and_optional_rule() -> None:
    required, optional, threshold = _resolve_duplicate_role_controls(
        ["Reclaim scan", "Pullback Quality scan", "Volume Accumulation"],
        {
            "mode": "required_plus_optional_min",
            "required_scans": ["Reclaim scan"],
            "optional_scans": ["Pullback Quality scan", "Volume Accumulation"],
            "optional_min_hits": 2,
        },
        1,
        ["Reclaim scan", "Pullback Quality scan", "Volume Accumulation"],
    )

    assert required == ["Reclaim scan"]
    assert optional == ["Pullback Quality scan", "Volume Accumulation"]
    assert threshold == 2


def test_duplicate_role_controls_preserve_required_only_ui_state() -> None:
    required, optional, threshold = _resolve_duplicate_role_controls(
        ["Reclaim scan", "21EMA Pattern H"],
        {
            "mode": "min_count",
            "min_count": 2,
        },
        2,
        ["Reclaim scan", "21EMA Pattern H", "Volume Accumulation"],
        ["Reclaim scan", "21EMA Pattern H"],
        [],
    )

    assert required == ["Reclaim scan", "21EMA Pattern H"]
    assert optional == []
    assert threshold == 1


def test_watchlist_control_values_persist_card_roles() -> None:
    values = _build_watchlist_control_values(
        ["Reclaim scan", "21EMA Pattern H", "Volume Accumulation"],
        [],
        [],
        1,
        {
            "mode": "required_plus_optional_min",
            "min_count": 1,
            "required_scans": ["Reclaim scan"],
            "optional_scans": ["21EMA Pattern H", "Volume Accumulation"],
            "optional_min_hits": 1,
        },
        ["Reclaim scan"],
        ["21EMA Pattern H", "Volume Accumulation"],
    )

    assert values["required_scan_names"] == ["Reclaim scan"]
    assert values["optional_scan_names"] == ["21EMA Pattern H", "Volume Accumulation"]


def test_read_watchlist_preset_values_restores_persisted_required_only_roles() -> None:
    values = _read_watchlist_preset_values(
        {
            "schema_version": 1,
            "kind": "watchlist_controls",
            "values": {
                "selected_scan_names": ["Reclaim scan", "21EMA Pattern H"],
                "required_scan_names": ["Reclaim scan", "21EMA Pattern H"],
                "optional_scan_names": [],
                "selected_annotation_filters": [],
                "selected_duplicate_subfilters": [],
                "duplicate_threshold": 2,
                "duplicate_rule": {
                    "mode": "min_count",
                    "min_count": 2,
                },
            },
        },
        available_scan_names=["Reclaim scan", "21EMA Pattern H", "Volume Accumulation"],
        available_annotation_names=[],
        available_duplicate_subfilters=[],
        default_duplicate_threshold=1,
    )

    assert values is not None
    assert values["required_scan_names"] == ["Reclaim scan", "21EMA Pattern H"]
    assert values["optional_scan_names"] == []


def test_duplicate_role_state_uses_optional_only_as_simple_overlap() -> None:
    selected, threshold, rule = _build_duplicate_role_state(
        [],
        ["Pocket Pivot", "VCS 52 High"],
        2,
    )

    assert selected == ["Pocket Pivot", "VCS 52 High"]
    assert threshold == 2
    assert rule["mode"] == "min_count"
    assert rule["min_count"] == 2


def test_duplicate_role_state_uses_required_only_as_all_required() -> None:
    selected, threshold, rule = _build_duplicate_role_state(
        ["Reclaim scan", "21EMA Pattern H"],
        [],
        1,
    )

    assert selected == ["Reclaim scan", "21EMA Pattern H"]
    assert threshold == 2
    assert rule["mode"] == "min_count"
    assert rule["min_count"] == 2


def test_load_artifacts_prefers_same_day_saved_run(monkeypatch) -> None:
    saved_artifact = object()

    class FakePlatform:
        def __init__(self, config_path: str) -> None:
            self.config_path = config_path

        def load_latest_run_artifacts(self, symbols, force_universe_refresh):
            assert symbols == ["AAPL"]
            assert force_universe_refresh is False
            return saved_artifact

        def run(self, *args, **kwargs):
            raise AssertionError("run should not be called when saved artifacts are reusable")

    monkeypatch.setattr("app.main.get_research_platform_class", lambda: FakePlatform)

    assert load_artifacts("config/default.yaml", ["AAPL"], False, False) is saved_artifact


def test_load_artifacts_force_refresh_bypasses_saved_run(monkeypatch) -> None:
    recomputed_artifact = object()

    class FakePlatform:
        def __init__(self, config_path: str) -> None:
            self.config_path = config_path

        def load_latest_run_artifacts(self, *args, **kwargs):
            raise AssertionError("saved artifacts should not be loaded during force refresh")

        def run(self, symbols, force_universe_refresh, force_price_refresh):
            assert symbols == ["AAPL"]
            assert force_universe_refresh is False
            assert force_price_refresh is True
            return recomputed_artifact

    monkeypatch.setattr("app.main.get_research_platform_class", lambda: FakePlatform)

    assert load_artifacts("config/default.yaml", ["AAPL"], False, True) is recomputed_artifact


def test_load_artifacts_force_recompute_from_cache_bypasses_saved_run_without_price_refresh(monkeypatch) -> None:
    recomputed_artifact = object()

    class FakePlatform:
        def __init__(self, config_path: str) -> None:
            self.config_path = config_path

        def load_latest_run_artifacts(self, *args, **kwargs):
            raise AssertionError("saved artifacts should not be loaded during cache recompute")

        def run(self, symbols, force_universe_refresh, force_price_refresh):
            assert symbols == ["AAPL"]
            assert force_universe_refresh is False
            assert force_price_refresh is False
            return recomputed_artifact

    monkeypatch.setattr("app.main.get_research_platform_class", lambda: FakePlatform)

    assert load_artifacts("config/default.yaml", ["AAPL"], False, False, force_recompute_from_cache=True) is recomputed_artifact


def test_export_watchlist_preset_csvs_writes_daily_folder_and_overwrites_files(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    preferences_path = tmp_path / "user_preferences.yaml"
    config_path.write_text(
        "\n".join(
            [
                "app:",
                f"  user_preferences_path: {str(preferences_path).replace(chr(92), '/')}",
                "scan:",
                "  card_sections:",
                "  - scan_name: 21EMA Pattern H",
                "    display_name: 21EMA",
                "  - scan_name: Pocket Pivot",
                "    display_name: Pocket Pivot",
                "  watchlist_presets:",
                "  - preset_name: Momentum Core",
                "    selected_scan_names: [21EMA Pattern H, Pocket Pivot]",
                "    selected_annotation_filters: []",
                "    selected_duplicate_subfilters: []",
                "    duplicate_threshold: 2",
                "    preset_status: enabled",
                "  - preset_name: Legacy Hidden",
                "    selected_scan_names: [21EMA Pattern H]",
                "    selected_annotation_filters: []",
                "    selected_duplicate_subfilters: []",
                "    duplicate_threshold: 1",
                "    preset_status: hidden_enabled",
                "  - preset_name: Disabled Legacy",
                "    selected_scan_names: [Pocket Pivot]",
                "    selected_annotation_filters: []",
                "    selected_duplicate_subfilters: []",
                "    duplicate_threshold: 1",
                "    preset_status: disabled",
                "  preset_csv_export:",
                f"    output_dir: {str(tmp_path / 'exports').replace(chr(92), '/')}",
                "    enabled: true",
                "    write_details: true",
                "    top_ticker_limit: 5",
            ]
        ),
        encoding="utf-8",
    )
    UserPreferenceStore(preferences_path).save_collection_item(
        "watchlist_presets",
        watchlist_preference_namespace(str(config_path)),
        "Custom VCS",
        {
            "schema_version": 1,
            "kind": "watchlist_controls",
            "values": {
                "selected_scan_names": ["Pocket Pivot"],
                "selected_annotation_filters": [],
                "selected_duplicate_subfilters": [],
                "duplicate_threshold": 1,
                "duplicate_rule": {"mode": "min_count", "min_count": 1},
            },
        },
    )

    def build_artifacts(watchlist_index: list[str]) -> PlatformArtifacts:
        watchlist = pd.DataFrame(
            {
                "hybrid_score": [95.0 for _ in watchlist_index],
                "overlap_count": [2 for _ in watchlist_index],
                "vcs": [70.0 for _ in watchlist_index],
            },
            index=watchlist_index,
        )
        hits = pd.DataFrame(
            [{"ticker": ticker, "name": name, "kind": "scan"} for ticker in watchlist_index for name in ["21EMA Pattern H", "Pocket Pivot"]]
        )
        return PlatformArtifacts(
            snapshot=pd.DataFrame({"trade_date": [pd.Timestamp("2026-04-09")]}, index=["AAA"]),
            eligible_snapshot=pd.DataFrame(),
            watchlist=watchlist,
            duplicate_tickers=pd.DataFrame(),
            watchlist_cards=[],
            earnings_today=pd.DataFrame(),
            scan_hits=hits,
            benchmark_history=pd.DataFrame(),
            vix_history=pd.DataFrame(),
            market_result=None,
            radar_result=None,
            used_sample_data=False,
            data_source_label="live",
            fetch_status=pd.DataFrame(),
            data_health_summary={},
            run_directory=None,
            universe_mode="manual",
            resolved_symbols=list(watchlist_index),
            universe_snapshot_path=None,
            artifact_origin="test",
        )

    first_dir = export_watchlist_preset_csvs(str(config_path), build_artifacts(["AAA"]))
    assert first_dir is not None
    summary_path = first_dir / "preset_summary.csv"
    hits_path = first_dir / "preset_hits.csv"
    details_path = first_dir / "preset_details.csv"
    assert first_dir.name == "20260409"
    assert summary_path.exists()
    assert hits_path.exists()
    assert details_path.exists()
    summary = pd.read_csv(summary_path)
    assert list(summary["ticker"]) == ["AAA"]
    assert summary.loc[summary["ticker"] == "AAA", "hit_presets"].iloc[0] == "Momentum Core, Legacy Hidden, Custom VCS"
    assert summary.loc[summary["ticker"] == "AAA", "custom_presets"].iloc[0] == "Custom VCS"
    hits = pd.read_csv(hits_path)
    assert set(hits["preset_source"]) == {"Built-in", "Custom"}

    second_dir = export_watchlist_preset_csvs(str(config_path), build_artifacts(["BBB"]))

    assert second_dir == first_dir
    summary = pd.read_csv(summary_path)
    assert list(summary["ticker"]) == ["BBB"]
    assert summary.loc[summary["ticker"] == "BBB", "hit_presets"].iloc[0] == "Momentum Core, Legacy Hidden, Custom VCS"


def test_build_builtin_watchlist_presets_hides_non_visible_presets() -> None:
    config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "21EMA Pattern H", "display_name": "21EMA"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Visible Preset",
                    "selected_scan_names": ["21EMA Pattern H"],
                    "preset_status": "enabled",
                },
                {
                    "preset_name": "Hidden Export Preset",
                    "selected_scan_names": ["21EMA Pattern H"],
                    "preset_status": "hidden_enabled",
                },
                {
                    "preset_name": "Disabled Preset",
                    "selected_scan_names": ["21EMA Pattern H"],
                    "preset_status": "disabled",
                },
            ],
        }
    )

    presets = _build_builtin_watchlist_presets(config)

    assert set(presets) == {"Visible Preset"}


def test_read_watchlist_preset_values_drops_preset_when_scan_is_unavailable() -> None:
    values = _read_watchlist_preset_values(
        {
            "selected_scan_names": ["21EMA Pattern H", "Disabled Scan"],
            "selected_annotation_filters": [],
            "selected_duplicate_subfilters": [],
            "duplicate_threshold": 2,
        },
        available_scan_names=["21EMA Pattern H"],
        available_annotation_names=[],
        available_duplicate_subfilters=[],
        default_duplicate_threshold=1,
    )

    assert values is None
