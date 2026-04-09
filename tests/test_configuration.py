from __future__ import annotations

import tempfile
from pathlib import Path

from src.configuration import load_settings


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

    assert len(presets) == 10
    assert presets[0]["preset_name"] == "Leader Breakout"
    assert presets[-1]["preset_name"] == "Pattern 5 - Early Reversal Signal"
