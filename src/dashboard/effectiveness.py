from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

import pandas as pd
from pandas.tseries.offsets import BDay

from src.configuration import load_settings
from src.dashboard.watchlist import WatchlistViewModelBuilder
from src.data.cache import CacheLayer
from src.data.tracking_db import connect_tracking_db
from src.data.providers import YFinancePriceDataProvider
from src.pipeline import PlatformArtifacts
from src.scan.rules import ScanConfig, annotation_filter_column_name

FORWARD_HORIZONS = (1, 5, 10, 20, 21)


@dataclass(slots=True)
class PresetEffectivenessSyncResult:
    tracking_db_path: str
    detection_count: int
    new_detection_count: int
    updated_detection_count: int
    closed_detection_count: int
    signal_entry_event_count: int
    updated_signal_entry_event_count: int
    scan_hit_count: int
    active_detection_count: int
    pending_signal_entry_event_count: int
    missing_hit_close_count: int
    missing_close_1d_count: int
    missing_close_5d_count: int
    filled_return_1d_count: int
    filled_return_5d_count: int
    filled_signal_event_return_5d_count: int
    filled_signal_event_outcome_count: int


@dataclass(slots=True)
class TrackingPriceRefreshResult:
    tracking_db_path: str
    detection_count: int
    updated_detection_count: int
    closed_detection_count: int
    signal_entry_event_count: int
    updated_signal_entry_event_count: int
    active_detection_count: int
    pending_signal_entry_event_count: int
    missing_hit_close_count: int
    missing_close_1d_count: int
    missing_close_5d_count: int
    filled_return_1d_count: int
    filled_return_5d_count: int
    filled_signal_event_return_5d_count: int
    filled_signal_event_outcome_count: int


def sync_preset_effectiveness_logs(
    config_path: str,
    artifacts: PlatformArtifacts,
    *,
    root_dir: Path | None = None,
    register_detections: bool = True,
) -> PresetEffectivenessSyncResult | None:
    trade_date = _latest_trade_date(artifacts)
    if trade_date is None:
        return None

    settings = load_settings(config_path)
    scan_config = ScanConfig.from_dict(settings.get("scan", {}))
    export_presets = [preset for preset in scan_config.watchlist_presets if preset.export_enabled]
    builder = WatchlistViewModelBuilder(scan_config)

    scan_hits = artifacts.scan_hits.copy() if not artifacts.scan_hits.empty else pd.DataFrame(columns=["ticker", "name", "kind"])
    if not scan_hits.empty and "ticker" in scan_hits.columns:
        scan_hits["ticker"] = scan_hits["ticker"].astype(str).str.upper()
        if "kind" in scan_hits.columns:
            scan_hits = scan_hits.loc[scan_hits["kind"] == "scan"].copy()

    market_label = getattr(artifacts.market_result, "label", None) if artifacts.market_result is not None else None
    tracking_conn = connect_tracking_db(root_dir=root_dir) if root_dir is not None else connect_tracking_db()
    tracking_db_path = str(_tracking_db_path(root_dir))
    scan_hit_count = _insert_scan_hits(tracking_conn, trade_date, scan_hits)
    new_detection_count = 0

    try:
        if register_detections:
            for preset in export_presets:
                filtered_watchlist = builder.filter_by_annotation_filters(
                    artifacts.watchlist,
                    preset.selected_annotation_filters,
                )
                projected_watchlist = builder.apply_selected_scan_metrics(
                    filtered_watchlist,
                    artifacts.scan_hits,
                    min_count=preset.duplicate_threshold,
                    selected_scan_names=preset.selected_scan_names,
                    duplicate_rule=preset.duplicate_rule,
                )
                duplicate_tickers = projected_watchlist.loc[projected_watchlist["duplicate_ticker"].fillna(False)].copy()
                if duplicate_tickers.empty:
                    continue
                for ticker, row in duplicate_tickers.iterrows():
                    ticker_str = str(ticker).upper()
                    matched_hits = sorted(
                        {
                            str(name)
                            for name in scan_hits.loc[
                                (scan_hits["ticker"] == ticker_str) & (scan_hits["name"].isin(preset.selected_scan_names)),
                                "name",
                            ].tolist()
                        }
                    )
                    inserted = _insert_detection(
                        tracking_conn,
                        trade_date=trade_date,
                        preset_name=preset.preset_name,
                        ticker=ticker_str,
                        row=row,
                        market_label=market_label,
                        matched_hits=matched_hits,
                        selected_annotation_filters=preset.selected_annotation_filters,
                    )
                    if inserted:
                        new_detection_count += 1
        price_histories = _load_tracking_price_histories(
            config_path,
            [
                *_tickers_due_for_detection_update(tracking_conn, trade_date),
                *_tickers_due_for_signal_entry_event_update(tracking_conn, trade_date),
            ],
            root_dir=root_dir,
        )
        updated_detection_count, closed_detection_count = _update_detection_returns(
            tracking_conn,
            trade_date,
            price_histories,
        )
        updated_signal_entry_event_count = _update_signal_entry_event_returns(tracking_conn, trade_date, price_histories)
        tracking_conn.commit()
        detection_count = _count_rows(tracking_conn, "detection")
        signal_entry_event_count = _count_rows(tracking_conn, "signal_entry_event")
        tracking_health = _tracking_health_counts(tracking_conn)
    finally:
        tracking_conn.close()

    return PresetEffectivenessSyncResult(
        tracking_db_path=tracking_db_path,
        detection_count=detection_count,
        new_detection_count=new_detection_count,
        updated_detection_count=updated_detection_count,
        closed_detection_count=closed_detection_count,
        signal_entry_event_count=signal_entry_event_count,
        updated_signal_entry_event_count=updated_signal_entry_event_count,
        scan_hit_count=scan_hit_count,
        active_detection_count=tracking_health["active_detection_count"],
        pending_signal_entry_event_count=tracking_health["pending_signal_entry_event_count"],
        missing_hit_close_count=tracking_health["missing_hit_close_count"],
        missing_close_1d_count=tracking_health["missing_close_1d_count"],
        missing_close_5d_count=tracking_health["missing_close_5d_count"],
        filled_return_1d_count=tracking_health["filled_return_1d_count"],
        filled_return_5d_count=tracking_health["filled_return_5d_count"],
        filled_signal_event_return_5d_count=tracking_health["filled_signal_event_return_5d_count"],
        filled_signal_event_outcome_count=tracking_health["filled_signal_event_outcome_count"],
    )


def refresh_tracking_detection_prices(
    config_path: str,
    *,
    root_dir: Path | None = None,
    trade_date: str | pd.Timestamp | None = None,
) -> TrackingPriceRefreshResult:
    current_trade_date = pd.Timestamp(trade_date).normalize() if trade_date is not None else pd.Timestamp.today().normalize()
    tracking_conn = connect_tracking_db(root_dir=root_dir) if root_dir is not None else connect_tracking_db()
    tracking_db_path = str(_tracking_db_path(root_dir))
    try:
        price_histories = _load_tracking_price_histories(
            config_path,
            [
                *_tickers_due_for_detection_update(tracking_conn, current_trade_date),
                *_tickers_due_for_signal_entry_event_update(tracking_conn, current_trade_date),
            ],
            root_dir=root_dir,
        )
        updated_detection_count, closed_detection_count = _update_detection_returns(
            tracking_conn,
            current_trade_date,
            price_histories,
        )
        updated_signal_entry_event_count = _update_signal_entry_event_returns(
            tracking_conn,
            current_trade_date,
            price_histories,
        )
        tracking_conn.commit()
        detection_count = _count_rows(tracking_conn, "detection")
        signal_entry_event_count = _count_rows(tracking_conn, "signal_entry_event")
        tracking_health = _tracking_health_counts(tracking_conn)
    finally:
        tracking_conn.close()
    return TrackingPriceRefreshResult(
        tracking_db_path=tracking_db_path,
        detection_count=detection_count,
        updated_detection_count=updated_detection_count,
        closed_detection_count=closed_detection_count,
        signal_entry_event_count=signal_entry_event_count,
        updated_signal_entry_event_count=updated_signal_entry_event_count,
        active_detection_count=tracking_health["active_detection_count"],
        pending_signal_entry_event_count=tracking_health["pending_signal_entry_event_count"],
        missing_hit_close_count=tracking_health["missing_hit_close_count"],
        missing_close_1d_count=tracking_health["missing_close_1d_count"],
        missing_close_5d_count=tracking_health["missing_close_5d_count"],
        filled_return_1d_count=tracking_health["filled_return_1d_count"],
        filled_return_5d_count=tracking_health["filled_return_5d_count"],
        filled_signal_event_return_5d_count=tracking_health["filled_signal_event_return_5d_count"],
        filled_signal_event_outcome_count=tracking_health["filled_signal_event_outcome_count"],
    )


def _latest_trade_date(artifacts: PlatformArtifacts) -> pd.Timestamp | None:
    if artifacts.snapshot.empty or "trade_date" not in artifacts.snapshot.columns:
        return None
    trade_date = pd.to_datetime(artifacts.snapshot["trade_date"], errors="coerce").max()
    if pd.isna(trade_date):
        return None
    return pd.Timestamp(trade_date).normalize()


def _tracking_db_path(root_dir: Path | None) -> Path:
    base = root_dir or Path(__file__).resolve().parents[2]
    return base / "data_runs" / "tracking.db"


def _count_rows(conn: sqlite3.Connection, table_name: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _tracking_health_counts(conn: sqlite3.Connection) -> dict[str, int]:
    detection_row = conn.execute(
        """
        SELECT
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active_detection_count,
            SUM(CASE WHEN status = 'active' AND close_at_hit IS NULL THEN 1 ELSE 0 END) AS missing_hit_close_count,
            SUM(CASE WHEN status = 'active' AND close_at_1d IS NULL THEN 1 ELSE 0 END) AS missing_close_1d_count,
            SUM(CASE WHEN status = 'active' AND close_at_5d IS NULL THEN 1 ELSE 0 END) AS missing_close_5d_count,
            SUM(CASE WHEN return_1d IS NOT NULL THEN 1 ELSE 0 END) AS filled_return_1d_count,
            SUM(CASE WHEN return_5d IS NOT NULL THEN 1 ELSE 0 END) AS filled_return_5d_count
        FROM detection
        """
    ).fetchone()
    signal_row = conn.execute(
        """
        SELECT
            SUM(CASE WHEN return_20d IS NULL THEN 1 ELSE 0 END) AS pending_signal_entry_event_count,
            SUM(CASE WHEN return_5d IS NOT NULL THEN 1 ELSE 0 END) AS filled_signal_event_return_5d_count,
            SUM(CASE WHEN first_outcome IS NOT NULL THEN 1 ELSE 0 END) AS filled_signal_event_outcome_count
        FROM signal_entry_event
        """
    ).fetchone()
    return {
        "active_detection_count": int(detection_row["active_detection_count"] or 0),
        "pending_signal_entry_event_count": int(signal_row["pending_signal_entry_event_count"] or 0),
        "missing_hit_close_count": int(detection_row["missing_hit_close_count"] or 0),
        "missing_close_1d_count": int(detection_row["missing_close_1d_count"] or 0),
        "missing_close_5d_count": int(detection_row["missing_close_5d_count"] or 0),
        "filled_return_1d_count": int(detection_row["filled_return_1d_count"] or 0),
        "filled_return_5d_count": int(detection_row["filled_return_5d_count"] or 0),
        "filled_signal_event_return_5d_count": int(signal_row["filled_signal_event_return_5d_count"] or 0),
        "filled_signal_event_outcome_count": int(signal_row["filled_signal_event_outcome_count"] or 0),
    }


def _load_tracking_price_histories(
    config_path: str,
    tickers: list[str],
    *,
    root_dir: Path | None = None,
) -> dict[str, pd.DataFrame]:
    normalized_tickers = list(dict.fromkeys(str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()))
    if not normalized_tickers:
        return {}

    settings = load_settings(config_path)
    app_settings = settings.get("app", {}) if isinstance(settings.get("app", {}), dict) else {}
    data_settings = settings.get("data", {}) if isinstance(settings.get("data", {}), dict) else {}
    root = root_dir or Path(__file__).resolve().parents[2]
    cache_dir = Path(str(app_settings.get("cache_dir", "data_cache"))).expanduser()
    if not cache_dir.is_absolute():
        cache_dir = root / cache_dir
    provider = YFinancePriceDataProvider(
        CacheLayer(cache_dir),
        technical_ttl_hours=int(data_settings.get("technical_cache_ttl_hours", 12)),
        allow_stale_cache_on_failure=bool(data_settings.get("allow_stale_cache_on_failure", True)),
        batch_size=int(data_settings.get("price_batch_size", 80)),
        max_retries=int(data_settings.get("price_max_retries", 3)),
        request_sleep_seconds=float(data_settings.get("price_request_sleep_seconds", 2.0)),
        retry_backoff_multiplier=float(data_settings.get("price_retry_backoff_multiplier", 2.0)),
        incremental_period=data_settings.get("price_incremental_period", "5d"),
    )
    period = str(app_settings.get("price_period", "18mo"))
    try:
        return provider.get_price_history(normalized_tickers, period=period, force_refresh=False).histories
    except RuntimeError:
        return {}


def _insert_scan_hits(conn: sqlite3.Connection, trade_date: pd.Timestamp, scan_hits: pd.DataFrame) -> int:
    if scan_hits.empty:
        return 0
    records = []
    for _, row in scan_hits.iterrows():
        ticker = str(row.get("ticker", "")).strip().upper()
        scan_name = str(row.get("name", "")).strip()
        if not ticker or not scan_name:
            continue
        records.append((trade_date.strftime("%Y-%m-%d"), ticker, scan_name, str(row.get("kind", "")).strip() or None))
    if not records:
        return 0
    conn.executemany(
        "INSERT OR IGNORE INTO scan_hits (hit_date, ticker, scan_name, kind) VALUES (?, ?, ?, ?)",
        records,
    )
    return len(records)


def _insert_detection(
    conn: sqlite3.Connection,
    *,
    trade_date: pd.Timestamp,
    preset_name: str,
    ticker: str,
    row: pd.Series,
    market_label: object,
    matched_hits: list[str],
    selected_annotation_filters: tuple[str, ...],
) -> bool:
    active = conn.execute(
        "SELECT id FROM detection WHERE preset_name = ? AND ticker = ? AND status = 'active' LIMIT 1",
        (preset_name, ticker),
    ).fetchone()
    if active is not None:
        return False
    try:
        cur = conn.execute(
            """
            INSERT INTO detection (
                hit_date, preset_name, ticker, status, market_env, close_at_hit,
                rs21_at_hit, vcs_at_hit, atr_at_hit, hybrid_score_at_hit, duplicate_hit_count
            )
            VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_date.strftime("%Y-%m-%d"),
                preset_name,
                ticker,
                _normalize_market_env(market_label),
                _to_float(row.get("close")),
                _to_float(row.get("rs21")),
                _to_float(row.get("vcs")),
                _to_float(row.get("atr", row.get("atr14", row.get("atr_14")))),
                _to_float(row.get("hybrid_score")),
                _to_int(row.get("selected_scan_hit_count", row.get("scan_hit_count"))),
            ),
        )
    except sqlite3.IntegrityError:
        return False
    detection_id = int(cur.lastrowid)
    conn.executemany(
        "INSERT OR IGNORE INTO detection_scans (detection_id, scan_name) VALUES (?, ?)",
        [(detection_id, scan_name) for scan_name in matched_hits],
    )
    matched_filters = _matched_annotation_filters(row, selected_annotation_filters)
    conn.executemany(
        "INSERT OR IGNORE INTO detection_filters (detection_id, filter_name) VALUES (?, ?)",
        [(detection_id, filter_name) for filter_name in matched_filters],
    )
    return True


def _matched_annotation_filters(row: pd.Series, selected_annotation_filters: tuple[str, ...]) -> list[str]:
    matched = []
    for filter_name in selected_annotation_filters:
        column_name = annotation_filter_column_name(filter_name)
        if bool(row.get(column_name, False)):
            matched.append(filter_name)
    return matched


def _normalize_market_env(label: object) -> str | None:
    if label is None:
        return None
    value = str(label).strip().lower()
    if not value or value == "no data":
        return None
    if value in {"bull", "bullish", "positive"}:
        return "bull"
    if value in {"neutral"}:
        return "neutral"
    if value in {"weak", "negative"}:
        return "weak"
    if value in {"bear", "bearish"}:
        return "bear"
    return value


def _tickers_due_for_detection_update(conn: sqlite3.Connection, trade_date: pd.Timestamp) -> list[str]:
    active_rows = conn.execute(
        """
        SELECT
            ticker,
            hit_date,
            close_at_hit,
            close_at_1d,
            close_at_5d,
            close_at_10d,
            close_at_20d,
            close_at_21d,
            return_1d,
            return_5d,
            return_10d,
            return_20d,
            return_21d
        FROM detection
        WHERE status = 'active'
           OR close_at_21d IS NULL
           OR return_21d IS NULL
        """
    ).fetchall()
    due_tickers: list[str] = []
    current_trade_date = pd.Timestamp(trade_date).normalize()
    for row in active_rows:
        hit_date = pd.to_datetime(row["hit_date"], errors="coerce")
        if pd.isna(hit_date):
            continue
        if row["close_at_hit"] is None and current_trade_date >= pd.Timestamp(hit_date).normalize():
            due_tickers.append(str(row["ticker"]).upper())
            continue
        for horizon in FORWARD_HORIZONS:
            if row[f"close_at_{horizon}d"] is not None and row[f"return_{horizon}d"] is not None:
                continue
            target_date = (pd.Timestamp(hit_date).normalize() + BDay(horizon)).normalize()
            if current_trade_date >= target_date:
                due_tickers.append(str(row["ticker"]).upper())
                break
    return list(dict.fromkeys(due_tickers))


def _tickers_due_for_signal_entry_event_update(conn: sqlite3.Connection, trade_date: pd.Timestamp) -> list[str]:
    event_rows = conn.execute(
        """
        SELECT
            ticker,
            event_date,
            close_at_1d,
            close_at_5d,
            close_at_10d,
            close_at_20d,
            close_at_21d,
            return_1d,
            return_5d,
            return_10d,
            return_20d,
            return_21d,
            hit_sl,
            hit_tp1,
            first_outcome,
            max_gain_20d,
            max_drawdown_20d,
            max_gain_21d,
            max_drawdown_21d
        FROM signal_entry_event
        """
    ).fetchall()
    due_tickers: list[str] = []
    current_trade_date = pd.Timestamp(trade_date).normalize()
    for row in event_rows:
        event_date = pd.to_datetime(row["event_date"], errors="coerce")
        if pd.isna(event_date):
            continue
        normalized_event_date = pd.Timestamp(event_date).normalize()
        if current_trade_date <= normalized_event_date:
            continue
        if row["hit_sl"] is None or row["hit_tp1"] is None or row["first_outcome"] is None:
            due_tickers.append(str(row["ticker"]).upper())
            continue
        for horizon in FORWARD_HORIZONS:
            if row[f"close_at_{horizon}d"] is not None and row[f"return_{horizon}d"] is not None:
                continue
            target_date = (normalized_event_date + BDay(horizon)).normalize()
            if current_trade_date >= target_date:
                due_tickers.append(str(row["ticker"]).upper())
                break
        target_20d = (normalized_event_date + BDay(20)).normalize()
        if current_trade_date >= target_20d and (row["max_gain_20d"] is None or row["max_drawdown_20d"] is None):
            due_tickers.append(str(row["ticker"]).upper())
            continue
        target_21d = (normalized_event_date + BDay(21)).normalize()
        if current_trade_date >= target_21d and (
            row["close_at_21d"] is None
            or row["return_21d"] is None
            or row["max_gain_21d"] is None
            or row["max_drawdown_21d"] is None
        ):
            due_tickers.append(str(row["ticker"]).upper())
    return list(dict.fromkeys(due_tickers))


def _update_detection_returns(
    conn: sqlite3.Connection,
    trade_date: pd.Timestamp,
    price_histories: dict[str, pd.DataFrame],
) -> tuple[int, int]:
    if not price_histories:
        return 0, 0
    active_rows = conn.execute(
        """
        SELECT
            id,
            status,
            hit_date,
            ticker,
            close_at_hit,
            close_at_1d,
            close_at_5d,
            close_at_10d,
            close_at_20d,
            close_at_21d,
            return_1d,
            return_5d,
            return_10d,
            return_20d,
            return_21d,
            max_gain_20d,
            max_drawdown_20d,
            max_gain_21d,
            max_drawdown_21d,
            closed_above_ema21_5d,
            hit_new_high_20d
        FROM detection
        WHERE status = 'active'
           OR close_at_21d IS NULL
           OR return_21d IS NULL
           OR max_gain_21d IS NULL
           OR max_drawdown_21d IS NULL
        """
    ).fetchall()
    updated_detection_count = 0
    closed_detection_count = 0
    for row in active_rows:
        close_at_hit = _to_float(row["close_at_hit"])
        ticker = str(row["ticker"]).upper()
        history = price_histories.get(ticker, pd.DataFrame())
        if history.empty:
            continue
        updates: dict[str, float] = {}
        hit_date = pd.to_datetime(row["hit_date"], errors="coerce")
        if pd.isna(hit_date):
            continue
        current_trade_date = pd.Timestamp(trade_date).normalize()
        normalized_hit_date = pd.Timestamp(hit_date).normalize()
        if close_at_hit is None and current_trade_date >= normalized_hit_date:
            close_at_hit = _close_on_or_after(history, normalized_hit_date)
            if close_at_hit is not None:
                updates["close_at_hit"] = close_at_hit
        if close_at_hit is None or close_at_hit == 0:
            if updates:
                assignments = ", ".join(f"{column_name} = ?" for column_name in updates)
                values = [*updates.values(), int(row["id"])]
                conn.execute(f"UPDATE detection SET {assignments} WHERE id = ?", values)
                updated_detection_count += 1
            continue
        for horizon in FORWARD_HORIZONS:
            price_column_name = f"close_at_{horizon}d"
            return_column_name = f"return_{horizon}d"
            if row[price_column_name] is not None and row[return_column_name] is not None:
                continue
            target_date = (normalized_hit_date + BDay(horizon)).normalize()
            if current_trade_date >= target_date:
                close_at_target = _to_float(row[price_column_name])
                if close_at_target is None:
                    close_at_target = _close_on_or_after(history, target_date)
                if close_at_target is None:
                    continue
                if row[price_column_name] is None:
                    updates[price_column_name] = close_at_target
                if row[return_column_name] is None:
                    updates[return_column_name] = ((close_at_target / close_at_hit) - 1.0) * 100.0
        if row["closed_above_ema21_5d"] is None:
            target_5d = (normalized_hit_date + BDay(5)).normalize()
            if current_trade_date >= target_5d:
                closed_above = _closed_above_ema21_on_or_after(history, target_5d)
                if closed_above is not None:
                    updates["closed_above_ema21_5d"] = float(int(closed_above))
        target_20d = (normalized_hit_date + BDay(20)).normalize()
        if current_trade_date >= target_20d:
            window_stats = _twenty_day_window_stats(history, normalized_hit_date, target_20d, close_at_hit)
            if row["max_gain_20d"] is None and window_stats.get("max_gain_20d") is not None:
                updates["max_gain_20d"] = float(window_stats["max_gain_20d"])
            if row["max_drawdown_20d"] is None and window_stats.get("max_drawdown_20d") is not None:
                updates["max_drawdown_20d"] = float(window_stats["max_drawdown_20d"])
            if row["hit_new_high_20d"] is None and window_stats.get("hit_new_high_20d") is not None:
                updates["hit_new_high_20d"] = float(int(bool(window_stats["hit_new_high_20d"])))
        target_21d = (normalized_hit_date + BDay(21)).normalize()
        if current_trade_date >= target_21d:
            window_stats_21d = _forward_window_stats(
                history,
                normalized_hit_date,
                target_21d,
                close_at_hit,
                prefix="21d",
            )
            if row["max_gain_21d"] is None and window_stats_21d.get("max_gain_21d") is not None:
                updates["max_gain_21d"] = float(window_stats_21d["max_gain_21d"])
            if row["max_drawdown_21d"] is None and window_stats_21d.get("max_drawdown_21d") is not None:
                updates["max_drawdown_21d"] = float(window_stats_21d["max_drawdown_21d"])
        if not updates:
            continue
        assignments = ", ".join(f"{column_name} = ?" for column_name in updates)
        values = [*updates.values(), int(row["id"])]
        conn.execute(f"UPDATE detection SET {assignments} WHERE id = ?", values)
        updated_detection_count += 1
        if row["status"] == "active" and (row["return_20d"] is not None or "return_20d" in updates):
            conn.execute(
                "UPDATE detection SET status = 'closed', closed_at = ? WHERE id = ?",
                (pd.Timestamp(trade_date).date().isoformat(), int(row["id"])),
            )
            closed_detection_count += 1
    return updated_detection_count, closed_detection_count


def _update_signal_entry_event_returns(
    conn: sqlite3.Connection,
    trade_date: pd.Timestamp,
    price_histories: dict[str, pd.DataFrame],
) -> int:
    if not price_histories:
        return 0
    event_rows = conn.execute(
        """
        SELECT
            id,
            event_date,
            ticker,
            entry_price,
            stop_loss,
            tp1,
            close_at_1d,
            close_at_5d,
            close_at_10d,
            close_at_20d,
            close_at_21d,
            return_1d,
            return_5d,
            return_10d,
            return_20d,
            return_21d,
            hit_sl,
            hit_tp1,
            hit_sl_date,
            hit_tp1_date,
            first_outcome,
            first_outcome_date,
            days_to_first_outcome,
            outcome_r,
            max_gain_20d,
            max_drawdown_20d,
            max_gain_21d,
            max_drawdown_21d
        FROM signal_entry_event
        WHERE return_20d IS NULL
           OR return_21d IS NULL
           OR hit_sl IS NULL
           OR hit_tp1 IS NULL
           OR first_outcome IS NULL
           OR max_gain_20d IS NULL
           OR max_drawdown_20d IS NULL
           OR max_gain_21d IS NULL
           OR max_drawdown_21d IS NULL
        """
    ).fetchall()
    updated_event_count = 0
    current_trade_date = pd.Timestamp(trade_date).normalize()
    for row in event_rows:
        ticker = str(row["ticker"]).upper()
        history = price_histories.get(ticker, pd.DataFrame())
        if history.empty:
            continue
        entry_price = _to_float(row["entry_price"])
        if entry_price is None or entry_price == 0:
            continue
        event_date = pd.to_datetime(row["event_date"], errors="coerce")
        if pd.isna(event_date):
            continue
        normalized_event_date = pd.Timestamp(event_date).normalize()
        updates: dict[str, float | int | str | None] = {}

        for horizon in FORWARD_HORIZONS:
            price_column_name = f"close_at_{horizon}d"
            return_column_name = f"return_{horizon}d"
            if row[price_column_name] is not None and row[return_column_name] is not None:
                continue
            target_date = (normalized_event_date + BDay(horizon)).normalize()
            if current_trade_date < target_date:
                continue
            close_at_target = _to_float(row[price_column_name])
            if close_at_target is None:
                close_at_target = _close_on_or_after(history, target_date)
            if close_at_target is None:
                continue
            if row[price_column_name] is None:
                updates[price_column_name] = close_at_target
            if row[return_column_name] is None:
                updates[return_column_name] = ((close_at_target / entry_price) - 1.0) * 100.0

        outcome_stats = _signal_entry_event_window_stats(
            history=history,
            event_date=normalized_event_date,
            current_trade_date=current_trade_date,
            entry_price=entry_price,
            stop_loss=_to_float(row["stop_loss"]),
            tp1=_to_float(row["tp1"]),
        )
        target_20d = (normalized_event_date + BDay(20)).normalize()
        final_outcome_window = current_trade_date >= target_20d
        for column_name in ("hit_sl", "hit_tp1"):
            candidate_hit = outcome_stats.get(column_name)
            existing_hit = _to_int(row[column_name])
            if candidate_hit is None:
                continue
            if int(candidate_hit) == 1 and existing_hit != 1:
                updates[column_name] = 1
            elif final_outcome_window and row[column_name] is None:
                updates[column_name] = int(candidate_hit)
        for column_name in (
            "hit_sl_date",
            "hit_tp1_date",
            "first_outcome",
            "first_outcome_date",
            "days_to_first_outcome",
            "outcome_r",
        ):
            if row[column_name] is None and outcome_stats.get(column_name) is not None:
                updates[column_name] = outcome_stats[column_name]

        if current_trade_date >= target_20d:
            if row["max_gain_20d"] is None and outcome_stats.get("max_gain_20d") is not None:
                updates["max_gain_20d"] = outcome_stats["max_gain_20d"]
            if row["max_drawdown_20d"] is None and outcome_stats.get("max_drawdown_20d") is not None:
                updates["max_drawdown_20d"] = outcome_stats["max_drawdown_20d"]
            if row["first_outcome"] is None and outcome_stats.get("first_outcome") is None:
                close_at_20d = updates.get("close_at_20d", row["close_at_20d"])
                result_r = _result_r(_to_float(close_at_20d), entry_price, _to_float(row["stop_loss"]))
                if close_at_20d is not None:
                    updates["first_outcome"] = "time_20d"
                    updates["first_outcome_date"] = target_20d.date().isoformat()
                    updates["days_to_first_outcome"] = 20
                    updates["outcome_r"] = result_r
        target_21d = (normalized_event_date + BDay(21)).normalize()
        if current_trade_date >= target_21d:
            outcome_stats_21d = _signal_entry_event_window_stats(
                history=history,
                event_date=normalized_event_date,
                current_trade_date=current_trade_date,
                entry_price=entry_price,
                stop_loss=_to_float(row["stop_loss"]),
                tp1=_to_float(row["tp1"]),
                window_days=21,
            )
            if row["max_gain_21d"] is None and outcome_stats_21d.get("max_gain_21d") is not None:
                updates["max_gain_21d"] = outcome_stats_21d["max_gain_21d"]
            if row["max_drawdown_21d"] is None and outcome_stats_21d.get("max_drawdown_21d") is not None:
                updates["max_drawdown_21d"] = outcome_stats_21d["max_drawdown_21d"]

        if not updates:
            continue
        assignments = ", ".join(f"{column_name} = ?" for column_name in updates)
        values = [*updates.values(), int(row["id"])]
        conn.execute(f"UPDATE signal_entry_event SET {assignments} WHERE id = ?", values)
        updated_event_count += 1
    return updated_event_count


def _signal_entry_event_window_stats(
    *,
    history: pd.DataFrame,
    event_date: pd.Timestamp,
    current_trade_date: pd.Timestamp,
    entry_price: float,
    stop_loss: float | None,
    tp1: float | None,
    window_days: int = 20,
) -> dict[str, float | int | str | None]:
    max_gain_key = f"max_gain_{window_days}d"
    max_drawdown_key = f"max_drawdown_{window_days}d"
    working = _normalized_price_history(history)
    if working.empty:
        return {
            "hit_sl": None,
            "hit_tp1": None,
            "hit_sl_date": None,
            "hit_tp1_date": None,
            "first_outcome": None,
            "first_outcome_date": None,
            "days_to_first_outcome": None,
            "outcome_r": None,
            max_gain_key: None,
            max_drawdown_key: None,
        }
    end_date = min(current_trade_date.normalize(), (event_date + BDay(window_days)).normalize())
    window = working.loc[(working.index.normalize() > event_date.normalize()) & (working.index.normalize() <= end_date)].copy()
    if window.empty:
        return {
            "hit_sl": None,
            "hit_tp1": None,
            "hit_sl_date": None,
            "hit_tp1_date": None,
            "first_outcome": None,
            "first_outcome_date": None,
            "days_to_first_outcome": None,
            "outcome_r": None,
            max_gain_key: None,
            max_drawdown_key: None,
        }

    high_column = "high" if "high" in window.columns else "close" if "close" in window.columns else None
    low_column = "low" if "low" in window.columns else "close" if "close" in window.columns else None
    if high_column is None or low_column is None:
        return {
            "hit_sl": None,
            "hit_tp1": None,
            "hit_sl_date": None,
            "hit_tp1_date": None,
            "first_outcome": None,
            "first_outcome_date": None,
            "days_to_first_outcome": None,
            "outcome_r": None,
            max_gain_key: None,
            max_drawdown_key: None,
        }

    low_values = pd.to_numeric(window[low_column], errors="coerce")
    high_values = pd.to_numeric(window[high_column], errors="coerce")
    hit_sl_mask = low_values <= stop_loss if stop_loss is not None else pd.Series(False, index=window.index)
    hit_tp1_mask = high_values >= tp1 if tp1 is not None else pd.Series(False, index=window.index)
    hit_sl_date = _first_mask_date(hit_sl_mask)
    hit_tp1_date = _first_mask_date(hit_tp1_mask)
    first_outcome, first_outcome_date, outcome_r = _first_signal_outcome(
        hit_sl_date=hit_sl_date,
        hit_tp1_date=hit_tp1_date,
    )
    days_to_first_outcome = (
        _business_days_between(event_date, first_outcome_date) if first_outcome_date is not None else None
    )
    max_high = _to_float(window[high_column].max())
    min_low = _to_float(window[low_column].min())
    return {
        "hit_sl": int(hit_sl_date is not None) if stop_loss is not None else None,
        "hit_tp1": int(hit_tp1_date is not None) if tp1 is not None else None,
        "hit_sl_date": hit_sl_date.date().isoformat() if hit_sl_date is not None else None,
        "hit_tp1_date": hit_tp1_date.date().isoformat() if hit_tp1_date is not None else None,
        "first_outcome": first_outcome,
        "first_outcome_date": first_outcome_date.date().isoformat() if first_outcome_date is not None else None,
        "days_to_first_outcome": days_to_first_outcome,
        "outcome_r": outcome_r,
        max_gain_key: ((max_high / entry_price) - 1.0) * 100.0 if max_high is not None else None,
        max_drawdown_key: ((min_low / entry_price) - 1.0) * 100.0 if min_low is not None else None,
    }


def _first_mask_date(mask: pd.Series) -> pd.Timestamp | None:
    matches = mask.loc[mask.fillna(False)]
    if matches.empty:
        return None
    return pd.Timestamp(matches.index[0]).normalize()


def _first_signal_outcome(
    *,
    hit_sl_date: pd.Timestamp | None,
    hit_tp1_date: pd.Timestamp | None,
) -> tuple[str | None, pd.Timestamp | None, float | None]:
    if hit_sl_date is None and hit_tp1_date is None:
        return None, None, None
    if hit_sl_date is not None and hit_tp1_date is not None:
        if hit_sl_date == hit_tp1_date:
            return "ambiguous_same_day", hit_sl_date, -1.0
        if hit_sl_date < hit_tp1_date:
            return "sl", hit_sl_date, -1.0
        return "tp1", hit_tp1_date, 1.0
    if hit_sl_date is not None:
        return "sl", hit_sl_date, -1.0
    return "tp1", hit_tp1_date, 1.0


def _result_r(close_price: float | None, entry_price: float, stop_loss: float | None) -> float | None:
    if close_price is None or stop_loss is None:
        return None
    risk = entry_price - stop_loss
    if risk <= 0:
        return None
    return (close_price - entry_price) / risk


def _business_days_between(start_date: pd.Timestamp, end_date: pd.Timestamp) -> int:
    if end_date.normalize() <= start_date.normalize():
        return 0
    return max(0, len(pd.bdate_range(start_date.normalize(), end_date.normalize())) - 1)


def _close_on_or_after(history: pd.DataFrame, target_date: pd.Timestamp) -> float | None:
    target_row = _row_on_or_after(history, target_date)
    if target_row is None:
        return None
    return _to_float(target_row.get("close"))


def _closed_above_ema21_on_or_after(history: pd.DataFrame, target_date: pd.Timestamp) -> bool | None:
    working = _normalized_price_history(history)
    if working.empty or "close" not in working.columns:
        return None
    working["ema21_close"] = working["close"].astype(float).ewm(span=21, adjust=False).mean()
    target_row = _row_on_or_after(working, target_date)
    if target_row is None:
        return None
    close = _to_float(target_row.get("close"))
    ema21_close = _to_float(target_row.get("ema21_close"))
    if close is None or ema21_close is None:
        return None
    return close > ema21_close


def _twenty_day_window_stats(
    history: pd.DataFrame,
    hit_date: pd.Timestamp,
    target_20d: pd.Timestamp,
    close_at_hit: float,
) -> dict[str, float | bool | None]:
    return _forward_window_stats(history, hit_date, target_20d, close_at_hit, prefix="20d", include_new_high=True)


def _forward_window_stats(
    history: pd.DataFrame,
    hit_date: pd.Timestamp,
    target_date: pd.Timestamp,
    close_at_hit: float,
    *,
    prefix: str,
    include_new_high: bool = False,
) -> dict[str, float | bool | None]:
    working = _normalized_price_history(history)
    max_gain_key = f"max_gain_{prefix}"
    max_drawdown_key = f"max_drawdown_{prefix}"
    new_high_key = f"hit_new_high_{prefix}"
    if working.empty:
        result: dict[str, float | bool | None] = {max_gain_key: None, max_drawdown_key: None}
        if include_new_high:
            result[new_high_key] = None
        return result
    target_row = _row_on_or_after(working, target_date)
    if target_row is None:
        result = {max_gain_key: None, max_drawdown_key: None}
        if include_new_high:
            result[new_high_key] = None
        return result
    end_date = pd.Timestamp(target_row.name).normalize()
    window = working.loc[(working.index.normalize() > hit_date.normalize()) & (working.index.normalize() <= end_date)].copy()
    if window.empty:
        result = {max_gain_key: None, max_drawdown_key: None}
        if include_new_high:
            result[new_high_key] = None
        return result

    high_column = "high" if "high" in window.columns else "close" if "close" in window.columns else None
    low_column = "low" if "low" in window.columns else "close" if "close" in window.columns else None
    if high_column is None or low_column is None:
        result = {max_gain_key: None, max_drawdown_key: None}
        if include_new_high:
            result[new_high_key] = None
        return result

    max_high = _to_float(window[high_column].max())
    min_low = _to_float(window[low_column].min())
    prior_window = working.loc[working.index.normalize() <= hit_date.normalize()].tail(20)
    prior_high = _to_float(prior_window[high_column].max()) if high_column in prior_window.columns and not prior_window.empty else None
    result = {
        max_gain_key: ((max_high / close_at_hit) - 1.0) * 100.0 if max_high is not None else None,
        max_drawdown_key: ((min_low / close_at_hit) - 1.0) * 100.0 if min_low is not None else None,
    }
    if include_new_high:
        result[new_high_key] = (max_high > prior_high) if max_high is not None and prior_high is not None else None
    return result


def _row_on_or_after(history: pd.DataFrame, target_date: pd.Timestamp) -> pd.Series | None:
    working = _normalized_price_history(history)
    if working.empty:
        return None
    target = pd.Timestamp(target_date).normalize()
    candidates = working.loc[working.index.normalize() >= target]
    if candidates.empty:
        return None
    return candidates.iloc[0]


def _normalized_price_history(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty or "close" not in history.columns:
        return pd.DataFrame()
    working = history.copy()
    working.index = pd.to_datetime(working.index, errors="coerce")
    working = working.loc[working.index.notna()].sort_index()
    return working


def _to_int(value: object) -> int | None:
    number = _to_float(value)
    return int(number) if number is not None else None


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
