from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from src.data.models import FundamentalSnapshot, SymbolProfile


@dataclass(slots=True)
class FetchStatus:
    """Status metadata for one dataset and symbol."""

    symbol: str
    dataset: str
    source: str
    has_data: bool
    fetched_at: datetime | None = None
    note: str | None = None

    @property
    def is_live(self) -> bool:
        return self.source == "live"

    @property
    def is_cached(self) -> bool:
        return self.source.startswith("cache")

    @property
    def is_sample(self) -> bool:
        return self.source == "sample"

    def to_record(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "dataset": self.dataset,
            "source": self.source,
            "has_data": self.has_data,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "note": self.note,
        }


@dataclass(slots=True)
class PriceHistoryBatch:
    """Batch output for price histories plus status metadata."""

    histories: dict[str, pd.DataFrame]
    statuses: dict[str, FetchStatus]


@dataclass(slots=True)
class ProfileBatchResult:
    """Batch output for profiles plus status metadata."""

    profiles: list[SymbolProfile]
    statuses: dict[str, FetchStatus]


@dataclass(slots=True)
class FundamentalBatchResult:
    """Batch output for fundamentals plus status metadata."""

    fundamentals: list[FundamentalSnapshot]
    statuses: dict[str, FetchStatus]


@dataclass(slots=True)
class UniverseSnapshotLoadResult:
    """Loaded weekly universe snapshot plus metadata."""

    snapshot: pd.DataFrame | None
    metadata: dict[str, object] | None
    path: str | None


@dataclass(slots=True)
class RunArtifactsLoadResult:
    """Loaded persisted run bundle plus optional dashboard payloads."""

    path: str | None
    metadata: dict[str, object] | None
    snapshot: pd.DataFrame | None
    eligible_snapshot: pd.DataFrame | None
    watchlist: pd.DataFrame | None
    fetch_status: pd.DataFrame | None
    scan_hits: pd.DataFrame | None
    market_metadata: dict[str, object] | None = None
    radar_metadata: dict[str, object] | None = None
    market_frames: dict[str, pd.DataFrame] = field(default_factory=dict)
    radar_frames: dict[str, pd.DataFrame] = field(default_factory=dict)
