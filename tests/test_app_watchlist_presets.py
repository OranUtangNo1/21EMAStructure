from pathlib import Path

import pandas as pd

from app.main import _build_builtin_watchlist_presets, _read_watchlist_preset_values, _watchlist_controls_equal, export_watchlist_preset_csvs
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
    assert set(summary["preset_name"]) == {"Momentum Core", "Legacy Hidden"}
    assert summary.loc[summary["preset_name"] == "Momentum Core", "top_tickers"].iloc[0] == "AAA"

    second_dir = export_watchlist_preset_csvs(str(config_path), build_artifacts(["BBB"]))

    assert second_dir == first_dir
    summary = pd.read_csv(summary_path)
    assert summary.loc[summary["preset_name"] == "Momentum Core", "top_tickers"].iloc[0] == "BBB"


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
