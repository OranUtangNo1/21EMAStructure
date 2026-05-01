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

FORWARD_HORIZONS = (1, 5, 10, 20)


@dataclass(slots=True)
class PresetEffectivenessSyncResult:
    tracking_db_path: str
    detection_count: int
    new_detection_count: int
    updated_detection_count: int
    closed_detection_count: int
    scan_hit_count: int
    active_detection_count: int
    missing_hit_close_count: int
    missing_close_1d_count: int
    missing_close_5d_count: int
    filled_return_1d_count: int
    filled_return_5d_count: int


@dataclass(slots=True)
class TrackingPriceRefreshResult:
    tracking_db_path: str
    detection_count: int
    updated_detection_count: int
    closed_detection_count: int
    active_detection_count: int
    missing_hit_close_count: int
    missing_close_1d_count: int
    missing_close_5d_count: int
    filled_return_1d_count: int
    filled_return_5d_count: int


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
        updated_detection_count, closed_detection_count = _update_detection_returns(
            tracking_conn,
            trade_date,
            _load_tracking_price_histories(
                config_path,
                _tickers_due_for_detection_update(tracking_conn, trade_date),
                root_dir=root_dir,
            ),
        )
        tracking_conn.commit()
        detection_count = _count_rows(tracking_conn, "detection")
        tracking_health = _tracking_health_counts(tracking_conn)
    finally:
        tracking_conn.close()

    return PresetEffectivenessSyncResult(
        tracking_db_path=tracking_db_path,
        detection_count=detection_count,
        new_detection_count=new_detection_count,
        updated_detection_count=updated_detection_count,
        closed_detection_count=closed_detection_count,
        scan_hit_count=scan_hit_count,
        active_detection_count=tracking_health["active_detection_count"],
        missing_hit_close_count=tracking_health["missing_hit_close_count"],
        missing_close_1d_count=tracking_health["missing_close_1d_count"],
        missing_close_5d_count=tracking_health["missing_close_5d_count"],
        filled_return_1d_count=tracking_health["filled_return_1d_count"],
        filled_return_5d_count=tracking_health["filled_return_5d_count"],
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
        updated_detection_count, closed_detection_count = _update_detection_returns(
            tracking_conn,
            current_trade_date,
            _load_tracking_price_histories(
                config_path,
                _tickers_due_for_detection_update(tracking_conn, current_trade_date),
                root_dir=root_dir,
            ),
        )
        tracking_conn.commit()
        detection_count = _count_rows(tracking_conn, "detection")
        tracking_health = _tracking_health_counts(tracking_conn)
    finally:
        tracking_conn.close()
    return TrackingPriceRefreshResult(
        tracking_db_path=tracking_db_path,
        detection_count=detection_count,
        updated_detection_count=updated_detection_count,
        closed_detection_count=closed_detection_count,
        active_detection_count=tracking_health["active_detection_count"],
        missing_hit_close_count=tracking_health["missing_hit_close_count"],
        missing_close_1d_count=tracking_health["missing_close_1d_count"],
        missing_close_5d_count=tracking_health["missing_close_5d_count"],
        filled_return_1d_count=tracking_health["filled_return_1d_count"],
        filled_return_5d_count=tracking_health["filled_return_5d_count"],
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
    row = conn.execute(
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
    return {
        "active_detection_count": int(row["active_detection_count"] or 0),
        "missing_hit_close_count": int(row["missing_hit_close_count"] or 0),
        "missing_close_1d_count": int(row["missing_close_1d_count"] or 0),
        "missing_close_5d_count": int(row["missing_close_5d_count"] or 0),
        "filled_return_1d_count": int(row["filled_return_1d_count"] or 0),
        "filled_return_5d_count": int(row["filled_return_5d_count"] or 0),
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
            return_1d,
            return_5d,
            return_10d,
            return_20d
        FROM detection
        WHERE status = 'active'
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
            hit_date,
            ticker,
            close_at_hit,
            close_at_1d,
            close_at_5d,
            close_at_10d,
            close_at_20d,
            return_1d,
            return_5d,
            return_10d,
            return_20d,
            max_gain_20d,
            max_drawdown_20d,
            closed_above_ema21_5d,
            hit_new_high_20d
        FROM detection
        WHERE status = 'active'
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
        if not updates:
            continue
        assignments = ", ".join(f"{column_name} = ?" for column_name in updates)
        values = [*updates.values(), int(row["id"])]
        conn.execute(f"UPDATE detection SET {assignments} WHERE id = ?", values)
        updated_detection_count += 1
        if row["return_20d"] is not None or "return_20d" in updates:
            conn.execute(
                "UPDATE detection SET status = 'closed', closed_at = ? WHERE id = ?",
                (pd.Timestamp(trade_date).date().isoformat(), int(row["id"])),
            )
            closed_detection_count += 1
    return updated_detection_count, closed_detection_count


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
    working = _normalized_price_history(history)
    if working.empty:
        return {"max_gain_20d": None, "max_drawdown_20d": None, "hit_new_high_20d": None}
    target_row = _row_on_or_after(working, target_20d)
    if target_row is None:
        return {"max_gain_20d": None, "max_drawdown_20d": None, "hit_new_high_20d": None}
    end_date = pd.Timestamp(target_row.name).normalize()
    window = working.loc[(working.index.normalize() > hit_date.normalize()) & (working.index.normalize() <= end_date)].copy()
    if window.empty:
        return {"max_gain_20d": None, "max_drawdown_20d": None, "hit_new_high_20d": None}

    high_column = "high" if "high" in window.columns else "close" if "close" in window.columns else None
    low_column = "low" if "low" in window.columns else "close" if "close" in window.columns else None
    if high_column is None or low_column is None:
        return {"max_gain_20d": None, "max_drawdown_20d": None, "hit_new_high_20d": None}

    max_high = _to_float(window[high_column].max())
    min_low = _to_float(window[low_column].min())
    prior_window = working.loc[working.index.normalize() <= hit_date.normalize()].tail(20)
    prior_high = _to_float(prior_window[high_column].max()) if high_column in prior_window.columns and not prior_window.empty else None
    return {
        "max_gain_20d": ((max_high / close_at_hit) - 1.0) * 100.0 if max_high is not None else None,
        "max_drawdown_20d": ((min_low / close_at_hit) - 1.0) * 100.0 if min_low is not None else None,
        "hit_new_high_20d": (max_high > prior_high) if max_high is not None and prior_high is not None else None,
    }


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
