# Watchlist Preset Spec: RS Breakout Setup

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `RS Breakout Setup` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: RS Breakout Setup
selected_scan_names: [RS New High, VCS 52 High, Pocket Pivot, 4% bullish, PP Count]
selected_annotation_filters: [Trend Base]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [RS New High, VCS 52 High]
  optional_groups:
  - group_name: Breakout Event
    scans: [Pocket Pivot, 4% bullish, PP Count]
    min_hits: 1
preset_status: enabled
```

## Selected Scans

| Scan name | Scan reference |
|---|---|
| `RS New High` | [../Scan/scan_28_rs_new_high.md](../Scan/scan_28_rs_new_high.md) |
| `VCS 52 High` | [../Scan/scan_13_vcs_52_high.md](../Scan/scan_13_vcs_52_high.md) |
| `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) |
| `4% bullish` | [../Scan/scan_02_4pct_bullish.md](../Scan/scan_02_4pct_bullish.md) |
| `PP Count` | [../Scan/scan_08_pp_count.md](../Scan/scan_08_pp_count.md) |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`
- selected duplicate subfilters: none
- duplicate rule: `grouped_threshold`
  - required: `RS New High`, `VCS 52 High`
  - optional group `Breakout Event`: min 1 of 3
