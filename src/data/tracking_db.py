from __future__ import annotations

import sqlite3
from pathlib import Path


DEFAULT_TRACKING_DB_RELATIVE_PATH = Path("data_runs") / "tracking.db"
SCHEMA_PATH = Path(__file__).with_name("tracking_schema.sql")
VIEW_SCHEMA_START = "DROP VIEW IF EXISTS v_detection_detail;"
DETECTION_COLUMN_MIGRATIONS = {
    "close_at_1d": "REAL",
    "close_at_5d": "REAL",
    "close_at_10d": "REAL",
    "close_at_20d": "REAL",
}
SIGNAL_POOL_ENTRY_COLUMN_MIGRATIONS = {
    "preset_sources": "TEXT NOT NULL DEFAULT '[]'",
    "latest_detected_date": "TEXT",
    "detection_count": "INTEGER NOT NULL DEFAULT 1",
    "pool_status": "TEXT NOT NULL DEFAULT 'active'",
    "invalidated_date": "TEXT",
    "invalidated_reason": "TEXT",
    "snapshot_at_detection": "TEXT NOT NULL DEFAULT '{}'",
    "low_since_detection": "REAL",
    "high_since_detection": "REAL",
    "updated_at": "TEXT",
}
SIGNAL_EVALUATION_COLUMN_MIGRATIONS = {
    "signal_version": "TEXT NOT NULL DEFAULT '1.0'",
    "setup_maturity_score": "REAL",
    "timing_score": "REAL",
    "risk_reward_score": "REAL",
    "entry_strength": "REAL",
    "maturity_detail": "TEXT",
    "timing_detail": "TEXT",
    "stop_price": "REAL",
    "reward_target": "REAL",
    "rr_ratio": "REAL",
    "risk_in_atr": "REAL",
    "reward_in_atr": "REAL",
    "stop_adjusted": "INTEGER DEFAULT 0",
}


def resolve_tracking_db_path(
    db_path: str | Path | None = None,
    *,
    root_dir: str | Path | None = None,
) -> Path:
    if db_path is not None:
        return Path(db_path).expanduser().resolve(strict=False)
    base = Path(root_dir).expanduser() if root_dir is not None else Path(__file__).resolve().parents[2]
    return (base / DEFAULT_TRACKING_DB_RELATIVE_PATH).resolve(strict=False)


def connect_tracking_db(
    db_path: str | Path | None = None,
    *,
    root_dir: str | Path | None = None,
    initialize: bool = True,
) -> sqlite3.Connection:
    resolved_path = resolve_tracking_db_path(db_path, root_dir=root_dir)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(resolved_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    if initialize:
        initialize_tracking_db(conn)
    return conn


def initialize_tracking_db(conn: sqlite3.Connection) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    if VIEW_SCHEMA_START in schema:
        table_schema, view_schema = schema.split(VIEW_SCHEMA_START, maxsplit=1)
        conn.executescript(table_schema)
        _ensure_tracking_columns(conn)
        conn.executescript(f"{VIEW_SCHEMA_START}{view_schema}")
    else:
        conn.executescript(schema)
        _ensure_tracking_columns(conn)
    conn.commit()


def _ensure_tracking_columns(conn: sqlite3.Connection) -> None:
    _ensure_table_columns(conn, "detection", DETECTION_COLUMN_MIGRATIONS)
    _ensure_table_columns(conn, "signal_pool_entry", SIGNAL_POOL_ENTRY_COLUMN_MIGRATIONS)
    _ensure_table_columns(conn, "signal_evaluation", SIGNAL_EVALUATION_COLUMN_MIGRATIONS)
    _deduplicate_signal_evaluations(conn)
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_signal_evaluation_unique_day
        ON signal_evaluation(signal_name, ticker, eval_date)
        """
    )


def _ensure_table_columns(
    conn: sqlite3.Connection,
    table_name: str,
    column_migrations: dict[str, str],
) -> None:
    existing_columns = {
        str(row["name"] if isinstance(row, sqlite3.Row) else row[1])
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, column_type in column_migrations.items():
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def _deduplicate_signal_evaluations(conn: sqlite3.Connection) -> None:
    existing_tables = {
        str(row["name"] if isinstance(row, sqlite3.Row) else row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    if "signal_evaluation" not in existing_tables:
        return
    duplicate_groups = conn.execute(
        """
        SELECT signal_name, ticker, eval_date
        FROM signal_evaluation
        GROUP BY signal_name, ticker, eval_date
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    for group in duplicate_groups:
        rows = conn.execute(
            """
            SELECT id
            FROM signal_evaluation
            WHERE signal_name = ? AND ticker = ? AND eval_date = ?
            ORDER BY id DESC
            """,
            (group["signal_name"], group["ticker"], group["eval_date"]),
        ).fetchall()
        if len(rows) <= 1:
            continue
        obsolete_ids = [int(row["id"]) for row in rows[1:]]
        placeholders = ", ".join("?" for _ in obsolete_ids)
        conn.execute(
            f"DELETE FROM signal_evaluation WHERE id IN ({placeholders})",
            obsolete_ids,
        )
