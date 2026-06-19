from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.data.cache import CacheLayer


PRICE_COLUMNS = ("open", "high", "low", "close", "adjusted_close", "volume")


@dataclass(frozen=True, slots=True)
class PriceStore:
    """File-backed local access to canonical daily price histories."""

    root_dir: str | Path
    cache: CacheLayer = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "cache", CacheLayer(self.root_dir))

    def load(
        self,
        symbol: str,
        *,
        interval: str = "1d",
        start_date: str | pd.Timestamp | None = None,
        end_date: str | pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        frame = self.cache.load_csv(self.cache_key(symbol, interval))
        if frame is None:
            return self.empty_frame()
        return self.slice_frame(self.normalize(frame), start_date=start_date, end_date=end_date)

    def save(self, symbol: str, history: pd.DataFrame, *, interval: str = "1d") -> None:
        self.cache.save_csv(self.cache_key(symbol, interval), self.normalize(history))

    def load_many(
        self,
        symbols: list[str] | tuple[str, ...],
        *,
        interval: str = "1d",
        start_date: str | pd.Timestamp | None = None,
        end_date: str | pd.Timestamp | None = None,
    ) -> dict[str, pd.DataFrame]:
        result: dict[str, pd.DataFrame] = {}
        for symbol in self.normalize_symbols(symbols):
            result[symbol] = self.load(symbol, interval=interval, start_date=start_date, end_date=end_date)
        return result

    def slice_as_of(
        self,
        symbol: str,
        as_of_date: str | pd.Timestamp,
        *,
        interval: str = "1d",
        start_date: str | pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        return self.load(symbol, interval=interval, start_date=start_date, end_date=as_of_date)

    def list_symbols(self, *, interval: str = "1d") -> list[str]:
        suffix = f"_{interval}.csv"
        symbols: list[str] = []
        for path in sorted(Path(self.cache.root_dir).glob(f"prices_*{suffix}")):
            name = path.name
            if not name.startswith("prices_") or not name.endswith(suffix):
                continue
            symbols.append(name[len("prices_") : -len(suffix)])
        return symbols

    def path_for(self, symbol: str, *, interval: str = "1d") -> Path:
        return self.cache._path(self.cache_key(symbol, interval), "csv")

    def cache_key(self, symbol: str, interval: str = "1d") -> str:
        return f"prices_{self.normalize_symbol(symbol)}_{interval}"

    def normalize(self, history: pd.DataFrame) -> pd.DataFrame:
        if history is None or history.empty:
            return self.empty_frame()
        frame = history.copy()
        frame.columns = [str(column).strip().lower().replace(" ", "_") for column in frame.columns]
        if "adj_close" in frame.columns and "adjusted_close" not in frame.columns:
            frame = frame.rename(columns={"adj_close": "adjusted_close"})
        if "adjusted_close" not in frame.columns and "close" in frame.columns:
            frame["adjusted_close"] = frame["close"]
        for column in PRICE_COLUMNS:
            if column not in frame.columns:
                frame[column] = pd.NA
        frame = frame.loc[:, list(PRICE_COLUMNS)].copy()
        for column in PRICE_COLUMNS:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame.index = pd.to_datetime(frame.index, errors="coerce")
        if getattr(frame.index, "tz", None) is not None:
            frame.index = frame.index.tz_localize(None)
        frame = frame.loc[frame.index.notna()].copy()
        frame = frame.loc[~frame.index.duplicated(keep="last")].sort_index()
        frame.index.name = "date"
        return frame

    def slice_frame(
        self,
        history: pd.DataFrame,
        *,
        start_date: str | pd.Timestamp | None = None,
        end_date: str | pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        frame = self.normalize(history)
        if start_date is not None:
            frame = frame.loc[frame.index >= self._date_bound(start_date)]
        if end_date is not None:
            frame = frame.loc[frame.index <= self._date_bound(end_date)]
        return frame.copy()

    def empty_frame(self) -> pd.DataFrame:
        frame = pd.DataFrame(columns=list(PRICE_COLUMNS))
        frame.index = pd.DatetimeIndex([], name="date")
        return frame

    def normalize_symbol(self, symbol: object) -> str:
        return str(symbol).strip().upper()

    def normalize_symbols(self, symbols: list[str] | tuple[str, ...]) -> list[str]:
        return list(dict.fromkeys(self.normalize_symbol(symbol) for symbol in symbols if self.normalize_symbol(symbol)))

    def _date_bound(self, value: str | pd.Timestamp) -> pd.Timestamp:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            raise ValueError(f"Invalid date: {value}")
        stamp = pd.Timestamp(parsed)
        if stamp.tzinfo is not None:
            stamp = stamp.tz_localize(None)
        return stamp.normalize()
