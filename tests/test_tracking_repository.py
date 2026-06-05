from __future__ import annotations

from pathlib import Path

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
    read_signal_entry_events,
    read_signal_entry_performance,
    read_signal_evaluations,
    read_signal_pool_entries,
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
                close_at_hit, return_1d, return_5d, return_20d, return_21d,
                max_gain_20d, max_drawdown_20d, max_gain_21d, max_drawdown_21d
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026-04-17", "Momentum Core", "AAA", "closed", "bull", 100.0, 2.0, 5.0, 12.0, 14.0, 20.0, -4.0, 22.0, -5.0),
        )
        cur2 = conn.execute(
            """
            INSERT INTO detection (
                hit_date, preset_name, ticker, status, market_env,
                close_at_hit, return_1d, return_5d, return_20d, return_21d,
                max_gain_20d, max_drawdown_20d, max_gain_21d, max_drawdown_21d
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026-04-17", "Pullback", "AAA", "closed", "bull", 100.0, -1.0, -2.0, -3.0, -4.0, 4.0, -8.0, 5.0, -9.0),
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
    vcs_21d = scan_performance.loc[
        (scan_performance["preset_name"] == "Momentum Core")
        & (scan_performance["scan_name"] == "VCS")
        & (scan_performance["horizon_days"] == 21)
    ].iloc[0]

    assert momentum_detail["hit_scans"] == "21EMA Pattern H, VCS"
    assert momentum_detail["matched_filters"] == "Above EMA21"
    assert int(momentum_1d["detection_count"]) == 2
    assert int(momentum_1d["active_count"]) == 1
    assert int(momentum_1d["closed_count"]) == 1
    assert float(momentum_1d["avg_return_pct"]) == 3.0
    assert int(vcs_20d["detection_count"]) == 1
    assert float(vcs_20d["avg_max_gain_20d"]) == 20.0
    assert float(vcs_21d["avg_return_pct"]) == 14.0
    assert float(vcs_21d["avg_max_gain_21d"]) == 22.0
    assert float(vcs_21d["avg_max_drawdown_21d"]) == -5.0
    assert set(summary["preset_name"]) == {"Momentum Core", "Pullback"}
    assert float(summary.loc[summary["preset_name"] == "Momentum Core", "avg_return_21d"].iloc[0]) == 14.0
    assert "21EMA Pattern H, VCS" in set(combo["scan_combo"])
    assert float(combo.loc[combo["scan_combo"] == "21EMA Pattern H, VCS", "avg_return_21d"].iloc[0]) == 14.0
    assert list(overlap["ticker"]) == ["AAA"]
    assert int(overlap.loc[0, "preset_count"]) == 2


def test_tracking_repository_reads_signal_tracking_tables(tmp_path: Path) -> None:
    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        pool_cur = conn.execute(
            """
            INSERT INTO signal_pool_entry (
                signal_name,
                ticker,
                preset_sources,
                first_detected_date,
                latest_detected_date,
                detection_count,
                pool_status,
                snapshot_at_detection,
                low_since_detection,
                high_since_detection
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "orderly_pullback_entry",
                "AAA",
                "[\"Pullback Trigger\"]",
                "2026-04-17",
                "2026-04-20",
                2,
                "active",
                "{\"close\":100.0}",
                97.5,
                103.0,
            ),
        )
        conn.execute(
            """
            INSERT INTO signal_evaluation (
                pool_entry_id,
                signal_name,
                ticker,
                eval_date,
                signal_version,
                setup_maturity_score,
                timing_score,
                risk_reward_score,
                entry_strength,
                maturity_detail,
                timing_detail,
                stop_price,
                reward_target,
                rr_ratio,
                risk_in_atr,
                reward_in_atr,
                stop_adjusted
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(pool_cur.lastrowid),
                "orderly_pullback_entry",
                "AAA",
                "2026-04-20",
                "1.0",
                70.0,
                80.0,
                60.0,
                72.0,
                "{\"volume_exhaustion\":80.0}",
                "{\"ema_reclaim_event\":100.0}",
                96.0,
                112.0,
                2.0,
                1.0,
                2.5,
                0,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    pool_entries = read_signal_pool_entries(root_dir=tmp_path, signal_name="orderly_pullback_entry", ticker="aaa")
    evaluations = read_signal_evaluations(root_dir=tmp_path, eval_date="2026-04-20")
    events = read_signal_entry_events(root_dir=tmp_path, event_date="2026-04-20")

    assert list(pool_entries["ticker"]) == ["AAA"]
    assert pool_entries.loc[0, "latest_detected_date"] == "2026-04-20"
    assert int(pool_entries.loc[0, "detection_count"]) == 2
    assert float(pool_entries.loc[0, "low_since_detection"]) == 97.5
    assert list(evaluations["signal_version"]) == ["1.0"]
    assert float(evaluations.loc[0, "entry_strength"]) == 72.0
    assert float(evaluations.loc[0, "rr_ratio"]) == 2.0
    assert events.empty
    assert "rr_current" in events.columns


def test_tracking_repository_reads_signal_entry_performance(tmp_path: Path) -> None:
    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        conn.executemany(
            """
            INSERT INTO signal_entry_event (
                signal_name, ticker, event_date, action_bucket, market_env, plan_type,
                entry_price, stop_loss, tp1, return_5d, return_10d, return_21d,
                hit_sl, hit_tp1, first_outcome, days_to_first_outcome, outcome_r,
                max_gain_21d, max_drawdown_21d
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "orderly_pullback_entry",
                    "AAA",
                    "2026-04-20",
                    "Entry Ready",
                    "bull",
                    "Ready Now",
                    100.0,
                    95.0,
                    110.0,
                    3.0,
                    6.0,
                    8.0,
                    0,
                    1,
                    "tp1",
                    4,
                    1.0,
                    12.0,
                    -2.0,
                ),
                (
                    "orderly_pullback_entry",
                    "BBB",
                    "2026-04-21",
                    "Entry Ready",
                    "bull",
                    "Ready Now",
                    100.0,
                    95.0,
                    110.0,
                    -2.0,
                    -3.0,
                    -4.0,
                    1,
                    0,
                    "sl",
                    6,
                    -1.0,
                    2.0,
                    -7.0,
                ),
                (
                    "momentum_acceleration_entry",
                    "CCC",
                    "2026-04-22",
                    "Entry Ready",
                    "weak",
                    "Ready Now",
                    50.0,
                    47.0,
                    56.0,
                    4.0,
                    5.0,
                    5.0,
                    0,
                    0,
                    "time_20d",
                    20,
                    0.5,
                    6.0,
                    -1.0,
                ),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    performance = read_signal_entry_performance(root_dir=tmp_path)

    orderly = performance.loc[
        (performance["signal_name"] == "orderly_pullback_entry")
        & (performance["market_env"] == "bull")
    ].iloc[0]
    momentum = performance.loc[performance["signal_name"] == "momentum_acceleration_entry"].iloc[0]

    assert int(orderly["event_count"]) == 2
    assert int(orderly["ticker_count"]) == 2
    assert float(orderly["avg_return_21d"]) == 2.0
    assert float(orderly["win_rate_21d"]) == 0.5
    assert int(orderly["tp1_count"]) == 1
    assert int(orderly["sl_count"]) == 1
    assert float(orderly["tp1_rate"]) == 0.5
    assert float(orderly["sl_rate"]) == 0.5
    assert float(orderly["avg_outcome_r"]) == 0.0
    assert float(orderly["avg_days_to_first_outcome"]) == 5.0
    assert float(orderly["avg_max_gain_21d"]) == 7.0
    assert float(orderly["avg_max_drawdown_21d"]) == -4.5
    assert int(momentum["timeout_count"]) == 1
