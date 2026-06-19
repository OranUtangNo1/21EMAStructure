from __future__ import annotations

import pandas as pd

from src.data.results import FetchStatus, PriceHistoryBatch
from src.services.indicator_service import IndicatorService
from src.services.module_output_store import ModuleOutputStore
from src.services.price_store import PriceStore


def test_indicator_service_builds_rows_for_ticker_pool_and_date_range(tmp_path) -> None:
    price_service = FakePriceService(tmp_path)
    service = IndicatorService(price_service=price_service, indicator_calculator=FakeIndicatorCalculator())

    result = service.build(["AAA", "BBB"], start_date="2026-03-03", end_date="2026-03-04")

    assert price_service.calls == [(("AAA", "BBB"), None, "2026-03-04", False, False)]
    assert result.missing == {}
    assert result.frame[["date_key", "ticker", "sma2"]].to_dict("records") == [
        {"date_key": "20260303", "ticker": "AAA", "sma2": 10.5},
        {"date_key": "20260304", "ticker": "AAA", "sma2": 11.5},
        {"date_key": "20260303", "ticker": "BBB", "sma2": 20.5},
        {"date_key": "20260304", "ticker": "BBB", "sma2": 21.5},
    ]


def test_indicator_service_defaults_to_latest_row_as_of_date(tmp_path) -> None:
    service = IndicatorService(price_service=FakePriceService(tmp_path), indicator_calculator=FakeIndicatorCalculator())

    result = service.build(["AAA"], as_of_date="2026-03-03")

    assert result.frame[["date_key", "ticker", "close", "sma2"]].to_dict("records") == [
        {"date_key": "20260303", "ticker": "AAA", "close": 11.0, "sma2": 10.5},
    ]


def test_indicator_service_optionally_writes_date_keyed_outputs(tmp_path) -> None:
    output_store = ModuleOutputStore(tmp_path / "outputs")
    service = IndicatorService(
        price_service=FakePriceService(tmp_path),
        indicator_calculator=FakeIndicatorCalculator(),
        output_store=output_store,
    )

    result = service.build(["AAA"], start_date="2026-03-03", end_date="2026-03-04", write_outputs=True)

    assert [record.date_key for record in result.output_records] == ["20260303", "20260304"]
    assert output_store.load_frame("indicators", "20260303")["ticker"].tolist() == ["AAA"]
    assert output_store.load_metadata("indicators", "20260303")["ticker_count"] == 1


class FakePriceService:
    def __init__(self, tmp_path) -> None:
        self.store = PriceStore(tmp_path / "prices")
        self.calls: list[tuple[tuple[str, ...], object, object, bool, bool]] = []
        self.histories = {
            "AAA": _history([10.0, 11.0, 12.0], ["2026-03-02", "2026-03-03", "2026-03-04"]),
            "BBB": _history([20.0, 21.0, 22.0], ["2026-03-02", "2026-03-03", "2026-03-04"]),
        }

    def get_histories(
        self,
        symbols,
        *,
        start_date=None,
        end_date=None,
        refresh_missing=False,
        force_refresh=False,
    ) -> PriceHistoryBatch:
        normalized = tuple(str(symbol).upper() for symbol in symbols)
        self.calls.append((normalized, start_date, end_date, refresh_missing, force_refresh))
        histories = {
            symbol: self.histories[symbol].loc[self.histories[symbol].index <= pd.Timestamp(end_date)].copy()
            if end_date is not None
            else self.histories[symbol].copy()
            for symbol in normalized
            if symbol in self.histories
        }
        statuses = {
            symbol: FetchStatus(symbol=symbol, dataset="price", source="cache_fresh", has_data=symbol in histories)
            for symbol in normalized
        }
        return PriceHistoryBatch(histories=histories, statuses=statuses)


class FakeIndicatorCalculator:
    def calculate(self, history: pd.DataFrame) -> pd.DataFrame:
        result = history.copy()
        result["sma2"] = result["close"].rolling(2).mean()
        return result


def _history(closes: list[float], dates: list[str]) -> pd.DataFrame:
    index = pd.to_datetime(dates)
    return pd.DataFrame(
        {
            "open": closes,
            "high": [value + 1.0 for value in closes],
            "low": [value - 1.0 for value in closes],
            "close": closes,
            "adjusted_close": closes,
            "volume": [1_000_000.0 for _ in closes],
        },
        index=index,
    )
