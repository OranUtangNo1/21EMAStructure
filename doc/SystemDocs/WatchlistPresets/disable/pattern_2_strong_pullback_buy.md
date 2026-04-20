# Watchlist Preset Spec: Pattern 2 - Strong Pullback Buy

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Pattern 2 - Strong Pullback Buy` |
| Preset type | disabled legacy watchlist preset reference |
| Runtime source | not loaded from the current `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Legacy Config Payload

```yaml
# Not present in the current config/default/scan.yaml built-in preset catalog.
preset_name: Pattern 2 - Strong Pullback Buy
selected_scan_names: [21EMA scan, PP Count, Volume Accumulation]
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
| `21EMA scan` | `21EMA` | [../../Scan/scan_01_21ema.md](../../Scan/scan_01_21ema.md) | no config keys; retained legacy rule uses `weekly_return`, `dcr_percent`, `atr_21ema_zone`, and `atr_50sma_zone`; disabled by default |
| `PP Count` | `PP Count` | [../Scan/scan_08_pp_count.md](../Scan/scan_08_pp_count.md) | `pp_count_scan_min=3` |
| `Volume Accumulation` | `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) | `vol_accum_ud_ratio_min=1.5`, `vol_accum_rel_vol_min=1.0`, plus hard-coded `daily_change_pct > 0.0` |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- historical duplicate threshold after preset load: `2`

## Scope Notes

- This legacy preset is not loaded by the active app.
- When it was active, it changed watchlist page controls only.
- It does not override global scan thresholds.
