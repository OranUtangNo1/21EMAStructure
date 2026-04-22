# Watchlist Preset Spec: Trend Pullback

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Trend Pullback` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |
| Market environment | `Confirmed Uptrend` |

## Current Config Payload

```yaml
preset_name: Trend Pullback
selected_scan_names: [Reclaim scan, Pullback Quality scan, RS Acceleration, Volume Accumulation]
selected_annotation_filters: [Trend Base]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: [Reclaim scan]
  optional_groups:
  - group_name: Pullback Evidence
    scans: [Pullback Quality scan]
    min_hits: 1
  - group_name: Strength Confirmation
    scans: [RS Acceleration, Volume Accumulation]
    min_hits: 1
preset_status: enabled
```

## Pre-Scan Context

- preset-specific pre-scan filters: none
- shared pre-scan universe filter: active global `UniverseBuilder.filter()` rules only
- shared scan-context enrichment: `weekly_return_rank`, `quarterly_return_rank`, `eps_growth_rank`

## Selected Scans

| Scan name | Card display | Scan reference | Direct threshold summary |
|---|---|---|---|
| `Pullback Quality scan` | `PB Quality` | [../Scan/scan_16_pullback_quality.md](../Scan/scan_16_pullback_quality.md) | no config keys; hard-coded rule uses `atr_21ema_zone`, `atr_50sma_zone`, `weekly_return`, `dcr_percent`, drawdown, and volume-cooling bounds |
| `Reclaim scan` | `Reclaim` | [../Scan/scan_17_reclaim.md](../Scan/scan_17_reclaim.md) | no config keys; hard-coded rule uses reclaim-location, recent-pullback, and trigger-confirmation bounds |
| `RS Acceleration` | `RS Accel` | [../Scan/scan_12_rs_acceleration.md](../Scan/scan_12_rs_acceleration.md) | `rs_acceleration_rs21_min=70.0`, plus hard-coded `rs21 > rs63` |
| `Volume Accumulation` | `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) | `vol_accum_ud_ratio_min=1.5`, `vol_accum_rel_vol_min=1.0`, plus hard-coded `daily_change_pct > 0.0` |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`
- selected duplicate subfilters: none
- UI optional threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `grouped_threshold`; requires `Reclaim scan`, at least `1` hit from `Pullback Evidence`, and at least `1` hit from `Strength Confirmation`

## Scan Role Mapping

| Role | Scan | Rationale |
|---|---|---|
| Core | `Pullback Quality scan` | Proves orderly pullback structure: volume cooling, proper drawdown depth, 21EMA proximity |
| Trigger | `Reclaim scan` | Detects the 21EMA reclaim event with volume + cross + recent pullback evidence |
| Confirmation | `RS Acceleration` | RS21 > RS63 confirms relative strength is accelerating, not decaying |
| Confirmation | `Volume Accumulation` | U/D volume ratio confirms institutional demand backing the move |

## Logic Structure

```
duplicate_rule.mode: grouped_threshold
required_scans: [Reclaim scan]
optional_groups:
- group_name: Pullback Evidence
  scans: [Pullback Quality scan]
  min_hits: 1
- group_name: Strength Confirmation
  scans: [RS Acceleration, Volume Accumulation]
  min_hits: 1
ticker must hit Reclaim scan + Pullback Quality scan + one strength confirmation scan
```

Representative hit patterns:

- `Reclaim scan` + `Pullback Quality scan` + `RS Acceleration` -> reclaim with pullback evidence and RS acceleration
- `Reclaim scan` + `Pullback Quality scan` + `Volume Accumulation` -> reclaim with pullback evidence and demand confirmation

## Setup Interpretation

- **Target phase**: pullback -> reclaim two-stage process
- **Why effective in Confirmed Uptrend**: healthy pullbacks to 21EMA occur naturally in uptrends; reclaim entries from this zone offer reliable swing re-entries with market tailwind supporting follow-through

## Design Rationale

The rule keeps `Reclaim scan` as required and enforces `Pullback Quality scan` through a dedicated `Pullback Evidence` group. Strength confirmation remains flexible with `RS Acceleration` or `Volume Accumulation` in the second group.

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
