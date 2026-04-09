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
selected_scan_names: [VCS 52 Low, Volume Accumulation, Trend Reversal Setup]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 2
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

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- UI duplicate threshold after preset load: `2`

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
