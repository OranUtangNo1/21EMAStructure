# Momentum Acceleration Entry

## Identity

- Signal key: `momentum_acceleration_entry`
- Display name: `Momentum Acceleration Entry`
- Version: `1.0`
- Runtime owner: `src/signals/evaluators/momentum_acceleration.py`
- Config owner: `config/default/entry_signals.yaml`
- Status: `enabled`
- Startup selected: `yes`

## Pool Definition

- Preset source: `Momentum Ignition`
- Detection window: `3` business days
- Pool persistence: `signal_pool_entry`
- Daily evaluation persistence: `signal_evaluation`

Pool snapshot fields:
- `close`
- `high`
- `low`
- `atr`
- `rs21`
- `vcs`
- `weekly_return_rank`
- `rel_volume`
- `daily_change_pct`
- `dcr_percent`
- `dist_from_52w_high`
- `pp_count_window`

Pool tracking fields:
- `low_since_detection`
- `high_since_detection`

Invalidation rules:
- `daily_change_pct < -4.0`
- `close < sma50`
- `weekly_return_rank < 80.0`

## Scoring Axes

Setup maturity weight in entry strength: `0.20`

Setup maturity indicators:
- `vcs_quality`: `vcs`, weight `0.40`
- `pp_density`: `pp_count_window`, weight `0.30`
- `momentum_rank`: `weekly_return_rank`, weight `0.30`

Timing weight in entry strength: `0.45`

Timing indicators:
- `acceleration_event`: custom evaluator, weight `0.35`
- `volume_confirmation`: `rel_volume`, weight `0.30`
- `close_quality`: `dcr_percent`, weight `0.20`
- `follow_through`: custom evaluator, weight `0.15`

Custom timing evaluator summary:

| Indicator | Score | Runtime condition |
| --- | ---: | --- |
| `acceleration_event` | `100` | `daily_change_pct >= 4.0` and `rel_volume >= 1.0` |
| `acceleration_event` | `80` | `daily_change_pct >= 4.0` or `hit_scans` contains `4% bullish` |
| `acceleration_event` | `75` | `pp_count_window >= 3.0` or `hit_scans` contains `PP Count` |
| `acceleration_event` | `35` | `hit_scans` contains `Momentum 97` |
| `acceleration_event` | `15` | none of the above |
| `follow_through` | `50` | first pool day |
| `follow_through` | `100` | after first pool day, current close is above detection close and `daily_change_pct > 1.0` |
| `follow_through` | `80` | after first pool day, `daily_change_pct > 0.0` |
| `follow_through` | `70` | high since detection is above detection high |
| `follow_through` | `30` | second pool day without stronger follow-through |
| `follow_through` | `15` | later pool day without stronger follow-through |

Risk/reward weight in entry strength: `0.35`

Risk/reward behavior:
- Stop reference: acceleration-day snapshot `low`
- ATR buffer: `0.25`
- Minimum stop distance: `0.25 ATR`
- Target priority: `rolling_20d_close_high -> high_52w -> entry + 2R -> entry * 1.08`
- Structural targets must be above entry and normally provide at least `1.5R`; otherwise the evaluator falls back to `entry + 2R`.
- R/R score is capped at `35` when risk exceeds `2.0 ATR`.

## Climax Guard

The evaluator flags a climax warning and caps the final entry strength below `Signal Detected` when any condition is true:
- `rel_volume >= 5.0`
- `dist_from_52w_high >= -1.0` and `daily_change_pct >= 6.0`
- First pool day and `dcr_percent < 50.0`

This allows the candidate to remain visible as `Approaching` while avoiding a high-confidence entry label on exhaustion-style moves.

## Display Thresholds

- `Signal Detected`: `entry_strength >= 55`
- `Approaching`: `entry_strength >= 40`
- `Tracking`: `entry_strength < 40`

## Runtime Notes

- Pool candidates are created only from duplicate output of the `Momentum Ignition` preset.
- The custom timing evaluator is intentionally code-defined in `src/signals/evaluators/momentum_acceleration.py`; this table mirrors the current runtime breakpoints.
