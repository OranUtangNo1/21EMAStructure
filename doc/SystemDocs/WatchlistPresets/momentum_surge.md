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
selected_annotation_filters: []
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
| `4% bullish` | `4% bullish` | [../Scan/scan_02_4pct_bullish.md](../Scan/scan_02_4pct_bullish.md) | `relative_volume_bullish_threshold=1.0`, `daily_gain_bullish_threshold=4.0`, plus hard-coded `raw_rs21 > 60.0` |
| `Momentum 97` | `Momentum 97` | [../Scan/scan_04_momentum97.md](../Scan/scan_04_momentum97.md) | `momentum_97_weekly_rank=97.0`, `momentum_97_quarterly_rank=85.0` |
| `PP Count` | `PP Count` | [../Scan/scan_08_pp_count.md](../Scan/scan_08_pp_count.md) | `pp_count_scan_min=3` |
| `Sustained Leadership` | `RS Leader` | [../Scan/scan_19_sustained_leadership.md](../Scan/scan_19_sustained_leadership.md) | `sustained_rs21_min=80.0`, `sustained_rs63_min=70.0`, `sustained_rs126_min=60.0` |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- UI duplicate threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `required_plus_optional_min`; requires every scan in `4% bullish, Momentum 97` plus at least `1` hit from optional scans `PP Count, Sustained Leadership`

## Consolidation Notes

This preset absorbs the former `Pattern 4 - Momentum Confirmation`, which was an exact subset (4% bullish, Momentum 97, PP Count).

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
