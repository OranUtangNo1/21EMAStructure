# Watchlist Preset Spec: Pattern 1 - Initial Leader Breakout

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Pattern 1 - Initial Leader Breakout` |
| Preset type | disabled legacy watchlist preset reference |
| Runtime source | not loaded from the current `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Legacy Config Payload

```yaml
# Not present in the current config/default/scan.yaml built-in preset catalog.
preset_name: Pattern 1 - Initial Leader Breakout
selected_scan_names: [97 Club, VCS 52 High, RS Acceleration]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 2
preset_status: disabled_legacy_reference
```

## Pre-Scan Context

- preset-specific pre-scan filters: none
- shared pre-scan universe filter: active global `UniverseBuilder.filter()` rules only
- shared scan-context enrichment: `weekly_return_rank`, `quarterly_return_rank`, `eps_growth_rank`

## Selected Scans

| Scan name | Card display | Scan reference | Direct threshold summary |
|---|---|---|---|
| `97 Club` | `97 Club` | [../Scan/scan_05_97club.md](../Scan/scan_05_97club.md) | `club_97_hybrid_threshold=90.0`, `club_97_rs21_threshold=97.0` |
| `VCS 52 High` | `VCS 52 High` | [../Scan/scan_13_vcs_52_high.md](../Scan/scan_13_vcs_52_high.md) | `vcs_52_high_vcs_min=55.0`, `vcs_52_high_rs21_min=25.0`, `vcs_52_high_dist_max=-20.0` |
| `RS Acceleration` | `RS Accel` | [../Scan/scan_12_rs_acceleration.md](../Scan/scan_12_rs_acceleration.md) | `rs_acceleration_rs21_min=70.0`, plus hard-coded `rs21 > rs63` |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- historical duplicate threshold after preset load: `2`

## Scope Notes

- This legacy preset is not loaded by the active app.
- When it was active, it changed watchlist page controls only.
- It does not override global scan thresholds.
