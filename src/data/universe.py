from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(slots=True)
class UniverseConfig:
    """Common universe filters used before detailed scans."""

    min_market_cap: float = 1_000_000_000.0
    min_avg_volume_50d: float = 1_000_000.0
    min_price: float = 10.0
    min_adr_percent: float = 3.5
    max_adr_percent: float | None = 10.0
    excluded_sectors: tuple[str, ...] = field(default_factory=lambda: ("Healthcare",))

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "UniverseConfig":
        return cls(
            min_market_cap=float(payload.get("min_market_cap", 1_000_000_000.0)),
            min_avg_volume_50d=float(payload.get("min_avg_volume_50d", 1_000_000.0)),
            min_price=float(payload.get("min_price", 10.0)),
            min_adr_percent=float(payload.get("min_adr_percent", 3.5)),
            max_adr_percent=(
                float(payload["max_adr_percent"]) if payload.get("max_adr_percent") is not None else None
            ),
            excluded_sectors=tuple(payload.get("excluded_sectors", ["Healthcare"])),
        )


class UniverseBuilder:
    """Apply broad filters before scan-specific logic."""

    def __init__(self, config: UniverseConfig) -> None:
        self.config = config

    def filter(self, snapshot: pd.DataFrame) -> pd.DataFrame:
        if snapshot.empty:
            return snapshot.copy()

        sector_series = snapshot["sector"].fillna("")
        mask = (
            snapshot["market_cap"].fillna(0) >= self.config.min_market_cap
        ) & (
            snapshot["avg_volume_50d"].fillna(0) >= self.config.min_avg_volume_50d
        ) & (
            snapshot["close"].fillna(0) >= self.config.min_price
        ) & (
            snapshot["adr_percent"].fillna(0) >= self.config.min_adr_percent
        ) & (
            ~sector_series.isin(self.config.excluded_sectors)
        )
        if self.config.max_adr_percent is not None:
            mask &= snapshot["adr_percent"].fillna(0) <= self.config.max_adr_percent
        return snapshot.loc[mask].copy()
