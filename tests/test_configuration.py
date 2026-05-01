from __future__ import annotations

import tempfile
from pathlib import Path

from src.configuration import load_settings
from src.scan.rules import ScanConfig


def test_load_settings_merges_manifest_includes() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        base = root / "base"
        base.mkdir()
        (base / "app.yaml").write_text(
            """app:
  benchmark_symbol: SPY
  price_period: 1y
""",
            encoding="utf-8",
        )
        (base / "scan.yaml").write_text(
            """scan:
  duplicate_min_count: 3
  enabled_scan_rules:
    - VCS
""",
            encoding="utf-8",
        )
        manifest = root / "default.yaml"
        manifest.write_text(
            """includes:
  - base/app.yaml
  - base/scan.yaml
scan:
  duplicate_min_count: 5
""",
            encoding="utf-8",
        )

        settings = load_settings(manifest)

        assert settings["app"]["benchmark_symbol"] == "SPY"
        assert settings["app"]["price_period"] == "1y"
        assert settings["scan"]["duplicate_min_count"] == 5
        assert settings["scan"]["enabled_scan_rules"] == ["VCS"]


def test_load_settings_accepts_config_directory_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        config_dir = root / "default"
        config_dir.mkdir()
        (config_dir / "01_app.yaml").write_text(
            """app:
  benchmark_symbol: QQQ
""",
            encoding="utf-8",
        )
        (config_dir / "02_scan.yaml").write_text(
            """scan:
  watchlist_sort_mode: hybrid_score
""",
            encoding="utf-8",
        )

        settings = load_settings(config_dir)

        assert settings["app"]["benchmark_symbol"] == "QQQ"
        assert settings["scan"]["watchlist_sort_mode"] == "hybrid_score"


def test_default_settings_include_builtin_watchlist_presets() -> None:
    settings = load_settings()

    presets = settings["scan"]["watchlist_presets"]
    preset_names = [preset["preset_name"] for preset in presets]

    assert len(presets) == 17
    assert preset_names == [
        "Leader Breakout",
        "Orderly Pullback",
        "Reclaim Trigger",
        "Momentum Surge",
        "Early Cycle Recovery",
        "Base Breakout",
        "Accumulation Breakout",
        "VCP 3T Breakout",
        "50SMA Defense",
        "Power Gap Pullback",
        "RS Breakout Setup",
        "Trend Pullback",
        "Resilient Leader",
        "Early Recovery",
        "Screening Thesis",
        "Pullback Trigger",
        "Momentum Ignition",
    ]


def test_default_watchlist_presets_use_expected_duplicate_rules() -> None:
    settings = load_settings()
    scan_config = ScanConfig.from_dict(settings["scan"])
    required_plus_optional_rules = {
        "Leader Breakout": (("97 Club", "VCS 52 High"), ("RS Acceleration", "Three Weeks Tight")),
        "Reclaim Trigger": (("Reclaim scan",), ("Pocket Pivot",)),
        "Momentum Surge": (("4% bullish", "Momentum 97"), ("PP Count", "Sustained Leadership")),
        "Early Cycle Recovery": (("Trend Reversal Setup",), ("Pocket Pivot", "VCS 52 Low", "Volume Accumulation")),
        "Base Breakout": (("VCS 52 High", "Pocket Pivot"), ("97 Club", "Three Weeks Tight")),
        "Early Recovery": (("Trend Reversal Setup", "Structure Pivot"), ("VCS 52 Low", "Volume Accumulation")),
    }
    grouped_rules = {
        "Orderly Pullback": (
            (),
            (
                ("21EMA Trigger", ("21EMA Pattern H", "21EMA Pattern L"), 1),
                ("Quality / Strength Confirmation", ("Pullback Quality scan", "RS Acceleration", "Volume Accumulation"), 1),
            ),
        ),
        "Accumulation Breakout": (
            ("VCS 52 High",),
            (
                ("Accumulation Evidence", ("PP Count", "Volume Accumulation"), 1),
                ("Breakout Trigger", ("Pocket Pivot", "4% bullish", "VCP 3T"), 1),
            ),
        ),
        "VCP 3T Breakout": (
            ("VCP 3T",),
            (
                ("Leadership / High Tightness", ("VCS 52 High", "RS New High"), 1),
                ("Demand Confirmation", ("Pocket Pivot", "Volume Accumulation"), 1),
            ),
        ),
        "50SMA Defense": (
            ("50SMA Reclaim",),
            (
                ("Pullback Quality", ("Pullback Quality scan",), 1),
                ("Demand Confirmation", ("Volume Accumulation", "Pocket Pivot"), 1),
            ),
        ),
        "Power Gap Pullback": (
            ("Pullback Quality scan",),
            (
                ("Reentry Trigger", ("21EMA Pattern H", "21EMA Pattern L", "Reclaim scan"), 1),
                ("Demand Confirmation", ("Volume Accumulation", "Pocket Pivot"), 1),
            ),
        ),
        "RS Breakout Setup": (
            ("RS New High", "VCS 52 High"),
            (
                ("Breakout Event", ("Pocket Pivot", "4% bullish", "PP Count"), 1),
            ),
        ),
        "Trend Pullback": (
            ("Reclaim scan",),
            (
                ("Pullback Evidence", ("Pullback Quality scan",), 1),
                ("Strength Confirmation", ("RS Acceleration", "Volume Accumulation"), 1),
            ),
        ),
        "Screening Thesis": (
            ("Trend Reversal Setup",),
            (
                (
                    "Structure Break",
                    ("LL-HL Structure 1st Pivot", "LL-HL Structure 2nd Pivot", "LL-HL Structure Trend Line Break"),
                    1,
                ),
                ("Demand Confirmation", ("Volume Accumulation", "Pocket Pivot"), 1),
            ),
        ),
        "Pullback Trigger": (
            ("Pullback Quality scan",),
            (
                ("Pattern Trigger", ("21EMA Pattern H", "21EMA Pattern L"), 1),
                ("Demand Confirmation", ("Volume Accumulation", "Pocket Pivot"), 1),
            ),
        ),
        "Momentum Ignition": (
            ("Momentum 97",),
            (
                ("Acceleration Event", ("4% bullish", "PP Count"), 1),
                ("Quality Structure", ("VCS 52 High", "Volume Accumulation"), 1),
            ),
        ),
    }

    presets = {preset.preset_name: preset for preset in scan_config.watchlist_presets}

    assert set(presets) == {*required_plus_optional_rules, *grouped_rules, "Resilient Leader"}
    for preset_name, (required_scans, optional_scans) in required_plus_optional_rules.items():
        preset = presets[preset_name]
        assert preset.duplicate_threshold == 1
        assert preset.duplicate_rule.mode == "required_plus_optional_min"
        assert preset.duplicate_rule.required_scans == required_scans
        assert preset.duplicate_rule.optional_scans == optional_scans
        assert preset.duplicate_rule.optional_min_hits == 1

    for preset_name, (required_scans, optional_groups) in grouped_rules.items():
        preset = presets[preset_name]
        assert preset.duplicate_threshold == 1
        assert preset.duplicate_rule.mode == "grouped_threshold"
        assert preset.duplicate_rule.required_scans == required_scans
        assert [(group.group_name, group.scans, group.min_hits) for group in preset.duplicate_rule.optional_groups] == list(
            optional_groups
        )

    resilient = presets["Resilient Leader"]
    assert resilient.duplicate_threshold == 2
    assert resilient.duplicate_rule.mode == "min_count"
    assert resilient.duplicate_rule.min_count == 2
    assert resilient.selected_scan_names == ("Sustained Leadership", "Near 52W High")


def test_default_watchlist_presets_do_not_reference_disabled_scans() -> None:
    settings = load_settings()
    scan_config = ScanConfig.from_dict(settings["scan"])
    disabled_scans = {
        name
        for name, status in scan_config.scan_status_map.items()
        if status == "disabled"
    }

    assert {"Vol Up", "VCS"}.issubset(disabled_scans)
    for preset in scan_config.watchlist_presets:
        if preset.preset_status == "disabled":
            continue
        assert disabled_scans.isdisjoint(preset.selected_scan_names)
        assert disabled_scans.isdisjoint(preset.duplicate_rule.required_scans)
        assert disabled_scans.isdisjoint(preset.duplicate_rule.optional_scans)


def test_default_settings_include_annotation_and_entry_signal_status_maps() -> None:
    settings = load_settings()

    annotation_status_map = settings["scan"]["annotation_filter_status_map"]
    signal_status_map = settings["entry_signals"]["signal_status_map"]
    context_guard = settings["entry_signals"]["context_guard"]
    orderly_pool = settings["entry_signals"]["definitions"]["orderly_pullback_entry"]["pool"]

    assert annotation_status_map["Trend Base"] == "enabled"
    assert annotation_status_map["Recent Power Gap"] == "enabled"
    assert signal_status_map["orderly_pullback_entry"] == "enabled"
    assert signal_status_map["pullback_resumption_entry"] == "enabled"
    assert context_guard["enabled"] is True
    assert context_guard["weak_market_score_threshold"] == 30.0
    assert context_guard["signal_overrides"]["momentum_acceleration_entry"]["weak_market_score_threshold"] == 40.0
    assert context_guard["signal_overrides"]["early_cycle_recovery_entry"]["weak_market_score_threshold"] == 20.0
    assert orderly_pool["preset_sources"] == ["Pullback Trigger"]
