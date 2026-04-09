from pathlib import Path

import pandas as pd

from app.main import _watchlist_controls_equal, export_watchlist_preset_csvs
from src.pipeline import PlatformArtifacts


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
                "    export_enabled: true",
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
    assert pd.read_csv(summary_path).iloc[0]["top_tickers"] == "AAA"

    second_dir = export_watchlist_preset_csvs(str(config_path), build_artifacts(["BBB"]))

    assert second_dir == first_dir
    assert pd.read_csv(summary_path).iloc[0]["top_tickers"] == "BBB"
