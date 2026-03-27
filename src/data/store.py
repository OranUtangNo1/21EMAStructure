from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.results import UniverseSnapshotLoadResult


class DataSnapshotStore:
    """Persist per-run research snapshots and reusable universe snapshots."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.universe_dir = self.root_dir / "universe_snapshots"
        self.universe_dir.mkdir(parents=True, exist_ok=True)

    def save_run(
        self,
        snapshot: pd.DataFrame,
        eligible_snapshot: pd.DataFrame,
        watchlist: pd.DataFrame,
        fetch_status: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.root_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)

        snapshot.to_csv(run_dir / "snapshot.csv", index_label="ticker")
        eligible_snapshot.to_csv(run_dir / "eligible_snapshot.csv", index_label="ticker")
        watchlist.to_csv(run_dir / "watchlist.csv", index_label="ticker")
        fetch_status.to_csv(run_dir / "fetch_status.csv", index=False)
        with (run_dir / "metadata.json").open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle, ensure_ascii=False, indent=2)
        return run_dir

    def save_universe_snapshot(self, snapshot: pd.DataFrame, metadata: dict[str, Any]) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = self.universe_dir / f"{timestamp}.csv"
        json_path = self.universe_dir / f"{timestamp}.json"
        latest_csv = self.universe_dir / "latest.csv"
        latest_json = self.universe_dir / "latest.json"

        snapshot.to_csv(csv_path, index=False)
        snapshot.to_csv(latest_csv, index=False)
        payload = {**metadata, "saved_at": datetime.now().isoformat(timespec="seconds"), "row_count": int(len(snapshot))}
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        with latest_json.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return csv_path

    def load_latest_universe_snapshot(self, max_age_days: int | None = None) -> UniverseSnapshotLoadResult:
        csv_path = self.universe_dir / "latest.csv"
        json_path = self.universe_dir / "latest.json"
        if not csv_path.exists() or not json_path.exists():
            return UniverseSnapshotLoadResult(snapshot=None, metadata=None, path=None)

        with json_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)
        saved_at_raw = metadata.get("saved_at")
        if max_age_days is not None and saved_at_raw:
            saved_at = datetime.fromisoformat(str(saved_at_raw))
            if datetime.now() - saved_at > timedelta(days=max_age_days):
                return UniverseSnapshotLoadResult(snapshot=None, metadata=metadata, path=str(csv_path))

        snapshot = pd.read_csv(csv_path)
        if "ticker" in snapshot.columns:
            snapshot["ticker"] = snapshot["ticker"].astype(str).str.upper()
        return UniverseSnapshotLoadResult(snapshot=snapshot, metadata=metadata, path=str(csv_path))
