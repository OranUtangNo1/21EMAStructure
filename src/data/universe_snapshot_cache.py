from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


@dataclass(frozen=True, slots=True)
class UniverseSnapshotCacheResult:
    snapshot: pd.DataFrame | None
    metadata: dict[str, object] | None
    path: str | None


@dataclass(frozen=True, slots=True)
class UniverseSnapshotCache:
    """TTL cache for universe discovery, separate from durable run outputs."""

    root_dir: str | Path

    def save(self, snapshot: pd.DataFrame, metadata: dict[str, object]) -> Path:
        root = Path(self.root_dir)
        root.mkdir(parents=True, exist_ok=True)
        date_key = datetime.now().strftime("%Y%m%d")
        dated_csv = root / f"{date_key}.csv"
        dated_json = root / f"{date_key}.json"
        latest_csv = root / "latest.csv"
        latest_json = root / "latest.json"
        payload = {
            **metadata,
            "saved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "row_count": int(len(snapshot)),
        }
        normalized = snapshot.copy()
        if "ticker" in normalized.columns:
            normalized["ticker"] = normalized["ticker"].astype(str).str.upper()
        normalized.to_csv(dated_csv, index=False)
        normalized.to_csv(latest_csv, index=False)
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        dated_json.write_text(text, encoding="utf-8", newline="\n")
        latest_json.write_text(text, encoding="utf-8", newline="\n")
        return dated_csv

    def load(self, max_age_days: int | None = None) -> UniverseSnapshotCacheResult:
        root = Path(self.root_dir)
        csv_path = root / "latest.csv"
        json_path = root / "latest.json"
        if not csv_path.exists() or not json_path.exists():
            return UniverseSnapshotCacheResult(None, None, None)
        try:
            metadata = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return UniverseSnapshotCacheResult(None, None, None)
        saved_at = pd.to_datetime(metadata.get("saved_at"), errors="coerce", utc=True)
        if max_age_days is not None and pd.notna(saved_at):
            age = datetime.now().astimezone() - pd.Timestamp(saved_at).to_pydatetime()
            if age > timedelta(days=max_age_days):
                return UniverseSnapshotCacheResult(None, metadata, str(csv_path))
        snapshot = pd.read_csv(csv_path)
        if "ticker" in snapshot.columns:
            snapshot["ticker"] = snapshot["ticker"].astype(str).str.upper()
        return UniverseSnapshotCacheResult(snapshot, metadata, str(csv_path))
