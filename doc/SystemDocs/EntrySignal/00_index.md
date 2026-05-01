# Entry Signal Documentation Index

`doc/SystemDocs/EntrySignal/` documents the active Entry Signal workflow implemented by `src/signals/rules.py`, `src/signals/runner.py`, `src/signals/evaluators/`, and the tracking DB signal tables.

## Purpose

- Keep one canonical document per active Entry Signal definition.
- Record pool source presets, detection window, invalidation rules, snapshot fields, scoring axes, and display thresholds.
- Keep Entry Signal docs aligned with the current Streamlit page and tracking DB persistence.

## Common Workflow

- Pool source of truth: preset duplicate output from the current artifact set, including same-day saved-run restores.
- Pool persistence: `signal_pool_entry`.
- Daily evaluation persistence: `signal_evaluation`.
- Pool lifecycle: `active`, `invalidated`, `expired`, `orphaned`.
- Daily score axes: `setup_maturity_score`, `timing_score`, `risk_reward_score`.
- Integrated score: `entry_strength`.
- Page buckets: `Signal Detected`, `Approaching`, `Tracking`.
- Context guard: when enabled, weak `market_score` or near-term earnings can cap `entry_strength` below `Signal Detected` while preserving the row and writing warning keys into `Timing Detail`.
- Market score guard: the shared threshold is `30.0`, with signal-specific lower-bound overrides in `entry_signals.context_guard.signal_overrides`.

## Current Status Matrix

- [status_matrix.md](status_matrix.md)

## Active Entry Signals

| File | Signal key | Display name | Implementation owner |
| --- | --- | --- | --- |
| [signal_01_orderly_pullback_entry.md](signal_01_orderly_pullback_entry.md) | `orderly_pullback_entry` | `Orderly Pullback Entry` | `src/signals/evaluators/orderly_pullback.py` |
| [signal_02_pullback_resumption_entry.md](signal_02_pullback_resumption_entry.md) | `pullback_resumption_entry` | `Pullback Resumption Entry` | `src/signals/evaluators/pullback_resumption.py` |
| [signal_03_momentum_acceleration_entry.md](signal_03_momentum_acceleration_entry.md) | `momentum_acceleration_entry` | `Momentum Acceleration Entry` | `src/signals/evaluators/momentum_acceleration.py` |
| [signal_04_accumulation_breakout_entry.md](signal_04_accumulation_breakout_entry.md) | `accumulation_breakout_entry` | `Accumulation Breakout Entry` | `src/signals/evaluators/accumulation_breakout.py` |
| [signal_05_early_cycle_recovery_entry.md](signal_05_early_cycle_recovery_entry.md) | `early_cycle_recovery_entry` | `Early Cycle Recovery Entry` | `src/signals/evaluators/early_cycle_recovery.py` |
| [signal_06_power_gap_pullback_entry.md](signal_06_power_gap_pullback_entry.md) | `power_gap_pullback_entry` | `Power Gap Pullback Entry` | `src/signals/evaluators/power_gap_pullback.py` |
