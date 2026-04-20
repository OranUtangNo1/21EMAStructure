from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.tracking_db import connect_tracking_db
from src.data.tracking_repository import (
    read_detection_detail,
    read_detections,
    read_preset_horizon_performance,
    read_preset_overlap,
    read_preset_scan_performance,
    read_preset_summary,
    read_scan_combo_performance,
    read_scan_hits,
    read_scan_hits_for_watchlist,
)


def test_tracking_repository_returns_empty_frames_without_creating_db(tmp_path: Path) -> None:
    frame = read_detections(root_dir=tmp_path)

    assert frame.empty
    assert "preset_name" in frame.columns
    assert not (tmp_path / "data_runs" / "tracking.db").exists()


def test_tracking_repository_reads_detections_and_scan_hits(tmp_path: Path) -> None:
    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        conn.execute(
            """
            INSERT INTO detection (
                hit_date, preset_name, ticker, status, close_at_hit, return_1d
            )
            VALUES (?, ?, ?, 'active', ?, ?)
            """,
            ("2026-04-17", "Momentum Core", "AAA", 100.0, 3.0),
        )
        conn.execute(
            "INSERT INTO scan_hits (hit_date, ticker, scan_name, kind) VALUES (?, ?, ?, ?)",
            ("2026-04-17", "AAA", "21EMA Pattern H", "scan"),
        )
        conn.commit()
    finally:
        conn.close()

    detections = read_detections(root_dir=tmp_path, status="active", ticker="aaa")
    scan_hits = read_scan_hits(root_dir=tmp_path, hit_date="2026-04-17")
    watchlist_hits = read_scan_hits_for_watchlist("2026-04-17", root_dir=tmp_path)

    assert list(detections["ticker"]) == ["AAA"]
    assert detections.loc[0, "return_1d"] == 3.0
    assert list(scan_hits["scan_name"]) == ["21EMA Pattern H"]
    assert list(watchlist_hits.columns) == ["ticker", "kind", "name"]
    assert list(watchlist_hits["name"]) == ["21EMA Pattern H"]


def test_tracking_repository_reads_tracking_views(tmp_path: Path) -> None:
    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        cur1 = conn.execute(
            """
            INSERT INTO detection (
                hit_date, preset_name, ticker, status, market_env,
                close_at_hit, return_1d, return_5d, return_20d, max_gain_20d, max_drawdown_20d
            )
            VALUES (?, ?, ?, 'closed', ?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026-04-17", "Momentum Core", "AAA", "bull", 100.0, 2.0, 5.0, 12.0, 20.0, -4.0),
        )
        cur2 = conn.execute(
            """
            INSERT INTO detection (
                hit_date, preset_name, ticker, status, market_env,
                close_at_hit, return_1d, return_5d, return_20d, max_gain_20d, max_drawdown_20d
            )
            VALUES (?, ?, ?, 'closed', ?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026-04-17", "Pullback", "AAA", "bull", 100.0, -1.0, -2.0, -3.0, 4.0, -8.0),
        )
        cur3 = conn.execute(
            """
            INSERT INTO detection (
                hit_date, preset_name, ticker, status, market_env,
                close_at_hit, return_1d
            )
            VALUES (?, ?, ?, 'active', ?, ?, ?)
            """,
            ("2026-04-17", "Momentum Core", "BBB", "bull", 50.0, 4.0),
        )
        conn.executemany(
            "INSERT INTO detection_scans (detection_id, scan_name) VALUES (?, ?)",
            [
                (int(cur1.lastrowid), "21EMA Pattern H"),
                (int(cur1.lastrowid), "VCS"),
                (int(cur2.lastrowid), "Reclaim"),
                (int(cur3.lastrowid), "21EMA Pattern H"),
            ],
        )
        conn.execute(
            "INSERT INTO detection_filters (detection_id, filter_name) VALUES (?, ?)",
            (int(cur1.lastrowid), "Above EMA21"),
        )
        conn.commit()
    finally:
        conn.close()

    detail = read_detection_detail(root_dir=tmp_path)
    horizon = read_preset_horizon_performance(root_dir=tmp_path)
    scan_performance = read_preset_scan_performance(root_dir=tmp_path)
    summary = read_preset_summary(root_dir=tmp_path)
    combo = read_scan_combo_performance(root_dir=tmp_path)
    overlap = read_preset_overlap(root_dir=tmp_path)

    momentum_detail = detail.loc[(detail["preset_name"] == "Momentum Core") & (detail["ticker"] == "AAA")].iloc[0]
    momentum_1d = horizon.loc[
        (horizon["preset_name"] == "Momentum Core") & (horizon["horizon_days"] == 1)
    ].iloc[0]
    vcs_20d = scan_performance.loc[
        (scan_performance["preset_name"] == "Momentum Core")
        & (scan_performance["scan_name"] == "VCS")
        & (scan_performance["horizon_days"] == 20)
    ].iloc[0]

    assert momentum_detail["hit_scans"] == "21EMA Pattern H, VCS"
    assert momentum_detail["matched_filters"] == "Above EMA21"
    assert int(momentum_1d["detection_count"]) == 2
    assert int(momentum_1d["active_count"]) == 1
    assert int(momentum_1d["closed_count"]) == 1
    assert float(momentum_1d["avg_return_pct"]) == 3.0
    assert int(vcs_20d["detection_count"]) == 1
    assert float(vcs_20d["avg_max_gain_20d"]) == 20.0
    assert set(summary["preset_name"]) == {"Momentum Core", "Pullback"}
    assert "21EMA Pattern H, VCS" in set(combo["scan_combo"])
    assert list(overlap["ticker"]) == ["AAA"]
    assert int(overlap.loc[0, "preset_count"]) == 2
