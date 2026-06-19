from __future__ import annotations

import numpy as np
import pandas as pd

from src.dashboard.market import MarketConditionConfig, MarketConditionScorer
from src.dashboard.radar import RadarConfig, RadarViewModelBuilder
from src.indicators.core import IndicatorCalculator, IndicatorConfig
from src.services.market_service import (
    MARKET_OUTPUT_MODULE,
    MARKET_SNAPSHOT_OUTPUT_MODULE,
    RS_RADAR_INDUSTRY_OUTPUT_MODULE,
    RS_RADAR_SECTOR_OUTPUT_MODULE,
    MarketService,
)
from src.services.module_output_store import ModuleOutputStore
from src.services.price_data_service import PriceDataService
from src.services.price_store import PriceStore


def test_market_service_builds_market_and_radar_from_local_cache_as_of_date(tmp_path) -> None:
    dates = pd.date_range("2025-01-01", periods=320, freq="B")
    store = PriceStore(tmp_path / "prices")
    store.save("SPY", _history([100.0 + (i * 0.10) for i in range(320)], dates))
    store.save("SMH", _history([90.0 + (i * 0.18) for i in range(320)], dates))
    store.save("^VIX", _history([17.0 for _ in range(320)], dates))
    store.save("TLT", _history([120.0 - (i * 0.02) for i in range(320)], dates))
    output_store = ModuleOutputStore(tmp_path / "outputs")
    service = _service(store, output_store)

    result = service.run(as_of_date="2026-03-05", write_outputs=True)

    assert result.market_result.trade_date == pd.Timestamp("2026-03-05")
    assert result.market_result.label in {"Bullish", "Positive", "Neutral", "Negative", "Bearish"}
    assert list(result.market_result.market_snapshot["TICKER"]) == ["SPY"]
    assert not result.radar_result.sector_leaders.empty
    assert not result.radar_result.industry_leaders.empty
    assert result.radar_result.industry_leaders.iloc[0]["TICKER"] == "SMH"
    assert {record.module for record in result.output_records}.issuperset(
        {
            MARKET_OUTPUT_MODULE,
            MARKET_SNAPSHOT_OUTPUT_MODULE,
            RS_RADAR_SECTOR_OUTPUT_MODULE,
            RS_RADAR_INDUSTRY_OUTPUT_MODULE,
        }
    )
    assert output_store.load_json("market", "20260305")["trade_date"] == "2026-03-05"
    assert output_store.load_frame("market_snapshot", "20260305")["TICKER"].tolist() == ["SPY"]
    assert output_store.load_frame("rs_radar_industry", "20260305")["TICKER"].tolist() == ["SMH"]


def test_market_service_does_not_call_price_provider_when_cache_is_available(tmp_path) -> None:
    dates = pd.date_range("2025-01-01", periods=320, freq="B")
    store = PriceStore(tmp_path / "prices")
    store.save("SPY", _history([100.0 + (i * 0.10) for i in range(320)], dates))
    service = _service(store, None)

    result = service.run(as_of_date="2026-03-05")

    assert result.market_result.trade_date == pd.Timestamp("2026-03-05")
    assert "SPY" not in result.missing


def test_market_service_builds_from_existing_price_histories_without_provider(tmp_path) -> None:
    dates = pd.date_range("2025-01-01", periods=320, freq="B")
    store = PriceStore(tmp_path / "prices")
    service = _service(store, None)
    histories = {
        "SPY": _history([100.0 + (i * 0.10) for i in range(320)], dates),
        "SMH": _history([90.0 + (i * 0.18) for i in range(320)], dates),
        "^VIX": _history([17.0 for _ in range(320)], dates),
        "TLT": _history([120.0 - (i * 0.02) for i in range(320)], dates),
    }

    result = service.run_from_price_histories(histories, as_of_date="2026-03-04")

    assert result.market_result.trade_date == pd.Timestamp("2026-03-04")
    assert list(result.market_result.market_snapshot["TICKER"]) == ["SPY"]
    assert result.radar_result.industry_leaders.iloc[0]["TICKER"] == "SMH"
    assert result.missing == {}


class FailingProvider:
    def get_price_history(self, *args, **kwargs):
        raise AssertionError("provider should not be called")


def _service(store: PriceStore, output_store: ModuleOutputStore | None) -> MarketService:
    market_config = MarketConditionConfig.from_dict(
        {
            "market_condition_etf_universe": [{"ticker": "SPY", "name": "S&P 500"}],
            "safe_haven_risk_on_symbol": "SPY",
            "safe_haven_risk_off_symbol": "TLT",
            "index_state": {"symbols": ["SPY"]},
        }
    )
    radar_config = RadarConfig.from_dict(
        {
            "sector_etfs": [{"ticker": "SPY", "name": "S&P 500"}],
            "industry_etfs": [{"ticker": "SMH", "name": "Semiconductor", "major_stocks": ["NVDA", "AVGO", "AMD"]}],
        }
    )
    return MarketService(
        price_service=PriceDataService(store=store, provider=FailingProvider()),
        indicator_calculator=IndicatorCalculator(IndicatorConfig()),
        market_scorer=MarketConditionScorer(market_config),
        radar_builder=RadarViewModelBuilder(radar_config),
        benchmark_symbol="SPY",
        fred_provider=None,
        output_store=output_store,
    )


def _history(values: list[float], dates: pd.DatetimeIndex) -> pd.DataFrame:
    close = pd.Series(values, index=dates, dtype=float)
    return pd.DataFrame(
        {
            "open": close * 0.995,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "adjusted_close": close,
            "volume": np.linspace(1_000_000, 2_000_000, len(close)),
        },
        index=dates,
    )
