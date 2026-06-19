from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.configuration import load_settings
from src.data.cache import CacheLayer
from src.data.providers import YFinancePriceDataProvider
from src.data.results import FetchStatus, PriceHistoryBatch
from src.services.price_store import PriceStore


@dataclass(slots=True)
class PriceDataService:
    """Local-first price access with explicit live refresh controls."""

    store: PriceStore
    provider: object | None = None
    default_period: str = "3y"
    interval: str = "1d"

    @classmethod
    def from_config(cls, config_path: str | Path | None = None) -> "PriceDataService":
        settings = load_settings(config_path)
        app_settings = settings.get("app", {}) if isinstance(settings.get("app", {}), dict) else {}
        data_settings = settings.get("data", {}) if isinstance(settings.get("data", {}), dict) else {}
        root = Path(__file__).resolve().parents[2]
        cache_dir = Path(str(data_settings.get("price_cache_dir", app_settings.get("cache_dir", "data_cache")))).expanduser()
        if not cache_dir.is_absolute():
            cache_dir = root / cache_dir
        provider = YFinancePriceDataProvider(
            CacheLayer(cache_dir),
            technical_ttl_hours=int(data_settings.get("technical_cache_ttl_hours", 12)),
            allow_stale_cache_on_failure=bool(data_settings.get("allow_stale_cache_on_failure", True)),
            batch_size=int(data_settings.get("price_batch_size", 80)),
            max_retries=int(data_settings.get("price_max_retries", 3)),
            request_sleep_seconds=float(data_settings.get("price_request_sleep_seconds", 2.0)),
            retry_backoff_multiplier=float(data_settings.get("price_retry_backoff_multiplier", 2.0)),
            incremental_period=data_settings.get("price_incremental_period", "5d"),
        )
        return cls(
            store=PriceStore(cache_dir),
            provider=provider,
            default_period=str(app_settings.get("price_period", "3y")),
        )

    def get_histories(
        self,
        symbols: list[str] | tuple[str, ...],
        *,
        start_date: str | pd.Timestamp | None = None,
        end_date: str | pd.Timestamp | None = None,
        interval: str | None = None,
        refresh_missing: bool = False,
        force_refresh: bool = False,
        period: str | None = None,
    ) -> PriceHistoryBatch:
        resolved_interval = interval or self.interval
        normalized_symbols = self.store.normalize_symbols(symbols)
        histories: dict[str, pd.DataFrame] = {}
        statuses: dict[str, FetchStatus] = {}
        missing_symbols: list[str] = []

        if not force_refresh:
            for symbol in normalized_symbols:
                frame = self.store.load(symbol, interval=resolved_interval, start_date=start_date, end_date=end_date)
                if frame.empty:
                    missing_symbols.append(symbol)
                    statuses[symbol] = self._status(symbol, "missing", False, "local price cache missing or empty for requested range")
                    continue
                histories[symbol] = frame
                statuses[symbol] = self._status(symbol, "cache_fresh", True)
        else:
            missing_symbols = normalized_symbols

        should_fetch = force_refresh or (refresh_missing and bool(missing_symbols))
        if should_fetch:
            if self.provider is None:
                raise RuntimeError("PriceDataService cannot refresh without a provider.")
            fetched = self.provider.get_price_history(
                missing_symbols,
                period=period or self.default_period,
                interval=resolved_interval,
                force_refresh=force_refresh,
            )
            for symbol, history in fetched.histories.items():
                normalized = self.store.normalize(history)
                self.store.save(symbol, normalized, interval=resolved_interval)
                histories[symbol] = self.store.slice_frame(normalized, start_date=start_date, end_date=end_date)
            statuses.update(fetched.statuses)

        return PriceHistoryBatch(histories=histories, statuses=statuses)

    def load_range(
        self,
        symbol: str,
        *,
        start_date: str | pd.Timestamp | None = None,
        end_date: str | pd.Timestamp | None = None,
        interval: str | None = None,
    ) -> pd.DataFrame:
        return self.store.load(symbol, interval=interval or self.interval, start_date=start_date, end_date=end_date)

    def slice_as_of(
        self,
        symbol: str,
        as_of_date: str | pd.Timestamp,
        *,
        start_date: str | pd.Timestamp | None = None,
        interval: str | None = None,
    ) -> pd.DataFrame:
        return self.store.slice_as_of(symbol, as_of_date, interval=interval or self.interval, start_date=start_date)

    def _status(self, symbol: str, source: str, has_data: bool, note: str | None = None) -> FetchStatus:
        return FetchStatus(
            symbol=symbol,
            dataset="price",
            source=source,
            has_data=has_data,
            fetched_at=datetime.now(),
            note=note,
        )
