from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from src.configuration import load_settings
from src.data.cache import CacheLayer
from src.data.providers import FredSeriesProvider
from src.dashboard.market import MarketConditionConfig, MarketConditionResult, MarketConditionScorer
from src.dashboard.radar import RadarConfig, RadarResult, RadarViewModelBuilder
from src.indicators.core import IndicatorCalculator, IndicatorConfig
from src.services.module_output_store import ModuleOutputRecord, ModuleOutputStore
from src.services.price_data_service import PriceDataService


MARKET_OUTPUT_MODULE = "market"
MARKET_SNAPSHOT_OUTPUT_MODULE = "market_snapshot"
MARKET_FACTORS_OUTPUT_MODULE = "market_factors"
RS_RADAR_SECTOR_OUTPUT_MODULE = "rs_radar_sector"
RS_RADAR_INDUSTRY_OUTPUT_MODULE = "rs_radar_industry"
RS_RADAR_TOP_DAILY_OUTPUT_MODULE = "rs_radar_top_daily"
RS_RADAR_TOP_WEEKLY_OUTPUT_MODULE = "rs_radar_top_weekly"


@dataclass(frozen=True, slots=True)
class MarketServiceResult:
    market_result: MarketConditionResult
    radar_result: RadarResult
    missing: dict[str, str] = field(default_factory=dict)
    output_records: list[ModuleOutputRecord] = field(default_factory=list)


@dataclass(slots=True)
class MarketService:
    """Date-addressable market and RS Radar service over shared price histories."""

    price_service: PriceDataService
    indicator_calculator: object
    market_scorer: MarketConditionScorer
    radar_builder: RadarViewModelBuilder
    benchmark_symbol: str = "SPY"
    fred_provider: object | None = None
    output_store: ModuleOutputStore | None = None

    @classmethod
    def from_config(
        cls,
        config_path: str | Path | None = None,
        *,
        price_service: PriceDataService | None = None,
        output_store: ModuleOutputStore | None = None,
    ) -> "MarketService":
        settings = load_settings(config_path)
        app_settings = settings.get("app", {}) if isinstance(settings.get("app", {}), dict) else {}
        data_settings = settings.get("data", {}) if isinstance(settings.get("data", {}), dict) else {}
        resolved_price_service = price_service or PriceDataService.from_config(config_path)
        fred_provider = FredSeriesProvider(
            CacheLayer(resolved_price_service.store.cache.root_dir),
            series_ttl_hours=int(data_settings.get("fred_series_cache_ttl_hours", 24)),
            allow_stale_cache_on_failure=bool(data_settings.get("allow_stale_cache_on_failure", True)),
        )
        return cls(
            price_service=resolved_price_service,
            indicator_calculator=IndicatorCalculator(IndicatorConfig.from_dict(settings.get("indicators", {}))),
            market_scorer=MarketConditionScorer(MarketConditionConfig.from_dict(settings.get("market", {}))),
            radar_builder=RadarViewModelBuilder(RadarConfig.from_dict(settings.get("radar", {}))),
            benchmark_symbol=str(app_settings.get("benchmark_symbol", "SPY")).strip().upper() or "SPY",
            fred_provider=fred_provider,
            output_store=output_store,
        )

    def run(
        self,
        stock_symbols: Iterable[str] | None = None,
        *,
        as_of_date: str | pd.Timestamp | None = None,
        refresh_missing: bool = False,
        force_refresh: bool = False,
        write_outputs: bool = False,
    ) -> MarketServiceResult:
        normalized_stock_symbols = self.price_service.store.normalize_symbols(tuple(stock_symbols or ()))
        market_symbols = self.market_scorer.required_symbols()
        radar_symbols = self.radar_builder.required_symbols()
        price_symbols = list(dict.fromkeys([*normalized_stock_symbols, self.benchmark_symbol, *market_symbols, *radar_symbols]))
        price_batch = self.price_service.get_histories(
            price_symbols,
            end_date=as_of_date,
            refresh_missing=refresh_missing,
            force_refresh=force_refresh,
        )
        fred_histories = self._load_fred_histories(
            as_of_date=as_of_date,
            refresh_missing=refresh_missing,
            force_refresh=force_refresh,
        )
        histories = {**price_batch.histories, **fred_histories}
        indicator_histories = self._build_indicator_histories(histories)

        stock_histories = {symbol: indicator_histories[symbol] for symbol in normalized_stock_symbols if symbol in indicator_histories}
        market_histories = {
            symbol: indicator_histories[symbol]
            for symbol in [*market_symbols, *self.market_scorer.required_fred_series()]
            if symbol in indicator_histories
        }
        radar_histories = {symbol: indicator_histories[symbol] for symbol in radar_symbols if symbol in indicator_histories}
        benchmark_history = indicator_histories.get(self.benchmark_symbol, pd.DataFrame())

        market_result = self.market_scorer.score(stock_histories, market_histories, benchmark_history)
        radar_result = self.radar_builder.build(radar_histories, benchmark_history)
        missing = self._missing(price_symbols, price_batch.histories, price_batch.statuses)
        output_records = self._write_outputs(market_result, radar_result) if write_outputs else []
        return MarketServiceResult(
            market_result=market_result,
            radar_result=radar_result,
            missing=missing,
            output_records=output_records,
        )

    def run_from_price_histories(
        self,
        histories: dict[str, pd.DataFrame],
        stock_symbols: Iterable[str] | None = None,
        *,
        as_of_date: str | pd.Timestamp | None = None,
        write_outputs: bool = False,
    ) -> MarketServiceResult:
        normalized_stock_symbols = self.price_service.store.normalize_symbols(tuple(stock_symbols or ()))
        sliced_histories = {
            symbol: self.price_service.store.slice_frame(history, end_date=as_of_date)
            for symbol, history in histories.items()
            if history is not None and not history.empty
        }
        indicator_histories = self._build_indicator_histories(sliced_histories)
        return self._build_from_indicator_histories(
            indicator_histories,
            normalized_stock_symbols,
            write_outputs=write_outputs,
        )

    def _load_fred_histories(
        self,
        *,
        as_of_date: str | pd.Timestamp | None,
        refresh_missing: bool,
        force_refresh: bool,
    ) -> dict[str, pd.DataFrame]:
        histories: dict[str, pd.DataFrame] = {}
        missing: list[str] = []
        for series_id in self.market_scorer.required_fred_series():
            cached = self.price_service.store.cache.load_csv(f"fred_{series_id}", allow_stale=True)
            normalized = self.price_service.store.slice_frame(cached, end_date=as_of_date) if cached is not None else pd.DataFrame()
            if normalized.empty:
                missing.append(series_id)
            else:
                histories[series_id] = normalized

        if (force_refresh or (refresh_missing and missing)) and self.fred_provider is not None:
            fetched = self.fred_provider.get_series(missing if not force_refresh else self.market_scorer.required_fred_series(), force_refresh=force_refresh)
            for series_id, history in fetched.histories.items():
                histories[series_id] = self.price_service.store.slice_frame(history, end_date=as_of_date)
        return histories

    def _build_indicator_histories(self, histories: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        result: dict[str, pd.DataFrame] = {}
        for symbol, history in histories.items():
            if history.empty:
                continue
            indicators = self.indicator_calculator.calculate(history)
            if not indicators.empty:
                result[symbol] = indicators
        return result

    def _build_from_indicator_histories(
        self,
        indicator_histories: dict[str, pd.DataFrame],
        stock_symbols: list[str],
        *,
        write_outputs: bool,
    ) -> MarketServiceResult:
        market_symbols = self.market_scorer.required_symbols()
        radar_symbols = self.radar_builder.required_symbols()
        stock_histories = {symbol: indicator_histories[symbol] for symbol in stock_symbols if symbol in indicator_histories}
        market_histories = {
            symbol: indicator_histories[symbol]
            for symbol in [*market_symbols, *self.market_scorer.required_fred_series()]
            if symbol in indicator_histories
        }
        radar_histories = {symbol: indicator_histories[symbol] for symbol in radar_symbols if symbol in indicator_histories}
        benchmark_history = indicator_histories.get(self.benchmark_symbol, pd.DataFrame())

        market_result = self.market_scorer.score(stock_histories, market_histories, benchmark_history)
        radar_result = self.radar_builder.build(radar_histories, benchmark_history)
        output_records = self._write_outputs(market_result, radar_result) if write_outputs else []
        return MarketServiceResult(
            market_result=market_result,
            radar_result=radar_result,
            missing={},
            output_records=output_records,
        )

    def _missing(self, symbols: list[str], histories: dict[str, pd.DataFrame], statuses: dict[str, Any]) -> dict[str, str]:
        missing: dict[str, str] = {}
        for symbol in symbols:
            if symbol in histories and not histories[symbol].empty:
                continue
            status = statuses.get(symbol)
            missing[symbol] = getattr(status, "note", None) or "price history unavailable"
        return missing

    def _write_outputs(self, market_result: MarketConditionResult, radar_result: RadarResult) -> list[ModuleOutputRecord]:
        if self.output_store is None:
            return []
        date_key = self._date_key(market_result)
        records = [
            self.output_store.save_json(
                MARKET_OUTPUT_MODULE,
                date_key,
                self._market_payload(market_result),
                metadata={"label": market_result.label, "score": market_result.score},
            )
        ]
        records.extend(
            self._write_optional_frame(
                module,
                date_key,
                frame,
            )
            for module, frame in (
                (MARKET_SNAPSHOT_OUTPUT_MODULE, market_result.market_snapshot),
                (MARKET_FACTORS_OUTPUT_MODULE, market_result.factors_vs_sp500),
                (RS_RADAR_SECTOR_OUTPUT_MODULE, radar_result.sector_leaders),
                (RS_RADAR_INDUSTRY_OUTPUT_MODULE, radar_result.industry_leaders),
                (RS_RADAR_TOP_DAILY_OUTPUT_MODULE, radar_result.top_daily),
                (RS_RADAR_TOP_WEEKLY_OUTPUT_MODULE, radar_result.top_weekly),
            )
            if frame is not None and not frame.empty
        )
        return records

    def _write_optional_frame(self, module: str, date_key: str, frame: pd.DataFrame) -> ModuleOutputRecord:
        payload = frame.copy()
        payload.insert(0, "date_key", date_key)
        return self.output_store.save_frame(module, date_key, payload, metadata={"row_count": int(len(payload))})

    def _market_payload(self, result: MarketConditionResult) -> dict[str, Any]:
        return self._jsonable(
            {
                "date_key": self._date_key(result),
                "trade_date": result.trade_date,
                "score": result.score,
                "label": result.label,
                "score_1d_ago": result.score_1d_ago,
                "score_1w_ago": result.score_1w_ago,
                "score_1m_ago": result.score_1m_ago,
                "score_3m_ago": result.score_3m_ago,
                "component_scores": result.component_scores,
                "breadth_summary": result.breadth_summary,
                "breadth_momentum_summary": result.breadth_momentum_summary,
                "breadth_internal_summary": result.breadth_internal_summary,
                "participation_summary": result.participation_summary,
                "performance_overview": result.performance_overview,
                "high_vix_summary": result.high_vix_summary,
                "risk_on_ratio_summary": result.risk_on_ratio_summary,
                "defensive_cyclical_summary": result.defensive_cyclical_summary,
                "volatility_term_structure": result.volatility_term_structure,
                "credit_risk_proxy": result.credit_risk_proxy,
                "index_state_summary": result.index_state_summary,
                "drawdown_summary": result.drawdown_summary,
                "series_as_of": result.series_as_of,
                "update_time": result.update_time,
            }
        )

    def _date_key(self, result: MarketConditionResult) -> str:
        if result.trade_date is not None and pd.notna(result.trade_date):
            return pd.Timestamp(result.trade_date).strftime("%Y%m%d")
        return pd.Timestamp.today().strftime("%Y%m%d")

    def _jsonable(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._jsonable(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._jsonable(item) for item in value]
        if isinstance(value, tuple):
            return [self._jsonable(item) for item in value]
        if isinstance(value, pd.Timestamp):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return None if np.isnan(value) else float(value)
        if isinstance(value, float):
            return None if np.isnan(value) else value
        return value
