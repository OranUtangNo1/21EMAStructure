from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.configuration import load_settings
from src.dashboard.market import MarketConditionConfig, MarketConditionResult, MarketConditionScorer
from src.dashboard.radar import RadarConfig, RadarResult, RadarViewModelBuilder
from src.dashboard.watchlist import ScanCardViewModel, WatchlistViewModelBuilder
from src.data.cache import CacheLayer
from src.data.models import FundamentalSnapshot, SymbolProfile
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


class ResearchPlatform:
    """Orchestrate active screening workflow: data, indicators, scans, and dashboard outputs."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self.root = Path(__file__).resolve().parents[1]
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
        self.watchlist_builder = WatchlistViewModelBuilder()
        self.radar_builder = RadarViewModelBuilder(RadarConfig.from_dict(self.settings.get("radar", {})))

        allow_stale = bool(data_settings.get("allow_stale_cache_on_failure", True))
        self.persist_research_snapshots = bool(data_settings.get("persist_research_snapshots", True))
        self.price_provider = YFinancePriceDataProvider(
            self.cache,
            technical_ttl_hours=int(data_settings.get("technical_cache_ttl_hours", 12)),
            allow_stale_cache_on_failure=allow_stale,
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
        self.screener_provider = YahooScreenerProvider(YahooScreenerConfig.from_dict(discovery_payload))

    def run(self, symbols: list[str] | None = None, force_universe_refresh: bool = False) -> PlatformArtifacts:
        active_symbols, universe_mode, universe_snapshot_path = self._resolve_active_symbols(symbols, force_universe_refresh)
        if not active_symbols:
            raise ValueError("At least one symbol is required.")

        price_batch, benchmark_history, vix_history, profile_batch, fundamental_batch = self._load_data(active_symbols)
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
            eligible_snapshot = snapshot.sort_values(["data_quality_score", "hybrid_score"], ascending=[False, False]).head(min(10, len(snapshot))).copy()

        scan_result = self.scan_runner.run(eligible_snapshot)
        watchlist = self.watchlist_builder.build(scan_result.watchlist)
        watchlist_cards = self.watchlist_builder.build_scan_cards(scan_result.watchlist, scan_result.hits)
        earnings_today = self.watchlist_builder.build_earnings_today(eligible_snapshot)

        radar_histories = self._build_indicator_histories(price_batch.histories, self.radar_builder.required_symbols())
        radar_result = self.radar_builder.build(radar_histories, benchmark_history)

        fetch_status = self._build_fetch_status_frame(price_batch.statuses, profile_batch.statuses, fundamental_batch.statuses)
        data_health_summary = summarize_data_health(fetch_status)
        data_source_label = summarize_data_source_label(fetch_status)
        used_sample_data = bool((fetch_status["source"] == "sample").any()) if not fetch_status.empty else False
        market_result = self.market_scorer.score(snapshot, benchmark_history, vix_history if not vix_history.empty else None)
        run_directory = self._persist_run(
            snapshot,
            eligible_snapshot,
            watchlist,
            fetch_status,
            data_source_label,
            data_health_summary,
            market_result,
            active_symbols,
            universe_mode,
            universe_snapshot_path,
        )

        return PlatformArtifacts(
            snapshot=snapshot,
            eligible_snapshot=eligible_snapshot,
            watchlist=watchlist,
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
        )

    def _resolve_active_symbols(self, symbols: list[str] | None, force_universe_refresh: bool) -> tuple[list[str], str, str | None]:
        manual_symbols = self._normalize_symbols(symbols or [])
        if manual_symbols:
            return manual_symbols, "manual", None

        if self.use_snapshot_when_no_manual_symbols and self.universe_discovery_enabled:
            fresh = self.snapshot_store.load_latest_universe_snapshot(max_age_days=self.universe_snapshot_ttl_days)
            if not force_universe_refresh and fresh.snapshot is not None and not fresh.snapshot.empty:
                return self._symbols_from_universe_snapshot(fresh.snapshot), "weekly_snapshot_cached", fresh.path

            stale = self.snapshot_store.load_latest_universe_snapshot(max_age_days=None)
            try:
                discovery = self.screener_provider.discover()
                if not discovery.snapshot.empty:
                    snapshot_path = self.snapshot_store.save_universe_snapshot(discovery.snapshot, discovery.metadata)
                    return self._symbols_from_universe_snapshot(discovery.snapshot), "weekly_snapshot_live", str(snapshot_path)
            except Exception:
                if stale.snapshot is not None and not stale.snapshot.empty:
                    return self._symbols_from_universe_snapshot(stale.snapshot), "weekly_snapshot_stale", stale.path
                raise

            if stale.snapshot is not None and not stale.snapshot.empty:
                return self._symbols_from_universe_snapshot(stale.snapshot), "weekly_snapshot_stale", stale.path

        default_symbols = self._normalize_symbols(self.settings.get("app", {}).get("default_symbols", []))
        if default_symbols:
            return default_symbols, "default_symbols", None
        return [], "none", None

    def _symbols_from_universe_snapshot(self, snapshot: pd.DataFrame) -> list[str]:
        if snapshot.empty or "ticker" not in snapshot.columns:
            return []
        return self._normalize_symbols(snapshot["ticker"].tolist())

    def _normalize_symbols(self, symbols: list[str]) -> list[str]:
        return list(dict.fromkeys(symbol.strip().upper() for symbol in symbols if str(symbol).strip()))

    def _load_data(
        self,
        symbols: list[str],
    ) -> tuple[PriceHistoryBatch, pd.DataFrame, pd.DataFrame, ProfileBatchResult, FundamentalBatchResult]:
        app_settings = self.settings.get("app", {})
        benchmark_symbol = str(app_settings.get("benchmark_symbol", "SPY"))
        vix_symbol = str(app_settings.get("vix_symbol", "^VIX"))
        period = str(app_settings.get("price_period", "18mo"))

        auxiliary_symbols = self.radar_builder.required_symbols()
        requested_price_symbols = list(dict.fromkeys(symbols + [benchmark_symbol, vix_symbol] + auxiliary_symbols))
        price_batch = self.price_provider.get_price_history(requested_price_symbols, period=period)
        self._apply_sample_price_fallback(price_batch, requested_price_symbols, benchmark_symbol, vix_symbol)

        benchmark_history = price_batch.histories.get(benchmark_symbol, pd.DataFrame())
        vix_history = price_batch.histories.get(vix_symbol, pd.DataFrame())
        if benchmark_history.empty:
            raise RuntimeError(f"Benchmark history for {benchmark_symbol} is required but unavailable.")

        active_price_symbols = [symbol for symbol in symbols if symbol in price_batch.histories and not price_batch.histories[symbol].empty]
        profile_batch = self.profile_provider.get_profiles(active_price_symbols)
        fundamental_batch = self.fundamental_provider.get_fundamentals(active_price_symbols)
        self._apply_sample_profile_fallback(profile_batch, active_price_symbols)
        self._apply_sample_fundamental_fallback(fundamental_batch, active_price_symbols)
        return price_batch, benchmark_history, vix_history, profile_batch, fundamental_batch

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
        requested_symbols: list[str],
        universe_mode: str,
        universe_snapshot_path: str | None,
    ) -> str | None:
        if not self.persist_research_snapshots:
            return None
        metadata = {
            "run_created_at": datetime.now().isoformat(timespec="seconds"),
            "requested_symbols": requested_symbols,
            "available_symbols": list(snapshot.index),
            "data_source_label": data_source_label,
            "used_sample_data": bool((fetch_status["source"] == "sample").any()) if not fetch_status.empty else False,
            "data_health_summary": data_health_summary,
            "market_score": market_result.score,
            "market_label": market_result.label,
            "universe_mode": universe_mode,
            "universe_snapshot_path": universe_snapshot_path,
        }
        run_dir = self.snapshot_store.save_run(snapshot, eligible_snapshot, watchlist, fetch_status, metadata)
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
