from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd

from app.main import _stock_card_metadata_lookup, export_stock_cards_for_symbols
from src.dashboard.stock_card import StockCardGenerator, StockCardMetadata
from src.data.results import FetchStatus, PriceHistoryBatch
from src.pipeline import PlatformArtifacts


def _history(dates: pd.DatetimeIndex) -> pd.DataFrame:
    close = pd.Series([20.0 + index * 0.08 for index in range(len(dates))], index=dates)
    return pd.DataFrame(
        {
            "open": close - 0.10,
            "high": close + 0.25,
            "low": close - 0.25,
            "close": close,
            "adjusted_close": close,
            "volume": [100_000 + (index % 7) * 1_000 for index in range(len(dates))],
        },
        index=dates,
    )


def _artifacts() -> PlatformArtifacts:
    snapshot = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2026-03-13")],
            "close": [40.72],
            "sector": ["Technology"],
            "rs_pctl": [86.0],
        },
        index=["AAA"],
    )
    return PlatformArtifacts(
        snapshot=snapshot,
        eligible_snapshot=snapshot.copy(),
        watchlist=pd.DataFrame(),
        duplicate_tickers=pd.DataFrame(),
        watchlist_cards=[],
        earnings_today=pd.DataFrame(),
        scan_hits=pd.DataFrame(),
        benchmark_history=pd.DataFrame(),
        vix_history=pd.DataFrame(),
        market_result=None,
        radar_result=None,
        used_sample_data=False,
        data_source_label="test",
        fetch_status=pd.DataFrame(),
        data_health_summary={},
        run_directory=None,
        universe_mode="manual",
        resolved_symbols=["AAA"],
        universe_snapshot_path=None,
        artifact_origin="test",
    )


def _half_up(value: object, digits: int = 2) -> Decimal:
    quantizer = Decimal("1") if digits == 0 else Decimal("1").scaleb(-digits)
    return Decimal(str(value)).quantize(quantizer, rounding=ROUND_HALF_UP)


def _breakout_pullback_history(dates: pd.DatetimeIndex) -> pd.DataFrame:
    close = pd.Series([45.0 + index * 0.11 for index in range(len(dates))], index=dates)
    history = pd.DataFrame(
        {
            "open": close - 0.40,
            "high": close + 0.80,
            "low": close - 0.80,
            "close": close,
            "adjusted_close": close,
            "volume": [800_000 + (index % 11) * 10_000 for index in range(len(dates))],
        },
        index=dates,
    )
    history.iloc[-60, history.columns.get_loc("low")] = 40.00
    last_rows = [
        (68.40, 69.23, 66.77, 68.29, 900_000),
        (70.30, 75.79, 65.20, 70.91, 1_500_000),
        (69.51, 76.78, 69.02, 69.61, 1_000_000),
        (71.48, 76.30, 69.47, 76.15, 1_100_000),
        (76.34, 83.30, 75.23, 82.78, 1_700_000),
    ]
    for row, (open_, high, low, close_, volume) in zip(range(-5, 0), last_rows):
        history.iloc[row, history.columns.get_loc("open")] = open_
        history.iloc[row, history.columns.get_loc("high")] = high
        history.iloc[row, history.columns.get_loc("low")] = low
        history.iloc[row, history.columns.get_loc("close")] = close_
        history.iloc[row, history.columns.get_loc("adjusted_close")] = close_
        history.iloc[row, history.columns.get_loc("volume")] = volume
    return history


def _mock_indicator_frame(history: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "stage_label": ["stage2_candidate"] * len(history),
            "sma50": [70.00] * len(history),
            "sma150": [58.00] * len(history),
            "sma200": [54.00] * len(history),
            "sma200_slope_1m_pct": [1.0] * len(history),
            "ema21_close": [70.00] * len(history),
            "atr": [3.00] * len(history),
            "high_52w": [83.30] * len(history),
            "low_52w": [19.64] * len(history),
        },
        index=history.index,
    )


def test_stock_card_generator_outputs_fixed_sections_and_embeds_tape() -> None:
    dates = pd.bdate_range("2025-03-03", periods=270)
    document = StockCardGenerator().build(
        "aaa",
        _history(dates),
        metadata=StockCardMetadata(sector_etf="XLK", industry_etf="SMH", industry_rs_rank=1, rs_pctl=86.0),
    )

    assert document.filename == "card_AAA_20260313.md"
    assert document.text.startswith("# STOCK_CARD AAA | 2026-03-13 (Fri) | schema card-v1.0.2")
    for section in ["META", "GATES", "TREND", "MOMO_VOL", "VOLUME", "LEVELS", "SETUP", "RISK_PLAN", "TAPE"]:
        assert f"## {section}" in document.text
    assert "INDUSTRY_ETF=SMH IND_RS_RANK=1 SECTOR=XLK" in document.text
    assert "TT=" in document.text and "RS_PCTL=86" in document.text
    assert "## TAPE (tape-v1.0.1)" in document.text
    assert "## EVENTS_50D" in document.text
    assert "RV20=+" not in document.text


def test_stock_card_marks_current_day_pivot_and_uses_display_buy_rounding() -> None:
    dates = pd.bdate_range("2025-03-03", periods=270)
    history = _history(dates)
    history.iloc[-1, history.columns.get_loc("high")] = 41.7040
    history.iloc[-1, history.columns.get_loc("close")] = 41.50
    history.iloc[-1, history.columns.get_loc("adjusted_close")] = 41.50

    document = StockCardGenerator().build("AAA", history)

    assert "PIVOT=41.70(0313*)" in document.text
    assert "BUY=41.74" in document.text


def test_stock_card_risk_plan_recomputes_from_display_values() -> None:
    dates = pd.bdate_range("2025-03-03", periods=270)
    document = StockCardGenerator().build("AAA", _history(dates))
    lines = document.text.splitlines()
    risk_header = next(line for line in lines if line.startswith("## RISK_PLAN"))
    momo_line = next(line for line in lines if line.startswith("ATR14="))
    sl_line = next(line for line in lines if line.startswith("SL_CAND:"))
    tp_line = next(line for line in lines if line.startswith("TP_CAND:"))

    basis = Decimal(risk_header.split("basis: BUY=")[1].split(")")[0].replace("(ref", ""))
    atr = Decimal(momo_line.split("ATR14=")[1].split("(")[0])
    atr2 = Decimal(sl_line.split("atr2=")[1].split("(")[0])
    cap8 = Decimal(sl_line.split("cap8=")[1].split("(")[0])
    sl_first = Decimal(sl_line.split("struct=")[1].split("(")[0]) if "struct=NA" not in sl_line else atr2
    risk = basis - sl_first
    tp2 = Decimal(tp_line.split("2R=")[1].split(" ")[0])
    tp3 = Decimal(tp_line.split("3R=")[1].split(" ")[0])
    oneil_low = Decimal(tp_line.split("oneil=")[1].split("..")[0])
    oneil_high = Decimal(tp_line.split("..")[1].split(" ")[0])

    assert atr2 == _half_up(basis - Decimal("2.0") * atr)
    assert cap8 == _half_up(basis * Decimal("0.92"))
    assert tp2 == _half_up(basis + Decimal("2.0") * risk)
    assert tp3 == _half_up(basis + Decimal("3.0") * risk)
    assert oneil_low == _half_up(basis * Decimal("1.20"))
    assert oneil_high == _half_up(basis * Decimal("1.25"))


def test_stock_card_expires_stale_non_pivot_candidates_and_uses_buy_ref_basis() -> None:
    dates = pd.bdate_range("2025-03-03", periods=270)
    history = _history(dates)
    history.iloc[-65:, history.columns.get_loc("low")] = 30.0
    history.iloc[-5:, history.columns.get_loc("open")] = [49.0, 50.0, 52.5, 58.0, 59.0]
    history.iloc[-5:, history.columns.get_loc("high")] = [50.0, 51.0, 54.0, 61.5, 61.0]
    history.iloc[-5:, history.columns.get_loc("low")] = [48.0, 49.0, 52.0, 57.0, 59.0]
    history.iloc[-5:, history.columns.get_loc("close")] = [49.5, 50.5, 53.0, 58.5, 60.0]
    history.iloc[-5:, history.columns.get_loc("adjusted_close")] = history["close"].iloc[-5:]

    document = StockCardGenerator().build("AAA", history)

    assert "CANDIDATES=NONE" in document.text
    assert "RECLAIM" not in next(line for line in document.text.splitlines() if line.startswith("CANDIDATES="))
    assert "## RISK_PLAN (basis: BUY=" in document.text
    assert "(ref))" in document.text


def test_stock_card_struct_stop_ignores_noise_inside_distance_floor() -> None:
    dates = pd.bdate_range("2025-03-03", periods=270)
    history = _history(dates)
    history.iloc[-65:, history.columns.get_loc("low")] = 30.0
    history.iloc[-1, history.columns.get_loc("open")] = 59.9
    history.iloc[-1, history.columns.get_loc("high")] = 61.0
    history.iloc[-1, history.columns.get_loc("low")] = 59.8
    history.iloc[-1, history.columns.get_loc("close")] = 60.0
    history.iloc[-1, history.columns.get_loc("adjusted_close")] = 60.0

    document = StockCardGenerator().build("AAA", history)

    assert "SL_CAND: struct=NA" in document.text


def test_stock_card_prioritizes_current_day_pivot_breakout_over_pullback(monkeypatch) -> None:
    dates = pd.bdate_range("2025-06-02", periods=270)
    history = _breakout_pullback_history(dates)
    generator = StockCardGenerator()
    monkeypatch.setattr(generator.indicator_calculator, "calculate", lambda frame: _mock_indicator_frame(frame))

    document = generator.build("AMKR", history)
    candidate_line = next(line for line in document.text.splitlines() if line.startswith("CANDIDATES="))

    assert candidate_line.startswith("CANDIDATES=PIVOT_BREAKOUT")
    assert "PULLBACK" not in candidate_line
    assert "## RISK_PLAN (basis: BUY=83.38)" in document.text
    assert "PULLBACK_REF=0611(69.47)" in document.text


def test_stock_card_metadata_falls_back_to_profile_industry(tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "radar:",
                "  industry_etfs:",
                "  - ticker: SMH",
                "    name: Semiconductor",
                "    major_stocks: [NVDA, AVGO, AMD]",
            ]
        ),
        encoding="utf-8",
    )
    artifacts = _artifacts()
    artifacts.snapshot.loc["BBB", "sector"] = "Technology"
    artifacts.snapshot.loc["BBB", "industry"] = ""
    artifacts.eligible_snapshot = artifacts.snapshot.copy()
    artifacts.eligible_snapshot.loc["BBB", "industry"] = "Semiconductor Equipment & Materials"
    artifacts.radar_result = type(
        "RadarResult",
        (),
        {"industry_leaders": pd.DataFrame([{"TICKER": "SMH"}, {"TICKER": "XBI"}])},
    )()

    lookup = _stock_card_metadata_lookup(str(config_path), artifacts)

    assert lookup["BBB"].industry_etf == "SMH"
    assert lookup["BBB"].industry_rs_rank == 1


def test_export_stock_cards_for_symbols_writes_manifest(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.yaml"
    output_dir = tmp_path / "stock_cards"
    config_path.write_text(
        "\n".join(
            [
                "stock_card:",
                f"  output_dir: {str(output_dir).replace(chr(92), '/')}",
                "radar:",
                "  industry_etfs:",
                "  - ticker: SMH",
                "    name: Semiconductor",
                "    major_stocks: [AAA]",
            ]
        ),
        encoding="utf-8",
    )
    dates = pd.bdate_range("2025-03-03", periods=270)

    class FakePlatform:
        def __init__(self, config_path: str) -> None:
            self.config_path = config_path

        def load_price_histories(self, symbols: list[str], *, period: str | None = None, force_refresh: bool = False) -> PriceHistoryBatch:
            return PriceHistoryBatch(
                histories={"AAA": _history(dates)},
                statuses={"AAA": FetchStatus(symbol="AAA", dataset="price", source="cache_fresh", has_data=True)},
            )

    monkeypatch.setattr("app.main.ResearchPlatform", FakePlatform)

    result = export_stock_cards_for_symbols(str(config_path), _artifacts(), ["AAA"], source="manual_symbols")

    assert len(result.documents) == 1
    assert (output_dir / "20260313" / "card_AAA_20260313.md").exists()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "stock_card_manifest_v1"
    assert manifest["documents"][0]["ticker"] == "AAA"
    assert manifest["missing"] == {}
