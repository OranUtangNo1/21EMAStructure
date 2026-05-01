# Watchlist Preset Documentation Index

`doc/SystemDocs/WatchlistPresets/` documents the built-in watchlist presets loaded from `config/default/scan.yaml`.
Use the per-preset files for exact payload details. Use the status matrix for the current runtime state.

## Purpose

- Keep one fact-based document per built-in preset.
- Separate exact preset payloads from current enabled or disabled state.
- Keep preset docs stable even when scan status changes disable a preset at runtime.

## Source Of Truth

- runtime source of truth: `config/default/scan.yaml`
- preset shape: `src/scan/rules.py::WatchlistPresetConfig`
- UI loader: `app/main.py::_load_builtin_watchlist_preset_definitions`
- scan formulas: `doc/SystemDocs/Scan/`

Editing these documents does not change app behavior by itself.
To change built-in preset behavior, edit `config/default/scan.yaml`.

## Current Status Matrix

- [status_matrix.md](status_matrix.md)
- `Status` shows effective runtime preset status.
- `UI` shows whether the preset is visible in the built-in preset picker.
- `Export` shows whether the preset is included in built-in exports.

## Preset Files

| File | Preset name |
| --- | --- |
| [leader_breakout.md](leader_breakout.md) | `Leader Breakout` |
| [orderly_pullback.md](orderly_pullback.md) | `Orderly Pullback` |
| [reclaim_trigger.md](reclaim_trigger.md) | `Reclaim Trigger` |
| [momentum_surge.md](momentum_surge.md) | `Momentum Surge` |
| [early_cycle_recovery.md](early_cycle_recovery.md) | `Early Cycle Recovery` |
| [base_breakout.md](base_breakout.md) | `Base Breakout` |
| [accumulation_breakout.md](accumulation_breakout.md) | `Accumulation Breakout` |
| [vcp_3t_breakout.md](vcp_3t_breakout.md) | `VCP 3T Breakout` |
| [trend_pullback.md](trend_pullback.md) | `Trend Pullback` |
| [resilient_leader.md](resilient_leader.md) | `Resilient Leader` |
| [early_recovery.md](early_recovery.md) | `Early Recovery` |
| [50sma_defense.md](50sma_defense.md) | `50SMA Defense` |
| [power_gap_pullback.md](power_gap_pullback.md) | `Power Gap Pullback` |
| [rs_breakout_setup.md](rs_breakout_setup.md) | `RS Breakout Setup` |
| [screening_thesis.md](screening_thesis.md) | `Screening Thesis` |
| [pullback_trigger.md](pullback_trigger.md) | `Pullback Trigger` |
| [momentum_ignition.md](momentum_ignition.md) | `Momentum Ignition` |
