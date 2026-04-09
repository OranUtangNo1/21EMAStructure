from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pandas as pd

from src.dashboard.market import MarketConditionResult
from src.dashboard.radar import RadarResult
from src.data.cache import CacheLayer
from src.data.quality import append_data_quality, summarize_data_source_label
from src.data.store import DataSnapshotStore
from src.pipeline import ResearchPlatform


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
        assert run_dir.suffix == ".json"
        date_key = run_dir.stem
        assert (Path(tmp_dir) / "watchlist" / f"{date_key}.csv").exists()
        assert (Path(tmp_dir) / "run_metadata" / f"{date_key}.json").exists()


def test_summarize_data_source_label_handles_mixed_sources() -> None:
    frame = pd.DataFrame(
        [
            {"symbol": "AAA", "dataset": "price", "source": "live"},
            {"symbol": "AAA", "dataset": "profile", "source": "cache_stale"},
        ]
    )
    assert summarize_data_source_label(frame) == "live + cache"


def _sample_market_result(trade_date: pd.Timestamp) -> MarketConditionResult:
    snapshot = pd.DataFrame(
        [
            {"TICKER": "SPY", "NAME": "S&P 500", "PRICE": 500.0, "DAY %": 1.2, "VOL vs 50D %": 5.0, "21EMA POS": "above 21EMA High"}
        ]
    )
    factors = pd.DataFrame([{"TICKER": "VUG", "NAME": "Growth", "REL 1W %": 1.1, "REL 1M %": 2.2, "REL 1Y %": 3.3}])
    return MarketConditionResult(
        trade_date=trade_date,
        score=72.5,
        label="Positive",
        score_1d_ago=70.0,
        score_1w_ago=66.0,
        score_1m_ago=61.0,
        score_3m_ago=55.0,
        label_1d_ago="Positive",
        label_1w_ago="Positive",
        label_1m_ago="Positive",
        label_3m_ago="Neutral",
        component_scores={"pct_above_sma10": 75.0, "vix_score": 50.0},
        breadth_summary={"pct_above_sma10": 75.0},
        performance_overview={"% YTD": 12.3},
        high_vix_summary={"S2W HIGH %": 8.0, "VIX": 17.5},
        market_snapshot=snapshot,
        leadership_snapshot=snapshot.copy(),
        external_snapshot=snapshot.copy(),
        factors_vs_sp500=factors,
        s5th_series=pd.DataFrame(),
        vix_close=17.5,
        update_time="2026-04-08T08:00:00",
    )


def _sample_radar_result() -> RadarResult:
    leaders = pd.DataFrame(
        [
            {
                "RS": 95.0,
                "1D": 80.0,
                "1W": 85.0,
                "1M": 90.0,
                "TICKER": "QQQ",
                "NAME": "Nasdaq 100",
                "DAY %": 1.2,
                "WK %": 2.3,
                "MTH %": 4.5,
                "RS DAY%": 0.4,
                "RS WK%": 0.8,
                "RS MTH%": 1.6,
                "52W HIGH": "Yes",
            }
        ]
    )
    industry = leaders.copy()
    industry["MAJOR STOCKS"] = "NVDA, MSFT"
    movers = pd.DataFrame([{"RS": 95.0, "TICKER": "QQQ", "NAME": "Nasdaq 100", "PRICE": 500.0, "DAY %": 1.2, "RS DAY%": 0.4}])
    weekly = movers.rename(columns={"DAY %": "WK %", "RS DAY%": "RS WK%"})
    return RadarResult(
        sector_leaders=leaders,
        industry_leaders=industry,
        top_daily=movers,
        top_weekly=weekly,
        update_time="2026-04-08T08:00:00",
    )


def test_snapshot_store_loads_latest_run_with_dashboard_payloads() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = DataSnapshotStore(tmp_dir)
        trade_date = pd.Timestamp("2026-04-08")
        snapshot = pd.DataFrame({"trade_date": [trade_date], "close": [10.0], "earnings_today": [True]}, index=["AAA"])
        eligible_snapshot = snapshot.copy()
        watchlist = pd.DataFrame(
            {
                "name": ["AAA Corp"],
                "hybrid_score": [95.0],
                "overlap_count": [1],
                "vcs": [88.0],
                "duplicate_ticker": [True],
                "earnings_in_7d": [True],
            },
            index=["AAA"],
        )
        fetch_status = pd.DataFrame(
            [{"symbol": "AAA", "dataset": "price", "source": "live", "has_data": True, "fetched_at": None, "note": None}]
        )
        scan_hits = pd.DataFrame([{"ticker": "AAA", "kind": "scan", "name": "Momentum 97"}])

        store.save_run(
            snapshot,
            eligible_snapshot,
            watchlist,
            fetch_status,
            {"data_source_label": "live", "config_path": "config/default.yaml", "manual_symbols_input": [], "requested_symbols": ["AAA"]},
            scan_hits=scan_hits,
            market_result=_sample_market_result(trade_date),
            radar_result=_sample_radar_result(),
        )

        loaded = store.load_latest_run()

        assert loaded.path is not None
        assert loaded.scan_hits is not None
        assert loaded.market_metadata is not None
        assert loaded.radar_metadata is not None
        assert loaded.watchlist is not None
        assert loaded.market_metadata["label"] == "Positive"
        assert "market_snapshot" in loaded.market_metadata
        assert "sector_leaders" in loaded.radar_metadata
        assert list(loaded.scan_hits["ticker"]) == ["AAA"]


def test_research_platform_reuses_same_day_saved_run(tmp_path: Path) -> None:
    platform = ResearchPlatform()
    platform.snapshot_store = DataSnapshotStore(tmp_path)
    trade_date = platform._expected_trade_date()
    first_scan_name = platform.scan_config.card_sections[0].scan_name

    snapshot = pd.DataFrame(
        {
            "trade_date": [trade_date],
            "close": [10.0],
            "market_cap": [1_000_000_000.0],
            "name": ["AAA Corp"],
            "sector": ["Technology"],
            "industry": ["Software"],
            "hybrid_score": [95.0],
            "earnings_today": [True],
        },
        index=["AAA"],
    )
    eligible_snapshot = snapshot.copy()
    watchlist = pd.DataFrame(
        {
            "name": ["AAA Corp"],
            "hybrid_score": [95.0],
            "overlap_count": [1],
            "vcs": [88.0],
            "duplicate_ticker": [True],
            "earnings_in_7d": [True],
        },
        index=["AAA"],
    )
    fetch_status = pd.DataFrame(
        [{"symbol": "AAA", "dataset": "price", "source": "live", "has_data": True, "fetched_at": None, "note": None}]
    )
    scan_hits = pd.DataFrame([{"ticker": "AAA", "kind": "scan", "name": first_scan_name}])

    platform.snapshot_store.save_run(
        snapshot,
        eligible_snapshot,
        watchlist,
        fetch_status,
        {
            "run_created_at": "2026-04-08T08:00:00",
            "config_path": str(platform.config_path),
            "manual_symbols_input": [],
            "requested_symbols": ["AAA"],
            "data_source_label": "live",
            "used_sample_data": False,
            "data_health_summary": {"sample_count": 0, "stale_cache_count": 0, "missing_count": 0},
            "market_score": 72.5,
            "market_label": "Positive",
            "universe_mode": "default_symbols",
            "universe_snapshot_path": None,
        },
        scan_hits=scan_hits,
        market_result=_sample_market_result(trade_date),
        radar_result=_sample_radar_result(),
    )

    reused = platform.load_latest_run_artifacts(symbols=None, force_universe_refresh=False)

    assert reused is not None
    assert reused.artifact_origin == "same_day_saved_run"
    assert reused.market_result.label == "Positive"
    assert reused.radar_result.top_daily.iloc[0]["TICKER"] == "QQQ"
    assert reused.earnings_today.empty
    assert platform.load_latest_run_artifacts(symbols=["MSFT"], force_universe_refresh=False) is None
