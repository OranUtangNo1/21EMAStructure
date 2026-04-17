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
        _ensure_detection_columns(conn)
        conn.executescript(f"{VIEW_SCHEMA_START}{view_schema}")
    else:
        conn.executescript(schema)
        _ensure_detection_columns(conn)
    conn.commit()


def _ensure_detection_columns(conn: sqlite3.Connection) -> None:
    existing_columns = {
        str(row["name"] if isinstance(row, sqlite3.Row) else row[1])
        for row in conn.execute("PRAGMA table_info(detection)").fetchall()
    }
    for column_name, column_type in DETECTION_COLUMN_MIGRATIONS.items():
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE detection ADD COLUMN {column_name} {column_type}")
