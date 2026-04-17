from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import sqlite3
from typing import Any

import pandas as pd

from src.data.tracking_db import connect_tracking_db, resolve_tracking_db_path

FORWARD_HORIZONS = (1, 5, 10, 20)


@dataclass(slots=True)
class TrackingBackfillResult:
    tracking_db_path: str
    source_event_count: int
    source_outcome_count: int
    source_scan_hit_count: int
    inserted_detection_count: int
    updated_detection_count: int
    skipped_duplicate_detection_count: int
    inserted_scan_hit_count: int


def backfill_tracking_db_from_csvs(
    root_dir: str | Path | None = None,
    *,
    db_path: str | Path | None = None,
) -> TrackingBackfillResult:
    root = Path(root_dir).expanduser().resolve(strict=False) if root_dir is not None else Path(__file__).resolve().parents[2]
    events_path = root / "data_runs" / "preset_effectiveness" / "events.csv"
    outcomes_path = root / "data_runs" / "preset_effectiveness" / "outcomes.csv"
    scan_hits_dir = root / "data_runs" / "scan_hits"
    resolved_db_path = resolve_tracking_db_path(db_path, root_dir=root)

    events = _read_csv(events_path)
    outcomes = _read_csv(outcomes_path)
    kept_events, skipped_duplicate_count = _oldest_events_by_preset_ticker(events)
    outcome_lookup = _build_outcome_lookup(outcomes)
    scan_hit_records = _legacy_scan_hit_records(scan_hits_dir)

    conn = connect_tracking_db(resolved_db_path, root_dir=root)
    try:
        inserted_detection_count = 0
        updated_detection_count = 0
        for _, event in kept_events.iterrows():
            payload = _detection_payload(event, outcome_lookup.get(_event_key(event.get("event_id")), {}))
            if payload is None:
                continue
            detection_id, action = _upsert_detection_preferring_oldest(conn, payload)
            if action == "inserted":
                inserted_detection_count += 1
            elif action == "updated":
                updated_detection_count += 1
            _replace_detection_scans(conn, detection_id, payload["hit_scans"])

        inserted_scan_hit_count = _insert_scan_hit_records(conn, scan_hit_records)
        conn.commit()
    finally:
        conn.close()

    return TrackingBackfillResult(
        tracking_db_path=str(resolved_db_path),
        source_event_count=int(len(events)),
        source_outcome_count=int(len(outcomes)),
        source_scan_hit_count=int(len(scan_hit_records)),
        inserted_detection_count=inserted_detection_count,
        updated_detection_count=updated_detection_count,
        skipped_duplicate_detection_count=skipped_duplicate_count,
        inserted_scan_hit_count=inserted_scan_hit_count,
    )


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _oldest_events_by_preset_ticker(events: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if events.empty:
        return events.copy(), 0
    required_columns = {"trade_date", "preset_name", "ticker"}
    if not required_columns.issubset(events.columns):
        return events.iloc[0:0].copy(), 0

    working = events.copy()
    working["preset_name"] = working["preset_name"].map(_clean_text)
    working["ticker"] = working["ticker"].map(lambda value: _clean_text(value).upper())
    working["_trade_date"] = pd.to_datetime(working["trade_date"], errors="coerce")
    working["_created_at"] = pd.to_datetime(working.get("created_at"), errors="coerce")
    working = working.loc[
        working["preset_name"].astype(bool)
        & working["ticker"].astype(bool)
        & working["_trade_date"].notna()
    ].copy()
    if working.empty:
        return working, 0

    working = working.sort_values(
        ["preset_name", "ticker", "_trade_date", "_created_at"],
        na_position="last",
    )
    kept = working.drop_duplicates(["preset_name", "ticker"], keep="first").copy()
    return kept, int(len(working) - len(kept))


def _build_outcome_lookup(outcomes: pd.DataFrame) -> dict[str, dict[int, pd.Series]]:
    if outcomes.empty or "event_id" not in outcomes.columns or "target_horizon_days" not in outcomes.columns:
        return {}
    working = outcomes.copy()
    working["_event_key"] = working["event_id"].map(_event_key)
    working["_horizon"] = pd.to_numeric(working["target_horizon_days"], errors="coerce")
    working = working.loc[working["_event_key"].astype(bool) & working["_horizon"].notna()].copy()
    if working.empty:
        return {}

    lookup: dict[str, dict[int, pd.Series]] = {}
    for _, row in working.sort_values(["_event_key", "_horizon"]).iterrows():
        horizon = int(row["_horizon"])
        if horizon not in FORWARD_HORIZONS:
            continue
        lookup.setdefault(str(row["_event_key"]), {}).setdefault(horizon, row)
    return lookup


def _legacy_scan_hit_records(scan_hits_dir: Path) -> list[tuple[str, str, str, str | None]]:
    if not scan_hits_dir.exists():
        return []
    records: list[tuple[str, str, str, str | None]] = []
    for path in sorted(scan_hits_dir.glob("*.csv")):
        hit_date = _date_from_scan_hit_path(path)
        if hit_date is None:
            continue
        frame = _read_csv(path)
        if frame.empty or "ticker" not in frame.columns:
            continue
        scan_name_column = "name" if "name" in frame.columns else "scan_name" if "scan_name" in frame.columns else None
        if scan_name_column is None:
            continue
        for _, row in frame.iterrows():
            ticker = _clean_text(row.get("ticker")).upper()
            scan_name = _clean_text(row.get(scan_name_column))
            if not ticker or not scan_name:
                continue
            records.append((hit_date, ticker, scan_name, _clean_text(row.get("kind")) or None))
    return records


def _date_from_scan_hit_path(path: Path) -> str | None:
    parsed = pd.to_datetime(path.stem, format="%Y%m%d", errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed).date().isoformat()


def _detection_payload(event: pd.Series, outcomes_by_horizon: dict[int, pd.Series]) -> dict[str, Any] | None:
    hit_date = pd.to_datetime(event.get("trade_date"), errors="coerce")
    preset_name = _clean_text(event.get("preset_name"))
    ticker = _clean_text(event.get("ticker")).upper()
    if pd.isna(hit_date) or not preset_name or not ticker:
        return None

    close_at_hit = _to_float(event.get("close_at_signal"))
    if close_at_hit is None:
        close_at_hit = _first_outcome_close_at_signal(outcomes_by_horizon)
    target_closes = {
        horizon: _to_float(outcomes_by_horizon.get(horizon).get("close_at_target")) if outcomes_by_horizon.get(horizon) is not None else None
        for horizon in FORWARD_HORIZONS
    }
    returns = {
        horizon: _return_from_outcome(outcomes_by_horizon.get(horizon), close_at_hit)
        for horizon in FORWARD_HORIZONS
    }
    closed_at = _closed_at_from_outcome(outcomes_by_horizon.get(20), returns[20])
    hit_scans = _split_names(event.get("hit_scans"))
    return {
        "hit_date": pd.Timestamp(hit_date).strftime("%Y-%m-%d"),
        "preset_name": preset_name,
        "ticker": ticker,
        "status": "closed" if returns[20] is not None else "active",
        "market_env": _clean_text(event.get("market_label")) or None,
        "close_at_hit": close_at_hit,
        "close_at_1d": target_closes[1],
        "close_at_5d": target_closes[5],
        "close_at_10d": target_closes[10],
        "close_at_20d": target_closes[20],
        "rs21_at_hit": _to_float(event.get("rs21")),
        "vcs_at_hit": _to_float(event.get("vcs")),
        "atr_at_hit": _to_float(event.get("atr", event.get("atr14", event.get("atr_14")))),
        "hybrid_score_at_hit": _to_float(event.get("hybrid_score")),
        "duplicate_hit_count": len(hit_scans) if hit_scans else None,
        "return_1d": returns[1],
        "return_5d": returns[5],
        "return_10d": returns[10],
        "return_20d": returns[20],
        "closed_at": closed_at,
        "created_at": _clean_text(event.get("created_at")) or None,
        "hit_scans": hit_scans,
    }


def _upsert_detection_preferring_oldest(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
) -> tuple[int, str]:
    existing_rows = conn.execute(
        """
        SELECT id, hit_date, status
        FROM detection
        WHERE preset_name = ? AND ticker = ?
        ORDER BY hit_date ASC, id ASC
        """,
        (payload["preset_name"], payload["ticker"]),
    ).fetchall()
    payload_hit_date = str(payload["hit_date"])
    if not existing_rows:
        return _insert_detection(conn, payload), "inserted"

    older_or_equal = [row for row in existing_rows if str(row["hit_date"]) <= payload_hit_date]
    if older_or_equal:
        return int(older_or_equal[0]["id"]), "skipped"

    active_rows = [row for row in existing_rows if row["status"] == "active"]
    target_row = active_rows[0] if active_rows else existing_rows[0]
    _update_detection_from_payload(conn, int(target_row["id"]), payload)
    return int(target_row["id"]), "updated"


def _insert_detection(conn: sqlite3.Connection, payload: dict[str, Any]) -> int:
    cur = conn.execute(
        """
        INSERT INTO detection (
            hit_date, preset_name, ticker, status, market_env, close_at_hit,
            close_at_1d, close_at_5d, close_at_10d, close_at_20d,
            rs21_at_hit, vcs_at_hit, atr_at_hit, hybrid_score_at_hit,
            duplicate_hit_count, return_1d, return_5d, return_10d, return_20d,
            closed_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
        """,
        (
            payload["hit_date"],
            payload["preset_name"],
            payload["ticker"],
            payload["status"],
            payload["market_env"],
            payload["close_at_hit"],
            payload["close_at_1d"],
            payload["close_at_5d"],
            payload["close_at_10d"],
            payload["close_at_20d"],
            payload["rs21_at_hit"],
            payload["vcs_at_hit"],
            payload["atr_at_hit"],
            payload["hybrid_score_at_hit"],
            payload["duplicate_hit_count"],
            payload["return_1d"],
            payload["return_5d"],
            payload["return_10d"],
            payload["return_20d"],
            payload["closed_at"],
            payload["created_at"],
        ),
    )
    return int(cur.lastrowid)


def _update_detection_from_payload(conn: sqlite3.Connection, detection_id: int, payload: dict[str, Any]) -> None:
    conn.execute(
        """
        UPDATE detection
        SET
            hit_date = ?,
            status = ?,
            market_env = COALESCE(?, market_env),
            close_at_hit = COALESCE(?, close_at_hit),
            close_at_1d = COALESCE(?, close_at_1d),
            close_at_5d = COALESCE(?, close_at_5d),
            close_at_10d = COALESCE(?, close_at_10d),
            close_at_20d = COALESCE(?, close_at_20d),
            rs21_at_hit = COALESCE(?, rs21_at_hit),
            vcs_at_hit = COALESCE(?, vcs_at_hit),
            atr_at_hit = COALESCE(?, atr_at_hit),
            hybrid_score_at_hit = COALESCE(?, hybrid_score_at_hit),
            duplicate_hit_count = COALESCE(?, duplicate_hit_count),
            return_1d = COALESCE(?, return_1d),
            return_5d = COALESCE(?, return_5d),
            return_10d = COALESCE(?, return_10d),
            return_20d = COALESCE(?, return_20d),
            closed_at = COALESCE(?, closed_at),
            created_at = COALESCE(?, created_at)
        WHERE id = ?
        """,
        (
            payload["hit_date"],
            payload["status"],
            payload["market_env"],
            payload["close_at_hit"],
            payload["close_at_1d"],
            payload["close_at_5d"],
            payload["close_at_10d"],
            payload["close_at_20d"],
            payload["rs21_at_hit"],
            payload["vcs_at_hit"],
            payload["atr_at_hit"],
            payload["hybrid_score_at_hit"],
            payload["duplicate_hit_count"],
            payload["return_1d"],
            payload["return_5d"],
            payload["return_10d"],
            payload["return_20d"],
            payload["closed_at"],
            payload["created_at"],
            detection_id,
        ),
    )


def _replace_detection_scans(conn: sqlite3.Connection, detection_id: int, hit_scans: list[str]) -> None:
    if not hit_scans:
        return
    conn.execute("DELETE FROM detection_scans WHERE detection_id = ?", (detection_id,))
    conn.executemany(
        "INSERT OR IGNORE INTO detection_scans (detection_id, scan_name) VALUES (?, ?)",
        [(detection_id, scan_name) for scan_name in hit_scans],
    )


def _insert_scan_hit_records(conn: sqlite3.Connection, records: list[tuple[str, str, str, str | None]]) -> int:
    if not records:
        return 0
    before = conn.total_changes
    conn.executemany(
        "INSERT OR IGNORE INTO scan_hits (hit_date, ticker, scan_name, kind) VALUES (?, ?, ?, ?)",
        records,
    )
    return int(conn.total_changes - before)


def _return_from_outcome(outcome: pd.Series | None, close_at_hit: float | None) -> float | None:
    if outcome is None:
        return None
    return_pct = _to_float(outcome.get("return_pct"))
    if return_pct is not None:
        return return_pct
    target = _to_float(outcome.get("close_at_target"))
    signal = _to_float(outcome.get("close_at_signal"))
    if signal is None:
        signal = close_at_hit
    if signal is None or signal == 0 or target is None:
        return None
    return ((target / signal) - 1.0) * 100.0


def _closed_at_from_outcome(outcome: pd.Series | None, return_20d: float | None) -> str | None:
    if outcome is None or return_20d is None:
        return None
    target_date = pd.to_datetime(outcome.get("target_date"), errors="coerce")
    if pd.isna(target_date):
        return None
    return pd.Timestamp(target_date).date().isoformat()


def _first_outcome_close_at_signal(outcomes_by_horizon: dict[int, pd.Series]) -> float | None:
    for horizon in FORWARD_HORIZONS:
        outcome = outcomes_by_horizon.get(horizon)
        if outcome is None:
            continue
        close_at_signal = _to_float(outcome.get("close_at_signal"))
        if close_at_signal is not None:
            return close_at_signal
    return None


def _split_names(value: object) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def _clean_text(value: object) -> str:
    try:
        if value is None or pd.isna(value):
            return ""
    except TypeError:
        if value is None:
            return ""
    return str(value).strip()


def _event_key(value: object) -> str:
    try:
        if value is None or pd.isna(value):
            return ""
    except TypeError:
        if value is None:
            return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


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


def _main() -> None:
    result = backfill_tracking_db_from_csvs()
    print(asdict(result))


if __name__ == "__main__":
    _main()
