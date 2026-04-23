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
