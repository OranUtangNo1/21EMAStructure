from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pandas as pd

from src.data.cache import CacheLayer
from src.data.quality import append_data_quality, summarize_data_source_label
from src.data.store import DataSnapshotStore


def test_cache_layer_allows_stale_reads() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = CacheLayer(tmp_dir)
        frame = pd.DataFrame(
            {
                "open": [10.0, 11.0],
                "high": [11.0, 12.0],
                "low": [9.0, 10.0],
                "close": [10.5, 11.5],
                "adjusted_close": [10.5, 11.5],
                "volume": [1000.0, 1200.0],
            },
            index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
        )
        cache.save_csv("prices_TEST_18mo_1d", frame)
        path = Path(tmp_dir) / "prices_TEST_18mo_1d.csv"
        old_timestamp = time.time() - 3 * 3600
        os.utime(path, (old_timestamp, old_timestamp))

        assert cache.load_csv("prices_TEST_18mo_1d", ttl_hours=1) is None
        stale = cache.load_csv("prices_TEST_18mo_1d", ttl_hours=1, allow_stale=True)
        assert stale is not None
        assert list(stale.columns) == ["open", "high", "low", "close", "adjusted_close", "volume"]


def test_append_data_quality_marks_live_and_stale_data() -> None:
    snapshot = pd.DataFrame(
        {
            "name": ["AAA Corp", "BBB Corp"],
            "market_cap": [1_000_000_000.0, None],
            "sector": ["Technology", None],
            "industry": ["Software", None],
            "ipo_date": [pd.Timestamp("2020-01-01"), None],
            "eps_growth": [50.0, None],
            "revenue_growth": [20.0, None],
            "earnings_date": [pd.Timestamp("2026-04-15"), None],
            "price_data_source": ["live", "cache_stale"],
            "profile_data_source": ["live", "missing"],
            "fundamental_data_source": ["live", "missing"],
        },
        index=["AAA", "BBB"],
    )
    result = append_data_quality(snapshot)
    assert result.loc["AAA", "data_quality_label"] == "live"
    assert result.loc["BBB", "data_quality_label"] in {"weak", "missing"}
    assert "stale price cache" in result.loc["BBB", "data_warning"]


def test_snapshot_store_persists_run_outputs() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = DataSnapshotStore(tmp_dir)
        snapshot = pd.DataFrame({"close": [10.0]}, index=["AAA"])
        eligible_snapshot = snapshot.copy()
        watchlist = snapshot.copy()
        fetch_status = pd.DataFrame(
            [{"symbol": "AAA", "dataset": "price", "source": "live", "has_data": True, "fetched_at": None, "note": None}]
        )
        run_dir = store.save_run(snapshot, eligible_snapshot, watchlist, fetch_status, {"data_source_label": "live"})
        assert (run_dir / "snapshot.csv").exists()
        assert (run_dir / "eligible_snapshot.csv").exists()
        assert (run_dir / "watchlist.csv").exists()
        assert (run_dir / "fetch_status.csv").exists()
        assert (run_dir / "metadata.json").exists()


def test_summarize_data_source_label_handles_mixed_sources() -> None:
    frame = pd.DataFrame(
        [
            {"symbol": "AAA", "dataset": "price", "source": "live"},
            {"symbol": "AAA", "dataset": "profile", "source": "cache_stale"},
        ]
    )
    assert summarize_data_source_label(frame) == "live + cache"
