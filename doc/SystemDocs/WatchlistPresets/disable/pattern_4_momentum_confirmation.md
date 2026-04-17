# Watchlist Preset Spec: Pattern 4 - Momentum Confirmation

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Pattern 4 - Momentum Confirmation` |
| Preset type | disabled legacy watchlist preset reference |
| Runtime source | not loaded from the current `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Legacy Config Payload

```yaml
# Not present in the current config/default/scan.yaml built-in preset catalog.
preset_name: Pattern 4 - Momentum Confirmation
selected_scan_names: [4% bullish, Momentum 97, PP Count]
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
| `4% bullish` | `4% bullish` | [../Scan/scan_02_4pct_bullish.md](../Scan/scan_02_4pct_bullish.md) | `relative_volume_bullish_threshold=1.0`, `daily_gain_bullish_threshold=4.0` |
| `Momentum 97` | `Momentum 97` | [../Scan/scan_04_momentum97.md](../Scan/scan_04_momentum97.md) | `momentum_97_weekly_rank=97.0`, `momentum_97_quarterly_rank=85.0` |
| `PP Count` | `PP Count` | [../Scan/scan_08_pp_count.md](../Scan/scan_08_pp_count.md) | `pp_count_scan_min=3` |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- historical duplicate threshold after preset load: `2`

## Scope Notes

- This legacy preset is not loaded by the active app.
- When it was active, it changed watchlist page controls only.
- It does not override global scan thresholds.
