from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import pandas as pd


ACTIVE_POOL_STATUS = "active"
INVALIDATED_POOL_STATUS = "invalidated"
EXPIRED_POOL_STATUS = "expired"
ORPHANED_POOL_STATUS = "orphaned"


@dataclass(frozen=True, slots=True)
class SignalPoolUpsertResult:
    pool_entry_id: int
    action: str


def upsert_signal_pool_entry(
    conn: sqlite3.Connection,
    *,
    signal_name: str,
    ticker: str,
    detected_date: str | pd.Timestamp,
    preset_sources: list[str] | tuple[str, ...],
    snapshot_at_detection: dict[str, Any] | None = None,
) -> SignalPoolUpsertResult:
    normalized_signal_name = str(signal_name).strip()
    normalized_ticker = str(ticker).strip().upper()
    detected_date_key = _date_key(detected_date)
    serialized_sources = _serialize_json(_normalize_text_values(preset_sources))
    serialized_snapshot = _serialize_json(snapshot_at_detection or {})

    active_row = conn.execute(
        """
        SELECT id, preset_sources, detection_count, latest_detected_date, low_since_detection, high_since_detection
        FROM signal_pool_entry
        WHERE signal_name = ? AND ticker = ? AND pool_status = ?
        LIMIT 1
        """,
        (normalized_signal_name, normalized_ticker, ACTIVE_POOL_STATUS),
    ).fetchone()
    if active_row is not None:
        merged_sources = _merge_json_text_lists(active_row["preset_sources"], serialized_sources)
        increment = 0 if str(active_row["latest_detected_date"] or "") == detected_date_key else 1
        low_at_detection = _to_float((snapshot_at_detection or {}).get("low"))
        high_at_detection = _to_float((snapshot_at_detection or {}).get("high"))
        merged_low = _merge_low(active_row["low_since_detection"], low_at_detection)
        merged_high = _merge_high(active_row["high_since_detection"], high_at_detection)
        conn.execute(
            """
            UPDATE signal_pool_entry
            SET preset_sources = ?,
                latest_detected_date = ?,
                detection_count = ?,
                snapshot_at_detection = ?,
                low_since_detection = ?,
                high_since_detection = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                _serialize_json(merged_sources),
                detected_date_key,
                int(active_row["detection_count"] or 0) + increment,
                serialized_snapshot,
                merged_low,
                merged_high,
                int(active_row["id"]),
            ),
        )
        return SignalPoolUpsertResult(pool_entry_id=int(active_row["id"]), action="updated")

    low_at_detection = _to_float((snapshot_at_detection or {}).get("low"))
    high_at_detection = _to_float((snapshot_at_detection or {}).get("high"))
    cur = conn.execute(
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
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
        """,
        (
            normalized_signal_name,
            normalized_ticker,
            serialized_sources,
            detected_date_key,
            detected_date_key,
            ACTIVE_POOL_STATUS,
            serialized_snapshot,
            low_at_detection,
            high_at_detection,
        ),
    )
    return SignalPoolUpsertResult(pool_entry_id=int(cur.lastrowid), action="inserted")


def update_signal_pool_tracking_fields(
    conn: sqlite3.Connection,
    *,
    pool_entry_id: int,
    today_low: float | int | None,
    today_high: float | int | None,
) -> None:
    row = conn.execute(
        """
        SELECT low_since_detection, high_since_detection
        FROM signal_pool_entry
        WHERE id = ?
        LIMIT 1
        """,
        (int(pool_entry_id),),
    ).fetchone()
    if row is None:
        return
    next_low = _merge_low(row["low_since_detection"], today_low)
    next_high = _merge_high(row["high_since_detection"], today_high)
    conn.execute(
        """
        UPDATE signal_pool_entry
        SET low_since_detection = ?,
            high_since_detection = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (next_low, next_high, int(pool_entry_id)),
    )


def transition_signal_pool_entries(
    conn: sqlite3.Connection,
    *,
    signal_name: str | None = None,
    tickers: list[str] | tuple[str, ...] | None = None,
    from_status: str = ACTIVE_POOL_STATUS,
    to_status: str,
    changed_date: str | pd.Timestamp | None = None,
    reason: str | None = None,
) -> int:
    clauses = ["pool_status = ?"]
    params: list[Any] = [from_status]
    if signal_name:
        clauses.append("signal_name = ?")
        params.append(str(signal_name).strip())
    normalized_tickers = [value.upper() for value in _normalize_text_values(tickers or ())]
    if normalized_tickers:
        placeholders = ", ".join("?" for _ in normalized_tickers)
        clauses.append(f"ticker IN ({placeholders})")
        params.extend(normalized_tickers)
    set_fragments = ["pool_status = ?", "updated_at = datetime('now')"]
    set_params: list[Any] = [to_status]
    if to_status == INVALIDATED_POOL_STATUS:
        set_fragments.extend(["invalidated_date = ?", "invalidated_reason = ?"])
        set_params.append(_date_key(changed_date) if changed_date is not None else None)
        set_params.append(str(reason).strip() if reason else None)
    where_clause = " AND ".join(clauses)
    cur = conn.execute(
        f"""
        UPDATE signal_pool_entry
        SET {', '.join(set_fragments)}
        WHERE {where_clause}
        """,
        [*set_params, *params],
    )
    return int(cur.rowcount or 0)


def mark_orphaned_signal_pool_entries(
    conn: sqlite3.Connection,
    *,
    available_preset_names: list[str] | tuple[str, ...],
) -> int:
    available = set(_normalize_text_values(available_preset_names))
    rows = conn.execute(
        """
        SELECT id, preset_sources
        FROM signal_pool_entry
        WHERE pool_status = ?
        """,
        (ACTIVE_POOL_STATUS,),
    ).fetchall()
    orphan_ids: list[int] = []
    for row in rows:
        sources = _deserialize_text_list(row["preset_sources"])
        if sources and not any(source in available for source in sources):
            orphan_ids.append(int(row["id"]))
    if not orphan_ids:
        return 0
    placeholders = ", ".join("?" for _ in orphan_ids)
    cur = conn.execute(
        f"""
        UPDATE signal_pool_entry
        SET pool_status = ?, updated_at = datetime('now')
        WHERE id IN ({placeholders})
        """,
        [ORPHANED_POOL_STATUS, *orphan_ids],
    )
    return int(cur.rowcount or 0)


def insert_signal_evaluation(
    conn: sqlite3.Connection,
    *,
    pool_entry_id: int,
    signal_name: str,
    ticker: str,
    eval_date: str | pd.Timestamp,
    signal_version: str,
    setup_maturity_score: float | None,
    timing_score: float | None,
    risk_reward_score: float | None,
    entry_strength: float | None,
    maturity_detail: dict[str, Any] | None = None,
    timing_detail: dict[str, Any] | None = None,
    stop_price: float | None = None,
    reward_target: float | None = None,
    rr_ratio: float | None = None,
    risk_in_atr: float | None = None,
    reward_in_atr: float | None = None,
    stop_adjusted: bool = False,
) -> int:
    eval_date_key = _date_key(eval_date)
    normalized_signal_name = str(signal_name).strip()
    normalized_ticker = str(ticker).strip().upper()
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
        ON CONFLICT(signal_name, ticker, eval_date)
        DO UPDATE SET
            pool_entry_id = excluded.pool_entry_id,
            signal_version = excluded.signal_version,
            setup_maturity_score = excluded.setup_maturity_score,
            timing_score = excluded.timing_score,
            risk_reward_score = excluded.risk_reward_score,
            entry_strength = excluded.entry_strength,
            maturity_detail = excluded.maturity_detail,
            timing_detail = excluded.timing_detail,
            stop_price = excluded.stop_price,
            reward_target = excluded.reward_target,
            rr_ratio = excluded.rr_ratio,
            risk_in_atr = excluded.risk_in_atr,
            reward_in_atr = excluded.reward_in_atr,
            stop_adjusted = excluded.stop_adjusted
        """,
        (
            int(pool_entry_id),
            normalized_signal_name,
            normalized_ticker,
            eval_date_key,
            str(signal_version).strip(),
            _to_float(setup_maturity_score),
            _to_float(timing_score),
            _to_float(risk_reward_score),
            _to_float(entry_strength),
            _serialize_json(maturity_detail or {}),
            _serialize_json(timing_detail or {}),
            _to_float(stop_price),
            _to_float(reward_target),
            _to_float(rr_ratio),
            _to_float(risk_in_atr),
            _to_float(reward_in_atr),
            1 if stop_adjusted else 0,
        ),
    )
    row = conn.execute(
        """
        SELECT id
        FROM signal_evaluation
        WHERE signal_name = ? AND ticker = ? AND eval_date = ?
        LIMIT 1
        """,
        (normalized_signal_name, normalized_ticker, eval_date_key),
    ).fetchone()
    return int(row["id"] if row is not None else 0)


def _normalize_text_values(values: list[str] | tuple[str, ...]) -> list[str]:
    normalized: list[str] = []
    existing: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        if text not in existing:
            normalized.append(text)
            existing.add(text)
    return normalized


def _merge_json_text_lists(existing_json: str, incoming_json: str) -> list[str]:
    merged = _deserialize_text_list(existing_json)
    seen = set(merged)
    for value in _deserialize_text_list(incoming_json):
        if value not in seen:
            merged.append(value)
            seen.add(value)
    return merged


def _deserialize_text_list(payload: str | None) -> list[str]:
    if not payload:
        return []
    try:
        loaded = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return _normalize_text_values(tuple(str(value) for value in loaded))


def deserialize_snapshot(payload: str | None) -> dict[str, object]:
    if not payload:
        return {}
    try:
        loaded = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _serialize_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True, default=_json_default)


def _json_default(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float):
        return None if pd.isna(value) else value
    try:
        if value is None or pd.isna(value):
            return None
    except TypeError:
        pass
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _date_key(value: str | pd.Timestamp) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return str(value)
    return pd.Timestamp(parsed).strftime("%Y-%m-%d")


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


def _merge_low(existing: object, incoming: object) -> float | None:
    existing_value = _to_float(existing)
    incoming_value = _to_float(incoming)
    if existing_value is None:
        return incoming_value
    if incoming_value is None:
        return existing_value
    return min(existing_value, incoming_value)


def _merge_high(existing: object, incoming: object) -> float | None:
    existing_value = _to_float(existing)
    incoming_value = _to_float(incoming)
    if existing_value is None:
        return incoming_value
    if incoming_value is None:
        return existing_value
    return max(existing_value, incoming_value)
