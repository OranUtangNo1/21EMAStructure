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
selected_scan_names: [Pullback Quality scan, 21EMA scan, RS Acceleration, Volume Accumulation]
selected_annotation_filters: [Trend Base]
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: required_plus_optional_min
  required_scans: [Pullback Quality scan, 21EMA scan]
  optional_scans: [RS Acceleration, Volume Accumulation]
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
| `Pullback Quality scan` | `PB Quality` | [../Scan/scan_16_pullback_quality.md](../Scan/scan_16_pullback_quality.md) | no config keys; hard-coded rule uses `atr_21ema_zone`, `atr_50sma_zone`, `weekly_return`, `dcr_percent`, drawdown, and volume-cooling bounds |
| `21EMA scan` | `21EMA` | [../Scan/scan_01_21ema.md](../Scan/scan_01_21ema.md) | no config keys; hard-coded rule uses `weekly_return`, `dcr_percent`, `atr_21ema_zone`, and `atr_50sma_zone` |
| `Volume Accumulation` | `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) | `vol_accum_ud_ratio_min=1.5`, `vol_accum_rel_vol_min=1.0`, plus hard-coded `daily_change_pct > 0.0` |
| `RS Acceleration` | `RS Accel` | [../Scan/scan_12_rs_acceleration.md](../Scan/scan_12_rs_acceleration.md) | `rs_acceleration_rs21_min=70.0`, plus hard-coded `rs21 > rs63` |

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`
- selected duplicate subfilters: none
- UI optional threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `required_plus_optional_min`; requires every scan in `Pullback Quality scan, 21EMA scan` plus at least `1` hit from optional scans `RS Acceleration, Volume Accumulation`

## Consolidation Notes

This preset absorbs the former `Pattern 2 - Strong Pullback Buy` by adding `21EMA scan`. PP Count from Pattern 2 was dropped as it is covered by `Momentum Surge`.

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
