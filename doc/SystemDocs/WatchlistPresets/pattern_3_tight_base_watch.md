# Watchlist Preset Spec: Pattern 3 - Tight Base Watch

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Pattern 3 - Tight Base Watch` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Pattern 3 - Tight Base Watch
selected_scan_names: [VCS, Three Weeks Tight, Near 52W High]
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
| `VCS` | `VCS` | [../Scan/scan_06_vcs.md](../Scan/scan_06_vcs.md) | `vcs_min_threshold=60.0`, plus hard-coded `raw_rs21 > 60.0` |
| `Three Weeks Tight` | `3WT` | [../Scan/scan_11_three_weeks_tight.md](../Scan/scan_11_three_weeks_tight.md) | `three_weeks_tight_vcs_min=50.0`; upstream `three_weeks_tight_pct_threshold=1.5` |
| `Near 52W High` | `Near 52W High` | [../Scan/scan_10_near_52w_high.md](../Scan/scan_10_near_52w_high.md) | `near_52w_high_threshold_pct=5.0`, `near_52w_high_hybrid_min=70.0` |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- UI duplicate threshold after preset load: `2`

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
