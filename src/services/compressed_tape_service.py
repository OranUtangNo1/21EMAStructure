from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.dashboard.compressed_tape import (
    CompressedTapeConfig,
    CompressedTapeDocument,
    CompressedTapeError,
    CompressedTapeGenerator,
)
from src.services.price_data_service import PriceDataService


@dataclass(frozen=True, slots=True)
class CompressedTapeBuildResult:
    documents: list[CompressedTapeDocument]
    missing: dict[str, str]
    fetch_status: dict[str, object]


@dataclass(slots=True)
class CompressedTapeService:
    """Build compressed-tape documents from the shared price-data service."""

    price_service: PriceDataService
    generator: CompressedTapeGenerator

    @classmethod
    def from_config(
        cls,
        config_path: str | Path | None = None,
        config: CompressedTapeConfig | None = None,
    ) -> "CompressedTapeService":
        return cls(
            price_service=PriceDataService.from_config(config_path),
            generator=CompressedTapeGenerator(config),
        )

    def build_many(
        self,
        symbols: list[str] | tuple[str, ...],
        *,
        tier: str = "T0",
        as_of_date: str | pd.Timestamp | None = None,
        start_date: str | pd.Timestamp | None = None,
        last_close_lookup: dict[str, float] | None = None,
        refresh_missing: bool = False,
        force_refresh: bool = False,
    ) -> CompressedTapeBuildResult:
        normalized_symbols = self.price_service.store.normalize_symbols(symbols)
        batch = self.price_service.get_histories(
            normalized_symbols,
            start_date=start_date,
            end_date=as_of_date,
            refresh_missing=refresh_missing,
            force_refresh=force_refresh,
        )
        last_close_lookup = last_close_lookup or {}
        documents: list[CompressedTapeDocument] = []
        missing: dict[str, str] = {}
        resolved_tier = tier.upper()

        for symbol in normalized_symbols:
            history = batch.histories.get(symbol, pd.DataFrame())
            if history.empty:
                status = batch.statuses.get(symbol)
                missing[symbol] = status.note if status is not None and status.note else "price history unavailable"
                continue
            try:
                if resolved_tier == "T1":
                    document = self.generator.build_t1(symbol, history, last_close=last_close_lookup.get(symbol))
                else:
                    document = self.generator.build_t0(symbol, history, last_close=last_close_lookup.get(symbol))
                documents.append(document)
            except CompressedTapeError as exc:
                missing[symbol] = str(exc)

        return CompressedTapeBuildResult(
            documents=documents,
            missing=missing,
            fetch_status={symbol: status.to_record() for symbol, status in batch.statuses.items()},
        )
