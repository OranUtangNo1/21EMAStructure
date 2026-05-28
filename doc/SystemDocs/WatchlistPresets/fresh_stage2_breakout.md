# Watchlist Preset Spec: Fresh Stage 2 Breakout

## Canonical Metadata

| Item | Value |
| --- | --- |
| Preset name | `Fresh Stage 2 Breakout` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Fresh Stage 2 Breakout
selected_scan_names: [Fresh Stage 2 Breakout, RS Leads Price Setup, VCS 52 High, Pocket Pivot, Volume Accumulation]
selected_annotation_filters: [Stage 2 Quality Score, Mature / Late Stage Risk Filter]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [Fresh Stage 2 Breakout]
  optional_groups:
  - group_name: Leadership Confirmation
    scans: [RS Leads Price Setup, VCS 52 High]
    min_hits: 1
  - group_name: Demand Confirmation
    scans: [Pocket Pivot, Volume Accumulation]
    min_hits: 1
preset_status: enabled
```

## Intent

This preset targets recent Stage 2 transitions with breakout evidence, then requires at least one leadership confirmation and one demand confirmation. It is the early Stage 2 watchlist preset.

