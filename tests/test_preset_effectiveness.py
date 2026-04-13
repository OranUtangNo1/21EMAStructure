from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from src.dashboard.effectiveness import sync_preset_effectiveness_logs
from src.pipeline import PlatformArtifacts


def _build_artifacts(
    trade_date: str,
    *,
    close: float,
    market_score: float = 72.0,
    market_label: str = "bull",
) -> PlatformArtifacts:
    watchlist = pd.DataFrame(
        {
            "close": [close],
            "volume": [1_400_000],
            "avg_volume_50d": [1_000_000],
            "rel_volume": [1.4],
            "hybrid_score": [91.0],
            "vcs": [68.0],
            "rs21": [88.0],
            "rs63": [84.0],
            "rs126": [79.0],
            "dist_from_52w_high": [-4.0],
            "dist_from_52w_low": [52.0],
        },
        index=["AAA"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "name": "21EMA scan", "kind": "scan"},
            {"ticker": "AAA", "name": "VCS", "kind": "scan"},
        ]
    )
    snapshot = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "trade_date": [pd.Timestamp(trade_date)],
            "close": [close],
        }
    )
    return PlatformArtifacts(
        snapshot=snapshot,
        eligible_snapshot=pd.DataFrame(),
        watchlist=watchlist,
        duplicate_tickers=pd.DataFrame(),
        watchlist_cards=[],
        earnings_today=pd.DataFrame(),
        scan_hits=hits,
        benchmark_history=pd.DataFrame(),
        vix_history=pd.DataFrame(),
        market_result=SimpleNamespace(score=market_score, label=market_label),
        radar_result=None,
        used_sample_data=False,
        data_source_label="live",
        fetch_status=pd.DataFrame(),
        data_health_summary={},
        run_directory=None,
        universe_mode="manual",
        resolved_symbols=["AAA"],
        universe_snapshot_path=None,
        artifact_origin="test",
    )


def test_sync_preset_effectiveness_logs_creates_events_and_pending_outcomes(tmp_path: Path) -> None:
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
            ]
        ),
        encoding="utf-8",
    )

    result = sync_preset_effectiveness_logs(
        str(config_path),
        _build_artifacts("2026-04-09", close=100.0),
        root_dir=tmp_path,
    )

    assert result is not None
    assert result.new_event_count == 1
    assert result.updated_outcome_count == 0

    events = pd.read_csv(tmp_path / "data_runs" / "preset_effectiveness" / "events.csv")
    outcomes = pd.read_csv(tmp_path / "data_runs" / "preset_effectiveness" / "outcomes.csv")

    assert events["event_id"].tolist() == ["2026-04-09::Momentum Core::AAA"]
    assert events["hit_scans"].tolist() == ["21EMA scan, VCS"]
    assert outcomes["status"].tolist() == ["pending", "pending", "pending", "pending"]
    assert outcomes["target_horizon_days"].tolist() == [1, 5, 10, 20]


def test_sync_preset_effectiveness_logs_updates_ready_outcomes_when_target_date_arrives(tmp_path: Path) -> None:
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
            ]
        ),
        encoding="utf-8",
    )

    sync_preset_effectiveness_logs(
        str(config_path),
        _build_artifacts("2026-04-09", close=100.0),
        root_dir=tmp_path,
    )
    result = sync_preset_effectiveness_logs(
        str(config_path),
        _build_artifacts("2026-04-10", close=110.0),
        root_dir=tmp_path,
    )

    assert result is not None
    assert result.new_event_count == 1
    assert result.updated_outcome_count == 1

    outcomes = pd.read_csv(tmp_path / "data_runs" / "preset_effectiveness" / "outcomes.csv")
    ready = outcomes.loc[(outcomes["event_id"] == "2026-04-09::Momentum Core::AAA") & (outcomes["target_horizon_days"] == 1)]
    assert ready["status"].iloc[0] == "ready"
    assert ready["close_at_target"].iloc[0] == 110.0
    assert round(float(ready["return_pct"].iloc[0]), 4) == 10.0

    pending = outcomes.loc[(outcomes["event_id"] == "2026-04-09::Momentum Core::AAA") & (outcomes["target_horizon_days"] == 5)]
    assert pending["status"].iloc[0] == "pending"
