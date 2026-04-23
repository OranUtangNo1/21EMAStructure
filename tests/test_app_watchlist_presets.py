from pathlib import Path

import pandas as pd

from app.main import (
    _build_builtin_watchlist_presets,
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
from src.ui_preferences import UserPreferenceStore


def test_watchlist_controls_equal_treats_duplicate_threshold_as_material() -> None:
    left = {
        "selected_scan_names": ["VCS", "97 Club"],
        "selected_annotation_filters": ["RS 21 >= 63"],
        "selected_duplicate_subfilters": ["Top3 HybridRS"],
        "duplicate_threshold": 2,
    }
    right = {
        "selected_scan_names": ["VCS", "97 Club"],
        "selected_annotation_filters": ["RS 21 >= 63"],
        "selected_duplicate_subfilters": ["Top3 HybridRS"],
        "duplicate_threshold": 1,
    }

    assert _watchlist_controls_equal(left, right) is False


def test_watchlist_controls_equal_accepts_equivalent_values() -> None:
    left = {
        "selected_scan_names": ["VCS"],
        "selected_annotation_filters": [],
        "selected_duplicate_subfilters": [],
        "duplicate_threshold": 1,
    }
    right = {
        "selected_scan_names": ["VCS"],
        "selected_annotation_filters": [],
        "selected_duplicate_subfilters": [],
        "duplicate_threshold": 1,
    }

    assert _watchlist_controls_equal(left, right) is True


def test_tracking_ranking_display_uses_readable_columns_and_hides_benchmark_return() -> None:
    ranking = pd.DataFrame(
        [
            {
                "preset_name": "Orderly Pullback",
                "market_env": "bull",
                "avg_return_pct": 3.25,
                "benchmark_avg_pct": 1.0,
                "excess_avg_pct": 2.25,
                "max_return_pct": 8.0,
                "min_return_pct": -1.5,
                "win_rate": 0.75,
                "detection_count": 4,
            }
        ]
    )

    display = _build_tracking_ranking_display(ranking)

    assert list(display.columns) == [
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
    assert display.iloc[0]["Win Rate (%)"] == "75.0%"
    assert display.iloc[0]["Excess vs Benchmark (%)"] == "+2.25%"


def test_tracking_detail_display_shows_only_returns_through_selected_horizon() -> None:
    detail = pd.DataFrame(
        [
            {
                "hit_date": "2026-04-01",
                "preset_name": "Orderly Pullback",
                "market_env": "bull",
                "ticker": "AAA",
                "status": "active",
                "close_at_hit": 100.0,
                "close_at_1d": 101.0,
                "close_at_5d": 105.0,
                "close_at_10d": 110.0,
                "close_at_20d": 120.0,
                "return_1d": 1.0,
                "return_5d": 5.0,
                "return_10d": 10.0,
                "return_20d": 20.0,
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
    assert display.iloc[0]["20D Return (%)"] == "-"
    assert display.iloc[0]["Excess vs SPY (%)"] == "+2.50%"


def test_resolve_selected_watchlist_preset_name_requires_available_preset() -> None:
    presets = {"Leader Breakout": {"selected_scan_names": ["97 Club"]}}

    assert _resolve_selected_watchlist_preset_name(" Leader Breakout ", presets) == "Leader Breakout"
    assert _resolve_selected_watchlist_preset_name("Missing Preset", presets) == ""
    assert _resolve_selected_watchlist_preset_name("", presets) == ""


def test_duplicate_role_controls_read_required_and_optional_rule() -> None:
    required, optional, threshold = _resolve_duplicate_role_controls(
        ["Reclaim scan", "Pullback Quality scan", "RS Acceleration"],
        {
            "mode": "required_plus_optional_min",
            "required_scans": ["Reclaim scan"],
            "optional_scans": ["Pullback Quality scan", "RS Acceleration"],
            "optional_min_hits": 2,
        },
        1,
        ["Reclaim scan", "Pullback Quality scan", "RS Acceleration"],
    )

    assert required == ["Reclaim scan"]
    assert optional == ["Pullback Quality scan", "RS Acceleration"]
    assert threshold == 2


def test_duplicate_role_controls_preserve_required_only_ui_state() -> None:
    required, optional, threshold = _resolve_duplicate_role_controls(
        ["Reclaim scan", "21EMA Pattern H"],
        {
            "mode": "min_count",
            "min_count": 2,
        },
        2,
        ["Reclaim scan", "21EMA Pattern H", "RS Acceleration"],
        ["Reclaim scan", "21EMA Pattern H"],
        [],
    )

    assert required == ["Reclaim scan", "21EMA Pattern H"]
    assert optional == []
    assert threshold == 1


def test_watchlist_control_values_persist_card_roles() -> None:
    values = _build_watchlist_control_values(
        ["Reclaim scan", "21EMA Pattern H", "RS Acceleration"],
        [],
        [],
        1,
        {
            "mode": "required_plus_optional_min",
            "min_count": 1,
            "required_scans": ["Reclaim scan"],
            "optional_scans": ["21EMA Pattern H", "RS Acceleration"],
            "optional_min_hits": 1,
        },
        ["Reclaim scan"],
        ["21EMA Pattern H", "RS Acceleration"],
    )

    assert values["required_scan_names"] == ["Reclaim scan"]
    assert values["optional_scan_names"] == ["21EMA Pattern H", "RS Acceleration"]


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
        available_scan_names=["Reclaim scan", "21EMA Pattern H", "RS Acceleration"],
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
        ["VCS", "97 Club"],
        2,
    )

    assert selected == ["VCS", "97 Club"]
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
                "  - scan_name: VCS",
                "    display_name: VCS",
                "  watchlist_presets:",
                "  - preset_name: Momentum Core",
                "    selected_scan_names: [21EMA Pattern H, VCS]",
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
                "    selected_scan_names: [VCS]",
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
                "selected_scan_names": ["VCS"],
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
            [{"ticker": ticker, "name": name, "kind": "scan"} for ticker in watchlist_index for name in ["21EMA Pattern H", "VCS"]]
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
