from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.data.tracking_db import connect_tracking_db
from src.data.tracking_migration import backfill_tracking_db_from_csvs


def test_backfill_tracking_db_keeps_oldest_detection_for_duplicate_preset_ticker(tmp_path: Path) -> None:
    _write_legacy_csvs(tmp_path)

    result = backfill_tracking_db_from_csvs(tmp_path)

    assert result.source_event_count == 3
    assert result.source_outcome_count == 2
    assert result.skipped_duplicate_detection_count == 1
    assert result.inserted_detection_count == 2
    assert result.updated_detection_count == 0
    assert result.inserted_scan_hit_count == 2

    conn = sqlite3.connect(tmp_path / "data_runs" / "tracking.db")
    conn.row_factory = sqlite3.Row
    try:
        detections = conn.execute(
            "SELECT * FROM detection ORDER BY preset_name, ticker"
        ).fetchall()
        momentum = conn.execute(
            """
            SELECT *
            FROM detection
            WHERE preset_name = ? AND ticker = ?
            """,
            ("Momentum Core", "AAA"),
        ).fetchone()
        detection_scans = conn.execute(
            """
            SELECT ds.scan_name
            FROM detection_scans ds
            JOIN detection d ON d.id = ds.detection_id
            WHERE d.preset_name = ? AND d.ticker = ?
            ORDER BY ds.scan_name
            """,
            ("Momentum Core", "AAA"),
        ).fetchall()
        scan_hits = conn.execute("SELECT * FROM scan_hits ORDER BY ticker, scan_name").fetchall()
    finally:
        conn.close()

    assert len(detections) == 2
    assert momentum["hit_date"] == "2026-04-10"
    assert momentum["close_at_hit"] == 100.0
    assert momentum["close_at_1d"] == 105.0
    assert momentum["close_at_20d"] == 122.0
    assert momentum["return_1d"] == 5.0
    assert momentum["return_20d"] == 22.0
    assert momentum["status"] == "closed"
    assert momentum["closed_at"] == "2026-05-08"
    assert [row["scan_name"] for row in detection_scans] == ["21EMA Pattern H", "VCS"]
    assert len(scan_hits) == 2


def test_backfill_tracking_db_updates_existing_newer_detection_to_older_hit_date(tmp_path: Path) -> None:
    _write_legacy_csvs(tmp_path)
    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        conn.execute(
            """
            INSERT INTO detection (
                hit_date, preset_name, ticker, status, close_at_hit
            )
            VALUES (?, ?, ?, 'active', ?)
            """,
            ("2026-04-14", "Momentum Core", "AAA", 120.0),
        )
        conn.commit()
    finally:
        conn.close()

    result = backfill_tracking_db_from_csvs(tmp_path)

    assert result.inserted_detection_count == 1
    assert result.updated_detection_count == 1
    assert result.skipped_duplicate_detection_count == 1

    conn = sqlite3.connect(tmp_path / "data_runs" / "tracking.db")
    conn.row_factory = sqlite3.Row
    try:
        momentum_rows = conn.execute(
            """
            SELECT hit_date, close_at_hit, return_20d, status
            FROM detection
            WHERE preset_name = ? AND ticker = ?
            """,
            ("Momentum Core", "AAA"),
        ).fetchall()
    finally:
        conn.close()

    assert len(momentum_rows) == 1
    assert momentum_rows[0]["hit_date"] == "2026-04-10"
    assert momentum_rows[0]["close_at_hit"] == 100.0
    assert momentum_rows[0]["return_20d"] == 22.0
    assert momentum_rows[0]["status"] == "closed"


def _write_legacy_csvs(root: Path) -> None:
    effectiveness_dir = root / "data_runs" / "preset_effectiveness"
    scan_hits_dir = root / "data_runs" / "scan_hits"
    effectiveness_dir.mkdir(parents=True)
    scan_hits_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "event_id": "old-aaa",
                "trade_date": "2026-04-10",
                "preset_name": "Momentum Core",
                "ticker": "AAA",
                "market_label": "bull",
                "hit_scans": "21EMA Pattern H, VCS",
                "close_at_signal": 100.0,
                "hybrid_score": 91.0,
                "vcs": 68.0,
                "rs21": 88.0,
                "created_at": "2026-04-10T16:00:00",
            },
            {
                "event_id": "new-aaa",
                "trade_date": "2026-04-14",
                "preset_name": "Momentum Core",
                "ticker": "AAA",
                "market_label": "bull",
                "hit_scans": "21EMA Pattern H",
                "close_at_signal": 120.0,
                "hybrid_score": 90.0,
                "vcs": 60.0,
                "rs21": 80.0,
                "created_at": "2026-04-14T16:00:00",
            },
            {
                "event_id": "bbb",
                "trade_date": "2026-04-12",
                "preset_name": "Pullback",
                "ticker": "BBB",
                "market_label": "neutral",
                "hit_scans": "Reclaim",
                "close_at_signal": 50.0,
                "hybrid_score": 75.0,
                "vcs": 55.0,
                "rs21": 65.0,
                "created_at": "2026-04-12T16:00:00",
            },
        ]
    ).to_csv(effectiveness_dir / "events.csv", index=False)
    pd.DataFrame(
        [
            {
                "outcome_id": "old-aaa-1",
                "event_id": "old-aaa",
                "trade_date": "2026-04-10",
                "target_horizon_days": 1,
                "target_date": "2026-04-13",
                "ticker": "AAA",
                "close_at_signal": 100.0,
                "close_at_target": 105.0,
                "return_pct": 5.0,
                "status": "ready",
                "updated_at": "2026-04-13T16:00:00",
            },
            {
                "outcome_id": "old-aaa-20",
                "event_id": "old-aaa",
                "trade_date": "2026-04-10",
                "target_horizon_days": 20,
                "target_date": "2026-05-08",
                "ticker": "AAA",
                "close_at_signal": 100.0,
                "close_at_target": 122.0,
                "return_pct": 22.0,
                "status": "ready",
                "updated_at": "2026-05-08T16:00:00",
            },
        ]
    ).to_csv(effectiveness_dir / "outcomes.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "AAA", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "BBB", "name": "Reclaim", "kind": "scan"},
        ]
    ).to_csv(scan_hits_dir / "20260410.csv", index=False)
