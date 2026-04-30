# Watchlist Preset Spec: Accumulation Breakout

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Accumulation Breakout` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Accumulation Breakout
selected_scan_names: [VCS 52 High, PP Count, Volume Accumulation, Pocket Pivot, 4% bullish]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [VCS 52 High]
  optional_groups:
  - group_name: Accumulation Evidence
    scans: [PP Count, Volume Accumulation]
    min_hits: 1
  - group_name: Breakout Trigger
    scans: [Pocket Pivot, 4% bullish]
    min_hits: 1
preset_status: enabled
```

## Selected Scans

| Scan name | Scan reference |
|---|---|
| `VCS 52 High` | [../Scan/scan_13_vcs_52_high.md](../Scan/scan_13_vcs_52_high.md) |
| `PP Count` | [../Scan/scan_08_pp_count.md](../Scan/scan_08_pp_count.md) |
| `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) |
| `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) |
| `4% bullish` | [../Scan/scan_02_4pct_bullish.md](../Scan/scan_02_4pct_bullish.md) |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- duplicate rule: `grouped_threshold`
  - required: `VCS 52 High`
  - optional group `Accumulation Evidence`: min 1 of 2
  - optional group `Breakout Trigger`: min 1 of 2
