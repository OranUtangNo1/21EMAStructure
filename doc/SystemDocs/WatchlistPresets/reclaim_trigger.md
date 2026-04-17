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
selected_annotation_filters: [Trend Base, Fund Score > 70, RS 21 >= 63]
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

- selected annotation filters: `Trend Base`, `Fund Score > 70`, `RS 21 >= 63`
- selected duplicate subfilters: none
- UI optional threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `required_plus_optional_min`; requires every scan in `Reclaim scan` plus at least `1` hit from optional scans `Pocket Pivot`

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
