from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


class CacheLayer:
    """Simple file-based cache with optional stale fallback support."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_key(self, key: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", key)

    def _path(self, key: str, suffix: str) -> Path:
        safe_key = self._sanitize_key(key)
        return self.root_dir / f"{safe_key}.{suffix}"

    def _is_fresh_path(self, path: Path, ttl_hours: int) -> bool:
        if not path.exists():
            return False
        modified_at = datetime.fromtimestamp(path.stat().st_mtime)
        return datetime.now() - modified_at <= timedelta(hours=ttl_hours)

    def is_fresh(self, key: str, suffix: str, ttl_hours: int) -> bool:
        return self._is_fresh_path(self._path(key, suffix), ttl_hours)

    def get_modified_at(self, key: str, suffix: str) -> datetime | None:
        path = self._path(key, suffix)
        if not path.exists():
            return None
        return datetime.fromtimestamp(path.stat().st_mtime)

    def load_csv(self, key: str, ttl_hours: int | None = None, allow_stale: bool = False) -> pd.DataFrame | None:
        path = self._path(key, "csv")
        if not path.exists():
            return None
        if ttl_hours is not None and not allow_stale and not self._is_fresh_path(path, ttl_hours):
            return None
        frame = pd.read_csv(path, index_col=0)
        frame.index = frame.index.astype(str)
        frame = frame.loc[~frame.index.isin(["Ticker", "Date", "date"])]
        frame.index = pd.to_datetime(frame.index, errors="coerce")
        frame = frame.loc[frame.index.notna()].copy()
        for column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame.index.name = "date"
        return frame.sort_index()

    def save_csv(self, key: str, frame: pd.DataFrame) -> None:
        path = self._path(key, "csv")
        frame.to_csv(path, index_label="date")

    def load_json(self, key: str, ttl_hours: int | None = None, allow_stale: bool = False) -> dict[str, Any] | None:
        path = self._path(key, "json")
        if not path.exists():
            return None
        if ttl_hours is not None and not allow_stale and not self._is_fresh_path(path, ttl_hours):
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save_json(self, key: str, payload: dict[str, Any]) -> None:
        path = self._path(key, "json")
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
