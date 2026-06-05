# Watchlist Preset Documentation Index

`doc/SystemDocs/WatchlistPresets/` documents the active built-in watchlist presets loaded from `config/default/scan.yaml`.
Use the per-preset files for exact payload details. Use the status matrix for the current runtime state.

## Purpose

- Keep one fact-based document per active built-in preset.
- Keep preset docs aligned with current default UI and export behavior.
- Exclude disabled presets and non-current recovery/reversal preset documents from SystemDocs.

## Source Of Truth

- runtime source of truth: `config/default/scan.yaml`
- preset shape: `src/scan/rules.py::WatchlistPresetConfig`
- UI loader: `app/main.py::_load_builtin_watchlist_preset_definitions`
- scan formulas: `doc/SystemDocs/Scan/`

Editing these documents does not change app behavior by itself.
To change built-in preset behavior, edit `config/default/scan.yaml`.

## Current Status Matrix

- [status_matrix.md](status_matrix.md)
- `Status` shows effective active runtime preset status.
- `UI` shows whether the preset is visible in the built-in preset picker.
- `Export` shows whether the preset is included in built-in exports.

## Preset Files

| File | Preset name |
| --- | --- |
| [reclaim_trigger.md](reclaim_trigger.md) | `Reclaim Trigger` |
| [fresh_stage2_breakout.md](fresh_stage2_breakout.md) | `Fresh Stage 2 Breakout` |
| [accumulation_breakout.md](accumulation_breakout.md) | `Accumulation Breakout` |
| [vcp_3t_breakout.md](vcp_3t_breakout.md) | `VCP 3T Breakout` |
| [50sma_defense.md](50sma_defense.md) | `50SMA Defense` |
| [power_gap_pullback.md](power_gap_pullback.md) | `Power Gap Pullback` |
| [rs_breakout_setup.md](rs_breakout_setup.md) | `RS Breakout Setup` |
| [pullback_trigger.md](pullback_trigger.md) | `Pullback Trigger` |
| [momentum_ignition.md](momentum_ignition.md) | `Momentum Ignition` |
