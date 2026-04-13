from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from pandas.tseries.offsets import BDay

from src.configuration import load_settings
from src.dashboard.watchlist import WatchlistViewModelBuilder
from src.pipeline import PlatformArtifacts
from src.scan.rules import ScanConfig

FORWARD_HORIZONS = (1, 5, 10, 20)


@dataclass(slots=True)
class PresetEffectivenessSyncResult:
    output_dir: str
    event_count: int
    new_event_count: int
    outcome_count: int
    updated_outcome_count: int


def sync_preset_effectiveness_logs(
    config_path: str,
    artifacts: PlatformArtifacts,
    *,
    root_dir: Path | None = None,
) -> PresetEffectivenessSyncResult | None:
    trade_date = _latest_trade_date(artifacts)
    if trade_date is None:
        return None

    base_dir = (root_dir or Path(__file__).resolve().parents[2]) / "data_runs" / "preset_effectiveness"
    base_dir.mkdir(parents=True, exist_ok=True)
    events_path = base_dir / "events.csv"
    outcomes_path = base_dir / "outcomes.csv"

    settings = load_settings(config_path)
    scan_config = ScanConfig.from_dict(settings.get("scan", {}))
    export_presets = [preset for preset in scan_config.watchlist_presets if preset.export_enabled]
    builder = WatchlistViewModelBuilder(scan_config)

    events = _load_csv(events_path)
    outcomes = _load_csv(outcomes_path)
    existing_event_ids = set(events["event_id"].astype(str)) if not events.empty and "event_id" in events.columns else set()
    existing_outcome_ids = set(outcomes["outcome_id"].astype(str)) if not outcomes.empty and "outcome_id" in outcomes.columns else set()

    new_events: list[dict[str, object]] = []
    new_outcomes: list[dict[str, object]] = []
    latest_snapshot = artifacts.snapshot.copy()
    if not latest_snapshot.empty and "ticker" not in latest_snapshot.columns:
        latest_snapshot = latest_snapshot.reset_index(names="ticker")
    if "ticker" in latest_snapshot.columns:
        latest_snapshot["ticker"] = latest_snapshot["ticker"].astype(str).str.upper()
        latest_snapshot = latest_snapshot.drop_duplicates(subset=["ticker"], keep="last").set_index("ticker")
    close_map = latest_snapshot["close"].to_dict() if not latest_snapshot.empty and "close" in latest_snapshot.columns else {}

    scan_hits = artifacts.scan_hits.copy() if not artifacts.scan_hits.empty else pd.DataFrame(columns=["ticker", "name", "kind"])
    if not scan_hits.empty and "ticker" in scan_hits.columns:
        scan_hits["ticker"] = scan_hits["ticker"].astype(str).str.upper()
        if "kind" in scan_hits.columns:
            scan_hits = scan_hits.loc[scan_hits["kind"] == "scan"].copy()

    market_score = getattr(artifacts.market_result, "score", None) if artifacts.market_result is not None else None
    market_label = getattr(artifacts.market_result, "label", None) if artifacts.market_result is not None else None

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
            event_id = f"{trade_date.strftime('%Y-%m-%d')}::{preset.preset_name}::{ticker_str}"
            if event_id in existing_event_ids:
                continue
            matched_hits = sorted(
                {
                    str(name)
                    for name in scan_hits.loc[
                        (scan_hits["ticker"] == ticker_str) & (scan_hits["name"].isin(preset.selected_scan_names)),
                        "name",
                    ].tolist()
                }
            )
            event_row = {
                "event_id": event_id,
                "trade_date": trade_date.strftime("%Y-%m-%d"),
                "preset_name": preset.preset_name,
                "ticker": ticker_str,
                "market_score": market_score,
                "market_label": market_label,
                "duplicate_rule_mode": preset.duplicate_rule.mode,
                "selected_scan_names": ", ".join(preset.selected_scan_names),
                "hit_scans": ", ".join(matched_hits),
                "close_at_signal": row.get("close"),
                "volume": row.get("volume"),
                "avg_volume_50d": row.get("avg_volume_50d"),
                "rel_volume": row.get("rel_volume"),
                "hybrid_score": row.get("hybrid_score"),
                "vcs": row.get("vcs"),
                "rs21": row.get("rs21"),
                "rs63": row.get("rs63"),
                "rs126": row.get("rs126"),
                "dist_from_52w_high": row.get("dist_from_52w_high"),
                "dist_from_52w_low": row.get("dist_from_52w_low"),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            new_events.append(event_row)
            existing_event_ids.add(event_id)
            close_at_signal = _to_float(row.get("close"))
            for horizon in FORWARD_HORIZONS:
                outcome_id = f"{event_id}::{horizon}d"
                if outcome_id in existing_outcome_ids:
                    continue
                target_date = (trade_date + BDay(horizon)).date().isoformat()
                new_outcomes.append(
                    {
                        "outcome_id": outcome_id,
                        "event_id": event_id,
                        "trade_date": trade_date.strftime("%Y-%m-%d"),
                        "target_horizon_days": horizon,
                        "target_date": target_date,
                        "ticker": ticker_str,
                        "close_at_signal": close_at_signal,
                        "close_at_target": None,
                        "return_pct": None,
                        "status": "pending",
                        "updated_at": None,
                    }
                )
                existing_outcome_ids.add(outcome_id)

    if new_events:
        events = pd.concat([events, pd.DataFrame(new_events)], ignore_index=True)
    if new_outcomes:
        outcomes = pd.concat([outcomes, pd.DataFrame(new_outcomes)], ignore_index=True)

    updated_outcome_count = 0
    if not outcomes.empty:
        for idx, row in outcomes.loc[outcomes["status"] == "pending"].iterrows():
            target_date = pd.to_datetime(row.get("target_date"), errors="coerce")
            if pd.isna(target_date) or pd.Timestamp(trade_date) < pd.Timestamp(target_date):
                continue
            ticker = str(row.get("ticker", "")).upper()
            if ticker not in close_map:
                continue
            close_at_signal = _to_float(row.get("close_at_signal"))
            close_at_target = _to_float(close_map.get(ticker))
            if close_at_signal is None or close_at_target is None or close_at_signal == 0:
                continue
            outcomes.at[idx, "close_at_target"] = close_at_target
            outcomes.at[idx, "return_pct"] = ((close_at_target / close_at_signal) - 1.0) * 100.0
            outcomes.at[idx, "status"] = "ready"
            outcomes.at[idx, "updated_at"] = datetime.now().isoformat(timespec="seconds")
            updated_outcome_count += 1

    events = events.sort_values(["trade_date", "preset_name", "ticker"], ascending=[True, True, True]) if not events.empty else events
    outcomes = (
        outcomes.sort_values(["trade_date", "ticker", "target_horizon_days"], ascending=[True, True, True])
        if not outcomes.empty
        else outcomes
    )
    events.to_csv(events_path, index=False)
    outcomes.to_csv(outcomes_path, index=False)

    return PresetEffectivenessSyncResult(
        output_dir=str(base_dir),
        event_count=int(len(events)),
        new_event_count=int(len(new_events)),
        outcome_count=int(len(outcomes)),
        updated_outcome_count=updated_outcome_count,
    )


def _latest_trade_date(artifacts: PlatformArtifacts) -> pd.Timestamp | None:
    if artifacts.snapshot.empty or "trade_date" not in artifacts.snapshot.columns:
        return None
    trade_date = pd.to_datetime(artifacts.snapshot["trade_date"], errors="coerce").max()
    if pd.isna(trade_date):
        return None
    return pd.Timestamp(trade_date).normalize()


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


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
