# Watchlist Preset Spec: Base Breakout

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Base Breakout` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |
| Market environment | `Confirmed Uptrend` |

## Current Config Payload

```yaml
preset_name: Base Breakout
selected_scan_names: [VCS 52 High, Pocket Pivot, 97 Club, Three Weeks Tight]
selected_annotation_filters: [Trend Base, Resistance Tests >= 2]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: required_plus_optional_min
  required_scans: [VCS 52 High, Pocket Pivot]
  optional_scans: [97 Club, Three Weeks Tight]
  optional_min_hits: 1
preset_status: enabled
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
| `Three Weeks Tight` | `3WT` | [../Scan/scan_11_three_weeks_tight.md](../Scan/scan_11_three_weeks_tight.md) | `three_weeks_tight_vcs_min=50.0`; upstream `three_weeks_tight_pct_threshold=1.5` |
| `Pocket Pivot` | `Pocket Pivot` | [../Scan/scan_07_pocket_pivot.md](../Scan/scan_07_pocket_pivot.md) | no scan config keys; requires `close > sma50` and `pocket_pivot=true` |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`, `Resistance Tests >= 2`
- selected duplicate subfilters: none
- UI optional threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `required_plus_optional_min`; requires every scan in `VCS 52 High, Pocket Pivot` plus at least `1` hit from optional scans `97 Club, Three Weeks Tight`

## Scan Role Mapping

| Role | Scan | Rationale |
|---|---|---|
| Core | `VCS 52 High` | 52-week high proximity with volatility contraction proves a tight base exists near highs |
| Trigger | `Pocket Pivot` / `Three Weeks Tight` | PP detects demand via volume; 3WT confirms contraction completion via price |
| Confirmation | `97 Club` | Hybrid score ≥ 90 + RS21 ≥ 97 enforces top-tier leadership quality |

## Logic Structure

```
duplicate_rule.mode: required_plus_optional_min
required_scans: [VCS 52 High, Pocket Pivot]
optional_scans: [97 Club, Three Weeks Tight]
optional_min_hits: 1
→ ticker must hit every required scan and 1+ optional scan
```

Representative hit patterns:

- `VCS 52 High` + `Pocket Pivot` + `97 Club` → top leader volume breakout from tight base
- `VCS 52 High` + `Pocket Pivot` + `Three Weeks Tight` → volume breakout from ultra-tight contraction

## Setup Interpretation

- **Target phase**: base completion → breakout initiation
- **Why effective in Confirmed Uptrend**: market tailwind maximizes follow-through on leader breakouts from tight bases; risk/reward is optimal when volatility has contracted near highs

## Design Rationale

VCS 52 High guarantees the "tight structure near highs" condition. 97 Club filters for the highest quality leaders only. Pocket Pivot and Three Weeks Tight detect the breakout event from two independent angles (volume vs price contraction completion). No overlap with pullback, reclaim, or reversal presets.

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
