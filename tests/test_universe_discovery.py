from __future__ import annotations

import pandas as pd

from src.data.providers import YahooScreenerConfig, YahooScreenerProvider
from src.data.universe_snapshot_cache import UniverseSnapshotCache


def test_yahoo_screener_normalize_quotes_filters_non_equity() -> None:
    provider = YahooScreenerProvider(YahooScreenerConfig())
    quotes = [
        {
            "symbol": "NVDA",
            "quoteType": "EQUITY",
            "typeDisp": "Equity",
            "longName": "NVIDIA Corporation",
            "marketCap": 1_000_000_000,
            "averageDailyVolume3Month": 2_000_000,
            "regularMarketPrice": 100.0,
            "fullExchangeName": "NasdaqGS",
            "currency": "USD",
        },
        {
            "symbol": "TLT",
            "quoteType": "ETF",
            "typeDisp": "ETF",
            "longName": "Bond ETF",
        },
        {
            "symbol": "BAD",
            "quoteType": "EQUITY",
            "typeDisp": "Preferred",
            "longName": "Preferred Security",
        },
    ]

    rows = provider._normalize_quotes(quotes, "NASDAQ")

    assert len(rows) == 1
    assert rows[0]["ticker"] == "NVDA"
    assert rows[0]["source"] == "yahoo_screener"
    assert rows[0]["exchange"] == "NasdaqGS"


def test_universe_snapshot_cache_roundtrip(tmp_path) -> None:
    cache = UniverseSnapshotCache(tmp_path)
    saved = cache.save(pd.DataFrame({"ticker": ["nvda", "meta"]}), {"source": "test"})
    loaded = cache.load(max_age_days=7)

    assert saved.exists()
    assert loaded.snapshot is not None
    assert loaded.snapshot["ticker"].tolist() == ["NVDA", "META"]
    assert loaded.metadata is not None
    assert loaded.metadata["source"] == "test"
