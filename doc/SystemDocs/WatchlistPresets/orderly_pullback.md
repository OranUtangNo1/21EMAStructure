# Watchlist Preset Spec: Orderly Pullback

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Orderly Pullback` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |

## Current Config Payload

```yaml
preset_name: Orderly Pullback
selected_scan_names: [Pullback Quality scan, 21EMA Pattern H, 21EMA Pattern L, RS Acceleration, Volume Accumulation]
selected_annotation_filters: [Trend Base]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: grouped_threshold
  required_scans: []
  optional_groups:
  - group_name: 21EMA Trigger
    scans: [21EMA Pattern H, 21EMA Pattern L]
    min_hits: 1
  - group_name: Quality / Strength Confirmation
    scans: [Pullback Quality scan, RS Acceleration, Volume Accumulation]
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
| `21EMA Pattern H` | `21EMA PH` | [../Scan/scan_22_21ema_pattern_h.md](../Scan/scan_22_21ema_pattern_h.md) | no config keys; hard-coded rule uses 50SMA distance, 21EMA(C) upper zone, 21EMA(H) low support, and previous-high breakout |
| `21EMA Pattern L` | `21EMA PL` | [../Scan/scan_23_21ema_pattern_l.md](../Scan/scan_23_21ema_pattern_l.md) | no config keys; hard-coded rule uses 50SMA distance, 21EMA(C) lower zone, 21EMA(L) intraday pierce, 21EMA(L) close reclaim, and previous-high breakout |
| `Volume Accumulation` | `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) | `vol_accum_ud_ratio_min=1.5`, `vol_accum_rel_vol_min=1.0`, plus hard-coded `daily_change_pct > 0.0` |
| `RS Acceleration` | `RS Accel` | [../Scan/scan_12_rs_acceleration.md](../Scan/scan_12_rs_acceleration.md) | `rs_acceleration_rs21_min=70.0`, plus hard-coded `rs21 > rs63` |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`
- selected duplicate subfilters: none
- UI optional threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `grouped_threshold`; no direct required scans, requires at least `1` hit from the `21EMA Trigger` group, and at least `1` hit from the `Quality / Strength Confirmation` group

## Consolidation Notes

This preset now replaces the retired broad `21EMA scan` with the two trigger-based 21EMA pattern scans. The grouped duplicate rule accepts either 21EMA pattern as the trigger-side confirmation and requires one hit from the quality/strength group (`Pullback Quality scan`, `RS Acceleration`, `Volume Accumulation`).

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
