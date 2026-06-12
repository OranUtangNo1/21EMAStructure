from __future__ import annotations

import json

import pandas as pd
import pytest

from app.main import export_compressed_tapes_for_symbols, export_preset_hit_compressed_tapes
from src.dashboard.compressed_tape import CompressedTapeConfig, CompressedTapeError, CompressedTapeGenerator
from src.data.results import FetchStatus, PriceHistoryBatch
from src.pipeline import PlatformArtifacts


def _history(dates: pd.DatetimeIndex) -> pd.DataFrame:
    close = pd.Series([20.0 + index * 0.1 for index in range(len(dates))], index=dates)
    return pd.DataFrame(
        {
            "open": close - 0.05,
            "high": close + 0.20,
            "low": close - 0.20,
            "close": close,
            "adjusted_close": close,
            "volume": [100_000] * len(dates),
        },
        index=dates,
    )


def test_compressed_tape_uses_previous_source_close_for_first_tape_row() -> None:
    dates = pd.bdate_range("2026-03-01", periods=60)
    history = _history(dates)
    generator = CompressedTapeGenerator(CompressedTapeConfig(t0_days=15))

    document = generator.build_t0("aaa", history)

    lines = document.text.splitlines()
    assert lines[0] == "## TAPE (tape-v1.0.1)"
    assert "ADJ=Y" in lines[1]
    assert len([line for line in lines if "|" in line]) == 16
    first_data_line = lines[3]
    assert first_data_line.split("|")[5] != "NA"
    assert first_data_line.split("|")[5].startswith("+")


def test_compressed_tape_formats_year_crossing_dates_as_iso() -> None:
    dates = pd.bdate_range("2025-12-22", periods=20)
    document = CompressedTapeGenerator(CompressedTapeConfig(t0_days=15)).build_t0("AAA", _history(dates))

    first_data_line = document.text.splitlines()[3]

    assert first_data_line.startswith("2025-")


def test_compressed_tape_flags_and_events_follow_spec_order() -> None:
    dates = pd.bdate_range("2026-03-01", periods=60)
    history = _history(dates)
    history.iloc[50, history.columns.get_loc("close")] = 25.0
    history.iloc[50, history.columns.get_loc("high")] = 25.1
    history.iloc[50, history.columns.get_loc("low")] = 20.0
    history.iloc[50, history.columns.get_loc("open")] = 20.2
    history.iloc[50, history.columns.get_loc("adjusted_close")] = 25.0
    history.iloc[50, history.columns.get_loc("volume")] = 300_000

    prior_low = float(history["low"].iloc[47:57].min())
    history.iloc[57, history.columns.get_loc("low")] = prior_low - 0.5
    history.iloc[57, history.columns.get_loc("close")] = prior_low + 0.1
    history.iloc[57, history.columns.get_loc("adjusted_close")] = prior_low + 0.1

    history.iloc[58, history.columns.get_loc("open")] = float(history["high"].iloc[57]) + 1.0
    history.iloc[58, history.columns.get_loc("high")] = float(history["high"].iloc[57]) + 2.0
    history.iloc[58, history.columns.get_loc("low")] = float(history["close"].iloc[57]) - 0.2
    history.iloc[58, history.columns.get_loc("close")] = float(history["low"].iloc[58]) + 0.05
    history.iloc[58, history.columns.get_loc("adjusted_close")] = float(history["close"].iloc[58])
    history.iloc[58, history.columns.get_loc("volume")] = 300_000

    document = CompressedTapeGenerator(CompressedTapeConfig(t0_days=5)).build_t0("AAA", history)

    assert "|U" in document.text
    assert "|G+!D" in document.text
    assert "## EVENTS_50D\n" in document.text
    assert "!A" in document.text


def test_compressed_tape_rejects_invalid_ohlc() -> None:
    dates = pd.bdate_range("2026-03-01", periods=60)
    history = _history(dates)
    history.iloc[-1, history.columns.get_loc("low")] = float(history.iloc[-1]["close"]) + 1.0

    with pytest.raises(CompressedTapeError):
        CompressedTapeGenerator().build_t0("AAA", history)


def test_export_compressed_tapes_for_symbols_writes_manifest(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.yaml"
    output_dir = tmp_path / "tapes"
    config_path.write_text(
        "\n".join(
            [
                "compressed_tape:",
                f"  output_dir: {str(output_dir).replace(chr(92), '/')}",
                "  t0_days: 15",
            ]
        ),
        encoding="utf-8",
    )
    dates = pd.bdate_range("2026-03-01", periods=60)

    class FakePlatform:
        def __init__(self, config_path: str) -> None:
            self.config_path = config_path

        def load_price_histories(self, symbols: list[str], *, period: str | None = None, force_refresh: bool = False) -> PriceHistoryBatch:
            return PriceHistoryBatch(
                histories={"AAA": _history(dates)},
                statuses={"AAA": FetchStatus(symbol="AAA", dataset="price", source="cache_fresh", has_data=True)},
            )

    monkeypatch.setattr("app.main.ResearchPlatform", FakePlatform)
    artifacts = PlatformArtifacts(
        snapshot=pd.DataFrame({"trade_date": [pd.Timestamp("2026-05-22")], "close": [25.9]}, index=["AAA"]),
        eligible_snapshot=pd.DataFrame(),
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

    result = export_compressed_tapes_for_symbols(str(config_path), artifacts, ["AAA"], source="manual_symbols")

    assert len(result.documents) == 1
    assert (output_dir / "20260522" / "tape_AAA_20260522.md").exists()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["documents"][0]["ticker"] == "AAA"
    assert manifest["missing"] == {}


def test_export_preset_hit_compressed_tapes_uses_preset_duplicate_hits(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.yaml"
    output_dir = tmp_path / "preset_tapes"
    config_path.write_text(
        "\n".join(
            [
                "compressed_tape:",
                f"  output_dir: {str(output_dir).replace(chr(92), '/')}",
                "scan:",
                "  duplicate_min_count: 2",
                "  enabled_scan_rules: [21EMA Pattern H, Pocket Pivot]",
                "  card_sections:",
                "  - scan_name: 21EMA Pattern H",
                "    display_name: 21EMA",
                "  - scan_name: Pocket Pivot",
                "    display_name: Pocket Pivot",
                "  watchlist_presets:",
                "  - preset_name: Momentum Core",
                "    selected_scan_names: [21EMA Pattern H, Pocket Pivot]",
                "    selected_annotation_filters: []",
                "    selected_duplicate_subfilters: []",
                "    duplicate_threshold: 2",
                "    preset_status: enabled",
            ]
        ),
        encoding="utf-8",
    )
    dates = pd.bdate_range("2026-03-01", periods=60)

    class FakePlatform:
        def __init__(self, config_path: str) -> None:
            self.config_path = config_path

        def load_price_histories(self, symbols: list[str], *, period: str | None = None, force_refresh: bool = False) -> PriceHistoryBatch:
            return PriceHistoryBatch(
                histories={symbol: _history(dates) for symbol in symbols},
                statuses={symbol: FetchStatus(symbol=symbol, dataset="price", source="cache_fresh", has_data=True) for symbol in symbols},
            )

    monkeypatch.setattr("app.main.ResearchPlatform", FakePlatform)
    watchlist = pd.DataFrame(
        {
            "hybrid_score": [90.0, 85.0],
            "overlap_count": [2, 1],
            "vcs": [70.0, 65.0],
        },
        index=["AAA", "BBB"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "name": "21EMA Pattern H", "kind": "scan"},
            {"ticker": "AAA", "name": "Pocket Pivot", "kind": "scan"},
            {"ticker": "BBB", "name": "21EMA Pattern H", "kind": "scan"},
        ]
    )
    artifacts = PlatformArtifacts(
        snapshot=pd.DataFrame({"trade_date": [pd.Timestamp("2026-05-22")]}, index=["AAA"]),
        eligible_snapshot=pd.DataFrame(),
        watchlist=watchlist,
        duplicate_tickers=pd.DataFrame(),
        watchlist_cards=[],
        earnings_today=pd.DataFrame(),
        scan_hits=hits,
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
        resolved_symbols=["AAA", "BBB"],
        universe_snapshot_path=None,
        artifact_origin="test",
    )

    result = export_preset_hit_compressed_tapes(str(config_path), artifacts)

    assert result is not None
    assert [document.ticker for document in result.documents] == ["AAA"]
    assert (output_dir / "20260522" / "tape_AAA_20260522.md").exists()
    assert not (output_dir / "20260522" / "tape_BBB_20260522.md").exists()
