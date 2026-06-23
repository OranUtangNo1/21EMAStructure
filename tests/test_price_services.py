from __future__ import annotations

import os
import time

import pandas as pd

from src.data.results import FetchStatus, PriceHistoryBatch
from src.services.price_data_service import PriceDataService
from src.services.price_store import PriceStore


def test_price_store_loads_inclusive_date_range_and_normalizes_schema(tmp_path) -> None:
    store = PriceStore(tmp_path)
    history = pd.DataFrame(
        {
            "Open": [10.0, 11.0, 12.0, 13.0],
            "High": [11.0, 12.0, 13.0, 14.0],
            "Low": [9.0, 10.0, 11.0, 12.0],
            "Close": [10.5, 11.5, 12.5, 13.5],
            "Volume": [1000, 1100, 1200, 1300],
        },
        index=pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"]),
    )

    store.save("nvda", history)
    loaded = store.load("NVDA", start_date="2026-01-03", end_date="2026-01-04")

    assert list(loaded.index) == [pd.Timestamp("2026-01-03"), pd.Timestamp("2026-01-04")]
    assert list(loaded.columns) == ["open", "high", "low", "close", "adjusted_close", "volume"]
    assert loaded.loc[pd.Timestamp("2026-01-04"), "adjusted_close"] == 12.5
    assert store.path_for("NVDA").name == "prices_NVDA_1d.csv"


def test_price_store_slice_as_of_excludes_future_rows(tmp_path) -> None:
    store = PriceStore(tmp_path)
    store.save("AAPL", _history([100.0, 101.0, 102.0], ["2026-02-02", "2026-02-03", "2026-02-04"]))

    sliced = store.slice_as_of("AAPL", "2026-02-03")

    assert list(sliced.index) == [pd.Timestamp("2026-02-02"), pd.Timestamp("2026-02-03")]


def test_price_data_service_uses_local_cache_without_provider_call(tmp_path) -> None:
    store = PriceStore(tmp_path)
    store.save("NVDA", _history([100.0, 101.0, 102.0], ["2026-03-02", "2026-03-03", "2026-03-04"]))
    service = PriceDataService(store=store, provider=FailingProvider())

    result = service.get_histories(["NVDA"], start_date="2026-03-03", end_date="2026-03-04")

    assert result.statuses["NVDA"].source == "cache_complete"
    assert list(result.histories["NVDA"].index) == [pd.Timestamp("2026-03-03"), pd.Timestamp("2026-03-04")]


def test_price_data_service_refreshes_missing_and_incomplete_symbols(tmp_path) -> None:
    store = PriceStore(tmp_path)
    store.save("NVDA", _history([100.0], ["2026-03-02"]))
    provider = FakeProvider(
        {
            "NVDA": _history([100.0, 101.0], ["2026-03-02", "2026-03-03"]),
            "AAPL": _history([200.0, 201.0], ["2026-03-02", "2026-03-03"]),
        }
    )
    service = PriceDataService(store=store, provider=provider, default_period="3y")

    result = service.get_histories(
        ["NVDA", "AAPL"],
        start_date="2026-03-02",
        end_date="2026-03-03",
        refresh_missing=True,
    )

    assert provider.calls == [(("AAPL", "NVDA"), "3y", "1d", False)]
    assert result.statuses["NVDA"].source == "refreshed_incremental"
    assert result.statuses["AAPL"].source == "live"
    assert store.path_for("AAPL").exists()
    assert list(result.histories["AAPL"].index) == [pd.Timestamp("2026-03-02"), pd.Timestamp("2026-03-03")]
    assert list(result.histories["NVDA"].index) == [pd.Timestamp("2026-03-02"), pd.Timestamp("2026-03-03")]


def test_price_data_service_marks_incomplete_cache_without_refresh(tmp_path) -> None:
    store = PriceStore(tmp_path)
    store.save("NVDA", _history([100.0], ["2026-03-02"]))
    service = PriceDataService(store=store, provider=FailingProvider())

    result = service.get_histories(["NVDA"], start_date="2026-03-02", end_date="2026-03-03")

    assert result.statuses["NVDA"].source == "cache_incomplete"
    assert "before expected 2026-03-03" in str(result.statuses["NVDA"].note)
    assert list(result.histories["NVDA"].index) == [pd.Timestamp("2026-03-02")]


def test_price_data_service_refreshes_expired_cache_when_all_symbols_share_latest_date(tmp_path) -> None:
    store = PriceStore(tmp_path)
    for symbol, close in (("NVDA", 100.0), ("AAPL", 200.0)):
        store.save(symbol, _history([close], ["2026-06-18"]))
        stale_timestamp = time.time() - 13 * 3600
        os.utime(store.path_for(symbol), (stale_timestamp, stale_timestamp))

    provider = FakeProvider(
        {
            "NVDA": _history([100.0, 101.0], ["2026-06-18", "2026-06-22"]),
            "AAPL": _history([200.0, 201.0], ["2026-06-18", "2026-06-22"]),
        }
    )
    service = PriceDataService(
        store=store,
        provider=provider,
        technical_cache_ttl_hours=12,
    )

    result = service.get_histories(["NVDA", "AAPL"], refresh_missing=True)

    assert provider.calls == [(("NVDA", "AAPL"), "3y", "1d", False)]
    assert result.statuses["NVDA"].source == "refreshed_incremental"
    assert result.statuses["AAPL"].source == "refreshed_incremental"
    assert result.histories["NVDA"].index.max() == pd.Timestamp("2026-06-22")
    assert result.histories["AAPL"].index.max() == pd.Timestamp("2026-06-22")


def test_price_data_service_does_not_refresh_missing_without_flag(tmp_path) -> None:
    service = PriceDataService(store=PriceStore(tmp_path), provider=FailingProvider())

    result = service.get_histories(["MSFT"], start_date="2026-03-02", end_date="2026-03-03")

    assert "MSFT" not in result.histories
    assert result.statuses["MSFT"].source == "missing"


class FailingProvider:
    def get_price_history(self, *args, **kwargs):
        raise AssertionError("provider should not be called")


class FakeProvider:
    def __init__(self, histories: dict[str, pd.DataFrame]) -> None:
        self.histories = histories
        self.calls: list[tuple[tuple[str, ...], str, str, bool]] = []

    def get_price_history(self, symbols, period="3y", interval="1d", *, force_refresh=False, progress_callback=None):
        normalized = tuple(str(symbol).upper() for symbol in symbols)
        self.calls.append((normalized, period, interval, force_refresh))
        histories = {symbol: self.histories[symbol] for symbol in normalized if symbol in self.histories}
        statuses = {
            symbol: FetchStatus(symbol=symbol, dataset="price", source="live", has_data=symbol in histories)
            for symbol in normalized
        }
        return PriceHistoryBatch(histories=histories, statuses=statuses)


def _history(closes: list[float], dates: list[str]) -> pd.DataFrame:
    index = pd.to_datetime(dates)
    return pd.DataFrame(
        {
            "open": [value - 0.5 for value in closes],
            "high": [value + 1.0 for value in closes],
            "low": [value - 1.0 for value in closes],
            "close": closes,
            "adjusted_close": closes,
            "volume": [1_000_000.0 for _ in closes],
        },
        index=index,
    )
