from __future__ import annotations

from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pandas as pd

from src.dashboard.effectiveness import refresh_tracking_detection_prices, sync_preset_effectiveness_logs
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
            {"ticker": "AAA", "name": "21EMA Pattern H", "kind": "scan"},
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


def test_sync_preset_effectiveness_logs_creates_db_detection_records(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
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
            ]
        ),
        encoding="utf-8",
    )

    result = sync_preset_effectiveness_logs(
        str(config_path),
        _build_artifacts("2026-04-09", close=100.0, market_label="Positive"),
        root_dir=tmp_path,
    )

    assert result is not None
    assert result.new_detection_count == 1
    assert result.updated_detection_count == 0
    assert result.closed_detection_count == 0
    assert result.active_detection_count == 1
    assert result.missing_hit_close_count == 0
    assert not (tmp_path / "data_runs" / "preset_effectiveness" / "events.csv").exists()
    assert not (tmp_path / "data_runs" / "preset_effectiveness" / "outcomes.csv").exists()

    conn = sqlite3.connect(tmp_path / "data_runs" / "tracking.db")
    conn.row_factory = sqlite3.Row
    try:
        detections = conn.execute("SELECT * FROM detection").fetchall()
        scan_hits = conn.execute("SELECT * FROM scan_hits").fetchall()
        detection_scans = conn.execute("SELECT * FROM detection_scans").fetchall()
    finally:
        conn.close()

    assert len(detections) == 1
    assert detections[0]["hit_date"] == "2026-04-09"
    assert detections[0]["preset_name"] == "Momentum Core"
    assert detections[0]["ticker"] == "AAA"
    assert detections[0]["market_env"] == "bull"
    assert detections[0]["close_at_hit"] == 100.0
    assert len(scan_hits) == 2
    assert {row["scan_name"] for row in detection_scans} == {"21EMA Pattern H", "VCS"}


def test_sync_preset_effectiveness_logs_updates_db_returns_from_target_date_history(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
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
            ]
        ),
        encoding="utf-8",
    )

    sync_preset_effectiveness_logs(
        str(config_path),
        _build_artifacts("2026-04-09", close=100.0),
        root_dir=tmp_path,
    )
    history = pd.DataFrame(
        {
            "open": [108.0, 998.0],
            "high": [112.0, 1002.0],
            "low": [107.0, 997.0],
            "close": [110.0, 999.0],
            "adjusted_close": [110.0, 999.0],
            "volume": [1_000_000, 1_100_000],
        },
        index=pd.to_datetime(["2026-04-10", "2026-04-13"]),
    )
    monkeypatch.setattr(
        "src.dashboard.effectiveness._load_tracking_price_histories",
        lambda config_path, tickers, *, root_dir=None: {"AAA": history},
    )
    result = sync_preset_effectiveness_logs(
        str(config_path),
        _build_artifacts("2026-04-10", close=999.0),
        root_dir=tmp_path,
    )

    assert result is not None
    assert result.new_detection_count == 0
    assert result.updated_detection_count == 1
    assert result.filled_return_1d_count == 1

    conn = sqlite3.connect(tmp_path / "data_runs" / "tracking.db")
    conn.row_factory = sqlite3.Row
    try:
        detection = conn.execute(
            "SELECT return_1d, return_5d, status FROM detection WHERE preset_name = ? AND ticker = ?",
            ("Momentum Core", "AAA"),
        ).fetchone()
        detection_count = conn.execute("SELECT COUNT(*) FROM detection").fetchone()[0]
    finally:
        conn.close()
    assert detection_count == 1
    assert round(float(detection["return_1d"]), 4) == 10.0
    assert detection["return_5d"] is None
    assert detection["status"] == "active"


def test_refresh_tracking_detection_prices_fills_missing_hit_and_target_closes(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("scan:\n  watchlist_presets: []\n", encoding="utf-8")

    sync_preset_effectiveness_logs(
        str(config_path),
        _build_artifacts("2026-04-09", close=100.0),
        root_dir=tmp_path,
        register_detections=False,
    )
    conn = sqlite3.connect(tmp_path / "data_runs" / "tracking.db")
    try:
        conn.execute(
            """
            INSERT INTO detection (hit_date, preset_name, ticker, status)
            VALUES (?, ?, ?, 'active')
            """,
            ("2026-04-09", "Backfilled Preset", "AAA"),
        )
        conn.commit()
    finally:
        conn.close()

    dates = pd.bdate_range("2026-04-09", periods=6)
    history = pd.DataFrame(
        {
            "open": [100.0, 110.0, 111.0, 112.0, 113.0, 120.0],
            "high": [101.0, 112.0, 113.0, 114.0, 115.0, 123.0],
            "low": [99.0, 108.0, 109.0, 110.0, 111.0, 118.0],
            "close": [100.0, 110.0, 111.0, 112.0, 113.0, 120.0],
            "adjusted_close": [100.0, 110.0, 111.0, 112.0, 113.0, 120.0],
            "volume": [1_000_000] * 6,
        },
        index=dates,
    )
    monkeypatch.setattr(
        "src.dashboard.effectiveness._load_tracking_price_histories",
        lambda config_path, tickers, *, root_dir=None: {"AAA": history},
    )

    result = refresh_tracking_detection_prices(
        str(config_path),
        root_dir=tmp_path,
        trade_date="2026-04-16",
    )

    assert result.updated_detection_count == 1
    assert result.missing_hit_close_count == 0
    conn = sqlite3.connect(tmp_path / "data_runs" / "tracking.db")
    conn.row_factory = sqlite3.Row
    try:
        detection = conn.execute(
            """
            SELECT close_at_hit, close_at_1d, close_at_5d, return_1d, return_5d, return_10d, status
            FROM detection
            WHERE preset_name = ? AND ticker = ?
            """,
            ("Backfilled Preset", "AAA"),
        ).fetchone()
    finally:
        conn.close()

    assert detection["close_at_hit"] == 100.0
    assert detection["close_at_1d"] == 110.0
    assert detection["close_at_5d"] == 120.0
    assert round(float(detection["return_1d"]), 4) == 10.0
    assert round(float(detection["return_5d"]), 4) == 20.0
    assert detection["return_10d"] is None
    assert detection["status"] == "active"


def test_sync_preset_effectiveness_logs_updates_twenty_day_tracking_metrics(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
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
            ]
        ),
        encoding="utf-8",
    )

    sync_preset_effectiveness_logs(
        str(config_path),
        _build_artifacts("2026-04-09", close=100.0),
        root_dir=tmp_path,
    )
    dates = pd.bdate_range("2026-04-09", periods=21)
    close_values = [100.0, 102.0, 104.0, 106.0, 108.0, 120.0, *([121.0] * 14), 130.0]
    high_values = [105.0, 108.0, 110.0, 112.0, 114.0, 123.0, *([150.0] * 14), 145.0]
    low_values = [98.0, 96.0, 94.0, 92.0, 91.0, 90.0, *([100.0] * 14), 110.0]
    history = pd.DataFrame(
        {
            "open": close_values,
            "high": high_values,
            "low": low_values,
            "close": close_values,
            "adjusted_close": close_values,
            "volume": [1_000_000] * len(dates),
        },
        index=dates,
    )
    monkeypatch.setattr(
        "src.dashboard.effectiveness._load_tracking_price_histories",
        lambda config_path, tickers, *, root_dir=None: {"AAA": history},
    )

    result = sync_preset_effectiveness_logs(
        str(config_path),
        _build_artifacts(dates[-1].strftime("%Y-%m-%d"), close=999.0),
        root_dir=tmp_path,
    )

    assert result is not None
    assert result.updated_detection_count == 1
    assert result.closed_detection_count == 1
    assert result.filled_return_5d_count == 1

    conn = sqlite3.connect(tmp_path / "data_runs" / "tracking.db")
    conn.row_factory = sqlite3.Row
    try:
        detection = conn.execute(
            """
            SELECT
                return_5d,
                return_20d,
                max_gain_20d,
                max_drawdown_20d,
                closed_above_ema21_5d,
                hit_new_high_20d,
                status,
                closed_at
            FROM detection
            WHERE preset_name = ? AND ticker = ?
            """,
            ("Momentum Core", "AAA"),
        ).fetchone()
    finally:
        conn.close()

    assert round(float(detection["return_5d"]), 4) == 20.0
    assert round(float(detection["return_20d"]), 4) == 30.0
    assert round(float(detection["max_gain_20d"]), 4) == 50.0
    assert round(float(detection["max_drawdown_20d"]), 4) == -10.0
    assert detection["closed_above_ema21_5d"] == 1
    assert detection["hit_new_high_20d"] == 1
    assert detection["status"] == "closed"
    assert detection["closed_at"] == dates[-1].date().isoformat()
