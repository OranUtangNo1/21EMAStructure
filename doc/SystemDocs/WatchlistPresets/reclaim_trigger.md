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
selected_scan_names: [Reclaim scan, Pocket Pivot, Fundamental Demand]
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
| `Reclaim scan` | `Reclaim` | [../Scan/scan_17_reclaim.txt](../Scan/scan_17_reclaim.txt) | no config keys; hard-coded rule uses reclaim-location, recent-pullback, and trigger-confirmation bounds |
| `Pocket Pivot` | `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) | no scan config keys; requires `close > sma50` and `pocket_pivot=true` |
| `Fundamental Demand` | `Fund Demand` | [../Scan/scan_18_fundamental_demand.md](../Scan/scan_18_fundamental_demand.md) | `fund_demand_fundamental_min=70.0`, `fund_demand_rs21_min=60.0`, `fund_demand_rel_vol_min=1.0` |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- UI duplicate threshold after preset load: `2`

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
