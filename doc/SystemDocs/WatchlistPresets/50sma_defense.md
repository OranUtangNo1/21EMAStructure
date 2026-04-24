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
