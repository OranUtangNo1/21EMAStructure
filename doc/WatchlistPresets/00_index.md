# Watchlist Preset Documentation Index

`doc/WatchlistPresets/` documents the built-in watchlist presets loaded from `config/default/scan.yaml`.

## Purpose

- Keep one fact-based document per built-in preset.
- Show the exact preset payload currently shipped in config.
- Show which scans each preset selects.
- Show the current preset-level duplicate threshold and post-scan filter settings.
- Provide an editable documentation set for users who want to understand the preset catalog.

## Source Of Truth

- Runtime source of truth for built-in presets: `config/default/scan.yaml`
- UI loader: `app/main.py::_build_builtin_watchlist_presets`
- Preset shape: `src/scan/rules.py::WatchlistPresetConfig`
- Scan formulas and per-scan direct thresholds: `doc/Scan/`

Editing these documents does not change app behavior by itself.
To change the built-in preset definitions used by the app, edit `config/default/scan.yaml`.

## Current Built-In Preset Schema

Each built-in preset currently contains:

- `preset_name`
- `selected_scan_names`
- `selected_annotation_filters`
- `selected_duplicate_subfilters`
- `duplicate_threshold`

## Shared Pre-Scan Context

The built-in presets do not define preset-specific pre-scan filters.
All built-in presets run on the same shared eligible snapshot and scan context:

- local universe filter:
  - `market_cap >= 1B`
  - `avg_volume_50d >= 1M`
  - `close >= 0.0`
  - `adr_percent` between `3.5` and `10.0`
  - `sector != Healthcare`
- scan-context enrichment:
  - `weekly_return_rank`
  - `quarterly_return_rank`
  - `eps_growth_rank` when `eps_growth` exists

## Current Built-In Preset Defaults

All 10 built-in presets currently share these non-scan values:

- `selected_annotation_filters: []`
- `selected_duplicate_subfilters: []`
- `duplicate_threshold: 2`

## Preset Files

| File | Preset name | Selected scans |
|---|---|---|
| [preset_01_leader_breakout.md](preset_01_leader_breakout.md) | `Leader Breakout` | `97 Club`, `VCS 52 High`, `Three Weeks Tight` |
| [preset_02_orderly_pullback.md](preset_02_orderly_pullback.md) | `Orderly Pullback` | `Pullback Quality scan`, `Volume Accumulation`, `RS Acceleration` |
| [preset_03_reclaim_trigger.md](preset_03_reclaim_trigger.md) | `Reclaim Trigger` | `Reclaim scan`, `Pocket Pivot`, `Fundamental Demand` |
| [preset_04_momentum_surge.md](preset_04_momentum_surge.md) | `Momentum Surge` | `4% bullish`, `Momentum 97`, `PP Count`, `Sustained Leadership` |
| [preset_05_early_cycle_recovery.md](preset_05_early_cycle_recovery.md) | `Early Cycle Recovery` | `VCS 52 Low`, `Volume Accumulation`, `Trend Reversal Setup` |
| [preset_06_pattern_1_initial_leader_breakout.md](preset_06_pattern_1_initial_leader_breakout.md) | `Pattern 1 - Initial Leader Breakout` | `97 Club`, `VCS 52 High`, `RS Acceleration` |
| [preset_07_pattern_2_strong_pullback_buy.md](preset_07_pattern_2_strong_pullback_buy.md) | `Pattern 2 - Strong Pullback Buy` | `21EMA scan`, `PP Count`, `Volume Accumulation` |
| [preset_08_pattern_3_tight_base_watch.md](preset_08_pattern_3_tight_base_watch.md) | `Pattern 3 - Tight Base Watch` | `VCS`, `Three Weeks Tight`, `Near 52W High` |
| [preset_09_pattern_4_momentum_confirmation.md](preset_09_pattern_4_momentum_confirmation.md) | `Pattern 4 - Momentum Confirmation` | `4% bullish`, `Momentum 97`, `PP Count` |
| [preset_10_pattern_5_early_reversal_signal.md](preset_10_pattern_5_early_reversal_signal.md) | `Pattern 5 - Early Reversal Signal` | `VCS 52 Low`, `Volume Accumulation`, `Pocket Pivot` |
