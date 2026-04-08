# Watchlist Preset Spec: Pattern 4 - Momentum Confirmation

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Pattern 4 - Momentum Confirmation` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Pattern 4 - Momentum Confirmation
selected_scan_names: [4% bullish, Momentum 97, PP Count]
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
| `4% bullish` | `4% bullish` | [../Scan/scan_02_4pct_bullish.md](../Scan/scan_02_4pct_bullish.md) | `relative_volume_bullish_threshold=1.0`, `daily_gain_bullish_threshold=4.0`, plus hard-coded `raw_rs21 > 60.0` |
| `Momentum 97` | `Momentum 97` | [../Scan/scan_04_momentum97.md](../Scan/scan_04_momentum97.md) | `momentum_97_weekly_rank=97.0`, `momentum_97_quarterly_rank=85.0` |
| `PP Count` | `PP Count` | [../Scan/scan_08_pp_count.md](../Scan/scan_08_pp_count.md) | `pp_count_scan_min=3` |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- UI duplicate threshold after preset load: `2`

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
