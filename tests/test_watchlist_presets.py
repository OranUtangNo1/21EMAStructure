from __future__ import annotations

from pathlib import Path

from src.ui_preferences import UserPreferenceStore
from src.watchlist_presets import (
    WATCHLIST_PRESET_GROUP,
    load_watchlist_preset_configs,
    watchlist_preference_namespace,
)


def test_load_watchlist_preset_configs_includes_custom_presets(tmp_path: Path) -> None:
    preference_path = tmp_path / "user_preferences.yaml"
    config_path = tmp_path / "default.yaml"
    config_path.write_text(
        f"""app:
  user_preferences_path: {preference_path.as_posix()}
scan:
  card_sections:
    - scan_name: Pullback Quality scan
      display_name: Pullback Quality
    - scan_name: Pocket Pivot
      display_name: Pocket Pivot
  annotation_filters:
    - filter_name: Trend Base
      display_name: Trend Base
  watchlist_presets: []
""",
        encoding="utf-8",
    )
    namespace = watchlist_preference_namespace(str(config_path))
    UserPreferenceStore(preference_path).save_collection_item(
        WATCHLIST_PRESET_GROUP,
        namespace,
        "Custom Pullback",
        {
            "schema_version": 1,
            "kind": "watchlist_controls",
            "values": {
                "selected_scan_names": ["Pullback Quality scan", "Pocket Pivot"],
                "selected_annotation_filters": ["Trend Base"],
                "selected_duplicate_subfilters": [],
                "duplicate_threshold": 1,
                "duplicate_rule": {"mode": "min_count", "min_count": 1},
            },
        },
    )

    presets = load_watchlist_preset_configs(str(config_path))
    custom = [preset for preset in presets if preset.preset_name == "Custom Pullback"]

    assert len(custom) == 1
    assert custom[0].source == "Custom"
    assert custom[0].config.selected_scan_names == ("Pullback Quality scan", "Pocket Pivot")
    assert custom[0].config.selected_annotation_filters == ("Trend Base",)
