from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

import pandas as pd

from src.data.signal_tracking import (
    ACTIVE_POOL_STATUS,
    EXPIRED_POOL_STATUS,
    INVALIDATED_POOL_STATUS,
    ORPHANED_POOL_STATUS,
    SignalPoolUpsertResult,
    deserialize_snapshot,
    mark_orphaned_signal_pool_entries,
    transition_signal_pool_entries,
    update_signal_pool_tracking_fields,
    upsert_signal_pool_entry,
)
from src.signals.rules import EntrySignalDefinition


@dataclass(frozen=True, slots=True)
class SignalPoolEntry:
    id: int
    signal_name: str
    ticker: str
    preset_sources: tuple[str, ...]
    first_detected_date: pd.Timestamp
    latest_detected_date: pd.Timestamp
    detection_count: int
    pool_status: str
    invalidated_date: pd.Timestamp | None
    invalidated_reason: str | None
    snapshot_at_detection: dict[str, object]
    low_since_detection: float | None
    high_since_detection: float | None


def create_pool_entry(
    conn: sqlite3.Connection,
    *,
    definition: EntrySignalDefinition,
    ticker: str,
    detected_date: str | pd.Timestamp,
    preset_sources: list[str] | tuple[str, ...],
    snapshot: dict[str, object],
) -> SignalPoolUpsertResult:
    return upsert_signal_pool_entry(
        conn,
        signal_name=definition.signal_key,
        ticker=ticker,
        detected_date=detected_date,
        preset_sources=preset_sources,
        snapshot_at_detection=snapshot,
    )


def invalidate_pool_entry(
    conn: sqlite3.Connection,
    *,
    signal_name: str,
    ticker: str,
    changed_date: str | pd.Timestamp,
    reason: str,
) -> int:
    return transition_signal_pool_entries(
        conn,
        signal_name=signal_name,
        tickers=[ticker],
        to_status=INVALIDATED_POOL_STATUS,
        changed_date=changed_date,
        reason=reason,
    )


def expire_pool_entries(
    conn: sqlite3.Connection,
    *,
    signal_name: str,
    tickers: list[str] | tuple[str, ...],
) -> int:
    return transition_signal_pool_entries(
        conn,
        signal_name=signal_name,
        tickers=tickers,
        to_status=EXPIRED_POOL_STATUS,
    )


def orphan_pool_entries(
    conn: sqlite3.Connection,
    *,
    valid_presets: list[str] | tuple[str, ...],
) -> int:
    return mark_orphaned_signal_pool_entries(conn, available_preset_names=valid_presets)


def update_tracking_fields(
    conn: sqlite3.Connection,
    *,
    entry_id: int,
    today_low: float | int | None,
    today_high: float | int | None,
) -> None:
    update_signal_pool_tracking_fields(
        conn,
        pool_entry_id=entry_id,
        today_low=today_low,
        today_high=today_high,
    )


def get_active_pool(
    conn: sqlite3.Connection,
    *,
    signal_name: str,
) -> list[SignalPoolEntry]:
    rows = conn.execute(
        """
        SELECT *
        FROM signal_pool_entry
        WHERE signal_name = ? AND pool_status = ?
        ORDER BY first_detected_date, ticker
        """,
        (signal_name, ACTIVE_POOL_STATUS),
    ).fetchall()
    return [_row_to_pool_entry(row) for row in rows]


def _row_to_pool_entry(row: sqlite3.Row) -> SignalPoolEntry:
    invalidated_date = pd.to_datetime(row["invalidated_date"], errors="coerce")
    return SignalPoolEntry(
        id=int(row["id"]),
        signal_name=str(row["signal_name"]),
        ticker=str(row["ticker"]).upper(),
        preset_sources=tuple(_deserialize_text_list(row["preset_sources"])),
        first_detected_date=pd.Timestamp(row["first_detected_date"]).normalize(),
        latest_detected_date=pd.Timestamp(row["latest_detected_date"]).normalize(),
        detection_count=int(row["detection_count"] or 0),
        pool_status=str(row["pool_status"]),
        invalidated_date=None if pd.isna(invalidated_date) else pd.Timestamp(invalidated_date).normalize(),
        invalidated_reason=str(row["invalidated_reason"]).strip() if row["invalidated_reason"] else None,
        snapshot_at_detection=deserialize_snapshot(row["snapshot_at_detection"]),
        low_since_detection=_to_float(row["low_since_detection"]),
        high_since_detection=_to_float(row["high_since_detection"]),
    )


def _deserialize_text_list(payload: str | None) -> list[str]:
    if not payload:
        return []
    try:
        loaded = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [str(value).strip() for value in loaded if str(value).strip()]


def _to_float(value: object) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
    except TypeError:
        if value is None:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "ACTIVE_POOL_STATUS",
    "EXPIRED_POOL_STATUS",
    "INVALIDATED_POOL_STATUS",
    "ORPHANED_POOL_STATUS",
    "SignalPoolEntry",
    "create_pool_entry",
    "expire_pool_entries",
    "get_active_pool",
    "invalidate_pool_entry",
    "orphan_pool_entries",
    "update_tracking_fields",
]
