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
    plan_status: str | None = None,
    plan_type: str | None = None,
    entry_type: str | None = None,
    entry_price: float | None = None,
    current_price: float | None = None,
    entry_zone_low: float | None = None,
    entry_zone_high: float | None = None,
    max_entry_price: float | None = None,
    distance_to_entry_zone_pct: float | None = None,
    stop_loss: float | None = None,
    tp1: float | None = None,
    tp2: str | None = None,
    rr_tp1: float | None = None,
    rr_current: float | None = None,
    rr_ideal: float | None = None,
    tp2_plan: str | None = None,
    trigger_condition: str | None = None,
    plan_verdict: str | None = None,
    plan_reject_codes: str | None = None,
    plan_reject_reason: str | None = None,
    sl_quality: str | None = None,
    sl_source: str | None = None,
    sl_basis: str | None = None,
    sl_safety: str | None = None,
    tp1_source: str | None = None,
    plan_invalidation: str | None = None,
    plan_note: str | None = None,
    plan_detail: str | None = None,
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
            stop_adjusted,
            plan_status,
            plan_type,
            entry_type,
            entry_price,
            current_price,
            entry_zone_low,
            entry_zone_high,
            max_entry_price,
            distance_to_entry_zone_pct,
            stop_loss,
            tp1,
            tp2,
            rr_tp1,
            rr_current,
            rr_ideal,
            tp2_plan,
            trigger_condition,
            plan_verdict,
            plan_reject_codes,
            plan_reject_reason,
            sl_quality,
            sl_source,
            sl_basis,
            sl_safety,
            tp1_source,
            plan_invalidation,
            plan_note,
            plan_detail
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            stop_adjusted = excluded.stop_adjusted,
            plan_status = excluded.plan_status,
            plan_type = excluded.plan_type,
            entry_type = excluded.entry_type,
            entry_price = excluded.entry_price,
            current_price = excluded.current_price,
            entry_zone_low = excluded.entry_zone_low,
            entry_zone_high = excluded.entry_zone_high,
            max_entry_price = excluded.max_entry_price,
            distance_to_entry_zone_pct = excluded.distance_to_entry_zone_pct,
            stop_loss = excluded.stop_loss,
            tp1 = excluded.tp1,
            tp2 = excluded.tp2,
            rr_tp1 = excluded.rr_tp1,
            rr_current = excluded.rr_current,
            rr_ideal = excluded.rr_ideal,
            tp2_plan = excluded.tp2_plan,
            trigger_condition = excluded.trigger_condition,
            plan_verdict = excluded.plan_verdict,
            plan_reject_codes = excluded.plan_reject_codes,
            plan_reject_reason = excluded.plan_reject_reason,
            sl_quality = excluded.sl_quality,
            sl_source = excluded.sl_source,
            sl_basis = excluded.sl_basis,
            sl_safety = excluded.sl_safety,
            tp1_source = excluded.tp1_source,
            plan_invalidation = excluded.plan_invalidation,
            plan_note = excluded.plan_note,
            plan_detail = excluded.plan_detail
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
            _clean_text(plan_status),
            _clean_text(plan_type),
            _clean_text(entry_type),
            _to_float(entry_price),
            _to_float(current_price),
            _to_float(entry_zone_low),
            _to_float(entry_zone_high),
            _to_float(max_entry_price),
            _to_float(distance_to_entry_zone_pct),
            _to_float(stop_loss),
            _to_float(tp1),
            _clean_text(tp2),
            _to_float(rr_tp1),
            _to_float(rr_current),
            _to_float(rr_ideal),
            _clean_text(tp2_plan),
            _clean_text(trigger_condition),
            _clean_text(plan_verdict),
            _clean_text(plan_reject_codes),
            _clean_text(plan_reject_reason),
            _clean_text(sl_quality),
            _clean_text(sl_source),
            _clean_text(sl_basis),
            _clean_text(sl_safety),
            _clean_text(tp1_source),
            _clean_text(plan_invalidation),
            _clean_text(plan_note),
            _clean_text(plan_detail),
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


def insert_signal_entry_event(
    conn: sqlite3.Connection,
    *,
    signal_name: str,
    ticker: str,
    event_date: str | pd.Timestamp,
    source_evaluation_id: int | None,
    plan_type: str | None,
    entry_price: float | None,
    entry_zone_low: float | None,
    entry_zone_high: float | None,
    max_entry_price: float | None,
    stop_loss: float | None,
    tp1: float | None,
    rr_current: float | None,
    rr_ideal: float | None,
    plan_verdict: str | None,
    reject_codes: str | None,
) -> int:
    event_date_key = _date_key(event_date)
    normalized_signal_name = str(signal_name).strip()
    normalized_ticker = str(ticker).strip().upper()
    conn.execute(
        """
        INSERT INTO signal_entry_event (
            signal_name,
            ticker,
            event_date,
            source_evaluation_id,
            plan_type,
            entry_price,
            entry_zone_low,
            entry_zone_high,
            max_entry_price,
            stop_loss,
            tp1,
            rr_current,
            rr_ideal,
            plan_verdict,
            reject_codes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(signal_name, ticker, event_date)
        DO UPDATE SET
            source_evaluation_id = excluded.source_evaluation_id,
            plan_type = excluded.plan_type,
            entry_price = excluded.entry_price,
            entry_zone_low = excluded.entry_zone_low,
            entry_zone_high = excluded.entry_zone_high,
            max_entry_price = excluded.max_entry_price,
            stop_loss = excluded.stop_loss,
            tp1 = excluded.tp1,
            rr_current = excluded.rr_current,
            rr_ideal = excluded.rr_ideal,
            plan_verdict = excluded.plan_verdict,
            reject_codes = excluded.reject_codes
        """,
        (
            normalized_signal_name,
            normalized_ticker,
            event_date_key,
            int(source_evaluation_id) if source_evaluation_id else None,
            _clean_text(plan_type),
            _to_float(entry_price),
            _to_float(entry_zone_low),
            _to_float(entry_zone_high),
            _to_float(max_entry_price),
            _to_float(stop_loss),
            _to_float(tp1),
            _to_float(rr_current),
            _to_float(rr_ideal),
            _clean_text(plan_verdict),
            _clean_text(reject_codes),
        ),
    )
    row = conn.execute(
        """
        SELECT id
        FROM signal_entry_event
        WHERE signal_name = ? AND ticker = ? AND event_date = ?
        LIMIT 1
        """,
        (normalized_signal_name, normalized_ticker, event_date_key),
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


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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
