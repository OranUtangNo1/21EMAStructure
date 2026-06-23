from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.dashboard.market import MarketConditionResult
from src.dashboard.radar import RadarResult
from src.dashboard.watchlist import ScanCardViewModel


@dataclass(slots=True)
class PlatformArtifacts:
    """In-memory screening result bundle shared by non-GUI downstream services."""

    snapshot: pd.DataFrame
    eligible_snapshot: pd.DataFrame
    watchlist: pd.DataFrame
    duplicate_tickers: pd.DataFrame
    watchlist_cards: list[ScanCardViewModel]
    earnings_today: pd.DataFrame
    scan_hits: pd.DataFrame
    benchmark_history: pd.DataFrame
    vix_history: pd.DataFrame
    market_result: MarketConditionResult
    radar_result: RadarResult
    used_sample_data: bool
    data_source_label: str
    fetch_status: pd.DataFrame
    data_health_summary: dict[str, float | int]
    run_directory: str | None
    universe_mode: str
    resolved_symbols: list[str]
    universe_snapshot_path: str | None
    artifact_origin: str
    entry_signal_watchlist: pd.DataFrame | None = None
