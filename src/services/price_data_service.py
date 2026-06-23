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
    technical_cache_ttl_hours: int = 12

    @classmethod
    def from_config(cls, config_path: str | Path | None = None) -> "PriceDataService":
        settings = load_settings(config_path)
        app_settings = settings.get("app", {}) if isinstance(settings.get("app", {}), dict) else {}
        data_settings = settings.get("data", {}) if isinstance(settings.get("data", {}), dict) else {}
        root = Path(__file__).resolve().parents[2]
        cache_dir = Path(str(data_settings.get("price_cache_dir", app_settings.get("cache_dir", "data_cache")))).expanduser()
        if not cache_dir.is_absolute():
            cache_dir = root / cache_dir
        technical_cache_ttl_hours = int(data_settings.get("technical_cache_ttl_hours", 12))
        provider = YFinancePriceDataProvider(
            CacheLayer(cache_dir),
            technical_ttl_hours=technical_cache_ttl_hours,
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
            technical_cache_ttl_hours=technical_cache_ttl_hours,
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
        progress_callback: object | None = None,
    ) -> PriceHistoryBatch:
        resolved_interval = interval or self.interval
        normalized_symbols = self.store.normalize_symbols(symbols)
        self._progress(progress_callback, f"Price cache check: {len(normalized_symbols)} symbols")
        histories: dict[str, pd.DataFrame] = {}
        statuses: dict[str, FetchStatus] = {}
        missing_symbols: list[str] = []
        local_frames: dict[str, pd.DataFrame] = {}
        local_latest_dates: dict[str, pd.Timestamp] = {}

        if not force_refresh:
            for symbol in normalized_symbols:
                full_frame = self.store.load(symbol, interval=resolved_interval)
                if full_frame.empty:
                    missing_symbols.append(symbol)
                    statuses[symbol] = self._status(symbol, "missing", False, "local price cache missing or empty for requested range")
                    continue
                local_frames[symbol] = full_frame
                local_latest_dates[symbol] = pd.Timestamp(full_frame.index.max()).normalize()

            expected_latest_date = self._expected_latest_date(local_latest_dates, end_date)
            for symbol, full_frame in local_frames.items():
                frame = self.store.slice_frame(full_frame, start_date=start_date, end_date=end_date)
                if frame.empty:
                    missing_symbols.append(symbol)
                    statuses[symbol] = self._status(symbol, "missing", False, "local price cache has no rows in requested range")
                    continue
                latest_date = local_latest_dates[symbol]
                histories[symbol] = frame
                cache_key = self.store.cache_key(symbol, resolved_interval)
                cache_is_fresh = self.store.cache.is_fresh(
                    cache_key,
                    "csv",
                    self.technical_cache_ttl_hours,
                )
                if not cache_is_fresh:
                    missing_symbols.append(symbol)
                    statuses[symbol] = self._status(
                        symbol,
                        "cache_incomplete",
                        True,
                        f"local price cache exceeded {self.technical_cache_ttl_hours} hour TTL",
                    )
                elif expected_latest_date is not None and latest_date < expected_latest_date:
                    missing_symbols.append(symbol)
                    statuses[symbol] = self._status(
                        symbol,
                        "cache_incomplete",
                        True,
                        f"latest local price date {latest_date.date()} is before expected {expected_latest_date.date()}",
                    )
                else:
                    statuses[symbol] = self._status(symbol, "cache_complete", True)
        else:
            missing_symbols = normalized_symbols

        should_fetch = force_refresh or (refresh_missing and bool(missing_symbols))
        complete_count = sum(1 for status in statuses.values() if status.source == "cache_complete")
        self._progress(
            progress_callback,
            f"Price cache check complete: complete={complete_count}, refresh_needed={len(missing_symbols)}",
        )
        if should_fetch:
            if self.provider is None:
                raise RuntimeError("PriceDataService cannot refresh without a provider.")
            self._progress(progress_callback, f"Price fetch: refreshing {len(missing_symbols)} symbols")
            fetched = self.provider.get_price_history(
                missing_symbols,
                period=period or self.default_period,
                interval=resolved_interval,
                force_refresh=force_refresh,
                progress_callback=progress_callback,
            )
            for symbol, history in fetched.histories.items():
                normalized = self.store.normalize(history)
                self.store.save(symbol, normalized, interval=resolved_interval)
                histories[symbol] = self.store.slice_frame(normalized, start_date=start_date, end_date=end_date)
            for symbol, status in fetched.statuses.items():
                if status.source == "live" and symbol in local_frames:
                    statuses[symbol] = self._status(symbol, "refreshed_incremental", True, status.note)
                else:
                    statuses[symbol] = status

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

    def _expected_latest_date(
        self,
        local_latest_dates: dict[str, pd.Timestamp],
        end_date: str | pd.Timestamp | None,
    ) -> pd.Timestamp | None:
        if end_date is not None:
            parsed = pd.to_datetime(end_date, errors="coerce")
            if pd.isna(parsed):
                raise ValueError(f"Invalid end_date: {end_date}")
            stamp = pd.Timestamp(parsed)
            if stamp.tzinfo is not None:
                stamp = stamp.tz_localize(None)
            return stamp.normalize()
        if not local_latest_dates:
            return None
        return max(local_latest_dates.values())

    def _progress(self, callback: object | None, message: str) -> None:
        if callable(callback):
            callback(message)
