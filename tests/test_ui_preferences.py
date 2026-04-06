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


def test_user_preference_store_persists_named_collections(tmp_path: Path) -> None:
    store = UserPreferenceStore(tmp_path / "user_preferences.yaml")

    store.save_collection_item(
        "watchlist_presets",
        "config-a",
        "Momentum Core",
        {
            "schema_version": 1,
            "kind": "watchlist_controls",
            "values": {
                "selected_scan_names": ["Momentum 97", "97 Club"],
                "selected_annotation_filters": ["RS 21 >= 63"],
                "selected_duplicate_subfilters": ["Top3 HybridRS"],
                "duplicate_threshold": 3,
            },
        },
    )
    store.save_collection_item(
        "watchlist_presets",
        "config-a",
        "Tight Bases",
        {
            "schema_version": 1,
            "kind": "watchlist_controls",
            "values": {
                "selected_scan_names": ["VCS", "Three Weeks Tight"],
                "selected_annotation_filters": [],
                "selected_duplicate_subfilters": [],
                "duplicate_threshold": 2,
            },
        },
    )

    loaded = store.load_collection("watchlist_presets", "config-a")

    assert list(loaded) == ["Momentum Core", "Tight Bases"]
    assert loaded["Momentum Core"]["values"]["duplicate_threshold"] == 3
    assert loaded["Tight Bases"]["values"]["selected_scan_names"] == ["VCS", "Three Weeks Tight"]


def test_user_preference_store_can_delete_named_collection_item(tmp_path: Path) -> None:
    store = UserPreferenceStore(tmp_path / "user_preferences.yaml")

    store.save_collection_item("watchlist_presets", "config-a", "Momentum Core", {"values": {"duplicate_threshold": 3}})
    store.save_collection_item("watchlist_presets", "config-a", "Tight Bases", {"values": {"duplicate_threshold": 2}})

    store.delete_collection_item("watchlist_presets", "config-a", "Momentum Core")

    assert store.load_collection("watchlist_presets", "config-a") == {
        "Tight Bases": {"values": {"duplicate_threshold": 2}}
    }
