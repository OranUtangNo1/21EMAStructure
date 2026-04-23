from __future__ import annotations

import pandas as pd

from src.scan.rules import ScanConfig
from src.signals.rules import EntrySignalConfig
from src.signals.runner import (
    ENTRY_SIGNAL_UNIVERSE_MODE_CURRENT,
    ENTRY_SIGNAL_UNIVERSE_MODE_ELIGIBLE,
    ENTRY_SIGNAL_UNIVERSE_MODE_PRESETS,
    ENTRY_SIGNAL_UNIVERSE_MODE_WATCHLIST,
    EntrySignalRunner,
)


def test_entry_signal_config_excludes_disabled_signals() -> None:
    config = EntrySignalConfig.from_dict(
        {
            "signal_status_map": {
                "Pocket Pivot Entry": "disabled",
                "Structure Pivot Breakout Entry": "enabled",
            },
            "default_selected_signal_names": [
                "Pocket Pivot Entry",
                "Structure Pivot Breakout Entry",
            ],
        }
    )

    assert "Pocket Pivot Entry" not in config.enabled_signal_names()
    assert config.startup_selected_signal_names() == ("Structure Pivot Breakout Entry",)


def test_entry_signal_runner_uses_preset_and_current_duplicate_universe() -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
                {"scan_name": "VCS", "display_name": "VCS"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Preset Core",
                    "selected_scan_names": ["Pocket Pivot", "VCS"],
                    "duplicate_threshold": 2,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict({})
    watchlist = pd.DataFrame(
        {
            "close": [55.0, 42.0],
            "sma50": [50.0, 40.0],
            "pocket_pivot": [True, False],
            "structure_pivot_long_breakout_first_day": [False, True],
            "rs21": [88.0, 72.0],
            "vcs": [65.0, 61.0],
            "rel_volume": [1.8, 1.2],
            "dist_from_52w_high": [-3.0, -24.0],
        },
        index=["AAA", "BBB"],
    )
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "kind": "scan", "name": "Pocket Pivot"},
            {"ticker": "AAA", "kind": "scan", "name": "VCS"},
            {"ticker": "BBB", "kind": "scan", "name": "VCS"},
        ]
    )

    runner = EntrySignalRunner(signal_config, scan_config)
    universe = runner.build_default_universe(
        watchlist,
        hits,
        selected_scan_names=["VCS"],
        duplicate_threshold=1,
    )
    result = runner.evaluate(
        universe,
        ["Pocket Pivot Entry", "Structure Pivot Breakout Entry"],
    )

    assert set(universe.index) == {"AAA", "BBB"}
    assert "Preset Core" in universe.loc["AAA", "universe_sources"]
    assert "Current Selection" in universe.loc["BBB", "universe_sources"]
    assert set(result["Ticker"]) == {"AAA", "BBB"}
    assert result.loc[result["Ticker"] == "AAA", "Entry Signals"].iloc[0] == "Pocket Pivot Entry"
    assert result.loc[result["Ticker"] == "BBB", "Entry Signals"].iloc[0] == "Structure Pivot Breakout"


def test_entry_signal_runner_builds_selected_universe_modes() -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
                {"scan_name": "VCS", "display_name": "VCS"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Preset Core",
                    "selected_scan_names": ["Pocket Pivot", "VCS"],
                    "duplicate_threshold": 2,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    watchlist = pd.DataFrame({"close": [55.0, 42.0]}, index=["AAA", "BBB"])
    eligible_snapshot = pd.DataFrame({"close": [55.0, 42.0, 80.0]}, index=["AAA", "BBB", "CCC"])
    hits = pd.DataFrame(
        [
            {"ticker": "AAA", "kind": "scan", "name": "Pocket Pivot"},
            {"ticker": "AAA", "kind": "scan", "name": "VCS"},
            {"ticker": "BBB", "kind": "scan", "name": "VCS"},
        ]
    )

    runner = EntrySignalRunner(EntrySignalConfig.from_dict({}), scan_config)

    preset_universe = runner.build_universe(
        watchlist,
        hits,
        selected_scan_names=["VCS"],
        duplicate_threshold=1,
        universe_mode=ENTRY_SIGNAL_UNIVERSE_MODE_PRESETS,
    )
    current_universe = runner.build_universe(
        watchlist,
        hits,
        selected_scan_names=["VCS"],
        duplicate_threshold=1,
        universe_mode=ENTRY_SIGNAL_UNIVERSE_MODE_CURRENT,
    )
    watchlist_universe = runner.build_universe(
        watchlist,
        hits,
        selected_scan_names=[],
        duplicate_threshold=1,
        universe_mode=ENTRY_SIGNAL_UNIVERSE_MODE_WATCHLIST,
    )
    eligible_universe = runner.build_universe(
        watchlist,
        hits,
        selected_scan_names=[],
        duplicate_threshold=1,
        universe_mode=ENTRY_SIGNAL_UNIVERSE_MODE_ELIGIBLE,
        eligible_snapshot=eligible_snapshot,
    )

    assert set(preset_universe.index) == {"AAA"}
    assert set(current_universe.index) == {"AAA", "BBB"}
    assert set(watchlist_universe.index) == {"AAA", "BBB"}
    assert set(eligible_universe.index) == {"AAA", "BBB", "CCC"}
    assert watchlist_universe.loc["AAA", "universe_sources"] == "Today's Watchlist"
    assert eligible_universe.loc["CCC", "universe_sources"] == "Eligible Universe"


def test_entry_signal_runner_evaluates_resistance_breakout_entry() -> None:
    scan_config = ScanConfig()
    signal_config = EntrySignalConfig.from_dict({})
    universe = pd.DataFrame(
        {
            "close": [101.0],
            "resistance_level_lookback": [100.0],
            "resistance_test_count": [2.0],
            "breakout_body_ratio": [0.7],
            "rel_volume": [1.6],
            "universe_sources": ["Current Selection"],
        },
        index=["AAA"],
    )

    runner = EntrySignalRunner(signal_config, scan_config)
    result = runner.evaluate(universe, ["Resistance Breakout Entry"])

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Entry Signals"] == "Resistance Breakout Entry"
    assert result.iloc[0]["Risk Reference"] == "resistance_level_lookback: 100.00"
