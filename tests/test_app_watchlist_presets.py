from pathlib import Path

import pandas as pd

from app.main import (
    _build_builtin_watchlist_presets,
    _build_watchlist_control_values,
    _build_duplicate_role_state,
    _read_watchlist_preset_values,
    _resolve_duplicate_role_controls,
    _resolve_selected_watchlist_preset_name,
    _watchlist_controls_equal,
    export_watchlist_preset_csvs,
    load_artifacts,
)
from src.pipeline import PlatformArtifacts
from src.scan.rules import ScanConfig


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
        ["Reclaim scan", "21EMA scan"],
        {
            "mode": "min_count",
            "min_count": 2,
        },
        2,
        ["Reclaim scan", "21EMA scan", "RS Acceleration"],
        ["Reclaim scan", "21EMA scan"],
        [],
    )

    assert required == ["Reclaim scan", "21EMA scan"]
    assert optional == []
    assert threshold == 1


def test_watchlist_control_values_persist_card_roles() -> None:
    values = _build_watchlist_control_values(
        ["Reclaim scan", "21EMA scan", "RS Acceleration"],
        [],
        [],
        1,
        {
            "mode": "required_plus_optional_min",
            "min_count": 1,
            "required_scans": ["Reclaim scan"],
            "optional_scans": ["21EMA scan", "RS Acceleration"],
            "optional_min_hits": 1,
        },
        ["Reclaim scan"],
        ["21EMA scan", "RS Acceleration"],
    )

    assert values["required_scan_names"] == ["Reclaim scan"]
    assert values["optional_scan_names"] == ["21EMA scan", "RS Acceleration"]


def test_read_watchlist_preset_values_restores_persisted_required_only_roles() -> None:
    values = _read_watchlist_preset_values(
        {
            "schema_version": 1,
            "kind": "watchlist_controls",
            "values": {
                "selected_scan_names": ["Reclaim scan", "21EMA scan"],
                "required_scan_names": ["Reclaim scan", "21EMA scan"],
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
        available_scan_names=["Reclaim scan", "21EMA scan", "RS Acceleration"],
        available_annotation_names=[],
        available_duplicate_subfilters=[],
        default_duplicate_threshold=1,
    )

    assert values is not None
    assert values["required_scan_names"] == ["Reclaim scan", "21EMA scan"]
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
        ["Reclaim scan", "21EMA scan"],
        [],
        1,
    )

    assert selected == ["Reclaim scan", "21EMA scan"]
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
    config_path.write_text(
        "\n".join(
            [
                "scan:",
                "  card_sections:",
                "  - scan_name: 21EMA scan",
                "    display_name: 21EMA",
                "  - scan_name: VCS",
                "    display_name: VCS",
                "  watchlist_presets:",
                "  - preset_name: Momentum Core",
                "    selected_scan_names: [21EMA scan, VCS]",
                "    selected_annotation_filters: []",
                "    selected_duplicate_subfilters: []",
                "    duplicate_threshold: 2",
                "    preset_status: enabled",
                "  - preset_name: Legacy Hidden",
                "    selected_scan_names: [21EMA scan]",
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
            [{"ticker": ticker, "name": name, "kind": "scan"} for ticker in watchlist_index for name in ["21EMA scan", "VCS"]]
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
    details_path = first_dir / "preset_details.csv"
    assert first_dir.name == "20260409"
    assert summary_path.exists()
    assert details_path.exists()
    summary = pd.read_csv(summary_path)
    assert list(summary["ticker"]) == ["AAA"]
    assert summary.loc[summary["ticker"] == "AAA", "hit_presets"].iloc[0] == "Momentum Core, Legacy Hidden"

    second_dir = export_watchlist_preset_csvs(str(config_path), build_artifacts(["BBB"]))

    assert second_dir == first_dir
    summary = pd.read_csv(summary_path)
    assert list(summary["ticker"]) == ["BBB"]
    assert summary.loc[summary["ticker"] == "BBB", "hit_presets"].iloc[0] == "Momentum Core, Legacy Hidden"


def test_build_builtin_watchlist_presets_hides_non_visible_presets() -> None:
    config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "21EMA scan", "display_name": "21EMA"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Visible Preset",
                    "selected_scan_names": ["21EMA scan"],
                    "preset_status": "enabled",
                },
                {
                    "preset_name": "Hidden Export Preset",
                    "selected_scan_names": ["21EMA scan"],
                    "preset_status": "hidden_enabled",
                },
                {
                    "preset_name": "Disabled Preset",
                    "selected_scan_names": ["21EMA scan"],
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
            "selected_scan_names": ["21EMA scan", "Disabled Scan"],
            "selected_annotation_filters": [],
            "selected_duplicate_subfilters": [],
            "duplicate_threshold": 2,
        },
        available_scan_names=["21EMA scan"],
        available_annotation_names=[],
        available_duplicate_subfilters=[],
        default_duplicate_threshold=1,
    )

    assert values is None
