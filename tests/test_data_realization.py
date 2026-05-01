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
from src.data.results import FetchStatus, FundamentalBatchResult, PriceHistoryBatch, ProfileBatchResult
from src.data.store import DataSnapshotStore
from src.pipeline import ResearchPlatform
from src.scan.rules import ScanConfig


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
        assert (Path(tmp_dir) / "eligible_snapshot" / f"{date_key}.csv").exists()
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
        assert loaded.eligible_snapshot is not None
        assert loaded.scan_hits is not None
        assert loaded.market_metadata is not None
        assert loaded.radar_metadata is not None
        assert loaded.watchlist is not None
        assert loaded.market_metadata["label"] == "Positive"
        assert "market_snapshot" in loaded.market_metadata
        assert "sector_leaders" in loaded.radar_metadata
        assert list(loaded.scan_hits["ticker"]) == ["AAA"]


def test_snapshot_store_preserves_eligible_snapshot_columns_for_saved_run() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = DataSnapshotStore(tmp_dir)
        trade_date = pd.Timestamp("2026-04-08")
        snapshot = pd.DataFrame({"trade_date": [trade_date]}, index=["AAA"])
        eligible_snapshot = pd.DataFrame(
            {
                "trade_date": [trade_date],
                "close": [101.5],
                "rs21": [88.0],
                "atr": [2.5],
                "rel_volume": [1.8],
                "daily_change_pct": [4.2],
                "volume_ratio_20d": [1.4],
            },
            index=["AAA"],
        )
        watchlist = pd.DataFrame({"vcs": [88.0], "atr_21ema_zone": [0.35]}, index=["AAA"])

        store.save_run(
            snapshot,
            eligible_snapshot,
            watchlist,
            pd.DataFrame(),
            {"data_source_label": "live", "config_path": "config/default.yaml", "requested_symbols": ["AAA"]},
        )

        loaded = store.load_latest_run()

        assert loaded.eligible_snapshot is not None
        assert float(loaded.eligible_snapshot.loc["AAA", "close"]) == 101.5
        assert float(loaded.eligible_snapshot.loc["AAA", "rs21"]) == 88.0
        assert float(loaded.eligible_snapshot.loc["AAA", "volume_ratio_20d"]) == 1.4


def test_snapshot_store_does_not_read_legacy_scan_hits_csv(tmp_path: Path) -> None:
    store = DataSnapshotStore(tmp_path)
    trade_date = pd.Timestamp("2026-04-08")
    snapshot = pd.DataFrame({"trade_date": [trade_date], "close": [10.0]}, index=["AAA"])
    watchlist = pd.DataFrame({"duplicate_ticker": [True]}, index=["AAA"])
    fetch_status = pd.DataFrame()

    store.save_run(
        snapshot,
        snapshot.copy(),
        watchlist,
        fetch_status,
        {"data_source_label": "live", "config_path": "config/default.yaml", "requested_symbols": ["AAA"]},
    )
    legacy_dir = tmp_path / "scan_hits"
    legacy_dir.mkdir(exist_ok=True)
    pd.DataFrame([{"ticker": "AAA", "kind": "scan", "name": "Legacy Scan"}]).to_csv(
        legacy_dir / "20260408.csv",
        index=False,
    )

    loaded = store.load_latest_run()

    assert loaded.scan_hits is None


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
    eligible_snapshot["rs21"] = [87.0]
    eligible_snapshot["atr"] = [2.0]
    eligible_snapshot["volume_ratio_20d"] = [1.3]
    eligible_snapshot["daily_change_pct"] = [3.5]
    vcp_fields = {
        "vcp_t1_depth_pct": 20.0,
        "vcp_t2_depth_pct": 12.0,
        "vcp_t3_depth_pct": 5.0,
        "vcp_prior_uptrend_pct": 60.0,
        "vcp_pivot_price": 100.0,
        "vcp_pivot_proximity_pct": 2.0,
        "vcp_volume_dryup_ratio": 0.55,
        "vcp_pivot_breakout": True,
        "vcp_tight_days": 4.0,
    }
    for column, value in vcp_fields.items():
        eligible_snapshot[column] = [value]
    watchlist = pd.DataFrame(
        {
            "name": ["AAA Corp"],
            "hybrid_score": [95.0],
            "overlap_count": [1],
            "vcs": [88.0],
            "duplicate_ticker": [True],
            "earnings_in_7d": [True],
            **{column: [value] for column, value in vcp_fields.items()},
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
    assert float(reused.eligible_snapshot.loc["AAA", "close"]) == 10.0
    assert float(reused.eligible_snapshot.loc["AAA", "rs21"]) == 87.0
    assert reused.earnings_today.empty
    assert platform.load_latest_run_artifacts(symbols=["MSFT"], force_universe_refresh=False) is None


def test_research_platform_rejects_saved_run_missing_vcp_columns() -> None:
    platform = ResearchPlatform()
    platform.scan_config = ScanConfig(enabled_scan_rules=("VCP 3T",))

    assert platform._saved_run_has_required_scan_columns(
        pd.DataFrame({"close": [10.0]}, index=["AAA"]),
        pd.DataFrame({"close": [10.0]}, index=["AAA"]),
    ) is False


def test_research_platform_passes_force_price_refresh_to_price_provider() -> None:
    platform = ResearchPlatform()
    calls: list[dict[str, object]] = []
    history = pd.DataFrame(
        {
            "open": [10.0],
            "high": [11.0],
            "low": [9.0],
            "close": [10.5],
            "adjusted_close": [10.5],
            "volume": [1000.0],
        },
        index=pd.to_datetime(["2026-04-10"]),
    )

    class FakePriceProvider:
        def get_price_history(self, symbols, period="18mo", interval="1d", *, force_refresh=False):
            calls.append(
                {"symbols": list(symbols), "period": period, "interval": interval, "force_refresh": force_refresh}
            )
            histories = {symbol: history for symbol in symbols}
            statuses = {
                symbol: FetchStatus(symbol=symbol, dataset="price", source="live", has_data=True)
                for symbol in symbols
            }
            return PriceHistoryBatch(histories=histories, statuses=statuses)

    class EmptyProfileProvider:
        def get_profiles(self, symbols):
            return ProfileBatchResult(profiles=[], statuses={})

    class EmptyFundamentalProvider:
        def get_fundamentals(self, symbols):
            return FundamentalBatchResult(fundamentals=[], statuses={})

    platform.price_provider = FakePriceProvider()
    platform.profile_provider = EmptyProfileProvider()
    platform.fundamental_provider = EmptyFundamentalProvider()

    platform._load_data(["AAA"], None, "manual", force_price_refresh=True)

    assert calls
    assert calls[0]["force_refresh"] is True
