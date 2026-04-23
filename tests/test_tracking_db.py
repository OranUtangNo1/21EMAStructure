from __future__ import annotations

import sqlite3

from src.data.tracking_db import connect_tracking_db, initialize_tracking_db


def test_tracking_db_initializes_schema(tmp_path) -> None:
    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        views = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'view'"
            ).fetchall()
        }

        assert {"detection", "detection_scans", "detection_filters", "scan_hits"}.issubset(tables)
        detection_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(detection)").fetchall()
        }
        assert {
            "v_detection_detail",
            "v_preset_horizon_performance",
            "v_preset_scan_performance",
            "v_preset_summary",
            "v_scan_combo_performance",
            "v_preset_overlap",
        }.issubset(views)
        assert {"close_at_1d", "close_at_5d", "close_at_10d", "close_at_20d"}.issubset(detection_columns)
        assert (tmp_path / "data_runs" / "tracking.db").exists()
    finally:
        conn.close()


def test_tracking_db_prevents_duplicate_active_detection(tmp_path) -> None:
    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        conn.execute(
            "INSERT INTO detection (hit_date, preset_name, ticker, status) VALUES (?, ?, ?, ?)",
            ("2026-04-17", "Momentum Surge", "AAA", "active"),
        )
        try:
            conn.execute(
                "INSERT INTO detection (hit_date, preset_name, ticker, status) VALUES (?, ?, ?, ?)",
                ("2026-04-20", "Momentum Surge", "AAA", "active"),
            )
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("duplicate active detection should be rejected")
    finally:
        conn.close()


def test_tracking_db_initialization_is_idempotent(tmp_path) -> None:
    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        initialize_tracking_db(conn)
        initialize_tracking_db(conn)
        conn.execute(
            "INSERT INTO scan_hits (hit_date, ticker, scan_name, kind) VALUES (?, ?, ?, ?)",
            ("2026-04-17", "AAA", "21EMA Pattern H", "scan"),
        )
        initialize_tracking_db(conn)
        count = conn.execute("SELECT COUNT(*) FROM scan_hits").fetchone()[0]

        assert count == 1
    finally:
        conn.close()
