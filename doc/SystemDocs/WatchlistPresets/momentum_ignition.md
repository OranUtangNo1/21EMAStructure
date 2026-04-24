# Watchlist Preset Spec: Momentum Ignition

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Momentum Ignition` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Momentum Ignition
selected_scan_names: [Momentum 97, 4% bullish, PP Count, VCS 52 High, Volume Accumulation]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [Momentum 97]
  optional_groups:
  - group_name: Acceleration Event
    scans: [4% bullish, PP Count]
    min_hits: 1
  - group_name: Quality Structure
    scans: [VCS 52 High, Volume Accumulation]
    min_hits: 1
preset_status: enabled
```

## Selected Scans

| Scan name | Scan reference |
|---|---|
| `Momentum 97` | [../Scan/scan_04_momentum97.md](../Scan/scan_04_momentum97.md) |
| `4% bullish` | [../Scan/scan_02_4pct_bullish.md](../Scan/scan_02_4pct_bullish.md) |
| `PP Count` | [../Scan/scan_08_pp_count.md](../Scan/scan_08_pp_count.md) |
| `VCS 52 High` | [../Scan/scan_13_vcs_52_high.md](../Scan/scan_13_vcs_52_high.md) |
| `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- duplicate rule: `grouped_threshold`
  - required: `Momentum 97`
  - optional group `Acceleration Event`: min 1 of 2
  - optional group `Quality Structure`: min 1 of 2
