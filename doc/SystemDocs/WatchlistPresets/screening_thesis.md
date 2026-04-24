# Watchlist Preset Spec: Screening Thesis

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Screening Thesis` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Screening Thesis
selected_scan_names: [Trend Reversal Setup, LL-HL Structure 1st Pivot, LL-HL Structure 2nd Pivot, LL-HL Structure Trend Line Break, Volume Accumulation, Pocket Pivot]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [Trend Reversal Setup]
  optional_groups:
  - group_name: Structure Break
    scans: [LL-HL Structure 1st Pivot, LL-HL Structure 2nd Pivot, LL-HL Structure Trend Line Break]
    min_hits: 1
  - group_name: Demand Confirmation
    scans: [Volume Accumulation, Pocket Pivot]
    min_hits: 1
preset_status: enabled
```

## Selected Scans

| Scan name | Scan reference |
|---|---|
| `Trend Reversal Setup` | [../Scan/scan_20_trend_reversal_setup.md](../Scan/scan_20_trend_reversal_setup.md) |
| `LL-HL Structure 1st Pivot` | [../Scan/scan_24_llhl_1st_pivot.md](../Scan/scan_24_llhl_1st_pivot.md) |
| `LL-HL Structure 2nd Pivot` | [../Scan/scan_25_llhl_2nd_pivot.md](../Scan/scan_25_llhl_2nd_pivot.md) |
| `LL-HL Structure Trend Line Break` | [../Scan/scan_26_llhl_ct_break.md](../Scan/scan_26_llhl_ct_break.md) |
| `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) |
| `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- duplicate rule: `grouped_threshold`
  - required: `Trend Reversal Setup`
  - optional group `Structure Break`: min 1 of 3
  - optional group `Demand Confirmation`: min 1 of 2
