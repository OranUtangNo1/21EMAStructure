from __future__ import annotations

from src.signals.evaluators.orderly_pullback import calculate_entry_strength
from src.signals.rules import EntrySignalConfig
from src.signals.scoring import composite_score, piecewise_linear_score


def test_piecewise_linear_score_clamps_and_interpolates() -> None:
    breakpoints = ((0.5, 5.0), (1.0, 25.0), (1.5, 50.0), (2.0, 70.0), (3.0, 95.0))

    assert piecewise_linear_score(0.1, breakpoints) == 5.0
    assert piecewise_linear_score(3.5, breakpoints) == 95.0
    assert piecewise_linear_score(1.0, breakpoints) == 25.0
    assert round(piecewise_linear_score(1.25, breakpoints), 2) == 37.5
    assert round(piecewise_linear_score(2.5, breakpoints), 2) == 82.5


def test_composite_score_uses_weights() -> None:
    score = composite_score(
        {
            "setup": (80.0, 0.25),
            "timing": (60.0, 0.40),
            "rr": (70.0, 0.35),
        }
    )

    assert round(score, 2) == 68.5


def test_entry_strength_floor_gate_caps_weak_axis() -> None:
    config = EntrySignalConfig.from_dict(
        {
            "definitions": {
                "orderly_pullback_entry": {
                    "display_name": "Orderly Pullback Entry",
                    "signal_version": "1.0",
                    "description": "test",
                    "pool": {
                        "preset_sources": ["Orderly Pullback"],
                        "detection_window_days": 10,
                        "invalidation": [],
                        "snapshot_fields": ["close", "high"],
                        "pool_tracking": ["low_since_detection", "high_since_detection"],
                    },
                    "setup_maturity": {"indicators": {"a": {"weight": 1.0, "field": "close", "breakpoints": [[0, 0], [1, 100]]}}},
                    "timing": {"indicators": {"b": {"weight": 1.0, "field": "close", "breakpoints": [[0, 0], [1, 100]]}}},
                    "risk_reward": {
                        "stop": {"reference": "low_since_detection", "atr_buffer": 0.25, "min_distance_atr": 0.75, "structural_penalty": 0.8},
                        "reward": {"primary": "snapshot_rolling_20d_close_high"},
                        "scoring": {"breakpoints": [[0.5, 5], [1.0, 25]]},
                    },
                    "entry_strength": {
                        "weights": {"setup_maturity": 0.25, "timing": 0.40, "risk_reward": 0.35},
                        "floor_gate": {"min_axis_threshold": 20, "capped_strength": 30},
                    },
                    "display": {"thresholds": {"signal_detected": 50, "approaching": 35, "tracking": 0}},
                }
            }
        }
    )
    definition = config.definition_for("orderly_pullback_entry")

    assert calculate_entry_strength(80.0, 80.0, 80.0, definition) == 80.0
    assert calculate_entry_strength(90.0, 10.0, 80.0, definition) == 30.0
    assert calculate_entry_strength(0.0, 0.0, 0.0, definition) == 0.0
