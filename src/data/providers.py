from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
import time
from typing import Any

import pandas as pd

from src.data.cache import CacheLayer
from src.data.models import FundamentalSnapshot, SymbolProfile
from src.data.results import FetchStatus, FundamentalBatchResult, PriceHistoryBatch, ProfileBatchResult
from src.utils import coalesce_strings

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None


@dataclass(slots=True)
class UniverseDiscoveryResult:
    """Normalized output of coarse universe discovery."""

    snapshot: pd.DataFrame
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class YahooScreenerConfig:
    """Configuration for the Yahoo screener based universe discovery stage."""

    allowed_exchanges: tuple[str, ...] = ("NASDAQ", "NYSE")
    page_size: int = 250
    max_pages_per_exchange: int = 1
    max_symbols: int = 60
    min_market_cap: float = 1_000_000_000.0
    min_avgdailyvol3m: float = 1_000_000.0
    min_price: float = 10.0
    sort_field: str = "intradaymarketcap"
    sort_ascending: bool = False

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "YahooScreenerConfig":
        return cls(
            allowed_exchanges=tuple(str(value).strip().upper() for value in payload.get("allowed_exchanges", ["NASDAQ", "NYSE"]) if str(value).strip()),
            page_size=min(int(payload.get("page_size", 250)), 250),
            max_pages_per_exchange=int(payload.get("max_pages_per_exchange", 1)),
            max_symbols=int(payload.get("max_symbols", 60)),
            min_market_cap=float(payload.get("min_market_cap", 1_000_000_000.0)),
            min_avgdailyvol3m=float(payload.get("min_avgdailyvol3m", 1_000_000.0)),
            min_price=float(payload.get("min_price", 10.0)),
            sort_field=str(payload.get("sort_field", "intradaymarketcap")),
            sort_ascending=bool(payload.get("sort_ascending", False)),
        )


class PriceDataProvider(ABC):
    """Abstract interface for daily price retrieval."""

    @abstractmethod
    def get_price_history(
        self,
        symbols: list[str],
        period: str = "18mo",
        interval: str = "1d",
        *,
        force_refresh: bool = False,
    ) -> PriceHistoryBatch:
        """Fetch OHLCV history for a list of symbols."""


class ProfileDataProvider(ABC):
    """Abstract interface for profile data retrieval."""

    @abstractmethod
    def get_profiles(self, symbols: list[str]) -> ProfileBatchResult:
        """Fetch company profile data for a list of symbols."""


class FundamentalDataProvider(ABC):
    """Abstract interface for fundamental snapshot retrieval."""

    @abstractmethod
    def get_fundamentals(self, symbols: list[str]) -> FundamentalBatchResult:
        """Fetch fundamental data for a list of symbols."""


class UniverseDiscoveryProvider(ABC):
    """Abstract interface for coarse symbol discovery."""

    @abstractmethod
    def discover(self) -> UniverseDiscoveryResult:
        """Discover a screenable list of symbols."""


class YahooScreenerProvider(UniverseDiscoveryProvider):
    """Use Yahoo screener to build a coarse, low-cost weekly universe snapshot."""

    EXCHANGE_CODES = {
        "NASDAQ": "NMS",
        "NYSE": "NYQ",
        "AMEX": "ASE",
        "NMS": "NMS",
        "NYQ": "NYQ",
        "ASE": "ASE",
    }

    def __init__(self, config: YahooScreenerConfig) -> None:
        self.config = config

    def discover(self) -> UniverseDiscoveryResult:
        if yf is None:
            raise RuntimeError("yfinance is not installed.")

        rows: list[dict[str, object]] = []
        segments: list[dict[str, object]] = []
        for exchange in self.config.allowed_exchanges:
            exchange_code = self.EXCHANGE_CODES.get(exchange.upper(), exchange.upper())
            query = self._build_query(exchange_code)
            for page in range(self.config.max_pages_per_exchange):
                offset = page * self.config.page_size
                payload = yf.screen(
                    query,
                    offset=offset,
                    size=self.config.page_size,
                    sortField=self.config.sort_field,
                    sortAsc=self.config.sort_ascending,
                )
                quotes = payload.get("quotes", []) if isinstance(payload, dict) else []
                segments.append(
                    {
                        "exchange": exchange.upper(),
                        "exchange_code": exchange_code,
                        "page": page,
                        "offset": offset,
                        "quote_count": len(quotes),
                        "total": payload.get("total") if isinstance(payload, dict) else None,
                    }
                )
                if not quotes:
                    break
                rows.extend(self._normalize_quotes(quotes, exchange.upper()))
                total = int(payload.get("total", 0)) if isinstance(payload, dict) and payload.get("total") is not None else 0
                if len(quotes) < self.config.page_size:
                    break
                if total and (offset + len(quotes) >= total):
                    break

        snapshot = pd.DataFrame(rows)
        if snapshot.empty:
            return UniverseDiscoveryResult(snapshot=pd.DataFrame(), source="live", metadata={"segments": segments})

        snapshot = snapshot.drop_duplicates(subset=["ticker"]).copy()
        snapshot = snapshot.sort_values(["market_cap", "avg_volume_3m", "price"], ascending=[False, False, False])
        snapshot = snapshot.head(self.config.max_symbols).copy()
        snapshot["discovered_at"] = datetime.now().isoformat(timespec="seconds")
        snapshot = snapshot.reset_index(drop=True)
        return UniverseDiscoveryResult(
            snapshot=snapshot,
            source="live",
            metadata={
                "segments": segments,
                "max_symbols": self.config.max_symbols,
                "allowed_exchanges": list(self.config.allowed_exchanges),
                "sort_field": self.config.sort_field,
                "sort_ascending": self.config.sort_ascending,
            },
        )

    def _build_query(self, exchange_code: str) -> Any:
        return yf.EquityQuery(
            "and",
            [
                yf.EquityQuery("eq", ["exchange", exchange_code]),
                yf.EquityQuery("gt", ["intradaymarketcap", self.config.min_market_cap]),
                yf.EquityQuery("gt", ["avgdailyvol3m", self.config.min_avgdailyvol3m]),
                yf.EquityQuery("gt", ["intradayprice", self.config.min_price]),
            ],
        )

    def _normalize_quotes(self, quotes: list[dict[str, Any]], exchange_label: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for quote in quotes:
            ticker = str(quote.get("symbol", "")).strip().upper()
            if not ticker:
                continue
            if str(quote.get("quoteType", "")).upper() != "EQUITY":
                continue
            type_disp = str(quote.get("typeDisp", "")).strip().lower()
            if type_disp and type_disp != "equity":
                continue
            rows.append(
                {
                    "ticker": ticker,
                    "name": coalesce_strings([quote.get("longName"), quote.get("displayName"), ticker], fallback=ticker),
                    "market_cap": self._to_float(quote.get("marketCap")),
                    "avg_volume_3m": self._to_float(quote.get("averageDailyVolume3Month")),
                    "price": self._to_float(quote.get("regularMarketPrice")),
                    "exchange": coalesce_strings([quote.get("fullExchangeName"), quote.get("exchange"), exchange_label], fallback=exchange_label),
                    "quote_type": quote.get("quoteType"),
                    "type_disp": quote.get("typeDisp"),
                    "currency": quote.get("currency"),
                    "source": "yahoo_screener",
                }
            )
        return rows

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


class YFinancePriceDataProvider(PriceDataProvider):
    """Price provider backed by yfinance bulk downloads with fresh/stale cache support."""

    def __init__(
        self,
        cache: CacheLayer,
        technical_ttl_hours: int = 12,
        allow_stale_cache_on_failure: bool = True,
        batch_size: int = 80,
        max_retries: int = 3,
        request_sleep_seconds: float = 2.0,
        retry_backoff_multiplier: float = 2.0,
        incremental_period: str | None = "5d",
    ) -> None:
        self.cache = cache
        self.technical_ttl_hours = technical_ttl_hours
        self.allow_stale_cache_on_failure = allow_stale_cache_on_failure
        self.batch_size = max(1, int(batch_size))
        self.max_retries = max(1, int(max_retries))
        self.request_sleep_seconds = max(0.0, float(request_sleep_seconds))
        self.retry_backoff_multiplier = max(1.0, float(retry_backoff_multiplier))
        normalized_incremental_period = str(incremental_period).strip() if incremental_period is not None else ""
        self.incremental_period = normalized_incremental_period or None

    def get_price_history(
        self,
        symbols: list[str],
        period: str = "18mo",
        interval: str = "1d",
        *,
        force_refresh: bool = False,
    ) -> PriceHistoryBatch:
        if yf is None:
            raise RuntimeError("yfinance is not installed.")

        histories: dict[str, pd.DataFrame] = {}
        statuses: dict[str, FetchStatus] = {}
        stale_histories: dict[str, pd.DataFrame] = {}
        full_refresh_symbols: list[str] = []
        incremental_symbols: list[str] = []

        normalized_symbols = list(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))
        for symbol in normalized_symbols:
            cache_key = self._cache_key(symbol, period, interval)
            if not force_refresh:
                cached = self.cache.load_csv(cache_key, ttl_hours=self.technical_ttl_hours)
                if cached is not None and not cached.empty:
                    histories[symbol] = cached
                    statuses[symbol] = self._status(symbol, "cache_fresh", True, self.cache.get_modified_at(cache_key, "csv"))
                    continue

            stale = self.cache.load_csv(cache_key, ttl_hours=self.technical_ttl_hours, allow_stale=True)
            if stale is not None and not stale.empty:
                stale_histories[symbol] = stale
                incremental_symbols.append(symbol)
                continue

            full_refresh_symbols.append(symbol)

        self._fetch_symbol_group(
            symbols=full_refresh_symbols,
            download_period=period,
            cache_period=period,
            interval=interval,
            histories=histories,
            statuses=statuses,
            fallback_histories={},
        )

        update_period = self.incremental_period or period
        self._fetch_symbol_group(
            symbols=incremental_symbols,
            download_period=update_period,
            cache_period=period,
            interval=interval,
            histories=histories,
            statuses=statuses,
            fallback_histories=stale_histories,
        )
        return PriceHistoryBatch(histories=histories, statuses=statuses)

    def _fetch_symbol_group(
        self,
        symbols: list[str],
        download_period: str,
        cache_period: str,
        interval: str,
        histories: dict[str, pd.DataFrame],
        statuses: dict[str, FetchStatus],
        fallback_histories: dict[str, pd.DataFrame],
    ) -> None:
        batches = self._chunk_symbols(symbols)
        for batch_index, batch in enumerate(batches):
            downloaded, error_note = self._download_batch(batch, download_period, interval)
            fetched_at = datetime.now()
            for symbol in batch:
                cache_key = self._cache_key(symbol, cache_period, interval)
                history = downloaded.get(symbol, pd.DataFrame())
                if not history.empty:
                    merged = self._merge_histories(fallback_histories.get(symbol), history)
                    histories[symbol] = merged
                    self.cache.save_csv(cache_key, merged)
                    statuses[symbol] = self._status(symbol, "live", True, fetched_at)
                    continue

                stale = fallback_histories.get(symbol)
                if self.allow_stale_cache_on_failure and stale is not None and not stale.empty:
                    histories[symbol] = stale
                    statuses[symbol] = self._status(
                        symbol,
                        "cache_stale",
                        True,
                        self.cache.get_modified_at(cache_key, "csv"),
                        error_note,
                    )
                    continue

                statuses[symbol] = self._status(symbol, "missing", False, None, error_note or "price fetch returned no rows")

            if batch_index < len(batches) - 1 and self.request_sleep_seconds > 0:
                time.sleep(self.request_sleep_seconds)

    def _download_batch(self, symbols: list[str], period: str, interval: str) -> tuple[dict[str, pd.DataFrame], str | None]:
        downloaded: dict[str, pd.DataFrame] = {}
        remaining = list(symbols)
        error_note: str | None = None

        for attempt in range(self.max_retries):
            if not remaining:
                break
            try:
                raw = yf.download(
                    remaining,
                    period=period,
                    interval=interval,
                    auto_adjust=False,
                    progress=False,
                    threads=False,
                    group_by="ticker",
                )
                split_frames = self._split_download_frame(raw, remaining)
                for symbol in list(remaining):
                    normalized = self._normalize_download(split_frames.get(symbol, pd.DataFrame()))
                    if not normalized.empty:
                        downloaded[symbol] = normalized
                remaining = [symbol for symbol in remaining if symbol not in downloaded]
                if not remaining:
                    error_note = None
                    break
                error_note = f"price fetch incomplete: {', '.join(remaining)}"
            except Exception as exc:
                error_note = f"live fetch failed: {type(exc).__name__}"

            if remaining and attempt < self.max_retries - 1 and self.request_sleep_seconds > 0:
                delay = self.request_sleep_seconds * (self.retry_backoff_multiplier ** attempt)
                time.sleep(delay)

        return downloaded, error_note

    def _split_download_frame(self, frame: pd.DataFrame, symbols: list[str]) -> dict[str, pd.DataFrame]:
        if frame is None or frame.empty:
            return {}
        if isinstance(frame.columns, pd.MultiIndex):
            level_zero = {str(value) for value in frame.columns.get_level_values(0)}
            level_one = {str(value) for value in frame.columns.get_level_values(1)} if frame.columns.nlevels > 1 else set()
            if any(symbol in level_zero for symbol in symbols):
                return {
                    symbol: frame.xs(symbol, axis=1, level=0, drop_level=True)
                    for symbol in symbols
                    if symbol in level_zero
                }
            if any(symbol in level_one for symbol in symbols):
                return {
                    symbol: frame.xs(symbol, axis=1, level=1, drop_level=True)
                    for symbol in symbols
                    if symbol in level_one
                }
        if len(symbols) == 1:
            return {symbols[0]: frame}
        return {}

    def _merge_histories(self, existing: pd.DataFrame | None, incoming: pd.DataFrame) -> pd.DataFrame:
        if existing is None or existing.empty:
            return incoming.sort_index()
        if incoming.empty:
            return existing.sort_index()
        combined = pd.concat([existing, incoming], axis=0)
        combined = combined.loc[~combined.index.duplicated(keep="last")].sort_index()
        combined.index.name = "date"
        return combined

    def _chunk_symbols(self, symbols: list[str]) -> list[list[str]]:
        return [symbols[index : index + self.batch_size] for index in range(0, len(symbols), self.batch_size)]

    def _cache_key(self, symbol: str, period: str, interval: str) -> str:
        return f"prices_{symbol}_{period}_{interval}"

    def _normalize_download(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "adjusted_close", "volume"])
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = [str(column[0]) for column in frame.columns]
        normalized = frame.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adjusted_close",
                "Volume": "volume",
            }
        )
        normalized.columns = [str(column).strip().lower().replace(" ", "_") for column in normalized.columns]
        if "adj_close" in normalized.columns and "adjusted_close" not in normalized.columns:
            normalized = normalized.rename(columns={"adj_close": "adjusted_close"})
        if "adjusted_close" not in normalized.columns and "close" in normalized.columns:
            normalized["adjusted_close"] = normalized["close"]
        normalized = normalized[["open", "high", "low", "close", "adjusted_close", "volume"]].copy()
        for column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        normalized.index = pd.to_datetime(normalized.index, errors="coerce")
        if getattr(normalized.index, 'tz', None) is not None:
            normalized.index = normalized.index.tz_localize(None)
        normalized = normalized.loc[normalized.index.notna()].sort_index()
        normalized.index.name = "date"
        return normalized.dropna(how="all")

    def _status(
        self,
        symbol: str,
        source: str,
        has_data: bool,
        fetched_at: datetime | None,
        note: str | None = None,
    ) -> FetchStatus:
        return FetchStatus(symbol=symbol, dataset="price", source=source, has_data=has_data, fetched_at=fetched_at, note=note)

class YFinanceProfileDataProvider(ProfileDataProvider):
    """Profile provider backed by yfinance info payload with cache fallback."""

    def __init__(self, cache: CacheLayer, profile_ttl_hours: int = 168, allow_stale_cache_on_failure: bool = True) -> None:
        self.cache = cache
        self.profile_ttl_hours = profile_ttl_hours
        self.allow_stale_cache_on_failure = allow_stale_cache_on_failure

    def get_profiles(self, symbols: list[str]) -> ProfileBatchResult:
        if yf is None:
            raise RuntimeError("yfinance is not installed.")

        profiles: list[SymbolProfile] = []
        statuses: dict[str, FetchStatus] = {}
        for symbol in symbols:
            cache_key = f"profile_{symbol}"
            cached = self.cache.load_json(cache_key, ttl_hours=self.profile_ttl_hours)
            if cached is not None:
                profile = SymbolProfile.from_record(cached)
                profile.data_source = "cache_fresh"
                profiles.append(profile)
                statuses[symbol] = self._status(symbol, "cache_fresh", True, self.cache.get_modified_at(cache_key, "json"))
                continue

            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info or {}
                fast_info = self._safe_fast_info(ticker)
                profile = SymbolProfile(
                    ticker=symbol,
                    name=coalesce_strings([info.get("shortName"), info.get("longName"), symbol]),
                    market_cap=self._extract_market_cap(info, fast_info),
                    sector=info.get("sector"),
                    industry=info.get("industry"),
                    ipo_date=self._extract_ipo_date(info),
                    last_profile_update=datetime.now(),
                    data_source="live",
                )
                if any(value is not None for value in [profile.name, profile.market_cap, profile.sector, profile.industry, profile.ipo_date]):
                    self.cache.save_json(cache_key, profile.to_record())
                    profiles.append(profile)
                    statuses[symbol] = self._status(symbol, "live", True, datetime.now())
                    continue
                raise RuntimeError("Profile payload was empty.")
            except Exception as exc:
                if self.allow_stale_cache_on_failure:
                    stale = self.cache.load_json(cache_key, ttl_hours=self.profile_ttl_hours, allow_stale=True)
                    if stale is not None:
                        profile = SymbolProfile.from_record(stale)
                        profile.data_source = "cache_stale"
                        profiles.append(profile)
                        statuses[symbol] = self._status(
                            symbol,
                            "cache_stale",
                            True,
                            self.cache.get_modified_at(cache_key, "json"),
                            f"live fetch failed: {type(exc).__name__}",
                        )
                        continue
                statuses[symbol] = self._status(symbol, "missing", False, None, f"profile fetch failed: {type(exc).__name__}")
        return ProfileBatchResult(profiles=profiles, statuses=statuses)

    def _safe_fast_info(self, ticker: Any) -> dict[str, Any]:
        try:
            fast_info = ticker.fast_info or {}
            if hasattr(fast_info, "items"):
                return dict(fast_info.items())
        except Exception:
            return {}
        return {}

    def _extract_market_cap(self, info: dict[str, Any], fast_info: dict[str, Any]) -> float | None:
        for value in [info.get("marketCap"), fast_info.get("market_cap"), fast_info.get("marketCap")]:
            if value is not None:
                return float(value)
        return None

    def _extract_ipo_date(self, info: dict[str, Any]) -> date | None:
        first_trade = info.get("firstTradeDateEpochUtc")
        if not first_trade:
            return None
        return datetime.utcfromtimestamp(int(first_trade)).date()

    def _status(
        self,
        symbol: str,
        source: str,
        has_data: bool,
        fetched_at: datetime | None,
        note: str | None = None,
    ) -> FetchStatus:
        return FetchStatus(symbol=symbol, dataset="profile", source=source, has_data=has_data, fetched_at=fetched_at, note=note)


class YFinanceFundamentalDataProvider(FundamentalDataProvider):
    """Fundamental provider backed by yfinance info/calendar with cache fallback."""

    def __init__(self, cache: CacheLayer, fundamental_ttl_hours: int = 24, allow_stale_cache_on_failure: bool = True) -> None:
        self.cache = cache
        self.fundamental_ttl_hours = fundamental_ttl_hours
        self.allow_stale_cache_on_failure = allow_stale_cache_on_failure

    def get_fundamentals(self, symbols: list[str]) -> FundamentalBatchResult:
        if yf is None:
            raise RuntimeError("yfinance is not installed.")

        fundamentals: list[FundamentalSnapshot] = []
        statuses: dict[str, FetchStatus] = {}
        for symbol in symbols:
            cache_key = f"fundamentals_{symbol}"
            cached = self.cache.load_json(cache_key, ttl_hours=self.fundamental_ttl_hours)
            if cached is not None:
                snapshot = FundamentalSnapshot.from_record(cached)
                snapshot.data_source = "cache_fresh"
                fundamentals.append(snapshot)
                statuses[symbol] = self._status(symbol, "cache_fresh", True, self.cache.get_modified_at(cache_key, "json"))
                continue

            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info or {}
                snapshot = FundamentalSnapshot(
                    ticker=symbol,
                    eps_growth=self._normalize_growth(info.get("earningsQuarterlyGrowth")),
                    revenue_growth=self._normalize_growth(info.get("revenueGrowth")),
                    earnings_date=self._extract_earnings_date(info.get("earningsDate")) or self._extract_calendar_earnings_date(ticker),
                    last_fundamental_update=datetime.now(),
                    data_source="live",
                )
                if any(value is not None for value in [snapshot.eps_growth, snapshot.revenue_growth, snapshot.earnings_date]):
                    self.cache.save_json(cache_key, snapshot.to_record())
                    fundamentals.append(snapshot)
                    statuses[symbol] = self._status(symbol, "live", True, datetime.now())
                    continue
                raise RuntimeError("Fundamental payload was empty.")
            except Exception as exc:
                if self.allow_stale_cache_on_failure:
                    stale = self.cache.load_json(cache_key, ttl_hours=self.fundamental_ttl_hours, allow_stale=True)
                    if stale is not None:
                        snapshot = FundamentalSnapshot.from_record(stale)
                        snapshot.data_source = "cache_stale"
                        fundamentals.append(snapshot)
                        statuses[symbol] = self._status(
                            symbol,
                            "cache_stale",
                            True,
                            self.cache.get_modified_at(cache_key, "json"),
                            f"live fetch failed: {type(exc).__name__}",
                        )
                        continue
                statuses[symbol] = self._status(symbol, "missing", False, None, f"fundamental fetch failed: {type(exc).__name__}")
        return FundamentalBatchResult(fundamentals=fundamentals, statuses=statuses)

    def _normalize_growth(self, value: Any) -> float | None:
        if value is None:
            return None
        numeric = float(value)
        return numeric * 100.0 if abs(numeric) <= 1.5 else numeric

    def _extract_earnings_date(self, raw_value: Any) -> date | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, (list, tuple)) and raw_value:
            raw_value = raw_value[0]
        if isinstance(raw_value, datetime):
            return raw_value.date()
        if isinstance(raw_value, pd.Timestamp):
            return raw_value.date()
        return None

    def _extract_calendar_earnings_date(self, ticker: Any) -> date | None:
        try:
            calendar = ticker.calendar
        except Exception:
            return None
        if calendar is None:
            return None
        if isinstance(calendar, pd.DataFrame) and not calendar.empty:
            value = calendar.iloc[0, 0]
            if isinstance(value, pd.Timestamp):
                return value.date()
            if isinstance(value, datetime):
                return value.date()
        if isinstance(calendar, dict):
            for value in calendar.values():
                if isinstance(value, list) and value:
                    candidate = value[0]
                else:
                    candidate = value
                if isinstance(candidate, pd.Timestamp):
                    return candidate.date()
                if isinstance(candidate, datetime):
                    return candidate.date()
        return None

    def _status(
        self,
        symbol: str,
        source: str,
        has_data: bool,
        fetched_at: datetime | None,
        note: str | None = None,
    ) -> FetchStatus:
        return FetchStatus(symbol=symbol, dataset="fundamental", source=source, has_data=has_data, fetched_at=fetched_at, note=note)

