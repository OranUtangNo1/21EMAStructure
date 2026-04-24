# Watchlist Preset Spec: Pullback Trigger

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Pullback Trigger` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Pullback Trigger
selected_scan_names: [Pullback Quality scan, 21EMA Pattern H, 21EMA Pattern L, Volume Accumulation, Pocket Pivot]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [Pullback Quality scan]
  optional_groups:
  - group_name: Pattern Trigger
    scans: [21EMA Pattern H, 21EMA Pattern L]
    min_hits: 1
  - group_name: Demand Confirmation
    scans: [Volume Accumulation, Pocket Pivot]
    min_hits: 1
preset_status: enabled
```

## Selected Scans

| Scan name | Scan reference |
|---|---|
| `Pullback Quality scan` | [../Scan/scan_16_pullback_quality.md](../Scan/scan_16_pullback_quality.md) |
| `21EMA Pattern H` | [../Scan/scan_22_21ema_pattern_h.md](../Scan/scan_22_21ema_pattern_h.md) |
| `21EMA Pattern L` | [../Scan/scan_23_21ema_pattern_l.md](../Scan/scan_23_21ema_pattern_l.md) |
| `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) |
| `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- duplicate rule: `grouped_threshold`
  - required: `Pullback Quality scan`
  - optional group `Pattern Trigger`: min 1 of 2
  - optional group `Demand Confirmation`: min 1 of 2
