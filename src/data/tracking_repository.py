from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.data.tracking_db import resolve_tracking_db_path

DETECTION_COLUMNS = [
    "id",
    "hit_date",
    "preset_name",
    "ticker",
    "status",
    "market_env",
    "close_at_hit",
    "close_at_1d",
    "close_at_5d",
    "close_at_10d",
    "close_at_20d",
    "rs21_at_hit",
    "vcs_at_hit",
    "atr_at_hit",
    "hybrid_score_at_hit",
    "duplicate_hit_count",
    "return_1d",
    "return_5d",
    "return_10d",
    "return_20d",
    "max_gain_20d",
    "max_drawdown_20d",
    "closed_above_ema21_5d",
    "hit_new_high_20d",
    "entered",
    "entry_date",
    "entry_price",
    "closed_at",
    "created_at",
]
SCAN_HIT_COLUMNS = ["hit_date", "ticker", "scan_name", "kind"]
WATCHLIST_SCAN_HIT_COLUMNS = ["ticker", "kind", "name"]
PRESET_SUMMARY_COLUMNS = [
    "preset_name",
    "market_env",
    "detection_count",
    "avg_return_5d",
    "avg_return_20d",
    "win_rate_5d",
    "win_rate_20d",
    "avg_max_gain",
    "avg_max_drawdown",
]
SCAN_COMBO_PERFORMANCE_COLUMNS = [
    "preset_name",
    "scan_combo",
    "detection_count",
    "avg_return_5d",
    "avg_return_20d",
    "win_rate_20d",
    "avg_max_drawdown",
]
PRESET_OVERLAP_COLUMNS = ["hit_date", "ticker", "hit_presets", "preset_count"]
DETECTION_DETAIL_COLUMNS = [
    "detection_id",
    "hit_date",
    "preset_name",
    "ticker",
    "status",
    "market_env",
    "close_at_hit",
    "close_at_1d",
    "close_at_5d",
    "close_at_10d",
    "close_at_20d",
    "rs21_at_hit",
    "vcs_at_hit",
    "atr_at_hit",
    "hybrid_score_at_hit",
    "duplicate_hit_count",
    "return_1d",
    "return_5d",
    "return_10d",
    "return_20d",
    "max_gain_20d",
    "max_drawdown_20d",
    "closed_above_ema21_5d",
    "hit_new_high_20d",
    "entered",
    "entry_date",
    "entry_price",
    "closed_at",
    "created_at",
    "hit_scans",
    "matched_filters",
]
PRESET_HORIZON_PERFORMANCE_COLUMNS = [
    "preset_name",
    "market_env",
    "horizon_days",
    "detection_count",
    "ticker_count",
    "active_count",
    "closed_count",
    "avg_return_pct",
    "min_return_pct",
    "max_return_pct",
    "win_rate",
    "first_hit_date",
    "last_hit_date",
]
PRESET_SCAN_PERFORMANCE_COLUMNS = [
    "preset_name",
    "scan_name",
    "market_env",
    "horizon_days",
    "detection_count",
    "ticker_count",
    "active_count",
    "closed_count",
    "avg_return_pct",
    "min_return_pct",
    "max_return_pct",
    "win_rate",
    "avg_max_gain_20d",
    "avg_max_drawdown_20d",
    "first_hit_date",
    "last_hit_date",
]


def read_detections(
    *,
    root_dir: str | Path | None = None,
    db_path: str | Path | None = None,
    status: str | None = None,
    preset_name: str | None = None,
    ticker: str | None = None,
    hit_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    clauses: list[str] = []
    params: list[object] = []
    if status:
        clauses.append("status = ?")
        params.append(str(status))
    if preset_name:
        clauses.append("preset_name = ?")
        params.append(str(preset_name))
    if ticker:
        clauses.append("ticker = ?")
        params.append(str(ticker).upper())
    if hit_date is not None:
        clauses.append("hit_date = ?")
        params.append(_date_key(hit_date))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return _read_query(
        f"""
        SELECT {', '.join(DETECTION_COLUMNS)}
        FROM detection
        {where}
        ORDER BY hit_date, preset_name, ticker
        """,
        params,
        DETECTION_COLUMNS,
        root_dir=root_dir,
        db_path=db_path,
    )


def read_scan_hits(
    *,
    root_dir: str | Path | None = None,
    db_path: str | Path | None = None,
    hit_date: str | pd.Timestamp | None = None,
    ticker: str | None = None,
    scan_name: str | None = None,
) -> pd.DataFrame:
    clauses: list[str] = []
    params: list[object] = []
    if hit_date is not None:
        clauses.append("hit_date = ?")
        params.append(_date_key(hit_date))
    if ticker:
        clauses.append("ticker = ?")
        params.append(str(ticker).upper())
    if scan_name:
        clauses.append("scan_name = ?")
        params.append(str(scan_name))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return _read_query(
        f"""
        SELECT hit_date, ticker, scan_name, kind
        FROM scan_hits
        {where}
        ORDER BY hit_date, ticker, scan_name
        """,
        params,
        SCAN_HIT_COLUMNS,
        root_dir=root_dir,
        db_path=db_path,
    )


def read_scan_hits_for_watchlist(
    hit_date: str | pd.Timestamp,
    *,
    root_dir: str | Path | None = None,
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    return _read_query(
        """
        SELECT ticker, kind, scan_name AS name
        FROM scan_hits
        WHERE hit_date = ?
        ORDER BY ticker, name
        """,
        [_date_key(hit_date)],
        WATCHLIST_SCAN_HIT_COLUMNS,
        root_dir=root_dir,
        db_path=db_path,
    )


def read_preset_summary(
    *,
    root_dir: str | Path | None = None,
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    return _read_query(
        """
        SELECT preset_name, market_env, detection_count, avg_return_5d, avg_return_20d,
               win_rate_5d, win_rate_20d, avg_max_gain, avg_max_drawdown
        FROM v_preset_summary
        ORDER BY preset_name, market_env
        """,
        [],
        PRESET_SUMMARY_COLUMNS,
        root_dir=root_dir,
        db_path=db_path,
    )


def read_scan_combo_performance(
    *,
    root_dir: str | Path | None = None,
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    return _read_query(
        """
        SELECT preset_name, scan_combo, detection_count, avg_return_5d, avg_return_20d,
               win_rate_20d, avg_max_drawdown
        FROM v_scan_combo_performance
        ORDER BY preset_name, scan_combo
        """,
        [],
        SCAN_COMBO_PERFORMANCE_COLUMNS,
        root_dir=root_dir,
        db_path=db_path,
    )


def read_preset_overlap(
    *,
    root_dir: str | Path | None = None,
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    return _read_query(
        """
        SELECT hit_date, ticker, hit_presets, preset_count
        FROM v_preset_overlap
        ORDER BY ticker
        """,
        [],
        PRESET_OVERLAP_COLUMNS,
        root_dir=root_dir,
        db_path=db_path,
    )


def read_detection_detail(
    *,
    root_dir: str | Path | None = None,
    db_path: str | Path | None = None,
    status: str | None = None,
    preset_name: str | None = None,
    ticker: str | None = None,
) -> pd.DataFrame:
    clauses: list[str] = []
    params: list[object] = []
    if status:
        clauses.append("status = ?")
        params.append(str(status))
    if preset_name:
        clauses.append("preset_name = ?")
        params.append(str(preset_name))
    if ticker:
        clauses.append("ticker = ?")
        params.append(str(ticker).upper())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return _read_query(
        f"""
        SELECT {', '.join(DETECTION_DETAIL_COLUMNS)}
        FROM v_detection_detail
        {where}
        ORDER BY hit_date, preset_name, ticker
        """,
        params,
        DETECTION_DETAIL_COLUMNS,
        root_dir=root_dir,
        db_path=db_path,
    )


def read_preset_horizon_performance(
    *,
    root_dir: str | Path | None = None,
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    return _read_query(
        """
        SELECT preset_name, market_env, horizon_days, detection_count, ticker_count,
               active_count, closed_count, avg_return_pct, min_return_pct,
               max_return_pct, win_rate, first_hit_date, last_hit_date
        FROM v_preset_horizon_performance
        ORDER BY preset_name, market_env, horizon_days
        """,
        [],
        PRESET_HORIZON_PERFORMANCE_COLUMNS,
        root_dir=root_dir,
        db_path=db_path,
    )


def read_preset_scan_performance(
    *,
    root_dir: str | Path | None = None,
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    return _read_query(
        """
        SELECT preset_name, scan_name, market_env, horizon_days, detection_count,
               ticker_count, active_count, closed_count, avg_return_pct,
               min_return_pct, max_return_pct, win_rate, avg_max_gain_20d,
               avg_max_drawdown_20d, first_hit_date, last_hit_date
        FROM v_preset_scan_performance
        ORDER BY preset_name, scan_name, market_env, horizon_days
        """,
        [],
        PRESET_SCAN_PERFORMANCE_COLUMNS,
        root_dir=root_dir,
        db_path=db_path,
    )


def _read_query(
    query: str,
    params: Iterable[object],
    columns: list[str],
    *,
    root_dir: str | Path | None,
    db_path: str | Path | None,
) -> pd.DataFrame:
    resolved_path = resolve_tracking_db_path(db_path, root_dir=root_dir)
    if not resolved_path.exists():
        return pd.DataFrame(columns=columns)
    conn = sqlite3.connect(str(resolved_path))
    try:
        return pd.read_sql_query(query, conn, params=list(params))
    finally:
        conn.close()


def _date_key(value: str | pd.Timestamp) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return str(value)
    return pd.Timestamp(parsed).strftime("%Y-%m-%d")
