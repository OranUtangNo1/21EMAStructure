# Watchlist Preset Documentation Index

`doc/SystemDocs/WatchlistPresets/` documents the built-in watchlist presets loaded from `config/default/scan.yaml`.

## Purpose

- Keep one fact-based document per built-in preset.
- Show the exact preset payload currently shipped in config.
- Show which scans each preset selects.
- Show the current preset-level duplicate rule and post-scan filter settings.
- Provide an editable documentation set for users who want to understand the preset catalog.

## Source Of Truth

- Runtime source of truth for built-in presets: `config/default/scan.yaml`
- Documentation source for human review: the preset documents in this folder
- UI loader: `app/main.py::_build_builtin_watchlist_presets`
- Preset shape: `src/scan/rules.py::WatchlistPresetConfig`
- Scan formulas and per-scan direct thresholds: `doc/SystemDocs/Scan/`

Editing these documents does not change app behavior by itself.
To change the built-in preset definitions used by the app, edit `config/default/scan.yaml`.

## Current Built-In Preset Schema

Each built-in preset currently contains:

- `preset_name`
- `selected_scan_names`
- `selected_annotation_filters`
- `selected_duplicate_subfilters`
- `duplicate_threshold`
- optional `duplicate_rule`
- `preset_status`

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

All 9 built-in presets currently share:

- `selected_duplicate_subfilters: []`
- `preset_status: enabled`

Most presets use `duplicate_threshold: 1`, `duplicate_rule.mode: required_plus_optional_min`, and `duplicate_rule.optional_min_hits: 1`.
`Orderly Pullback` uses `duplicate_rule.mode: grouped_threshold` so the 21EMA trigger group and strength-confirmation group can have independent required-hit thresholds.
`Resilient Leader` uses `duplicate_threshold: 2` and `duplicate_rule.mode: min_count`.
Preset-level `selected_annotation_filters` vary by preset and are documented in each preset file.

## Current Preset Families

The active built-in catalog contains these 9 presets:

- legacy consolidated presets:
  - `Leader Breakout`
  - `Orderly Pullback`
  - `Reclaim Trigger`
  - `Momentum Surge`
  - `Early Cycle Recovery`
- environment-based presets:
  - `Base Breakout`
  - `Trend Pullback`
  - `Resilient Leader`
  - `Early Recovery`

## Current Preset Scan Map

| Preset | Selected scans |
|---|---|
| `Leader Breakout` | `97 Club`, `VCS 52 High`, `RS Acceleration`, `Three Weeks Tight` |
| `Orderly Pullback` | `Pullback Quality scan`, `21EMA Pattern H`, `21EMA Pattern L`, `RS Acceleration`, `Volume Accumulation` |
| `Reclaim Trigger` | `Reclaim scan`, `Pocket Pivot` |
| `Momentum Surge` | `4% bullish`, `Momentum 97`, `PP Count`, `Sustained Leadership` |
| `Early Cycle Recovery` | `Trend Reversal Setup`, `Pocket Pivot`, `VCS 52 Low`, `Volume Accumulation` |
| `Base Breakout` | `VCS 52 High`, `Pocket Pivot`, `97 Club`, `Three Weeks Tight` |
| `Trend Pullback` | `Reclaim scan`, `Pullback Quality scan`, `RS Acceleration`, `Volume Accumulation` |
| `Resilient Leader` | `Sustained Leadership`, `Near 52W High` |
| `Early Recovery` | `Trend Reversal Setup`, `Structure Pivot`, `VCS 52 Low`, `Volume Accumulation` |

Scans currently unused by any built-in preset:

- `Vol Up`
- `VCS`
- `Weekly 20% plus gainers`

## Preset Files

| File | Preset name | Category | Selected scans |
|---|---|---|---|
| [leader_breakout.md](leader_breakout.md) | `Leader Breakout` | Legacy consolidated | `97 Club`, `VCS 52 High`, `RS Acceleration`, `Three Weeks Tight` |
| [orderly_pullback.md](orderly_pullback.md) | `Orderly Pullback` | Legacy consolidated | `Pullback Quality scan`, `21EMA Pattern H`, `21EMA Pattern L`, `RS Acceleration`, `Volume Accumulation` |
| [reclaim_trigger.md](reclaim_trigger.md) | `Reclaim Trigger` | Legacy consolidated | `Reclaim scan`, `Pocket Pivot` |
| [momentum_surge.md](momentum_surge.md) | `Momentum Surge` | Legacy consolidated | `4% bullish`, `Momentum 97`, `PP Count`, `Sustained Leadership` |
| [early_cycle_recovery.md](early_cycle_recovery.md) | `Early Cycle Recovery` | Legacy consolidated | `Trend Reversal Setup`, `Pocket Pivot`, `VCS 52 Low`, `Volume Accumulation` |
| [base_breakout.md](base_breakout.md) | `Base Breakout` | Environment-based | `VCS 52 High`, `Pocket Pivot`, `97 Club`, `Three Weeks Tight` |
| [trend_pullback.md](trend_pullback.md) | `Trend Pullback` | Environment-based | `Reclaim scan`, `Pullback Quality scan`, `RS Acceleration`, `Volume Accumulation` |
| [resilient_leader.md](resilient_leader.md) | `Resilient Leader` | Environment-based | `Sustained Leadership`, `Near 52W High` |
| [early_recovery.md](early_recovery.md) | `Early Recovery` | Environment-based | `Trend Reversal Setup`, `Structure Pivot`, `VCS 52 Low`, `Volume Accumulation` |

## Disabled Legacy Preset References

Files under `disable/` are retained as legacy reference material only. They are not loaded from the current `config/default/scan.yaml` built-in preset catalog.
