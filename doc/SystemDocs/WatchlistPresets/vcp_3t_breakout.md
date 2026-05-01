# Watchlist Preset Spec: VCP 3T Breakout

## Canonical Metadata

| Item | Value |
| --- | --- |
| Preset name | `VCP 3T Breakout` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: VCP 3T Breakout
selected_scan_names: [VCP 3T, VCS 52 High, Pocket Pivot, Volume Accumulation, RS New High]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [VCP 3T]
  optional_groups:
  - group_name: Leadership / High Tightness
    scans: [VCS 52 High, RS New High]
    min_hits: 1
  - group_name: Demand Confirmation
    scans: [Pocket Pivot, Volume Accumulation]
    min_hits: 1
preset_status: enabled
```

## Selected Scans

| Scan name | Scan reference |
| --- | --- |
| `VCP 3T` | [../Scan/scan_29_vcp_3t.md](../Scan/scan_29_vcp_3t.md) |
| `VCS 52 High` | [../Scan/scan_13_vcs_52_high.md](../Scan/scan_13_vcs_52_high.md) |
| `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) |
| `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) |
| `RS New High` | [../Scan/scan_28_rs_new_high.md](../Scan/scan_28_rs_new_high.md) |

## Intent

This preset targets the image-style VCP breakout:

- an existing uptrend into the base
- three progressively smaller contractions
- final tight candles with volume dry-up
- breakout through the pivot while still close to the pivot
- at least one high-tightness or RS-new-high confirmation
- at least one demand confirmation from pocket-pivot or accumulation evidence

It is stricter than `Accumulation Breakout` and should be treated as a focused VCP breakout universe rather than a broad base-breakout universe.
