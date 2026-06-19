from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

from src.configuration import load_settings
from src.dashboard.stock_card import StockCardConfig, StockCardDocument, StockCardError, StockCardGenerator, StockCardMetadata
from src.scan.rules import ScanConfig, mature_late_stage_risk, stage2_quality_score
from src.scoring.rs import RSConfig, RSScorer
from src.scoring.vcs import VCSCalculator, VCSConfig
from src.services.price_data_service import PriceDataService
from src.services.stock_card_metadata_service import stock_card_industry_etf_from_row


@dataclass(frozen=True, slots=True)
class StockCardBuildResult:
    documents: list[StockCardDocument]
    missing: dict[str, str]
    fetch_status: dict[str, object]


@dataclass(slots=True)
class StockCardService:
    """Build stock-card documents from the shared price-data service."""

    price_service: PriceDataService
    generator: StockCardGenerator
    settings: dict[str, object] | None = None

    @classmethod
    def from_config(cls, config_path: str | Path | None = None, config: StockCardConfig | None = None) -> "StockCardService":
        settings = load_settings(config_path)
        return cls(
            price_service=PriceDataService.from_config(config_path),
            generator=StockCardGenerator(config),
            settings=settings,
        )

    def build(
        self,
        ticker: str,
        *,
        as_of_date: str | pd.Timestamp | None = None,
        start_date: str | pd.Timestamp | None = None,
        metadata: StockCardMetadata | None = None,
        last_close: float | None = None,
        refresh_missing: bool = False,
        force_refresh: bool = False,
    ) -> StockCardDocument:
        symbol = str(ticker).strip().upper()
        if not symbol:
            raise StockCardError("ticker is required")

        batch = self.price_service.get_histories(
            [symbol],
            start_date=start_date,
            end_date=as_of_date,
            refresh_missing=refresh_missing,
            force_refresh=force_refresh,
        )
        history = batch.histories.get(symbol, pd.DataFrame())
        if history.empty:
            status = batch.statuses.get(symbol)
            note = status.note if status is not None and status.note else "price history unavailable"
            raise StockCardError(f"{symbol}: {note}")
        enriched_metadata = self._enriched_metadata_lookup(
            [symbol],
            batch.histories,
            {symbol: metadata or StockCardMetadata()},
            as_of_date=as_of_date,
            refresh_missing=refresh_missing,
            force_refresh=force_refresh,
        )
        return self.generator.build(symbol, history, metadata=enriched_metadata.get(symbol, metadata), last_close=last_close)

    def build_many(
        self,
        symbols: list[str] | tuple[str, ...],
        *,
        as_of_date: str | pd.Timestamp | None = None,
        start_date: str | pd.Timestamp | None = None,
        metadata_lookup: dict[str, StockCardMetadata] | None = None,
        last_close_lookup: dict[str, float] | None = None,
        refresh_missing: bool = False,
        force_refresh: bool = False,
    ) -> StockCardBuildResult:
        normalized_symbols = self.price_service.store.normalize_symbols(symbols)
        batch = self.price_service.get_histories(
            normalized_symbols,
            start_date=start_date,
            end_date=as_of_date,
            refresh_missing=refresh_missing,
            force_refresh=force_refresh,
        )
        metadata_lookup = metadata_lookup or {}
        last_close_lookup = last_close_lookup or {}
        enriched_metadata_lookup = self._enriched_metadata_lookup(
            normalized_symbols,
            batch.histories,
            metadata_lookup,
            as_of_date=as_of_date,
            refresh_missing=refresh_missing,
            force_refresh=force_refresh,
        )
        documents: list[StockCardDocument] = []
        missing: dict[str, str] = {}

        for symbol in normalized_symbols:
            history = batch.histories.get(symbol, pd.DataFrame())
            if history.empty:
                status = batch.statuses.get(symbol)
                missing[symbol] = status.note if status is not None and status.note else "price history unavailable"
                continue
            try:
                documents.append(
                    self.generator.build(
                        symbol,
                        history,
                        metadata=enriched_metadata_lookup.get(symbol, StockCardMetadata()),
                        last_close=last_close_lookup.get(symbol),
                    )
                )
            except StockCardError as exc:
                missing[symbol] = str(exc)

        return StockCardBuildResult(
            documents=documents,
            missing=missing,
            fetch_status={symbol: status.to_record() for symbol, status in batch.statuses.items()},
        )

    def _enriched_metadata_lookup(
        self,
        symbols: list[str],
        histories: dict[str, pd.DataFrame],
        metadata_lookup: dict[str, StockCardMetadata],
        *,
        as_of_date: str | pd.Timestamp | None,
        refresh_missing: bool,
        force_refresh: bool,
    ) -> dict[str, StockCardMetadata]:
        result = {symbol: metadata_lookup.get(symbol, StockCardMetadata()) for symbol in symbols}
        settings = self.settings or {}
        scoring_settings = settings.get("scoring", {}) if isinstance(settings.get("scoring", {}), dict) else {}
        app_settings = settings.get("app", {}) if isinstance(settings.get("app", {}), dict) else {}
        radar_settings = settings.get("radar", {}) if isinstance(settings.get("radar", {}), dict) else {}
        industry_major_map, industry_name_map = _industry_maps_from_radar_settings(radar_settings)
        for symbol in symbols:
            base = result.get(symbol, StockCardMetadata())
            if _is_missing_text(base.industry_etf):
                industry_etf = industry_major_map.get(symbol)
                if industry_etf:
                    result[symbol] = replace(base, industry_etf=industry_etf)

        rs_config = RSConfig.from_dict(scoring_settings.get("rs", {}) if isinstance(scoring_settings.get("rs", {}), dict) else {})
        benchmark_symbol = str(app_settings.get("benchmark_symbol", rs_config.benchmark_symbol)).strip().upper() or rs_config.benchmark_symbol
        benchmark_history = pd.DataFrame()
        if benchmark_symbol:
            try:
                benchmark_batch = self.price_service.get_histories(
                    [benchmark_symbol],
                    end_date=as_of_date,
                    refresh_missing=refresh_missing,
                    force_refresh=force_refresh,
                )
                benchmark_history = benchmark_batch.histories.get(benchmark_symbol, pd.DataFrame())
            except Exception:
                benchmark_history = pd.DataFrame()

        if not benchmark_history.empty:
            snapshot = pd.DataFrame(index=symbols)
            try:
                rs_frame = RSScorer(rs_config).score(snapshot, histories, benchmark_history)
            except Exception:
                rs_frame = pd.DataFrame()
            for symbol in symbols:
                if symbol not in rs_frame.index:
                    continue
                row = rs_frame.loc[symbol]
                result[symbol] = replace(
                    result[symbol],
                    rs21=_optional_float(row.get("rs21")),
                    rs63=_optional_float(row.get("rs63")),
                    rs126=_optional_float(row.get("rs126")),
                    rs_hi52=_optional_bool(row.get("rs_ratio_at_52w_high")),
                    rs_hi3y=_optional_bool(row.get("rs_ratio_at_3y_high")),
                )

        vcs_config = VCSConfig.from_dict(scoring_settings.get("vcs", {}) if isinstance(scoring_settings.get("vcs", {}), dict) else {})
        vcs_calculator = VCSCalculator(vcs_config)
        scan_config = ScanConfig.from_dict(settings.get("scan", {}) if isinstance(settings.get("scan", {}), dict) else {})
        for symbol in symbols:
            history = histories.get(symbol, pd.DataFrame())
            if history.empty:
                continue
            vcs = None
            indicators = pd.DataFrame()
            try:
                vcs_series = vcs_calculator.calculate_series(history)
                if not vcs_series.empty:
                    vcs = _optional_float(vcs_series.iloc[-1])
            except Exception:
                vcs = None
            stage2_q = None
            late_stage = None
            try:
                indicators = self.generator.indicator_calculator.calculate(history)
                if not indicators.empty:
                    latest = indicators.iloc[-1]
                    stage2_q = _optional_float(stage2_quality_score(latest, scan_config))
                    late_stage = _optional_bool(mature_late_stage_risk(latest, scan_config))
            except Exception:
                stage2_q = None
                late_stage = None
            profile_industry_etf = None
            if _is_missing_text(result[symbol].industry_etf):
                latest_source = indicators.iloc[-1] if not indicators.empty else pd.Series(dtype=object)
                profile_industry_etf = stock_card_industry_etf_from_row(latest_source, industry_name_map)
            result[symbol] = replace(
                result[symbol],
                industry_etf=profile_industry_etf
                if profile_industry_etf and profile_industry_etf != "NA" and _is_missing_text(result[symbol].industry_etf)
                else result[symbol].industry_etf,
                vcs=vcs if vcs is not None else result[symbol].vcs,
                stage2_quality_score=stage2_q if stage2_q is not None else result[symbol].stage2_quality_score,
                mature_late_stage_risk=late_stage if late_stage is not None else result[symbol].mature_late_stage_risk,
            )
        return result


def _optional_float(value: object) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"y", "yes", "true", "1"}:
            return True
        if text in {"n", "no", "false", "0"}:
            return False
        return None
    return bool(value)


def _industry_maps_from_radar_settings(radar_settings: dict[str, object]) -> tuple[dict[str, str], dict[str, str]]:
    major_map: dict[str, str] = {}
    name_map: dict[str, str] = {}
    for item in radar_settings.get("industry_etfs", []) if isinstance(radar_settings, dict) else []:
        if not isinstance(item, dict):
            continue
        etf = str(item.get("ticker", "")).strip().upper()
        name = str(item.get("name", "")).strip().lower()
        if etf and name:
            name_map[name] = etf
        for symbol in item.get("major_stocks", []) or []:
            normalized = str(symbol).strip().upper()
            if etf and normalized:
                major_map[normalized] = etf
    return major_map, name_map


def _is_missing_text(value: object) -> bool:
    text = str(value or "").strip().upper()
    return text in {"", "NA", "NAN", "NONE", "NULL"}
