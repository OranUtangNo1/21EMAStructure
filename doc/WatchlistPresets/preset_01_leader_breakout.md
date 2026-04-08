# Watchlist Preset Spec: Leader Breakout

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Leader Breakout` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Leader Breakout
selected_scan_names: [97 Club, VCS 52 High, Three Weeks Tight]
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
| `97 Club` | `97 Club` | [../Scan/scan_05_97club.md](../Scan/scan_05_97club.md) | `club_97_hybrid_threshold=90.0`, `club_97_rs21_threshold=97.0` |
| `VCS 52 High` | `VCS 52 High` | [../Scan/scan_13_vcs_52_high.md](../Scan/scan_13_vcs_52_high.md) | `vcs_52_high_vcs_min=55.0`, `vcs_52_high_rs21_min=25.0`, `vcs_52_high_dist_max=-20.0`, `vcs_52_high_require_trend_base=true` |
| `Three Weeks Tight` | `3WT` | [../Scan/scan_11_three_weeks_tight.md](../Scan/scan_11_three_weeks_tight.md) | `three_weeks_tight_vcs_min=50.0`; upstream `three_weeks_tight_pct_threshold=1.5` |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- UI duplicate threshold after preset load: `2`

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
