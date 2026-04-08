from app.main import _watchlist_controls_equal


def test_watchlist_controls_equal_treats_duplicate_threshold_as_material() -> None:
    left = {
        "selected_scan_names": ["VCS", "97 Club"],
        "selected_annotation_filters": ["RS 21 >= 63"],
        "selected_duplicate_subfilters": ["Top3 HybridRS"],
        "duplicate_threshold": 2,
    }
    right = {
        "selected_scan_names": ["VCS", "97 Club"],
        "selected_annotation_filters": ["RS 21 >= 63"],
        "selected_duplicate_subfilters": ["Top3 HybridRS"],
        "duplicate_threshold": 1,
    }

    assert _watchlist_controls_equal(left, right) is False


def test_watchlist_controls_equal_accepts_equivalent_values() -> None:
    left = {
        "selected_scan_names": ["VCS"],
        "selected_annotation_filters": [],
        "selected_duplicate_subfilters": [],
        "duplicate_threshold": 1,
    }
    right = {
        "selected_scan_names": ["VCS"],
        "selected_annotation_filters": [],
        "selected_duplicate_subfilters": [],
        "duplicate_threshold": 1,
    }

    assert _watchlist_controls_equal(left, right) is True
