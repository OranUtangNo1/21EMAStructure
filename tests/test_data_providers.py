from __future__ import annotations

import os
import time
from datetime import date

import pandas as pd

from src.data.cache import CacheLayer
from src.data.finviz_provider import (
    FinvizScreenerConfig,
    FinvizScreenerProvider,
    build_fundamental_batch_from_snapshot,
    build_profile_batch_from_snapshot,
)
from src.data.providers import YFinancePriceDataProvider


def test_finviz_screener_provider_discovers_filtered_snapshot(monkeypatch) -> None:
    nasdaq_frame = pd.DataFrame(
        [
            {
                "Ticker": "NVDA",
                "Company": "NVIDIA Corporation",
                "Sector": "Technology",
                "Industry": "Semiconductors",
                "Country": "USA",
                "Market Cap.": "2.5T",
                "EPS growth qtr over qtr": "45.0%",
                "Sales growth qtr over qtr": "30.0%",
                "Earnings Date": "Apr-30-2026",
            },
            {
                "Ticker": "XLVH",
                "Company": "Healthcare Name",
                "Sector": "Healthcare",
                "Industry": "Biotech",
                "Country": "USA",
                "Market Cap.": "5.0B",
                "EPS growth qtr over qtr": "10.0%",
                "Sales growth qtr over qtr": "8.0%",
                "Earnings Date": "Today",
            },
            {
                "Ticker": "SMAL",
                "Company": "Too Small Corp",
                "Sector": "Technology",
                "Industry": "Software",
                "Country": "USA",
                "Market Cap.": "500M",
                "EPS growth qtr over qtr": "5.0%",
                "Sales growth qtr over qtr": "4.0%",
                "Earnings Date": "May-01-2026",
            },
        ]
    )
    nyse_frame = pd.DataFrame(
        [
            {
                "Ticker": "IBM",
                "Company": "International Business Machines",
                "Sector": "Technology",
                "Industry": "Information Technology Services",
                "Country": "USA",
                "Market Cap.": "250B",
                "EPS growth qtr over qtr": "12.0%",
                "Sales growth qtr over qtr": "3.0%",
                "Earnings Date": "Tomorrow",
            }
        ]
    )
    frames = {"NASDAQ": nasdaq_frame, "NYSE": nyse_frame, "AMEX": pd.DataFrame()}
    calls: list[dict[str, object]] = []

    class FakeCustom:
        def __init__(self) -> None:
            self.filters_dict: dict[str, object] = {}

        def set_filter(self, signal: str = "", filters_dict: dict[str, object] | None = None, ticker: str = "") -> None:
            self.filters_dict = filters_dict or {}

        def screener_view(self, order: str, limit: int, verbose: int, ascend: bool, columns: list[int], sleep_sec: int):
            exchange = str(self.filters_dict["Exchange"])
            calls.append({"exchange": exchange, "order": order, "limit": limit, "columns": list(columns)})
            return frames[exchange].copy()

    monkeypatch.setattr("src.data.finviz_provider.Custom", FakeCustom)

    provider = FinvizScreenerProvider(
        FinvizScreenerConfig(
            allowed_exchanges=("NASDAQ", "NYSE", "AMEX"),
            excluded_sectors=("Healthcare",),
            max_symbols=10,
            min_market_cap=1_000_000_000.0,
        )
    )

    result = provider.discover()

    assert list(result.snapshot["ticker"]) == ["NVDA", "IBM"]
    assert result.snapshot.loc[result.snapshot["ticker"] == "NVDA", "earnings_date"].iloc[0] == date(2026, 4, 30)
    assert result.snapshot.loc[result.snapshot["ticker"] == "IBM", "earnings_date"].iloc[0] >= date.today()
    assert result.snapshot.loc[result.snapshot["ticker"] == "NVDA", "eps_growth"].iloc[0] == 45.0
    assert result.metadata["provider"] == "finviz"
    assert calls[0]["columns"] == provider.COLUMN_IDS


def test_snapshot_helpers_build_profile_and_fundamental_batches() -> None:
    snapshot = pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "name": "NVIDIA Corporation",
                "market_cap": 2_500_000_000_000.0,
                "sector": "Technology",
                "industry": "Semiconductors",
                "eps_growth": 45.0,
                "revenue_growth": 30.0,
                "earnings_date": date(2026, 4, 30),
                "discovered_at": "2026-03-30T09:00:00",
            }
        ]
    )

    profile_batch = build_profile_batch_from_snapshot(snapshot, ["NVDA", "MSFT"], "cache_fresh")
    fundamental_batch = build_fundamental_batch_from_snapshot(snapshot, ["NVDA", "MSFT"], "cache_fresh")

    assert [profile.ticker for profile in profile_batch.profiles] == ["NVDA"]
    assert profile_batch.statuses["NVDA"].source == "cache_fresh"
    assert [fundamental.ticker for fundamental in fundamental_batch.fundamentals] == ["NVDA"]
    assert fundamental_batch.fundamentals[0].earnings_date == date(2026, 4, 30)


def test_yfinance_price_provider_batches_downloads_and_merges_stale_cache(tmp_path, monkeypatch) -> None:
    cache = CacheLayer(tmp_path)
    stale_index = pd.to_datetime(["2026-03-27"])
    cache.save_csv("prices_NVDA_18mo_1d", _normalized_history(300.0, stale_index))
    cache.save_csv("prices_META_18mo_1d", _normalized_history(400.0, stale_index))
    stale_timestamp = time.time() - 48 * 3600
    os.utime(tmp_path / "prices_NVDA_18mo_1d.csv", (stale_timestamp, stale_timestamp))
    os.utime(tmp_path / "prices_META_18mo_1d.csv", (stale_timestamp, stale_timestamp))

    calls: list[tuple[tuple[str, ...], str]] = []

    class FakeYF:
        def download(self, tickers, period, interval, auto_adjust, progress, threads, group_by):
            symbols = tuple(tickers)
            calls.append((symbols, period))
            fresh_index = pd.to_datetime(["2026-03-30"])
            if symbols == ("AAPL", "MSFT"):
                return _multi_symbol_download(
                    {
                        "AAPL": _raw_history(100.0, fresh_index),
                        "MSFT": _raw_history(200.0, fresh_index),
                    }
                )
            if symbols == ("NVDA", "META"):
                return _multi_symbol_download(
                    {
                        "NVDA": _raw_history(310.0, fresh_index),
                        "META": _raw_history(410.0, fresh_index),
                    }
                )
            raise AssertionError(f"unexpected symbols: {symbols}")

    monkeypatch.setattr("src.data.providers.yf", FakeYF())

    provider = YFinancePriceDataProvider(
        cache,
        technical_ttl_hours=1,
        allow_stale_cache_on_failure=True,
        batch_size=2,
        max_retries=1,
        request_sleep_seconds=0.0,
        retry_backoff_multiplier=1.0,
        incremental_period="5d",
    )
    result = provider.get_price_history(["AAPL", "MSFT", "NVDA", "META"], period="18mo")

    assert calls == [(("AAPL", "MSFT"), "18mo"), (("NVDA", "META"), "5d")]
    assert result.statuses["AAPL"].source == "live"
    assert result.statuses["NVDA"].source == "live"
    assert len(result.histories["NVDA"]) == 2
    assert result.histories["NVDA"].index.max() == pd.Timestamp("2026-03-30")
    assert result.histories["META"].loc[pd.Timestamp("2026-03-30"), "close"] == 410.0


def test_yfinance_price_provider_uses_stale_cache_when_batch_fails(tmp_path, monkeypatch) -> None:
    cache = CacheLayer(tmp_path)
    stale_index = pd.to_datetime(["2026-03-27"])
    stale_frame = _normalized_history(300.0, stale_index)
    cache.save_csv("prices_NVDA_18mo_1d", stale_frame)
    stale_timestamp = time.time() - 48 * 3600
    os.utime(tmp_path / "prices_NVDA_18mo_1d.csv", (stale_timestamp, stale_timestamp))

    class FakeYF:
        def download(self, *args, **kwargs):
            raise RuntimeError("network down")

    monkeypatch.setattr("src.data.providers.yf", FakeYF())

    provider = YFinancePriceDataProvider(
        cache,
        technical_ttl_hours=1,
        allow_stale_cache_on_failure=True,
        batch_size=2,
        max_retries=2,
        request_sleep_seconds=0.0,
        retry_backoff_multiplier=1.0,
        incremental_period="5d",
    )
    result = provider.get_price_history(["NVDA"], period="18mo")

    assert result.statuses["NVDA"].source == "cache_stale"
    assert "RuntimeError" in (result.statuses["NVDA"].note or "")
    pd.testing.assert_frame_equal(result.histories["NVDA"], stale_frame)


def _raw_history(base_close: float, index: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [base_close - 1.0 for _ in index],
            "High": [base_close + 1.0 for _ in index],
            "Low": [base_close - 2.0 for _ in index],
            "Close": [base_close for _ in index],
            "Adj Close": [base_close for _ in index],
            "Volume": [1_000_000.0 for _ in index],
        },
        index=index,
    )


def _normalized_history(base_close: float, index: pd.DatetimeIndex) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "open": [base_close - 1.0 for _ in index],
            "high": [base_close + 1.0 for _ in index],
            "low": [base_close - 2.0 for _ in index],
            "close": [base_close for _ in index],
            "adjusted_close": [base_close for _ in index],
            "volume": [1_000_000.0 for _ in index],
        },
        index=index,
    )
    frame.index.name = "date"
    return frame


def _multi_symbol_download(symbol_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    columns: list[tuple[str, str]] = []
    data: dict[tuple[str, str], pd.Series] = {}
    first_index: pd.DatetimeIndex | None = None
    for symbol, frame in symbol_frames.items():
        if first_index is None:
            first_index = frame.index
        for column in frame.columns:
            key = (symbol, column)
            columns.append(key)
            data[key] = frame[column]
    assert first_index is not None
    return pd.DataFrame(data, index=first_index, columns=pd.MultiIndex.from_tuples(columns))