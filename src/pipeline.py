from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time as dt_time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from pandas.tseries.offsets import BDay

from src.configuration import load_settings
from src.dashboard.market import MarketConditionConfig, MarketConditionResult, MarketConditionScorer
from src.dashboard.radar import RadarConfig, RadarResult, RadarViewModelBuilder
from src.dashboard.watchlist import ScanCardViewModel, WatchlistViewModelBuilder
from src.data.cache import CacheLayer
from src.data.models import FundamentalSnapshot, SymbolProfile
from src.data.finviz_provider import (
    FinvizScreenerConfig,
    FinvizScreenerProvider,
    build_fundamental_batch_from_snapshot,
    build_profile_batch_from_snapshot,
)
from src.data.providers import (
    YahooScreenerConfig,
    YahooScreenerProvider,
    YFinanceFundamentalDataProvider,
    YFinancePriceDataProvider,
    YFinanceProfileDataProvider,
)
from src.data.quality import append_data_quality, summarize_data_health, summarize_data_source_label
from src.data.results import FetchStatus, FundamentalBatchResult, PriceHistoryBatch, ProfileBatchResult
from src.data.sample import SampleDataFactory
from src.data.store import DataSnapshotStore
from src.data.universe import UniverseBuilder, UniverseConfig
from src.indicators.core import IndicatorCalculator, IndicatorConfig
from src.scan.runner import ScanRunner
from src.scan.rules import ScanConfig
from src.scoring.fundamental import FundamentalScoreConfig, FundamentalScorer
from src.scoring.hybrid import HybridScoreCalculator, HybridScoreConfig
from src.scoring.industry import IndustryScoreConfig, IndustryScorer
from src.scoring.rs import RSConfig, RSScorer
from src.scoring.vcs import VCSCalculator, VCSConfig


@dataclass(slots=True)
class PlatformArtifacts:
    """Full result bundle for active screening pages and tests."""

    snapshot: pd.DataFrame
    eligible_snapshot: pd.DataFrame
    watchlist: pd.DataFrame
    duplicate_tickers: pd.DataFrame
    watchlist_cards: list[ScanCardViewModel]
    earnings_today: pd.DataFrame
    scan_hits: pd.DataFrame
    benchmark_history: pd.DataFrame
    vix_history: pd.DataFrame
    market_result: MarketConditionResult
    radar_result: RadarResult
    used_sample_data: bool
    data_source_label: str
    fetch_status: pd.DataFrame
    data_health_summary: dict[str, float | int]
    run_directory: str | None
    universe_mode: str
    resolved_symbols: list[str]
    universe_snapshot_path: str | None
    artifact_origin: str


class ResearchPlatform:
    """Orchestrate active screening workflow: data, indicators, scans, and dashboard outputs."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self.root = Path(__file__).resolve().parents[1]
        resolved_config = Path(config_path).expanduser() if config_path is not None else self.root / "config" / "default.yaml"
        self.config_path = resolved_config.resolve(strict=False)
        self.settings = load_settings(config_path)
        app_settings = self.settings.get("app", {})
        data_settings = self.settings.get("data", {})
        universe_settings = self.settings.get("universe", {})
        discovery_settings = self.settings.get("universe_discovery", {})

        cache_dir = self.root / app_settings.get("cache_dir", "data_cache")
        self.cache = CacheLayer(cache_dir)
        self.sample_factory = SampleDataFactory()
        self.snapshot_store = DataSnapshotStore(self.root / app_settings.get("snapshot_dir", "data_runs"))
        self.allow_sample_fallback = bool(app_settings.get("use_sample_data_if_fetch_fails", False))

        self.indicator_calculator = IndicatorCalculator(IndicatorConfig.from_dict(self.settings.get("indicators", {})))
        self.universe_builder = UniverseBuilder(UniverseConfig.from_dict(universe_settings))
        self.rs_scorer = RSScorer(RSConfig.from_dict(self.settings.get("scoring", {}).get("rs", {})))
        self.fundamental_scorer = FundamentalScorer(
            FundamentalScoreConfig.from_dict(self.settings.get("scoring", {}).get("fundamental", {}))
        )
        self.industry_scorer = IndustryScorer(
            IndustryScoreConfig.from_dict(self.settings.get("scoring", {}).get("industry", {}))
        )
        self.hybrid_calculator = HybridScoreCalculator(
            HybridScoreConfig.from_dict(self.settings.get("scoring", {}).get("hybrid", {}))
        )
        self.vcs_calculator = VCSCalculator(VCSConfig.from_dict(self.settings.get("scoring", {}).get("vcs", {})))
        self.scan_config = ScanConfig.from_dict(self.settings.get("scan", {}))
        self.scan_runner = ScanRunner(self.scan_config)
        self.market_scorer = MarketConditionScorer(MarketConditionConfig.from_dict(self.settings.get("market", {})))
        self.watchlist_builder = WatchlistViewModelBuilder(self.scan_config)
        self.radar_builder = RadarViewModelBuilder(RadarConfig.from_dict(self.settings.get("radar", {})))

        allow_stale = bool(data_settings.get("allow_stale_cache_on_failure", True))
        self.persist_research_snapshots = bool(data_settings.get("persist_research_snapshots", True))
        self.price_provider = YFinancePriceDataProvider(
            self.cache,
            technical_ttl_hours=int(data_settings.get("technical_cache_ttl_hours", 12)),
            allow_stale_cache_on_failure=allow_stale,
            batch_size=int(data_settings.get("price_batch_size", 80)),
            max_retries=int(data_settings.get("price_max_retries", 3)),
            request_sleep_seconds=float(data_settings.get("price_request_sleep_seconds", 2.0)),
            retry_backoff_multiplier=float(data_settings.get("price_retry_backoff_multiplier", 2.0)),
            incremental_period=data_settings.get("price_incremental_period", "5d"),
        )
        self.profile_provider = YFinanceProfileDataProvider(
            self.cache,
            profile_ttl_hours=int(data_settings.get("profile_cache_ttl_hours", 168)),
            allow_stale_cache_on_failure=allow_stale,
        )
        self.fundamental_provider = YFinanceFundamentalDataProvider(
            self.cache,
            fundamental_ttl_hours=int(data_settings.get("fundamental_cache_ttl_hours", 24)),
            allow_stale_cache_on_failure=allow_stale,
        )

        discovery_payload = {**universe_settings, **discovery_settings}
        self.universe_discovery_enabled = bool(discovery_settings.get("enabled", True))
        self.use_snapshot_when_no_manual_symbols = bool(discovery_settings.get("use_snapshot_when_no_manual_symbols", True))
        self.universe_snapshot_ttl_days = int(discovery_settings.get("snapshot_ttl_days", 7))
        self.discovery_provider_name = str(discovery_settings.get("provider", "finviz")).strip().lower()
        if self.discovery_provider_name == "finviz":
            self.screener_provider = FinvizScreenerProvider(FinvizScreenerConfig.from_dict(discovery_payload))
        elif self.discovery_provider_name == "yahoo":
            self.screener_provider = YahooScreenerProvider(YahooScreenerConfig.from_dict(discovery_payload))
        else:
            raise ValueError(f"Unsupported universe discovery provider: {self.discovery_provider_name}")

    def run(
        self,
        symbols: list[str] | None = None,
        force_universe_refresh: bool = False,
        force_price_refresh: bool = False,
    ) -> PlatformArtifacts:
        manual_symbols = self._normalize_symbols(symbols or [])
        active_symbols, universe_mode, universe_snapshot_path, universe_snapshot = self._resolve_active_symbols(symbols, force_universe_refresh)
        if not active_symbols:
            raise ValueError("At least one symbol is required.")

        price_batch, benchmark_history, vix_history, profile_batch, fundamental_batch = self._load_data(
            active_symbols,
            universe_snapshot,
            universe_mode,
            force_price_refresh=force_price_refresh,
        )
        live_symbol_histories = self._build_indicator_histories(price_batch.histories, active_symbols)
        if not live_symbol_histories:
            raise RuntimeError("No price histories were available for the requested symbols.")

        snapshot = self._build_snapshot(live_symbol_histories, profile_batch.profiles, fundamental_batch.fundamentals)
        snapshot = self._attach_status_columns(snapshot, price_batch.statuses, profile_batch.statuses, fundamental_batch.statuses)
        snapshot = self.rs_scorer.score(snapshot, live_symbol_histories, benchmark_history)
        snapshot = self.fundamental_scorer.score(snapshot)
        snapshot = self.industry_scorer.score(snapshot)
        snapshot = self.hybrid_calculator.score(snapshot)
        snapshot = self.vcs_calculator.add_scores(snapshot, live_symbol_histories)
        snapshot = self._postprocess_snapshot(snapshot)
        snapshot = append_data_quality(snapshot)

        eligible_snapshot = self.universe_builder.filter(snapshot)
        if eligible_snapshot.empty and not snapshot.empty:
            eligible_snapshot = snapshot.sort_values(["data_quality_score", "hybrid_score"], ascending=[False, False]).copy()

        scan_result = self.scan_runner.run(eligible_snapshot)
        watchlist = self.watchlist_builder.build(scan_result.watchlist)
        duplicate_tickers = self.watchlist_builder.build_duplicate_tickers(scan_result.watchlist, scan_result.hits, self.scan_config.duplicate_min_count)
        watchlist_cards = self.watchlist_builder.build_scan_cards(scan_result.watchlist, scan_result.hits)
        earnings_today = self.watchlist_builder.build_earnings_today(eligible_snapshot)

        radar_histories = self._build_indicator_histories(price_batch.histories, self.radar_builder.required_symbols())
        radar_result = self.radar_builder.build(radar_histories, benchmark_history)
        market_histories = self._build_indicator_histories(price_batch.histories, self.market_scorer.required_symbols())

        fetch_status = self._build_fetch_status_frame(price_batch.statuses, profile_batch.statuses, fundamental_batch.statuses)
        data_health_summary = summarize_data_health(fetch_status)
        data_source_label = summarize_data_source_label(fetch_status)
        used_sample_data = bool((fetch_status["source"] == "sample").any()) if not fetch_status.empty else False
        market_result = self.market_scorer.score(live_symbol_histories, market_histories, benchmark_history)
        run_directory = self._persist_run(
            snapshot,
            eligible_snapshot,
            watchlist,
            fetch_status,
            data_source_label,
            data_health_summary,
            market_result,
            radar_result,
            scan_result.hits,
            active_symbols,
            manual_symbols,
            universe_mode,
            universe_snapshot_path,
        )

        return PlatformArtifacts(
            snapshot=snapshot,
            eligible_snapshot=eligible_snapshot,
            watchlist=watchlist,
            duplicate_tickers=duplicate_tickers,
            watchlist_cards=watchlist_cards,
            earnings_today=earnings_today,
            scan_hits=scan_result.hits,
            benchmark_history=benchmark_history,
            vix_history=vix_history,
            market_result=market_result,
            radar_result=radar_result,
            used_sample_data=used_sample_data,
            data_source_label=data_source_label,
            fetch_status=fetch_status,
            data_health_summary=data_health_summary,
            run_directory=run_directory,
            universe_mode=universe_mode,
            resolved_symbols=active_symbols,
            universe_snapshot_path=universe_snapshot_path,
            artifact_origin="pipeline_recomputed",
        )

    def load_latest_run_artifacts(self, symbols: list[str] | None = None, force_universe_refresh: bool = False) -> PlatformArtifacts | None:
        if force_universe_refresh or not self.persist_research_snapshots:
            return None

        loaded = self.snapshot_store.load_latest_run()
        if (
            loaded.path is None
            or loaded.metadata is None
            or loaded.watchlist is None
            or loaded.scan_hits is None
            or loaded.market_metadata is None
            or loaded.radar_metadata is None
        ):
            return None

        requested_manual_symbols = self._normalize_symbols(symbols or [])
        if not self._saved_run_matches_request(loaded.metadata, requested_manual_symbols):
            return None

        trade_date = self._trade_date_from_metadata(loaded.metadata)
        expected_trade_date = self._expected_trade_date()
        if trade_date is None or expected_trade_date is None or trade_date.normalize() != expected_trade_date.normalize():
            return None

        market_result = self._restore_market_result(loaded.market_metadata, loaded.market_frames)
        radar_result = self._restore_radar_result(loaded.radar_metadata, loaded.radar_frames)
        if market_result is None or radar_result is None:
            return None

        minimal_snapshot = self._minimal_snapshot_for_saved_run(loaded.watchlist.index.tolist(), trade_date)
        eligible_snapshot = minimal_snapshot.copy()

        duplicate_tickers = self.watchlist_builder.build_duplicate_tickers(
            loaded.watchlist,
            loaded.scan_hits,
            self.scan_config.duplicate_min_count,
        )
        watchlist_cards = self.watchlist_builder.build_scan_cards(loaded.watchlist, loaded.scan_hits)
        earnings_today = pd.DataFrame(columns=["Ticker", "Name", "Sector", "Industry", "Hybrid-RS"])
        fetch_status = pd.DataFrame()
        data_health_summary = self._data_health_summary_from_metadata(loaded.metadata)
        data_source_label = str(loaded.metadata.get("data_source_label") or "unknown")
        used_sample_data = bool(loaded.metadata.get("used_sample_data", False))

        requested_symbols = loaded.metadata.get("requested_symbols", [])
        resolved_symbols = self._normalize_symbols(requested_symbols) if isinstance(requested_symbols, list) else []
        if not resolved_symbols:
            resolved_symbols = self._normalize_symbols(list(loaded.watchlist.index))

        return PlatformArtifacts(
            snapshot=minimal_snapshot,
            eligible_snapshot=eligible_snapshot,
            watchlist=loaded.watchlist,
            duplicate_tickers=duplicate_tickers,
            watchlist_cards=watchlist_cards,
            earnings_today=earnings_today,
            scan_hits=loaded.scan_hits,
            benchmark_history=pd.DataFrame(),
            vix_history=pd.DataFrame(),
            market_result=market_result,
            radar_result=radar_result,
            used_sample_data=used_sample_data,
            data_source_label=data_source_label,
            fetch_status=fetch_status,
            data_health_summary=data_health_summary,
            run_directory=loaded.path,
            universe_mode=str(loaded.metadata.get("universe_mode", "persisted_run")),
            resolved_symbols=resolved_symbols,
            universe_snapshot_path=str(loaded.metadata.get("universe_snapshot_path")) if loaded.metadata.get("universe_snapshot_path") else None,
            artifact_origin="same_day_saved_run",
        )

    def _saved_run_matches_request(self, metadata: dict[str, object], manual_symbols: list[str]) -> bool:
        config_path_value = metadata.get("config_path")
        if not config_path_value:
            return False
        saved_config_path = Path(str(config_path_value)).expanduser().resolve(strict=False)
        if saved_config_path != self.config_path:
            return False

        saved_manual_symbols = metadata.get("manual_symbols_input", [])
        if not isinstance(saved_manual_symbols, list):
            return False
        return self._normalize_symbols(saved_manual_symbols) == manual_symbols

    def _expected_trade_date(self) -> pd.Timestamp:
        now_eastern = datetime.now(ZoneInfo("America/New_York"))
        current_date = pd.Timestamp(now_eastern.date())
        if now_eastern.weekday() >= 5:
            return (current_date - BDay(1)).normalize()
        if now_eastern.time() < dt_time(16, 0):
            return (current_date - BDay(1)).normalize()
        return current_date.normalize()

    def _latest_trade_date_from_snapshot(self, snapshot: pd.DataFrame) -> pd.Timestamp | None:
        if snapshot.empty or "trade_date" not in snapshot.columns:
            return None
        trade_date = pd.to_datetime(snapshot["trade_date"], errors="coerce").max()
        if pd.isna(trade_date):
            return None
        return pd.Timestamp(trade_date)

    def _restore_market_result(
        self,
        metadata: dict[str, object] | None,
        frames: dict[str, pd.DataFrame],
    ) -> MarketConditionResult | None:
        if metadata is None:
            return None

        trade_date_raw = metadata.get("trade_date")
        trade_date = pd.Timestamp(trade_date_raw) if trade_date_raw else None
        market_snapshot = self._frame_from_records(metadata.get("market_snapshot"))
        leadership_snapshot = self._frame_from_records(metadata.get("leadership_snapshot"))
        external_snapshot = self._frame_from_records(metadata.get("external_snapshot"))
        factors_vs_sp500 = self._frame_from_records(metadata.get("factors_vs_sp500"))
        return MarketConditionResult(
            trade_date=trade_date,
            score=float(metadata.get("score", 0.0)),
            label=str(metadata.get("label", "No Data")),
            score_1d_ago=self._optional_float(metadata.get("score_1d_ago")),
            score_1w_ago=self._optional_float(metadata.get("score_1w_ago")),
            score_1m_ago=self._optional_float(metadata.get("score_1m_ago")),
            score_3m_ago=self._optional_float(metadata.get("score_3m_ago")),
            label_1d_ago=self._optional_str(metadata.get("label_1d_ago")),
            label_1w_ago=self._optional_str(metadata.get("label_1w_ago")),
            label_1m_ago=self._optional_str(metadata.get("label_1m_ago")),
            label_3m_ago=self._optional_str(metadata.get("label_3m_ago")),
            component_scores=self._float_mapping(metadata.get("component_scores")),
            breadth_summary=self._float_mapping(metadata.get("breadth_summary")),
            performance_overview=self._float_mapping(metadata.get("performance_overview")),
            high_vix_summary=self._float_mapping(metadata.get("high_vix_summary")),
            market_snapshot=market_snapshot,
            leadership_snapshot=leadership_snapshot,
            external_snapshot=external_snapshot,
            factors_vs_sp500=factors_vs_sp500,
            s5th_series=pd.DataFrame(),
            vix_close=self._optional_float(metadata.get("vix_close")),
            update_time=str(metadata.get("update_time", "")),
        )

    def _restore_radar_result(
        self,
        metadata: dict[str, object] | None,
        frames: dict[str, pd.DataFrame],
    ) -> RadarResult | None:
        if metadata is None:
            return None
        return RadarResult(
            sector_leaders=self._frame_from_records(metadata.get("sector_leaders")),
            industry_leaders=self._frame_from_records(metadata.get("industry_leaders")),
            top_daily=self._frame_from_records(metadata.get("top_daily")),
            top_weekly=self._frame_from_records(metadata.get("top_weekly")),
            update_time=str(metadata.get("update_time", "")),
        )

    def _optional_float(self, value: object) -> float | None:
        if value is None or pd.isna(value):
            return None
        return float(value)

    def _optional_str(self, value: object) -> str | None:
        if value is None or pd.isna(value):
            return None
        text = str(value).strip()
        return text or None

    def _float_mapping(self, payload: object) -> dict[str, float]:
        if not isinstance(payload, dict):
            return {}
        result: dict[str, float] = {}
        for key, value in payload.items():
            if value is None:
                continue
            result[str(key)] = float(value)
        return result

    def _frame_from_records(self, payload: object) -> pd.DataFrame:
        if not isinstance(payload, list):
            return pd.DataFrame()
        return pd.DataFrame(payload)

    def _trade_date_from_metadata(self, metadata: dict[str, object]) -> pd.Timestamp | None:
        raw_value = metadata.get("trade_date")
        if raw_value is None:
            return None
        trade_date = pd.to_datetime(raw_value, errors="coerce")
        if pd.isna(trade_date):
            return None
        return pd.Timestamp(trade_date)

    def _minimal_snapshot_for_saved_run(self, tickers: list[str], trade_date: pd.Timestamp | None) -> pd.DataFrame:
        if trade_date is None:
            return pd.DataFrame(index=pd.Index(tickers, name="ticker"))
        return pd.DataFrame({"trade_date": [trade_date] * len(tickers)}, index=pd.Index(tickers, name="ticker"))

    def _data_health_summary_from_metadata(self, metadata: dict[str, object]) -> dict[str, float | int]:
        payload = metadata.get("data_health_summary")
        if isinstance(payload, dict):
            return payload  # type: ignore[return-value]
        fetch_summary = metadata.get("fetch_summary")
        if not isinstance(fetch_summary, dict):
            return {
                "live_price_coverage_pct": 0.0,
                "real_price_coverage_pct": 0.0,
                "stale_cache_count": 0,
                "sample_count": 0,
                "missing_count": 0,
            }
        return {
            "live_price_coverage_pct": 0.0,
            "real_price_coverage_pct": 0.0,
            "stale_cache_count": int(fetch_summary.get("cache", 0)),
            "sample_count": int(fetch_summary.get("sample", 0)),
            "missing_count": int(fetch_summary.get("missing", 0)),
        }

    def _resolve_active_symbols(self, symbols: list[str] | None, force_universe_refresh: bool) -> tuple[list[str], str, str | None, pd.DataFrame | None]:
        manual_symbols = self._normalize_symbols(symbols or [])
        if manual_symbols:
            return manual_symbols, "manual", None, None

        if self.use_snapshot_when_no_manual_symbols and self.universe_discovery_enabled:
            fresh = self.snapshot_store.load_latest_universe_snapshot(max_age_days=self.universe_snapshot_ttl_days)
            if not force_universe_refresh and fresh.snapshot is not None and not fresh.snapshot.empty:
                return self._symbols_from_universe_snapshot(fresh.snapshot), "weekly_snapshot_cached", fresh.path, fresh.snapshot

            stale = self.snapshot_store.load_latest_universe_snapshot(max_age_days=None)
            try:
                discovery = self.screener_provider.discover()
                if not discovery.snapshot.empty:
                    snapshot_path = self.snapshot_store.save_universe_snapshot(discovery.snapshot, discovery.metadata)
                    return self._symbols_from_universe_snapshot(discovery.snapshot), "weekly_snapshot_live", str(snapshot_path), discovery.snapshot
            except Exception:
                if stale.snapshot is not None and not stale.snapshot.empty:
                    return self._symbols_from_universe_snapshot(stale.snapshot), "weekly_snapshot_stale", stale.path, stale.snapshot
                raise

            if stale.snapshot is not None and not stale.snapshot.empty:
                return self._symbols_from_universe_snapshot(stale.snapshot), "weekly_snapshot_stale", stale.path, stale.snapshot

        default_symbols = self._normalize_symbols(self.settings.get("app", {}).get("default_symbols", []))
        if default_symbols:
            return default_symbols, "default_symbols", None, None
        return [], "none", None, None

    def _symbols_from_universe_snapshot(self, snapshot: pd.DataFrame) -> list[str]:
        if snapshot.empty or "ticker" not in snapshot.columns:
            return []
        return self._normalize_symbols(snapshot["ticker"].tolist())

    def _normalize_symbols(self, symbols: list[str]) -> list[str]:
        return list(dict.fromkeys(symbol.strip().upper() for symbol in symbols if str(symbol).strip()))

    def _load_data(
        self,
        symbols: list[str],
        universe_snapshot: pd.DataFrame | None,
        universe_mode: str,
        *,
        force_price_refresh: bool = False,
    ) -> tuple[PriceHistoryBatch, pd.DataFrame, pd.DataFrame, ProfileBatchResult, FundamentalBatchResult]:
        app_settings = self.settings.get("app", {})
        benchmark_symbol = str(app_settings.get("benchmark_symbol", "SPY"))
        vix_symbol = str(app_settings.get("vix_symbol", "^VIX"))
        period = str(app_settings.get("price_period", "18mo"))

        auxiliary_symbols = list(dict.fromkeys(self.radar_builder.required_symbols() + self.market_scorer.required_symbols()))
        requested_price_symbols = list(dict.fromkeys(symbols + [benchmark_symbol, vix_symbol] + auxiliary_symbols))
        price_batch = self.price_provider.get_price_history(
            requested_price_symbols,
            period=period,
            force_refresh=force_price_refresh,
        )
        self._apply_sample_price_fallback(price_batch, requested_price_symbols, benchmark_symbol, vix_symbol)

        benchmark_history = price_batch.histories.get(benchmark_symbol, pd.DataFrame())
        vix_history = price_batch.histories.get(vix_symbol, pd.DataFrame())
        if benchmark_history.empty:
            raise RuntimeError(f"Benchmark history for {benchmark_symbol} is required but unavailable.")

        active_price_symbols = [symbol for symbol in symbols if symbol in price_batch.histories and not price_batch.histories[symbol].empty]
        snapshot_source = self._snapshot_source_label(universe_mode)
        snapshot_fetched_at = self._snapshot_fetched_at(universe_snapshot)
        profile_batch = build_profile_batch_from_snapshot(universe_snapshot, active_price_symbols, snapshot_source, snapshot_fetched_at)
        fundamental_batch = build_fundamental_batch_from_snapshot(universe_snapshot, active_price_symbols, snapshot_source, snapshot_fetched_at)

        missing_profile_symbols = [symbol for symbol in active_price_symbols if symbol not in profile_batch.statuses]
        if missing_profile_symbols:
            fallback_profile_batch = self.profile_provider.get_profiles(missing_profile_symbols)
            self._merge_profile_batches(profile_batch, fallback_profile_batch)

        missing_fundamental_symbols = [symbol for symbol in active_price_symbols if symbol not in fundamental_batch.statuses]
        if missing_fundamental_symbols:
            fallback_fundamental_batch = self.fundamental_provider.get_fundamentals(missing_fundamental_symbols)
            self._merge_fundamental_batches(fundamental_batch, fallback_fundamental_batch)

        self._apply_sample_profile_fallback(profile_batch, active_price_symbols)
        self._apply_sample_fundamental_fallback(fundamental_batch, active_price_symbols)
        return price_batch, benchmark_history, vix_history, profile_batch, fundamental_batch

    def _snapshot_source_label(self, universe_mode: str) -> str:
        if universe_mode == "weekly_snapshot_live":
            return "live"
        if universe_mode == "weekly_snapshot_stale":
            return "cache_stale"
        if universe_mode == "weekly_snapshot_cached":
            return "cache_fresh"
        return "missing"

    def _snapshot_fetched_at(self, universe_snapshot: pd.DataFrame | None) -> datetime | None:
        if universe_snapshot is None or universe_snapshot.empty or "discovered_at" not in universe_snapshot.columns:
            return None
        parsed = pd.to_datetime(universe_snapshot["discovered_at"], errors="coerce")
        valid = parsed.dropna()
        if valid.empty:
            return None
        return valid.max().to_pydatetime()

    def _merge_profile_batches(self, target: ProfileBatchResult, incoming: ProfileBatchResult) -> None:
        existing = {profile.ticker for profile in target.profiles}
        for profile in incoming.profiles:
            if profile.ticker not in existing:
                target.profiles.append(profile)
                existing.add(profile.ticker)
        for symbol, status in incoming.statuses.items():
            if symbol not in target.statuses:
                target.statuses[symbol] = status

    def _merge_fundamental_batches(self, target: FundamentalBatchResult, incoming: FundamentalBatchResult) -> None:
        existing = {fundamental.ticker for fundamental in target.fundamentals}
        for fundamental in incoming.fundamentals:
            if fundamental.ticker not in existing:
                target.fundamentals.append(fundamental)
                existing.add(fundamental.ticker)
        for symbol, status in incoming.statuses.items():
            if symbol not in target.statuses:
                target.statuses[symbol] = status

    def _build_indicator_histories(self, histories: dict[str, pd.DataFrame], symbols: list[str]) -> dict[str, pd.DataFrame]:
        result: dict[str, pd.DataFrame] = {}
        for ticker in symbols:
            history = histories.get(ticker, pd.DataFrame())
            if history.empty:
                continue
            result[ticker] = self.indicator_calculator.calculate(history)
        return result

    def _build_snapshot(
        self,
        indicator_histories: dict[str, pd.DataFrame],
        profiles: list[SymbolProfile],
        fundamentals: list[FundamentalSnapshot],
    ) -> pd.DataFrame:
        snapshot = self._latest_snapshot_from_histories(indicator_histories)

        profile_frame = pd.DataFrame([profile.to_record() for profile in profiles]).set_index("ticker") if profiles else pd.DataFrame()
        fundamental_frame = (
            pd.DataFrame([fundamental.to_record() for fundamental in fundamentals]).set_index("ticker")
            if fundamentals
            else pd.DataFrame()
        )
        if not profile_frame.empty:
            snapshot = snapshot.join(profile_frame, how="left")
        if not fundamental_frame.empty:
            snapshot = snapshot.join(fundamental_frame, how="left", rsuffix="_fund")
        drop_columns = [column for column in ["data_source", "data_source_fund"] if column in snapshot.columns]
        if drop_columns:
            snapshot = snapshot.drop(columns=drop_columns)
        return snapshot

    def _latest_snapshot_from_histories(self, indicator_histories: dict[str, pd.DataFrame]) -> pd.DataFrame:
        latest_rows: list[pd.Series] = []
        for ticker, history in indicator_histories.items():
            if history.empty:
                continue
            latest = history.iloc[-1].copy()
            latest["ticker"] = ticker
            latest["trade_date"] = history.index[-1]
            latest_rows.append(latest)
        if not latest_rows:
            return pd.DataFrame()
        return pd.DataFrame(latest_rows).set_index("ticker")

    def _attach_status_columns(
        self,
        snapshot: pd.DataFrame,
        price_statuses: dict[str, FetchStatus],
        profile_statuses: dict[str, FetchStatus],
        fundamental_statuses: dict[str, FetchStatus],
    ) -> pd.DataFrame:
        result = snapshot.copy()
        result["price_data_source"] = result.index.map(lambda ticker: self._status_value(price_statuses, ticker, "source", "missing"))
        result["profile_data_source"] = result.index.map(lambda ticker: self._status_value(profile_statuses, ticker, "source", "missing"))
        result["fundamental_data_source"] = result.index.map(lambda ticker: self._status_value(fundamental_statuses, ticker, "source", "missing"))
        result["price_data_note"] = result.index.map(lambda ticker: self._status_value(price_statuses, ticker, "note", None))
        result["profile_data_note"] = result.index.map(lambda ticker: self._status_value(profile_statuses, ticker, "note", None))
        result["fundamental_data_note"] = result.index.map(lambda ticker: self._status_value(fundamental_statuses, ticker, "note", None))
        result["price_data_timestamp"] = result.index.map(lambda ticker: self._status_value(price_statuses, ticker, "fetched_at", None))
        result["profile_data_timestamp"] = result.index.map(lambda ticker: self._status_value(profile_statuses, ticker, "fetched_at", None))
        result["fundamental_data_timestamp"] = result.index.map(lambda ticker: self._status_value(fundamental_statuses, ticker, "fetched_at", None))
        return result

    def _postprocess_snapshot(self, snapshot: pd.DataFrame) -> pd.DataFrame:
        result = snapshot.copy()
        result["trade_date"] = pd.to_datetime(result["trade_date"], errors="coerce")
        result["ipo_date"] = pd.to_datetime(result.get("ipo_date"), errors="coerce")
        result["earnings_date"] = pd.to_datetime(result.get("earnings_date"), errors="coerce")
        result["listing_age_days"] = (result["trade_date"] - result["ipo_date"]).dt.days
        result["ipo_timer"] = result["listing_age_days"].apply(self._format_ipo_timer)
        earnings_delta = (result["earnings_date"] - result["trade_date"]).dt.days
        result["earnings_in_7d"] = earnings_delta.between(0, self.scan_config.earnings_warning_days)
        result["earnings_today"] = earnings_delta.eq(0)
        result["earnings_flag"] = result["earnings_in_7d"]
        return result

    def _build_fetch_status_frame(
        self,
        price_statuses: dict[str, FetchStatus],
        profile_statuses: dict[str, FetchStatus],
        fundamental_statuses: dict[str, FetchStatus],
    ) -> pd.DataFrame:
        records = [status.to_record() for status in [*price_statuses.values(), *profile_statuses.values(), *fundamental_statuses.values()]]
        frame = pd.DataFrame(records)
        if frame.empty:
            return frame
        frame["fetched_at"] = pd.to_datetime(frame["fetched_at"], errors="coerce")
        return frame.sort_values(["symbol", "dataset"]).reset_index(drop=True)

    def _persist_run(
        self,
        snapshot: pd.DataFrame,
        eligible_snapshot: pd.DataFrame,
        watchlist: pd.DataFrame,
        fetch_status: pd.DataFrame,
        data_source_label: str,
        data_health_summary: dict[str, float | int],
        market_result: MarketConditionResult,
        radar_result: RadarResult,
        scan_hits: pd.DataFrame,
        requested_symbols: list[str],
        manual_symbols_input: list[str],
        universe_mode: str,
        universe_snapshot_path: str | None,
    ) -> str | None:
        if not self.persist_research_snapshots:
            return None
        trade_date = self._latest_trade_date_from_snapshot(snapshot)
        metadata = {
            "run_created_at": datetime.now().isoformat(timespec="seconds"),
            "config_path": str(self.config_path),
            "manual_symbols_input": manual_symbols_input,
            "requested_symbols": requested_symbols,
            "available_symbols": list(snapshot.index),
            "trade_date": trade_date.isoformat() if trade_date is not None else None,
            "data_source_label": data_source_label,
            "used_sample_data": bool((fetch_status["source"] == "sample").any()) if not fetch_status.empty else False,
            "data_health_summary": data_health_summary,
            "market_score": market_result.score,
            "market_label": market_result.label,
            "universe_mode": universe_mode,
            "universe_snapshot_path": universe_snapshot_path,
        }
        run_dir = self.snapshot_store.save_run(
            snapshot,
            eligible_snapshot,
            watchlist,
            fetch_status,
            metadata,
            scan_hits=scan_hits,
            market_result=market_result,
            radar_result=radar_result,
        )
        return str(run_dir)

    def _apply_sample_price_fallback(
        self,
        price_batch: PriceHistoryBatch,
        requested_symbols: list[str],
        benchmark_symbol: str,
        vix_symbol: str,
    ) -> None:
        if not self.allow_sample_fallback:
            return
        missing_symbols = [symbol for symbol in requested_symbols if symbol not in price_batch.histories or price_batch.histories[symbol].empty]
        if not missing_symbols:
            return
        sample_histories = self.sample_factory.build_price_history([symbol for symbol in missing_symbols if symbol != vix_symbol])
        for symbol in missing_symbols:
            if symbol == vix_symbol:
                history = self._build_sample_vix_history(vix_symbol)
            else:
                history = sample_histories[symbol]
            price_batch.histories[symbol] = history
            price_batch.statuses[symbol] = FetchStatus(symbol=symbol, dataset="price", source="sample", has_data=True, fetched_at=datetime.now(), note="sample fallback")

    def _apply_sample_profile_fallback(self, profile_batch: ProfileBatchResult, symbols: list[str]) -> None:
        if not self.allow_sample_fallback:
            return
        existing = {profile.ticker for profile in profile_batch.profiles}
        missing = [symbol for symbol in symbols if symbol not in existing]
        if not missing:
            return
        for profile in self.sample_factory.build_profiles(missing):
            profile.data_source = "sample"
            profile_batch.profiles.append(profile)
            profile_batch.statuses[profile.ticker] = FetchStatus(symbol=profile.ticker, dataset="profile", source="sample", has_data=True, fetched_at=datetime.now(), note="sample fallback")

    def _apply_sample_fundamental_fallback(self, fundamental_batch: FundamentalBatchResult, symbols: list[str]) -> None:
        if not self.allow_sample_fallback:
            return
        existing = {fundamental.ticker for fundamental in fundamental_batch.fundamentals}
        missing = [symbol for symbol in symbols if symbol not in existing]
        if not missing:
            return
        for fundamental in self.sample_factory.build_fundamentals(missing):
            fundamental.data_source = "sample"
            fundamental_batch.fundamentals.append(fundamental)
            fundamental_batch.statuses[fundamental.ticker] = FetchStatus(symbol=fundamental.ticker, dataset="fundamental", source="sample", has_data=True, fetched_at=datetime.now(), note="sample fallback")

    def _status_value(self, statuses: dict[str, FetchStatus], ticker: str, field: str, default: object) -> object:
        status = statuses.get(ticker)
        return getattr(status, field) if status is not None else default

    def _format_ipo_timer(self, listing_age_days: object) -> str:
        if listing_age_days is None or pd.isna(listing_age_days):
            return "unknown"
        years = float(listing_age_days) / 365.25
        if years < 1.0:
            return f"{int(listing_age_days)}d"
        return f"{years:.1f}y"

    def _build_sample_vix_history(self, symbol: str) -> pd.DataFrame:
        history = self.sample_factory.build_price_history([symbol])[symbol].copy()
        history["close"] = history["close"].clip(lower=12.0, upper=35.0)
        history["adjusted_close"] = history["close"]
        history["high"] = history[["open", "close"]].max(axis=1) + 1.0
        history["low"] = history[["open", "close"]].min(axis=1) - 1.0
        return history

