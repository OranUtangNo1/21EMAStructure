# Entry Signal Documentation Index

`doc/SystemDocs/EntrySignal/` documents active entry-signal definitions in `src/signals/rules.py::ENTRY_SIGNAL_REGISTRY`.

## Purpose

- Keep one canonical document per entry signal.
- Record exact evaluator logic and required inputs.
- Keep signal docs aligned with Entry Signal page output.

## Common Evaluation Context

- Input unit: one latest row per ticker from selected signal universe.
- Evaluated by `src/signals/runner.py::EntrySignalRunner.evaluate`.
- Output contract: one boolean hit decision per signal per ticker.

## Current Status Matrix

- [status_matrix.md](status_matrix.md)
- `Status` shows runtime enabled or disabled state.
- `Startup` shows whether the signal is selected by default on page load.

## Active Entry Signals

| File | Canonical signal name | Implementation owner |
|---|---|---|
| [signal_01_pocket_pivot_entry.md](signal_01_pocket_pivot_entry.md) | `Pocket Pivot Entry` | `src/signals/rules.py::_pocket_pivot_entry` |
| [signal_02_structure_pivot_breakout_entry.md](signal_02_structure_pivot_breakout_entry.md) | `Structure Pivot Breakout Entry` | `src/signals/rules.py::_structure_pivot_breakout_entry` |
| [signal_03_pullback_low_risk_zone.md](signal_03_pullback_low_risk_zone.md) | `Pullback Low-Risk Zone` | `src/signals/rules.py::_pullback_low_risk_zone` |
| [signal_04_volume_reclaim_entry.md](signal_04_volume_reclaim_entry.md) | `Volume Reclaim Entry` | `src/signals/rules.py::_volume_reclaim_entry` |
| [signal_05_resistance_breakout_entry.md](signal_05_resistance_breakout_entry.md) | `Resistance Breakout Entry` | `src/signals/rules.py::_resistance_breakout_entry` |
