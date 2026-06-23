from __future__ import annotations

import pandas as pd
import pytest

from src.dashboard.compressed_tape import CompressedTapeConfig, CompressedTapeError, CompressedTapeGenerator


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
