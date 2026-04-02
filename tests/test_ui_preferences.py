from __future__ import annotations

from pathlib import Path

from src.ui_preferences import UserPreferenceStore


def test_user_preference_store_persists_grouped_values(tmp_path: Path) -> None:
    store = UserPreferenceStore(tmp_path / "user_preferences.yaml")

    store.save_group(
        "watchlist_controls",
        "config-a",
        {
            "selected_scan_names": ["Momentum 97", "97 Club"],
            "selected_annotation_filters": ["RS 21 >= 63"],
            "selected_duplicate_subfilters": ["Top3 HybridRS"],
            "duplicate_threshold": 3,
            "future_fields": {"example_toggle": True},
        },
    )

    loaded = store.load_group("watchlist_controls", "config-a")

    assert loaded == {
        "selected_scan_names": ["Momentum 97", "97 Club"],
        "selected_annotation_filters": ["RS 21 >= 63"],
        "selected_duplicate_subfilters": ["Top3 HybridRS"],
        "duplicate_threshold": 3,
        "future_fields": {"example_toggle": True},
    }


def test_user_preference_store_isolated_by_group_and_namespace(tmp_path: Path) -> None:
    store = UserPreferenceStore(tmp_path / "user_preferences.yaml")

    store.save_group("watchlist_controls", "config-a", {"duplicate_threshold": 2})
    store.save_group("watchlist_controls", "config-b", {"duplicate_threshold": 4})
    store.save_group("market_dashboard", "config-a", {"calculation_mode": "active_symbols"})

    assert store.load_group("watchlist_controls", "config-a") == {"duplicate_threshold": 2}
    assert store.load_group("watchlist_controls", "config-b") == {"duplicate_threshold": 4}
    assert store.load_group("market_dashboard", "config-a") == {"calculation_mode": "active_symbols"}
