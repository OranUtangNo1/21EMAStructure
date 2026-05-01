# Combined WatchlistPresets Markdown

This file combines every `*.md` file under `doc/SystemDocs/WatchlistPresets/`.
The original file contents are copied as-is between file-boundary markers.

Source file count: 18

---
FILE BOUNDARY NOTICE
You are now reading content copied from: 00_index.md
When this block ends, the document will switch to: 50sma_defense.md
---
<!-- BEGIN SOURCE FILE: 00_index.md -->
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
| [trend_pullback.md](trend_pullback.md) | `Trend Pullback` |
| [resilient_leader.md](resilient_leader.md) | `Resilient Leader` |
| [early_recovery.md](early_recovery.md) | `Early Recovery` |
| [50sma_defense.md](50sma_defense.md) | `50SMA Defense` |
| [power_gap_pullback.md](power_gap_pullback.md) | `Power Gap Pullback` |
| [rs_breakout_setup.md](rs_breakout_setup.md) | `RS Breakout Setup` |
| [screening_thesis.md](screening_thesis.md) | `Screening Thesis` |
| [pullback_trigger.md](pullback_trigger.md) | `Pullback Trigger` |
| [momentum_ignition.md](momentum_ignition.md) | `Momentum Ignition` |
<!-- END SOURCE FILE: 00_index.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: 50sma_defense.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: 50sma_defense.md
When this block ends, the document will switch to: accumulation_breakout.md
---
<!-- BEGIN SOURCE FILE: 50sma_defense.md -->
# Watchlist Preset Spec: 50SMA Defense

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `50SMA Defense` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: 50SMA Defense
selected_scan_names: [50SMA Reclaim, Pullback Quality scan, Volume Accumulation, Pocket Pivot]
selected_annotation_filters: [Trend Base]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [50SMA Reclaim]
  optional_groups:
  - group_name: Pullback Quality
    scans: [Pullback Quality scan]
    min_hits: 1
  - group_name: Demand Confirmation
    scans: [Volume Accumulation, Pocket Pivot]
    min_hits: 1
preset_status: enabled
```

## Selected Scans

| Scan name | Scan reference |
|---|---|
| `50SMA Reclaim` | [../Scan/scan_27_50sma_reclaim.md](../Scan/scan_27_50sma_reclaim.md) |
| `Pullback Quality scan` | [../Scan/scan_16_pullback_quality.md](../Scan/scan_16_pullback_quality.md) |
| `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) |
| `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`
- selected duplicate subfilters: none
- duplicate rule: `grouped_threshold`
  - required: `50SMA Reclaim`
  - optional group `Pullback Quality`: min 1 of 1
  - optional group `Demand Confirmation`: min 1 of 2
<!-- END SOURCE FILE: 50sma_defense.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: accumulation_breakout.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: accumulation_breakout.md
When this block ends, the document will switch to: base_breakout.md
---
<!-- BEGIN SOURCE FILE: accumulation_breakout.md -->
# Watchlist Preset Spec: Accumulation Breakout

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Accumulation Breakout` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Accumulation Breakout
selected_scan_names: [VCS 52 High, PP Count, Volume Accumulation, Pocket Pivot, 4% bullish]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [VCS 52 High]
  optional_groups:
  - group_name: Accumulation Evidence
    scans: [PP Count, Volume Accumulation]
    min_hits: 1
  - group_name: Breakout Trigger
    scans: [Pocket Pivot, 4% bullish]
    min_hits: 1
preset_status: enabled
```

## Selected Scans

| Scan name | Scan reference |
|---|---|
| `VCS 52 High` | [../Scan/scan_13_vcs_52_high.md](../Scan/scan_13_vcs_52_high.md) |
| `PP Count` | [../Scan/scan_08_pp_count.md](../Scan/scan_08_pp_count.md) |
| `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) |
| `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) |
| `4% bullish` | [../Scan/scan_02_4pct_bullish.md](../Scan/scan_02_4pct_bullish.md) |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- duplicate rule: `grouped_threshold`
  - required: `VCS 52 High`
  - optional group `Accumulation Evidence`: min 1 of 2
  - optional group `Breakout Trigger`: min 1 of 2
<!-- END SOURCE FILE: accumulation_breakout.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: base_breakout.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: base_breakout.md
When this block ends, the document will switch to: early_cycle_recovery.md
---
<!-- BEGIN SOURCE FILE: base_breakout.md -->
# Watchlist Preset Spec: Base Breakout

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Base Breakout` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |
| Market environment | `Confirmed Uptrend` |

## Current Config Payload

```yaml
preset_name: Base Breakout
selected_scan_names: [VCS 52 High, Pocket Pivot, 97 Club, Three Weeks Tight]
selected_annotation_filters: [Trend Base, Resistance Tests >= 2]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: required_plus_optional_min
  required_scans: [VCS 52 High, Pocket Pivot]
  optional_scans: [97 Club, Three Weeks Tight]
  optional_min_hits: 1
preset_status: enabled
```

## Pre-Scan Context

- preset-specific pre-scan filters: none
- shared pre-scan universe filter: active global `UniverseBuilder.filter()` rules only
- shared scan-context enrichment: `weekly_return_rank`, `quarterly_return_rank`, `eps_growth_rank`

## Selected Scans

| Scan name | Card display | Scan reference | Direct threshold summary |
|---|---|---|---|
| `97 Club` | `97 Club` | [../Scan/scan_05_97club.md](../Scan/scan_05_97club.md) | `club_97_hybrid_threshold=90.0`, `club_97_rs21_threshold=97.0` |
| `VCS 52 High` | `VCS 52 High` | [../Scan/scan_13_vcs_52_high.md](../Scan/scan_13_vcs_52_high.md) | `vcs_52_high_vcs_min=55.0`, `vcs_52_high_rs21_min=25.0`, `vcs_52_high_dist_max=-20.0` |
| `Three Weeks Tight` | `3WT` | [../Scan/scan_11_three_weeks_tight.md](../Scan/scan_11_three_weeks_tight.md) | `three_weeks_tight_vcs_min=50.0`; upstream `three_weeks_tight_pct_threshold=1.5` |
| `Pocket Pivot` | `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) | no scan config keys; requires `close > sma50` and `pocket_pivot=true` |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`, `Resistance Tests >= 2`
- selected duplicate subfilters: none
- UI optional threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `required_plus_optional_min`; requires every scan in `VCS 52 High, Pocket Pivot` plus at least `1` hit from optional scans `97 Club, Three Weeks Tight`

## Scan Role Mapping

| Role | Scan | Rationale |
|---|---|---|
| Core | `VCS 52 High` | 52-week high proximity with volatility contraction proves a tight base exists near highs |
| Trigger | `Pocket Pivot` / `Three Weeks Tight` | PP detects demand via volume; 3WT confirms contraction completion via price |
| Confirmation | `97 Club` | Hybrid score ≥ 90 + RS21 ≥ 97 enforces top-tier leadership quality |

## Logic Structure

```
duplicate_rule.mode: required_plus_optional_min
required_scans: [VCS 52 High, Pocket Pivot]
optional_scans: [97 Club, Three Weeks Tight]
optional_min_hits: 1
→ ticker must hit every required scan and 1+ optional scan
```

Representative hit patterns:

- `VCS 52 High` + `Pocket Pivot` + `97 Club` → top leader volume breakout from tight base
- `VCS 52 High` + `Pocket Pivot` + `Three Weeks Tight` → volume breakout from ultra-tight contraction

## Setup Interpretation

- **Target phase**: base completion → breakout initiation
- **Why effective in Confirmed Uptrend**: market tailwind maximizes follow-through on leader breakouts from tight bases; risk/reward is optimal when volatility has contracted near highs

## Design Rationale

VCS 52 High guarantees the "tight structure near highs" condition. 97 Club filters for the highest quality leaders only. Pocket Pivot and Three Weeks Tight detect the breakout event from two independent angles (volume vs price contraction completion). No overlap with pullback, reclaim, or reversal presets.

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
<!-- END SOURCE FILE: base_breakout.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: early_cycle_recovery.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: early_cycle_recovery.md
When this block ends, the document will switch to: early_recovery.md
---
<!-- BEGIN SOURCE FILE: early_cycle_recovery.md -->
# Watchlist Preset Spec: Early Cycle Recovery

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Early Cycle Recovery` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Early Cycle Recovery
selected_scan_names: [Trend Reversal Setup, Pocket Pivot, VCS 52 Low, Volume Accumulation]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: required_plus_optional_min
  required_scans: [Trend Reversal Setup]
  optional_scans: [Pocket Pivot, VCS 52 Low, Volume Accumulation]
  optional_min_hits: 1
preset_status: enabled
```

## Pre-Scan Context

- preset-specific pre-scan filters: none
- shared pre-scan universe filter: active global `UniverseBuilder.filter()` rules only
- shared scan-context enrichment: `weekly_return_rank`, `quarterly_return_rank`, `eps_growth_rank`

## Selected Scans

| Scan name | Card display | Scan reference | Direct threshold summary |
|---|---|---|---|
| `VCS 52 Low` | `VCS 52 Low` | [../Scan/scan_14_vcs_52_low.md](../Scan/scan_14_vcs_52_low.md) | `vcs_52_low_vcs_min=60.0`, `vcs_52_low_rs21_min=80.0`, `vcs_52_low_dist_max=25.0`, `vcs_52_low_dist_from_52w_high_max=-65.0` |
| `Volume Accumulation` | `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) | `vol_accum_ud_ratio_min=1.5`, `vol_accum_rel_vol_min=1.0`, plus hard-coded `daily_change_pct > 0.0` |
| `Trend Reversal Setup` | `Reversal Setup` | [../Scan/scan_20_trend_reversal_setup.md](../Scan/scan_20_trend_reversal_setup.md) | `reversal_dist_52w_low_max=40.0`, `reversal_dist_52w_high_min=-40.0`, `reversal_rs21_min=50.0`, plus hard-coded `pocket_pivot_count >= 1` |
| `Pocket Pivot` | `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) | no scan config keys; requires `close > sma50` and `pocket_pivot=true` |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- UI optional threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `required_plus_optional_min`; requires every scan in `Trend Reversal Setup` plus at least `1` hit from optional scans `Pocket Pivot, VCS 52 Low, Volume Accumulation`

## Consolidation Notes

This preset absorbs the former `Pattern 5 - Early Reversal Signal` by adding `Pocket Pivot`. Both presets shared VCS 52 Low and Volume Accumulation.

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
<!-- END SOURCE FILE: early_cycle_recovery.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: early_recovery.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: early_recovery.md
When this block ends, the document will switch to: leader_breakout.md
---
<!-- BEGIN SOURCE FILE: early_recovery.md -->
# Watchlist Preset Spec: Early Recovery

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Early Recovery` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |
| Market environment | `Correction` |

## Current Config Payload

```yaml
preset_name: Early Recovery
selected_scan_names: [Trend Reversal Setup, Structure Pivot, VCS 52 Low, Volume Accumulation]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: required_plus_optional_min
  required_scans: [Trend Reversal Setup, Structure Pivot]
  optional_scans: [VCS 52 Low, Volume Accumulation]
  optional_min_hits: 1
preset_status: enabled
```

## Pre-Scan Context

- preset-specific pre-scan filters: none
- shared pre-scan universe filter: active global `UniverseBuilder.filter()` rules only
- shared scan-context enrichment: `weekly_return_rank`, `quarterly_return_rank`, `eps_growth_rank`

## Selected Scans

| Scan name | Card display | Scan reference | Direct threshold summary |
|---|---|---|---|
| `Trend Reversal Setup` | `Reversal Setup` | [../Scan/scan_20_trend_reversal_setup.md](../Scan/scan_20_trend_reversal_setup.md) | `reversal_dist_52w_low_max=40.0`, `reversal_dist_52w_high_min=-40.0`, `reversal_rs21_min=50.0`, plus hard-coded `sma50 <= sma200`, `sma50_slope_10d_pct > 0.0`, `pocket_pivot_count >= 1` |
| `Structure Pivot` | `Structure Pivot` | [../Scan/scan_21_structure_pivot.md](../Scan/scan_21_structure_pivot.md) | no config keys; requires `structure_pivot_long_active=true` (bullish LL→HL structure confirmed) |
| `VCS 52 Low` | `VCS 52 Low` | [../Scan/scan_14_vcs_52_low.md](../Scan/scan_14_vcs_52_low.md) | `vcs_52_low_vcs_min=60.0`, `vcs_52_low_rs21_min=80.0`, `vcs_52_low_dist_max=25.0`, `vcs_52_low_dist_from_52w_high_max=-65.0` |
| `Volume Accumulation` | `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) | `vol_accum_ud_ratio_min=1.5`, `vol_accum_rel_vol_min=1.0`, plus hard-coded `daily_change_pct > 0.0` |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- UI optional threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `required_plus_optional_min`; requires every scan in `Trend Reversal Setup, Structure Pivot` plus at least `1` hit from optional scans `VCS 52 Low, Volume Accumulation`

## Scan Role Mapping

| Role | Scan | Rationale |
|---|---|---|
| Core | `Trend Reversal Setup` | SMA50 ≤ SMA200 but SMA50 turning up + close > SMA50 + PP present; structural reversal conditions |
| Core | `Structure Pivot` | Bullish LL→HL structure confirmed; bottom is forming higher lows |
| Confirmation | `VCS 52 Low` | Volatility contraction near 52-week lows with RS21 ≥ 80; quality tightening after damage |
| Confirmation | `Volume Accumulation` | U/D volume ratio shows institutional accumulation beginning |

## Logic Structure

```
duplicate_rule.mode: required_plus_optional_min
required_scans: [Trend Reversal Setup, Structure Pivot]
optional_scans: [VCS 52 Low, Volume Accumulation]
optional_min_hits: 1
→ ticker must hit every required scan and 1+ optional scan
```

Representative hit patterns:

- `Trend Reversal Setup` + `Structure Pivot` + `VCS 52 Low` → bottoming structure with low-zone contraction
- `Trend Reversal Setup` + `Structure Pivot` + `Volume Accumulation` → bottoming structure with institutional accumulation

## Setup Interpretation

- **Target phase**: late correction → early recovery; detecting the earliest structural change in beaten-down names
- **Why effective in Correction**: most stocks continue declining; those where SMA50 is turning up, higher lows are forming, volatility is contracting, and volume shows accumulation are the most likely next-cycle leaders
- **Very early detection**: this preset identifies candidates well before `Trend Base` becomes true, making it complementary to the uptrend and pressure presets that require the `Trend Base` annotation filter

## Design Rationale

Trend Reversal Setup's `sma50 <= sma200` condition is unique to this preset among the built-in presets. Presets that require the `Trend Base` annotation filter exclude dead-cross stocks entirely. Structure Pivot's LL->HL detection operates at the price structure level independent of MA state. VCS 52 Low requires the stock to be within 25% of the 52-week low and more than 65% below the 52-week high, the polar opposite of VCS 52 High used in Base Breakout. Volume Accumulation is shared with Trend Pullback, but the co-occurring scans separate recovery candidates from `Trend Base` candidates.

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
<!-- END SOURCE FILE: early_recovery.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: leader_breakout.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: leader_breakout.md
When this block ends, the document will switch to: momentum_ignition.md
---
<!-- BEGIN SOURCE FILE: leader_breakout.md -->
# Watchlist Preset Spec: Leader Breakout

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Leader Breakout` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Leader Breakout
selected_scan_names: [97 Club, VCS 52 High, RS Acceleration, Three Weeks Tight]
selected_annotation_filters: [Trend Base, Resistance Tests >= 2]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: required_plus_optional_min
  required_scans: [97 Club, VCS 52 High]
  optional_scans: [RS Acceleration, Three Weeks Tight]
  optional_min_hits: 1
preset_status: enabled
```

## Pre-Scan Context

- preset-specific pre-scan filters: none
- shared pre-scan universe filter: active global `UniverseBuilder.filter()` rules only
- shared scan-context enrichment: `weekly_return_rank`, `quarterly_return_rank`, `eps_growth_rank`

## Selected Scans

| Scan name | Card display | Scan reference | Direct threshold summary |
|---|---|---|---|
| `97 Club` | `97 Club` | [../Scan/scan_05_97club.md](../Scan/scan_05_97club.md) | `club_97_hybrid_threshold=90.0`, `club_97_rs21_threshold=97.0` |
| `VCS 52 High` | `VCS 52 High` | [../Scan/scan_13_vcs_52_high.md](../Scan/scan_13_vcs_52_high.md) | `vcs_52_high_vcs_min=55.0`, `vcs_52_high_rs21_min=25.0`, `vcs_52_high_dist_max=-20.0` |
| `RS Acceleration` | `RS Accel` | [../Scan/scan_12_rs_acceleration.md](../Scan/scan_12_rs_acceleration.md) | `rs_acceleration_rs21_min=70.0`, plus hard-coded `rs21 > rs63` |
| `Three Weeks Tight` | `3WT` | [../Scan/scan_11_three_weeks_tight.md](../Scan/scan_11_three_weeks_tight.md) | `three_weeks_tight_vcs_min=50.0`; upstream `three_weeks_tight_pct_threshold=1.5` |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`, `Resistance Tests >= 2`
- selected duplicate subfilters: none
- UI optional threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `required_plus_optional_min`; requires every scan in `97 Club, VCS 52 High` plus at least `1` hit from optional scans `RS Acceleration, Three Weeks Tight`

## Consolidation Notes

This preset absorbs the former `Pattern 1 - Initial Leader Breakout` (added RS Acceleration) and `Pattern 3 - Tight Base Watch` (Three Weeks Tight already included; VCS and Near 52W High coverage subsumed by 97 Club + VCS 52 High).

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
<!-- END SOURCE FILE: leader_breakout.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: momentum_ignition.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: momentum_ignition.md
When this block ends, the document will switch to: momentum_surge.md
---
<!-- BEGIN SOURCE FILE: momentum_ignition.md -->
# Watchlist Preset Spec: Momentum Ignition

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Momentum Ignition` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Momentum Ignition
selected_scan_names: [Momentum 97, 4% bullish, PP Count, VCS 52 High, Volume Accumulation]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [Momentum 97]
  optional_groups:
  - group_name: Acceleration Event
    scans: [4% bullish, PP Count]
    min_hits: 1
  - group_name: Quality Structure
    scans: [VCS 52 High, Volume Accumulation]
    min_hits: 1
preset_status: enabled
```

## Selected Scans

| Scan name | Scan reference |
|---|---|
| `Momentum 97` | [../Scan/scan_04_momentum97.md](../Scan/scan_04_momentum97.md) |
| `4% bullish` | [../Scan/scan_02_4pct_bullish.md](../Scan/scan_02_4pct_bullish.md) |
| `PP Count` | [../Scan/scan_08_pp_count.md](../Scan/scan_08_pp_count.md) |
| `VCS 52 High` | [../Scan/scan_13_vcs_52_high.md](../Scan/scan_13_vcs_52_high.md) |
| `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- duplicate rule: `grouped_threshold`
  - required: `Momentum 97`
  - optional group `Acceleration Event`: min 1 of 2
  - optional group `Quality Structure`: min 1 of 2
<!-- END SOURCE FILE: momentum_ignition.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: momentum_surge.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: momentum_surge.md
When this block ends, the document will switch to: orderly_pullback.md
---
<!-- BEGIN SOURCE FILE: momentum_surge.md -->
# Watchlist Preset Spec: Momentum Surge

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Momentum Surge` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Momentum Surge
selected_scan_names: [4% bullish, Momentum 97, PP Count, Sustained Leadership]
selected_annotation_filters: [Trend Base, RS 21 >= 63]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: required_plus_optional_min
  required_scans: [4% bullish, Momentum 97]
  optional_scans: [PP Count, Sustained Leadership]
  optional_min_hits: 1
preset_status: enabled
```

## Pre-Scan Context

- preset-specific pre-scan filters: none
- shared pre-scan universe filter: active global `UniverseBuilder.filter()` rules only
- shared scan-context enrichment: `weekly_return_rank`, `quarterly_return_rank`, `eps_growth_rank`

## Selected Scans

| Scan name | Card display | Scan reference | Direct threshold summary |
|---|---|---|---|
| `4% bullish` | `4% bullish` | [../Scan/scan_02_4pct_bullish.md](../Scan/scan_02_4pct_bullish.md) | `relative_volume_bullish_threshold=1.0`, `daily_gain_bullish_threshold=4.0` |
| `Momentum 97` | `Momentum 97` | [../Scan/scan_04_momentum97.md](../Scan/scan_04_momentum97.md) | `momentum_97_weekly_rank=97.0`, `momentum_97_quarterly_rank=85.0` |
| `PP Count` | `PP Count` | [../Scan/scan_08_pp_count.md](../Scan/scan_08_pp_count.md) | `pp_count_scan_min=3` |
| `Sustained Leadership` | `RS Leader` | [../Scan/scan_19_sustained_leadership.md](../Scan/scan_19_sustained_leadership.md) | `sustained_rs21_min=80.0`, `sustained_rs63_min=70.0`, `sustained_rs126_min=60.0` |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`, `RS 21 >= 63`
- selected duplicate subfilters: none
- UI optional threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `required_plus_optional_min`; requires every scan in `4% bullish, Momentum 97` plus at least `1` hit from optional scans `PP Count, Sustained Leadership`

## Consolidation Notes

This preset absorbs the former `Pattern 4 - Momentum Confirmation`, which was an exact subset (4% bullish, Momentum 97, PP Count).

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
<!-- END SOURCE FILE: momentum_surge.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: orderly_pullback.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: orderly_pullback.md
When this block ends, the document will switch to: power_gap_pullback.md
---
<!-- BEGIN SOURCE FILE: orderly_pullback.md -->
# Watchlist Preset Spec: Orderly Pullback

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Orderly Pullback` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Orderly Pullback
selected_scan_names: [Pullback Quality scan, 21EMA Pattern H, 21EMA Pattern L, RS Acceleration, Volume Accumulation]
selected_annotation_filters: [Trend Base]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: []
  optional_groups:
  - group_name: 21EMA Trigger
    scans: [21EMA Pattern H, 21EMA Pattern L]
    min_hits: 1
  - group_name: Quality / Strength Confirmation
    scans: [Pullback Quality scan, RS Acceleration, Volume Accumulation]
    min_hits: 1
preset_status: enabled
```

## Pre-Scan Context

- preset-specific pre-scan filters: none
- shared pre-scan universe filter: active global `UniverseBuilder.filter()` rules only
- shared scan-context enrichment: `weekly_return_rank`, `quarterly_return_rank`, `eps_growth_rank`

## Selected Scans

| Scan name | Card display | Scan reference | Direct threshold summary |
|---|---|---|---|
| `Pullback Quality scan` | `PB Quality` | [../Scan/scan_16_pullback_quality.md](../Scan/scan_16_pullback_quality.md) | no config keys; hard-coded rule uses `atr_21ema_zone`, `atr_50sma_zone`, `weekly_return`, `dcr_percent`, drawdown, and volume-cooling bounds |
| `21EMA Pattern H` | `21EMA PH` | [../Scan/scan_22_21ema_pattern_h.md](../Scan/scan_22_21ema_pattern_h.md) | no config keys; hard-coded rule uses 50SMA distance, 21EMA(C) upper zone, 21EMA(H) low support, and previous-high breakout |
| `21EMA Pattern L` | `21EMA PL` | [../Scan/scan_23_21ema_pattern_l.md](../Scan/scan_23_21ema_pattern_l.md) | no config keys; hard-coded rule uses 50SMA distance, 21EMA(C) lower zone, 21EMA(L) intraday pierce, 21EMA(L) close reclaim, and previous-high breakout |
| `Volume Accumulation` | `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) | `vol_accum_ud_ratio_min=1.5`, `vol_accum_rel_vol_min=1.0`, plus hard-coded `daily_change_pct > 0.0` |
| `RS Acceleration` | `RS Accel` | [../Scan/scan_12_rs_acceleration.md](../Scan/scan_12_rs_acceleration.md) | `rs_acceleration_rs21_min=70.0`, plus hard-coded `rs21 > rs63` |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`
- selected duplicate subfilters: none
- UI optional threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `grouped_threshold`; no direct required scans, requires at least `1` hit from the `21EMA Trigger` group, and at least `1` hit from the `Quality / Strength Confirmation` group

## Consolidation Notes

This preset now replaces the retired broad `21EMA scan` with the two trigger-based 21EMA pattern scans. The grouped duplicate rule accepts either 21EMA pattern as the trigger-side confirmation and requires one hit from the quality/strength group (`Pullback Quality scan`, `RS Acceleration`, `Volume Accumulation`).

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
<!-- END SOURCE FILE: orderly_pullback.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: power_gap_pullback.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: power_gap_pullback.md
When this block ends, the document will switch to: pullback_trigger.md
---
<!-- BEGIN SOURCE FILE: power_gap_pullback.md -->
# Watchlist Preset Spec: Power Gap Pullback

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Power Gap Pullback` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Power Gap Pullback
selected_scan_names: [Pullback Quality scan, 21EMA Pattern H, 21EMA Pattern L, Reclaim scan, Volume Accumulation, Pocket Pivot]
selected_annotation_filters: [Recent Power Gap, Trend Base]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [Pullback Quality scan]
  optional_groups:
  - group_name: Reentry Trigger
    scans: [21EMA Pattern H, 21EMA Pattern L, Reclaim scan]
    min_hits: 1
  - group_name: Demand Confirmation
    scans: [Volume Accumulation, Pocket Pivot]
    min_hits: 1
preset_status: enabled
```

## Selected Scans

| Scan name | Scan reference |
|---|---|
| `Pullback Quality scan` | [../Scan/scan_16_pullback_quality.md](../Scan/scan_16_pullback_quality.md) |
| `21EMA Pattern H` | [../Scan/scan_22_21ema_pattern_h.md](../Scan/scan_22_21ema_pattern_h.md) |
| `21EMA Pattern L` | [../Scan/scan_23_21ema_pattern_l.md](../Scan/scan_23_21ema_pattern_l.md) |
| `Reclaim scan` | [../Scan/scan_17_reclaim.md](../Scan/scan_17_reclaim.md) |
| `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) |
| `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Recent Power Gap`, `Trend Base`
- selected duplicate subfilters: none
- duplicate rule: `grouped_threshold`
  - required: `Pullback Quality scan`
  - optional group `Reentry Trigger`: min 1 of 3
  - optional group `Demand Confirmation`: min 1 of 2
<!-- END SOURCE FILE: power_gap_pullback.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: pullback_trigger.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: pullback_trigger.md
When this block ends, the document will switch to: reclaim_trigger.md
---
<!-- BEGIN SOURCE FILE: pullback_trigger.md -->
# Watchlist Preset Spec: Pullback Trigger

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Pullback Trigger` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Pullback Trigger
selected_scan_names: [Pullback Quality scan, 21EMA Pattern H, 21EMA Pattern L, Volume Accumulation, Pocket Pivot]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [Pullback Quality scan]
  optional_groups:
  - group_name: Pattern Trigger
    scans: [21EMA Pattern H, 21EMA Pattern L]
    min_hits: 1
  - group_name: Demand Confirmation
    scans: [Volume Accumulation, Pocket Pivot]
    min_hits: 1
preset_status: enabled
```

## Selected Scans

| Scan name | Scan reference |
|---|---|
| `Pullback Quality scan` | [../Scan/scan_16_pullback_quality.md](../Scan/scan_16_pullback_quality.md) |
| `21EMA Pattern H` | [../Scan/scan_22_21ema_pattern_h.md](../Scan/scan_22_21ema_pattern_h.md) |
| `21EMA Pattern L` | [../Scan/scan_23_21ema_pattern_l.md](../Scan/scan_23_21ema_pattern_l.md) |
| `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) |
| `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- duplicate rule: `grouped_threshold`
  - required: `Pullback Quality scan`
  - optional group `Pattern Trigger`: min 1 of 2
  - optional group `Demand Confirmation`: min 1 of 2
<!-- END SOURCE FILE: pullback_trigger.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: reclaim_trigger.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: reclaim_trigger.md
When this block ends, the document will switch to: resilient_leader.md
---
<!-- BEGIN SOURCE FILE: reclaim_trigger.md -->
# Watchlist Preset Spec: Reclaim Trigger

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Reclaim Trigger` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Reclaim Trigger
selected_scan_names: [Reclaim scan, Pocket Pivot]
selected_annotation_filters: [Trend Base]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: required_plus_optional_min
  required_scans: [Reclaim scan]
  optional_scans: [Pocket Pivot]
  optional_min_hits: 1
preset_status: enabled
```

## Pre-Scan Context

- preset-specific pre-scan filters: none
- shared pre-scan universe filter: active global `UniverseBuilder.filter()` rules only
- shared scan-context enrichment: `weekly_return_rank`, `quarterly_return_rank`, `eps_growth_rank`

## Selected Scans

| Scan name | Card display | Scan reference | Direct threshold summary |
|---|---|---|---|
| `Reclaim scan` | `Reclaim` | [../Scan/scan_17_reclaim.md](../Scan/scan_17_reclaim.md) | no config keys; hard-coded rule uses reclaim-location, recent-pullback, and trigger-confirmation bounds |
| `Pocket Pivot` | `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) | no scan config keys; requires `close > sma50` and `pocket_pivot=true` |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`
- selected duplicate subfilters: none
- UI optional threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `required_plus_optional_min`; requires every scan in `Reclaim scan` plus at least `1` hit from optional scans `Pocket Pivot`

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
<!-- END SOURCE FILE: reclaim_trigger.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: resilient_leader.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: resilient_leader.md
When this block ends, the document will switch to: rs_breakout_setup.md
---
<!-- BEGIN SOURCE FILE: resilient_leader.md -->
# Watchlist Preset Spec: Resilient Leader

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Resilient Leader` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |
| Market environment | `Under Pressure` |

## Current Config Payload

```yaml
preset_name: Resilient Leader
selected_scan_names: [Sustained Leadership, Near 52W High]
selected_annotation_filters: [Trend Base, Fund Score > 70, RS 21 >= 63]
selected_duplicate_subfilters: []
duplicate_threshold: 2
duplicate_rule:
  mode: min_count
  min_count: 2
preset_status: enabled
```

## Pre-Scan Context

- preset-specific pre-scan filters: none
- shared pre-scan universe filter: active global `UniverseBuilder.filter()` rules only
- shared scan-context enrichment: `weekly_return_rank`, `quarterly_return_rank`, `eps_growth_rank`

## Selected Scans

| Scan name | Card display | Scan reference | Direct threshold summary |
|---|---|---|---|
| `Sustained Leadership` | `RS Leader` | [../Scan/scan_19_sustained_leadership.md](../Scan/scan_19_sustained_leadership.md) | `sustained_rs21_min=80.0`, `sustained_rs63_min=70.0`, `sustained_rs126_min=60.0` |
| `Near 52W High` | `Near 52W High` | [../Scan/scan_10_near_52w_high.md](../Scan/scan_10_near_52w_high.md) | `near_52w_high_threshold_pct=5.0`, `near_52w_high_hybrid_min=70.0` |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`, `Fund Score > 70`, `RS 21 >= 63`
- selected duplicate subfilters: none
- UI optional threshold after preset load: not used by `min_count`
- preset status: `enabled`
- duplicate rule: `min_count`; requires both selected scans because `min_count=2`

## Scan Role Mapping

| Role | Scan | Rationale |
|---|---|---|
| Core | `Sustained Leadership` | All-horizon RS (21/63/126) proves persistent institutional holding through market weakness |
| Core | `Near 52W High` | Maintaining 52-week high proximity under market pressure is direct evidence of resilience |
| Filter | `Trend Base`, `Fund Score > 70`, `RS 21 >= 63` | Preset-level annotation filters enforce trend, fundamental score, and RS quality gates |

## Logic Structure

```
duplicate_rule.mode: min_count
min_count: 2
→ ticker must hit both selected scans, then pass every selected annotation filter
```

Representative hit patterns:

- `Sustained Leadership` + `Near 52W High` + all selected annotation filters → near-high leader with fundamental backing and trend/RS quality

## Setup Interpretation

- **Target phase**: relative strength identification during market pressure; watchlist building for recovery
- **Why effective in Under Pressure**: most stocks break down under pressure; those maintaining high-zone RS plus fundamentals signal persistent institutional ownership and will be first to break out when the market environment improves
- **Not an immediate entry preset**: entry timing deferred to Base Breakout or Trend Pullback when market returns to Confirmed Uptrend

## Design Rationale

Sustained Leadership's multi-horizon RS requirement (21/63/126) is environment-independent and identifies stocks that outperform regardless of market state. Near 52W High becomes a much stronger filter under pressure because fewer stocks qualify. The selected annotation filters add trend, RS, and earnings-quality backing. The selected scans do not overlap with breakout triggers (Pocket Pivot, 3WT), pullback detectors (PB Quality, Reclaim), or reversal structure (Trend Reversal Setup, Structure Pivot).

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
<!-- END SOURCE FILE: resilient_leader.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: rs_breakout_setup.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: rs_breakout_setup.md
When this block ends, the document will switch to: screening_thesis.md
---
<!-- BEGIN SOURCE FILE: rs_breakout_setup.md -->
# Watchlist Preset Spec: RS Breakout Setup

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `RS Breakout Setup` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: RS Breakout Setup
selected_scan_names: [RS New High, VCS 52 High, Pocket Pivot, 4% bullish, PP Count]
selected_annotation_filters: [Trend Base]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [RS New High, VCS 52 High]
  optional_groups:
  - group_name: Breakout Event
    scans: [Pocket Pivot, 4% bullish, PP Count]
    min_hits: 1
preset_status: enabled
```

## Selected Scans

| Scan name | Scan reference |
|---|---|
| `RS New High` | [../Scan/scan_28_rs_new_high.md](../Scan/scan_28_rs_new_high.md) |
| `VCS 52 High` | [../Scan/scan_13_vcs_52_high.md](../Scan/scan_13_vcs_52_high.md) |
| `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) |
| `4% bullish` | [../Scan/scan_02_4pct_bullish.md](../Scan/scan_02_4pct_bullish.md) |
| `PP Count` | [../Scan/scan_08_pp_count.md](../Scan/scan_08_pp_count.md) |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`
- selected duplicate subfilters: none
- duplicate rule: `grouped_threshold`
  - required: `RS New High`, `VCS 52 High`
  - optional group `Breakout Event`: min 1 of 3
<!-- END SOURCE FILE: rs_breakout_setup.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: screening_thesis.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: screening_thesis.md
When this block ends, the document will switch to: status_matrix.md
---
<!-- BEGIN SOURCE FILE: screening_thesis.md -->
# Watchlist Preset Spec: Screening Thesis

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Screening Thesis` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Screening Thesis
selected_scan_names: [Trend Reversal Setup, LL-HL Structure 1st Pivot, LL-HL Structure 2nd Pivot, LL-HL Structure Trend Line Break, Volume Accumulation, Pocket Pivot]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [Trend Reversal Setup]
  optional_groups:
  - group_name: Structure Break
    scans: [LL-HL Structure 1st Pivot, LL-HL Structure 2nd Pivot, LL-HL Structure Trend Line Break]
    min_hits: 1
  - group_name: Demand Confirmation
    scans: [Volume Accumulation, Pocket Pivot]
    min_hits: 1
preset_status: enabled
```

## Selected Scans

| Scan name | Scan reference |
|---|---|
| `Trend Reversal Setup` | [../Scan/scan_20_trend_reversal_setup.md](../Scan/scan_20_trend_reversal_setup.md) |
| `LL-HL Structure 1st Pivot` | [../Scan/scan_24_llhl_1st_pivot.md](../Scan/scan_24_llhl_1st_pivot.md) |
| `LL-HL Structure 2nd Pivot` | [../Scan/scan_25_llhl_2nd_pivot.md](../Scan/scan_25_llhl_2nd_pivot.md) |
| `LL-HL Structure Trend Line Break` | [../Scan/scan_26_llhl_ct_break.md](../Scan/scan_26_llhl_ct_break.md) |
| `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) |
| `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- duplicate rule: `grouped_threshold`
  - required: `Trend Reversal Setup`
  - optional group `Structure Break`: min 1 of 3
  - optional group `Demand Confirmation`: min 1 of 2
<!-- END SOURCE FILE: screening_thesis.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: status_matrix.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: status_matrix.md
When this block ends, the document will switch to: trend_pullback.md
---
<!-- BEGIN SOURCE FILE: status_matrix.md -->
# Watchlist Preset Status Matrix

Source of truth:
- config: `config/default/scan.yaml -> scan.watchlist_presets`
- runtime: `src/scan/rules.py::ScanConfig.from_dict`

Column meaning:
- `Status`: effective runtime preset status.
- `UI`: visible in the built-in preset picker.
- `Export`: included in built-in preset exports.
- `Inactive scans`: selected scans that are currently disabled. Any non-empty value forces runtime `Status` to `disabled`.

Current totals:
- enabled: 9
- hidden_enabled: 0
- disabled: 7

| Preset | Status | UI | Export | Inactive scans |
| --- | --- | --- | --- | --- |
| `Leader Breakout` | `disabled` | `no` | `no` | `97 Club`, `RS Acceleration`, `Three Weeks Tight` |
| `Orderly Pullback` | `disabled` | `no` | `no` | `RS Acceleration` |
| `Reclaim Trigger` | `enabled` | `yes` | `yes` | `-` |
| `Momentum Surge` | `disabled` | `no` | `no` | `Sustained Leadership` |
| `Early Cycle Recovery` | `enabled` | `yes` | `yes` | `-` |
| `Base Breakout` | `disabled` | `no` | `no` | `97 Club`, `Three Weeks Tight` |
| `Accumulation Breakout` | `enabled` | `yes` | `yes` | `-` |
| `50SMA Defense` | `enabled` | `yes` | `yes` | `-` |
| `Power Gap Pullback` | `enabled` | `yes` | `yes` | `-` |
| `RS Breakout Setup` | `enabled` | `yes` | `yes` | `-` |
| `Trend Pullback` | `disabled` | `no` | `no` | `RS Acceleration` |
| `Resilient Leader` | `disabled` | `no` | `no` | `Sustained Leadership`, `Near 52W High` |
| `Early Recovery` | `disabled` | `no` | `no` | `Structure Pivot` |
| `Screening Thesis` | `enabled` | `yes` | `yes` | `-` |
| `Pullback Trigger` | `enabled` | `yes` | `yes` | `-` |
| `Momentum Ignition` | `enabled` | `yes` | `yes` | `-` |
<!-- END SOURCE FILE: status_matrix.md -->

---
CONTENT SWITCH
The next section starts the copied contents of: trend_pullback.md
---

---
FILE BOUNDARY NOTICE
You are now reading content copied from: trend_pullback.md
This is the final source file block in the combined document.
---
<!-- BEGIN SOURCE FILE: trend_pullback.md -->
# Watchlist Preset Spec: Trend Pullback

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Trend Pullback` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |
| Market environment | `Confirmed Uptrend` |

## Current Config Payload

```yaml
preset_name: Trend Pullback
selected_scan_names: [Reclaim scan, Pullback Quality scan, RS Acceleration, Volume Accumulation]
selected_annotation_filters: [Trend Base]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [Reclaim scan]
  optional_groups:
  - group_name: Pullback Evidence
    scans: [Pullback Quality scan]
    min_hits: 1
  - group_name: Strength Confirmation
    scans: [RS Acceleration, Volume Accumulation]
    min_hits: 1
preset_status: enabled
```

## Pre-Scan Context

- preset-specific pre-scan filters: none
- shared pre-scan universe filter: active global `UniverseBuilder.filter()` rules only
- shared scan-context enrichment: `weekly_return_rank`, `quarterly_return_rank`, `eps_growth_rank`

## Selected Scans

| Scan name | Card display | Scan reference | Direct threshold summary |
|---|---|---|---|
| `Pullback Quality scan` | `PB Quality` | [../Scan/scan_16_pullback_quality.md](../Scan/scan_16_pullback_quality.md) | no config keys; hard-coded rule uses `atr_21ema_zone`, `atr_50sma_zone`, `weekly_return`, `dcr_percent`, drawdown, and volume-cooling bounds |
| `Reclaim scan` | `Reclaim` | [../Scan/scan_17_reclaim.md](../Scan/scan_17_reclaim.md) | no config keys; hard-coded rule uses reclaim-location, recent-pullback, and trigger-confirmation bounds |
| `RS Acceleration` | `RS Accel` | [../Scan/scan_12_rs_acceleration.md](../Scan/scan_12_rs_acceleration.md) | `rs_acceleration_rs21_min=70.0`, plus hard-coded `rs21 > rs63` |
| `Volume Accumulation` | `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) | `vol_accum_ud_ratio_min=1.5`, `vol_accum_rel_vol_min=1.0`, plus hard-coded `daily_change_pct > 0.0` |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`
- selected duplicate subfilters: none
- UI optional threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `grouped_threshold`; requires `Reclaim scan`, at least `1` hit from `Pullback Evidence`, and at least `1` hit from `Strength Confirmation`

## Scan Role Mapping

| Role | Scan | Rationale |
|---|---|---|
| Core | `Pullback Quality scan` | Proves orderly pullback structure: volume cooling, proper drawdown depth, 21EMA proximity |
| Trigger | `Reclaim scan` | Detects the 21EMA reclaim event with volume + cross + recent pullback evidence |
| Confirmation | `RS Acceleration` | RS21 > RS63 confirms relative strength is accelerating, not decaying |
| Confirmation | `Volume Accumulation` | U/D volume ratio confirms institutional demand backing the move |

## Logic Structure

```
duplicate_rule.mode: grouped_threshold
required_scans: [Reclaim scan]
optional_groups:
- group_name: Pullback Evidence
  scans: [Pullback Quality scan]
  min_hits: 1
- group_name: Strength Confirmation
  scans: [RS Acceleration, Volume Accumulation]
  min_hits: 1
ticker must hit Reclaim scan + Pullback Quality scan + one strength confirmation scan
```

Representative hit patterns:

- `Reclaim scan` + `Pullback Quality scan` + `RS Acceleration` -> reclaim with pullback evidence and RS acceleration
- `Reclaim scan` + `Pullback Quality scan` + `Volume Accumulation` -> reclaim with pullback evidence and demand confirmation

## Setup Interpretation

- **Target phase**: pullback -> reclaim two-stage process
- **Why effective in Confirmed Uptrend**: healthy pullbacks to 21EMA occur naturally in uptrends; reclaim entries from this zone offer reliable swing re-entries with market tailwind supporting follow-through

## Design Rationale

The rule keeps `Reclaim scan` as required and enforces `Pullback Quality scan` through a dedicated `Pullback Evidence` group. Strength confirmation remains flexible with `RS Acceleration` or `Volume Accumulation` in the second group.

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
<!-- END SOURCE FILE: trend_pullback.md -->
