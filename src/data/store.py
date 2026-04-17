from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.tracking_repository import read_scan_hits_for_watchlist
from src.data.tracking_db import connect_tracking_db
from src.data.results import RunArtifactsLoadResult, UniverseSnapshotLoadResult


class DataSnapshotStore:
    """Persist daily research artifacts in file-type folders and reusable universe snapshots."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.watchlist_dir = self.root_dir / "watchlist"
        self.market_summary_dir = self.root_dir / "market_summary"
        self.radar_summary_dir = self.root_dir / "radar_summary"
        self.metadata_dir = self.root_dir / "run_metadata"
        self.universe_dir = self.root_dir / "universe_snapshots"
        for directory in [
            self.watchlist_dir,
            self.market_summary_dir,
            self.radar_summary_dir,
            self.metadata_dir,
            self.universe_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

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
        date_key = self._date_key_from_metadata(metadata, snapshot)
        trade_date_iso = self._trade_date_iso(metadata, snapshot)

        watchlist.to_csv(self.watchlist_dir / f"{date_key}.csv", index_label="ticker")
        if scan_hits is not None:
            self._save_scan_hits(date_key, trade_date_iso, scan_hits)
        if market_result is not None:
            self._save_market_result(date_key, market_result)
        if radar_result is not None:
            self._save_radar_result(date_key, radar_result)

        fetch_summary = self._build_fetch_summary(fetch_status)
        metadata_payload = {
            **metadata,
            "trade_date": trade_date_iso,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "date_key": date_key,
            "watchlist_count": int(len(watchlist)),
            "scan_hit_count": int(len(scan_hits)) if scan_hits is not None else 0,
            "fetch_summary": fetch_summary,
        }
        with (self.metadata_dir / f"{date_key}.json").open("w", encoding="utf-8") as handle:
            json.dump(metadata_payload, handle, ensure_ascii=False, indent=2)
        return self.metadata_dir / f"{date_key}.json"

    def load_latest_run(self) -> RunArtifactsLoadResult:
        date_key = self._latest_date_key(self.metadata_dir, suffix=".json")
        if date_key is None:
            return RunArtifactsLoadResult(
                path=None,
                metadata=None,
                snapshot=None,
                eligible_snapshot=None,
                watchlist=None,
                fetch_status=None,
                scan_hits=None,
            )

        metadata_path = self.metadata_dir / f"{date_key}.json"
        return RunArtifactsLoadResult(
            path=str(metadata_path),
            metadata=self._load_json(metadata_path),
            snapshot=None,
            eligible_snapshot=None,
            watchlist=self._load_indexed_frame(self.watchlist_dir / f"{date_key}.csv", index_name="ticker"),
            fetch_status=None,
            scan_hits=self._load_scan_hits(date_key),
            market_metadata=self._load_json(self.market_summary_dir / f"{date_key}.json"),
            radar_metadata=self._load_json(self.radar_summary_dir / f"{date_key}.json"),
            market_frames={},
            radar_frames={},
        )

    def save_universe_snapshot(self, snapshot: pd.DataFrame, metadata: dict[str, Any]) -> Path:
        date_key = datetime.now().strftime("%Y%m%d")
        csv_path = self.universe_dir / f"{date_key}.csv"
        json_path = self.universe_dir / f"{date_key}.json"
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

    def _save_market_result(self, date_key: str, market_result: Any) -> None:
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
            "market_snapshot": self._frame_to_records(getattr(market_result, "market_snapshot", pd.DataFrame())),
            "leadership_snapshot": self._frame_to_records(getattr(market_result, "leadership_snapshot", pd.DataFrame())),
            "external_snapshot": self._frame_to_records(getattr(market_result, "external_snapshot", pd.DataFrame())),
            "factors_vs_sp500": self._frame_to_records(getattr(market_result, "factors_vs_sp500", pd.DataFrame())),
        }
        with (self.market_summary_dir / f"{date_key}.json").open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _save_radar_result(self, date_key: str, radar_result: Any) -> None:
        payload = {
            "update_time": radar_result.update_time,
            "sector_leaders": self._frame_to_records(getattr(radar_result, "sector_leaders", pd.DataFrame())),
            "industry_leaders": self._frame_to_records(getattr(radar_result, "industry_leaders", pd.DataFrame())),
            "top_daily": self._frame_to_records(getattr(radar_result, "top_daily", pd.DataFrame())),
            "top_weekly": self._frame_to_records(getattr(radar_result, "top_weekly", pd.DataFrame())),
        }
        with (self.radar_summary_dir / f"{date_key}.json").open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

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

    def _save_scan_hits(self, date_key: str, trade_date_iso: str | None, scan_hits: pd.DataFrame) -> None:
        if scan_hits.empty:
            return
        hit_date = self._hit_date_from_key(date_key, trade_date_iso)
        records = []
        for _, row in scan_hits.iterrows():
            ticker = str(row.get("ticker", "")).strip().upper()
            scan_name = str(row.get("name", row.get("scan_name", ""))).strip()
            if not ticker or not scan_name:
                continue
            records.append((hit_date, ticker, scan_name, str(row.get("kind", "")).strip() or None))
        if not records:
            return
        conn = connect_tracking_db(self.root_dir / "tracking.db")
        try:
            conn.executemany(
                "INSERT OR IGNORE INTO scan_hits (hit_date, ticker, scan_name, kind) VALUES (?, ?, ?, ?)",
                records,
            )
            conn.commit()
        finally:
            conn.close()

    def _load_scan_hits(self, date_key: str) -> pd.DataFrame | None:
        hit_date = self._hit_date_from_key(date_key, None)
        frame = read_scan_hits_for_watchlist(hit_date, db_path=self.root_dir / "tracking.db")
        return frame if not frame.empty else None

    def _hit_date_from_key(self, date_key: str, trade_date_iso: str | None) -> str:
        if trade_date_iso:
            parsed = pd.to_datetime(trade_date_iso, errors="coerce")
            if pd.notna(parsed):
                return pd.Timestamp(parsed).strftime("%Y-%m-%d")
        return datetime.strptime(date_key, "%Y%m%d").strftime("%Y-%m-%d")

    def _load_json(self, path: Path) -> dict[str, object] | None:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _latest_date_key(self, directory: Path, suffix: str) -> str | None:
        candidates = [
            path.stem
            for path in directory.iterdir()
            if path.is_file() and path.suffix == suffix and path.stem.isdigit() and len(path.stem) == 8
        ]
        if not candidates:
            return None
        return max(candidates)

    def _date_key_from_metadata(self, metadata: dict[str, Any], snapshot: pd.DataFrame) -> str:
        trade_date_raw = metadata.get("trade_date")
        if trade_date_raw:
            return datetime.fromisoformat(str(trade_date_raw)).strftime("%Y%m%d")
        if not snapshot.empty and "trade_date" in snapshot.columns:
            trade_date = pd.to_datetime(snapshot["trade_date"], errors="coerce").max()
            if pd.notna(trade_date):
                return pd.Timestamp(trade_date).strftime("%Y%m%d")
        return datetime.now().strftime("%Y%m%d")

    def _trade_date_iso(self, metadata: dict[str, Any], snapshot: pd.DataFrame) -> str | None:
        trade_date_raw = metadata.get("trade_date")
        if trade_date_raw:
            return str(trade_date_raw)
        if not snapshot.empty and "trade_date" in snapshot.columns:
            trade_date = pd.to_datetime(snapshot["trade_date"], errors="coerce").max()
            if pd.notna(trade_date):
                return pd.Timestamp(trade_date).isoformat()
        return None

    def _build_fetch_summary(self, fetch_status: pd.DataFrame) -> dict[str, int]:
        if fetch_status.empty or "source" not in fetch_status.columns:
            return {"live": 0, "cache": 0, "sample": 0, "missing": 0}
        sources = fetch_status["source"].astype(str)
        return {
            "live": int((sources == "live").sum()),
            "cache": int(sources.isin(["cache_fresh", "cache_stale"]).sum()),
            "sample": int((sources == "sample").sum()),
            "missing": int((sources == "missing").sum()),
        }

    def _frame_to_records(self, frame: pd.DataFrame) -> list[dict[str, object]]:
        if frame.empty:
            return []
        normalized = frame.copy()
        for column in normalized.columns:
            if pd.api.types.is_datetime64_any_dtype(normalized[column]):
                normalized[column] = normalized[column].astype(str)
        return normalized.to_dict(orient="records")
