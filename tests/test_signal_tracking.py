from __future__ import annotations

import json

from src.data.signal_tracking import (
    ACTIVE_POOL_STATUS,
    INVALIDATED_POOL_STATUS,
    ORPHANED_POOL_STATUS,
    insert_signal_evaluation,
    mark_orphaned_signal_pool_entries,
    transition_signal_pool_entries,
    update_signal_pool_tracking_fields,
    upsert_signal_pool_entry,
)
from src.data.tracking_db import connect_tracking_db


def test_signal_pool_upsert_updates_active_entry(tmp_path) -> None:
    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        first = upsert_signal_pool_entry(
            conn,
            signal_name="orderly_pullback_entry",
            ticker="aaa",
            detected_date="2026-04-17",
            preset_sources=["Orderly Pullback"],
            snapshot_at_detection={"close": 100.0, "low": 98.0, "high": 103.0},
        )
        second = upsert_signal_pool_entry(
            conn,
            signal_name="orderly_pullback_entry",
            ticker="AAA",
            detected_date="2026-04-20",
            preset_sources=["Orderly Pullback", "Trend Pullback"],
            snapshot_at_detection={"close": 105.0, "low": 99.0, "high": 107.0},
        )
        row = conn.execute(
            """
            SELECT id, ticker, preset_sources, latest_detected_date, detection_count, snapshot_at_detection,
                   low_since_detection, high_since_detection
            FROM signal_pool_entry
            WHERE signal_name = ? AND ticker = ? AND pool_status = ?
            """,
            ("orderly_pullback_entry", "AAA", ACTIVE_POOL_STATUS),
        ).fetchone()

        assert first.action == "inserted"
        assert second.action == "updated"
        assert int(row["id"]) == first.pool_entry_id == second.pool_entry_id
        assert row["ticker"] == "AAA"
        assert row["latest_detected_date"] == "2026-04-20"
        assert int(row["detection_count"]) == 2
        assert json.loads(row["preset_sources"]) == ["Orderly Pullback", "Trend Pullback"]
        assert json.loads(row["snapshot_at_detection"]) == {"close": 105.0, "high": 107.0, "low": 99.0}
        assert float(row["low_since_detection"]) == 98.0
        assert float(row["high_since_detection"]) == 107.0
    finally:
        conn.close()


def test_signal_pool_tracking_fields_merge_low_and_high(tmp_path) -> None:
    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        pool = upsert_signal_pool_entry(
            conn,
            signal_name="orderly_pullback_entry",
            ticker="AAA",
            detected_date="2026-04-20",
            preset_sources=["Orderly Pullback"],
            snapshot_at_detection={"close": 100.0, "low": 98.0, "high": 103.0},
        )
        update_signal_pool_tracking_fields(conn, pool_entry_id=pool.pool_entry_id, today_low=97.5, today_high=104.0)
        row = conn.execute(
            "SELECT low_since_detection, high_since_detection FROM signal_pool_entry WHERE id = ?",
            (pool.pool_entry_id,),
        ).fetchone()

        assert float(row["low_since_detection"]) == 97.5
        assert float(row["high_since_detection"]) == 104.0
    finally:
        conn.close()


def test_signal_pool_upsert_creates_new_row_after_invalidation(tmp_path) -> None:
    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        first = upsert_signal_pool_entry(
            conn,
            signal_name="orderly_pullback_entry",
            ticker="AAA",
            detected_date="2026-04-17",
            preset_sources=["Orderly Pullback"],
        )
        updated_count = transition_signal_pool_entries(
            conn,
            signal_name="orderly_pullback_entry",
            tickers=["AAA"],
            to_status=INVALIDATED_POOL_STATUS,
            changed_date="2026-04-18",
            reason="close_below_sma50",
        )
        second = upsert_signal_pool_entry(
            conn,
            signal_name="orderly_pullback_entry",
            ticker="AAA",
            detected_date="2026-04-20",
            preset_sources=["Trend Pullback"],
        )
        rows = conn.execute(
            """
            SELECT id, first_detected_date, pool_status, invalidated_reason
            FROM signal_pool_entry
            WHERE signal_name = ? AND ticker = ?
            ORDER BY first_detected_date
            """,
            ("orderly_pullback_entry", "AAA"),
        ).fetchall()

        assert updated_count == 1
        assert first.pool_entry_id != second.pool_entry_id
        assert [row["first_detected_date"] for row in rows] == ["2026-04-17", "2026-04-20"]
        assert rows[0]["pool_status"] == INVALIDATED_POOL_STATUS
        assert rows[0]["invalidated_reason"] == "close_below_sma50"
        assert rows[1]["pool_status"] == ACTIVE_POOL_STATUS
    finally:
        conn.close()


def test_signal_pool_entries_can_be_marked_orphaned(tmp_path) -> None:
    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        upsert_signal_pool_entry(
            conn,
            signal_name="orderly_pullback_entry",
            ticker="AAA",
            detected_date="2026-04-17",
            preset_sources=["Deleted Preset"],
        )
        orphaned_count = mark_orphaned_signal_pool_entries(conn, available_preset_names=["Orderly Pullback"])
        row = conn.execute(
            "SELECT pool_status FROM signal_pool_entry WHERE signal_name = ? AND ticker = ?",
            ("orderly_pullback_entry", "AAA"),
        ).fetchone()

        assert orphaned_count == 1
        assert row["pool_status"] == ORPHANED_POOL_STATUS
    finally:
        conn.close()


def test_signal_evaluation_upsert_updates_same_day_signal(tmp_path) -> None:
    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        pool_entry = upsert_signal_pool_entry(
            conn,
            signal_name="orderly_pullback_entry",
            ticker="AAA",
            detected_date="2026-04-17",
            preset_sources=["Orderly Pullback"],
        )
        first_id = insert_signal_evaluation(
            conn,
            pool_entry_id=pool_entry.pool_entry_id,
            signal_name="orderly_pullback_entry",
            ticker="AAA",
            eval_date="2026-04-20",
            signal_version="1.0",
            setup_maturity_score=70.0,
            timing_score=80.0,
            risk_reward_score=60.0,
            entry_strength=72.0,
            maturity_detail={"volume_exhaustion": 80.0},
            timing_detail={"ema_reclaim_event": 100.0},
            stop_price=96.0,
            reward_target=112.0,
            rr_ratio=2.0,
            risk_in_atr=1.0,
            reward_in_atr=2.5,
            stop_adjusted=False,
        )
        second_id = insert_signal_evaluation(
            conn,
            pool_entry_id=pool_entry.pool_entry_id,
            signal_name="orderly_pullback_entry",
            ticker="AAA",
            eval_date="2026-04-20",
            signal_version="1.1",
            setup_maturity_score=90.0,
            timing_score=85.0,
            risk_reward_score=70.0,
            entry_strength=81.0,
            maturity_detail={"volume_exhaustion": 95.0},
            timing_detail={"ema_reclaim_event": 100.0},
            stop_price=97.0,
            reward_target=114.0,
            rr_ratio=2.4,
            risk_in_atr=0.9,
            reward_in_atr=2.8,
            stop_adjusted=True,
        )
        rows = conn.execute(
            """
            SELECT id, signal_version, setup_maturity_score, entry_strength, stop_adjusted
            FROM signal_evaluation
            WHERE signal_name = ? AND ticker = ? AND eval_date = ?
            """,
            ("orderly_pullback_entry", "AAA", "2026-04-20"),
        ).fetchall()

        assert first_id == second_id
        assert len(rows) == 1
        assert int(rows[0]["id"]) == first_id
        assert rows[0]["signal_version"] == "1.1"
        assert float(rows[0]["setup_maturity_score"]) == 90.0
        assert float(rows[0]["entry_strength"]) == 81.0
        assert int(rows[0]["stop_adjusted"]) == 1
    finally:
        conn.close()
