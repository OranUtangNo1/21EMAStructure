from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.configuration import load_settings
from src.indicators.core import IndicatorCalculator, IndicatorConfig
from src.services.module_output_store import ModuleOutputRecord, ModuleOutputStore
from src.services.price_data_service import PriceDataService


@dataclass(frozen=True, slots=True)
class IndicatorRunResult:
    frame: pd.DataFrame
    histories: dict[str, pd.DataFrame]
    missing: dict[str, str]
    output_records: list[ModuleOutputRecord] = field(default_factory=list)


@dataclass(slots=True)
class IndicatorService:
    """Build date-addressable indicator rows from shared price histories."""

    price_service: PriceDataService
    indicator_calculator: object
    output_store: ModuleOutputStore | None = None

    @classmethod
    def from_config(
        cls,
        config_path: str | Path | None = None,
        *,
        output_store: ModuleOutputStore | None = None,
    ) -> "IndicatorService":
        settings = load_settings(config_path)
        return cls(
            price_service=PriceDataService.from_config(config_path),
            indicator_calculator=IndicatorCalculator(IndicatorConfig.from_dict(settings.get("indicators", {}))),
            output_store=output_store,
        )

    def build(
        self,
        symbols: list[str] | tuple[str, ...],
        *,
        start_date: str | pd.Timestamp | None = None,
        end_date: str | pd.Timestamp | None = None,
        as_of_date: str | pd.Timestamp | None = None,
        refresh_missing: bool = False,
        force_refresh: bool = False,
        write_outputs: bool = False,
        output_module: str = "indicators",
        progress_callback: object | None = None,
    ) -> IndicatorRunResult:
        effective_end_date = as_of_date if as_of_date is not None else end_date
        normalized_symbols = self.price_service.store.normalize_symbols(symbols)
        self._progress(progress_callback, f"Indicators: loading price histories for {len(normalized_symbols)} symbols")
        batch = self.price_service.get_histories(
            normalized_symbols,
            end_date=effective_end_date,
            refresh_missing=refresh_missing,
            force_refresh=force_refresh,
            progress_callback=progress_callback,
        )

        rows: list[pd.DataFrame] = []
        histories: dict[str, pd.DataFrame] = {}
        missing: dict[str, str] = {}
        total = len(normalized_symbols)
        for index, symbol in enumerate(normalized_symbols, start=1):
            if index == 1 or index == total or index % 250 == 0:
                self._progress(progress_callback, f"Indicators: calculating {index}/{total}")
            history = batch.histories.get(symbol, pd.DataFrame())
            if history.empty:
                status = batch.statuses.get(symbol)
                missing[symbol] = status.note if status is not None and status.note else "price history unavailable"
                continue
            indicators = self.indicator_calculator.calculate(history)
            if indicators.empty:
                missing[symbol] = "indicator calculation returned no rows"
                continue
            histories[symbol] = indicators
            selected = self._select_rows(indicators, start_date=start_date, end_date=effective_end_date)
            if selected.empty:
                missing[symbol] = "no indicator rows available for requested date range"
                continue
            selected = selected.copy()
            selected.insert(0, "ticker", symbol)
            selected.insert(1, "trade_date", selected.index)
            selected.insert(2, "date_key", selected.index.strftime("%Y%m%d"))
            rows.append(selected.reset_index(drop=True))

        frame = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
        self._progress(progress_callback, f"Indicators: completed rows={len(frame)}, missing={len(missing)}")
        output_records = self._write_outputs(frame, output_module) if write_outputs else []
        return IndicatorRunResult(frame=frame, histories=histories, missing=missing, output_records=output_records)

    def _select_rows(
        self,
        indicators: pd.DataFrame,
        *,
        start_date: str | pd.Timestamp | None,
        end_date: str | pd.Timestamp | None,
    ) -> pd.DataFrame:
        frame = indicators.copy()
        frame.index = pd.to_datetime(frame.index, errors="coerce")
        frame = frame.loc[frame.index.notna()].sort_index()
        if end_date is not None:
            frame = frame.loc[frame.index <= self._date_bound(end_date)]
        if start_date is not None:
            frame = frame.loc[frame.index >= self._date_bound(start_date)]
            return frame
        return frame.tail(1)

    def _write_outputs(self, frame: pd.DataFrame, output_module: str) -> list[ModuleOutputRecord]:
        if self.output_store is None or frame.empty or "date_key" not in frame.columns:
            return []
        records: list[ModuleOutputRecord] = []
        for date_key, group in frame.groupby("date_key", sort=True):
            records.append(
                self.output_store.save_frame(
                    output_module,
                    str(date_key),
                    group.reset_index(drop=True),
                    metadata={"ticker_count": int(group["ticker"].nunique()) if "ticker" in group.columns else 0},
                )
            )
        return records

    def _date_bound(self, value: str | pd.Timestamp) -> pd.Timestamp:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            raise ValueError(f"Invalid date: {value}")
        stamp = pd.Timestamp(parsed)
        if stamp.tzinfo is not None:
            stamp = stamp.tz_localize(None)
        return stamp.normalize()

    def _progress(self, callback: object | None, message: str) -> None:
        if callable(callback):
            callback(message)
