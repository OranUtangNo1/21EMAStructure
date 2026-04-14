# Watchlist Preset Spec: Pattern 5 - Early Reversal Signal

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Pattern 5 - Early Reversal Signal` |
| Preset type | disabled legacy watchlist preset reference |
| Runtime source | not loaded from the current `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Legacy Config Payload

```yaml
# Not present in the current config/default/scan.yaml built-in preset catalog.
preset_name: Pattern 5 - Early Reversal Signal
selected_scan_names: [VCS 52 Low, Volume Accumulation, Pocket Pivot]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 2
preset_status: disabled_legacy_reference
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
| `Pocket Pivot` | `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) | no scan config keys; requires `close > sma50` and `pocket_pivot=true` |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- historical duplicate threshold after preset load: `2`

## Scope Notes

- This legacy preset is not loaded by the active app.
- When it was active, it changed watchlist page controls only.
- It does not override global scan thresholds.
