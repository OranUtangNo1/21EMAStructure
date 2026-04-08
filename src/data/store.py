from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.results import RunArtifactsLoadResult, UniverseSnapshotLoadResult


class DataSnapshotStore:
    """Persist per-run research snapshots and reusable universe snapshots."""

    MARKET_FRAME_FILES = {
        "market_snapshot": "market_snapshot.csv",
        "leadership_snapshot": "leadership_snapshot.csv",
        "external_snapshot": "external_snapshot.csv",
        "factors_vs_sp500": "factors_vs_sp500.csv",
    }
    RADAR_FRAME_FILES = {
        "sector_leaders": "radar_sector_leaders.csv",
        "industry_leaders": "radar_industry_leaders.csv",
        "top_daily": "radar_top_daily.csv",
        "top_weekly": "radar_top_weekly.csv",
    }

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
        *,
        scan_hits: pd.DataFrame | None = None,
        market_result: Any | None = None,
        radar_result: Any | None = None,
    ) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.root_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)

        snapshot.to_csv(run_dir / "snapshot.csv", index_label="ticker")
        eligible_snapshot.to_csv(run_dir / "eligible_snapshot.csv", index_label="ticker")
        watchlist.to_csv(run_dir / "watchlist.csv", index_label="ticker")
        fetch_status.to_csv(run_dir / "fetch_status.csv", index=False)
        if scan_hits is not None:
            scan_hits.to_csv(run_dir / "scan_hits.csv", index=False)
        if market_result is not None:
            self._save_market_result(run_dir, market_result)
        if radar_result is not None:
            self._save_radar_result(run_dir, radar_result)
        with (run_dir / "metadata.json").open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle, ensure_ascii=False, indent=2)
        return run_dir

    def load_latest_run(self) -> RunArtifactsLoadResult:
        run_dir = self._latest_run_dir()
        if run_dir is None:
            return RunArtifactsLoadResult(
                path=None,
                metadata=None,
                snapshot=None,
                eligible_snapshot=None,
                watchlist=None,
                fetch_status=None,
                scan_hits=None,
            )

        return RunArtifactsLoadResult(
            path=str(run_dir),
            metadata=self._load_json(run_dir / "metadata.json"),
            snapshot=self._load_indexed_frame(run_dir / "snapshot.csv", index_name="ticker"),
            eligible_snapshot=self._load_indexed_frame(run_dir / "eligible_snapshot.csv", index_name="ticker"),
            watchlist=self._load_indexed_frame(run_dir / "watchlist.csv", index_name="ticker"),
            fetch_status=self._load_frame(run_dir / "fetch_status.csv"),
            scan_hits=self._load_frame(run_dir / "scan_hits.csv"),
            market_metadata=self._load_json(run_dir / "market_result.json"),
            radar_metadata=self._load_json(run_dir / "radar_result.json"),
            market_frames=self._load_named_frames(run_dir, self.MARKET_FRAME_FILES),
            radar_frames=self._load_named_frames(run_dir, self.RADAR_FRAME_FILES),
        )

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

    def _save_market_result(self, run_dir: Path, market_result: Any) -> None:
        payload = {
            "trade_date": market_result.trade_date.isoformat() if market_result.trade_date is not None else None,
            "score": market_result.score,
            "label": market_result.label,
            "score_1d_ago": market_result.score_1d_ago,
            "score_1w_ago": market_result.score_1w_ago,
            "score_1m_ago": market_result.score_1m_ago,
            "score_3m_ago": market_result.score_3m_ago,
            "label_1d_ago": market_result.label_1d_ago,
            "label_1w_ago": market_result.label_1w_ago,
            "label_1m_ago": market_result.label_1m_ago,
            "label_3m_ago": market_result.label_3m_ago,
            "component_scores": dict(market_result.component_scores),
            "breadth_summary": dict(market_result.breadth_summary),
            "performance_overview": dict(market_result.performance_overview),
            "high_vix_summary": dict(market_result.high_vix_summary),
            "vix_close": market_result.vix_close,
            "update_time": market_result.update_time,
        }
        with (run_dir / "market_result.json").open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        for name, filename in self.MARKET_FRAME_FILES.items():
            frame = getattr(market_result, name, pd.DataFrame())
            frame.to_csv(run_dir / filename, index=False)

    def _save_radar_result(self, run_dir: Path, radar_result: Any) -> None:
        payload = {"update_time": radar_result.update_time}
        with (run_dir / "radar_result.json").open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        for name, filename in self.RADAR_FRAME_FILES.items():
            frame = getattr(radar_result, name, pd.DataFrame())
            frame.to_csv(run_dir / filename, index=False)

    def _latest_run_dir(self) -> Path | None:
        candidates = [
            path
            for path in self.root_dir.iterdir()
            if path.is_dir() and path.name != self.universe_dir.name and (path / "metadata.json").exists()
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda value: value.name)

    def _load_frame(self, path: Path) -> pd.DataFrame | None:
        if not path.exists():
            return None
        return pd.read_csv(path)

    def _load_indexed_frame(self, path: Path, index_name: str) -> pd.DataFrame | None:
        if not path.exists():
            return None
        frame = pd.read_csv(path, index_col=0)
        frame.index = frame.index.astype(str)
        frame.index.name = index_name
        return frame

    def _load_json(self, path: Path) -> dict[str, object] | None:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _load_named_frames(self, run_dir: Path, mapping: dict[str, str]) -> dict[str, pd.DataFrame]:
        frames: dict[str, pd.DataFrame] = {}
        for name, filename in mapping.items():
            frame = self._load_frame(run_dir / filename)
            if frame is not None:
                frames[name] = frame
        return frames
