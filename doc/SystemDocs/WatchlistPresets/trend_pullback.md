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
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: required_plus_optional_min
  required_scans: [Reclaim scan]
  optional_scans: [Pullback Quality scan, RS Acceleration, Volume Accumulation]
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
| `Pullback Quality scan` | `PB Quality` | [../Scan/scan_16_pullback_quality.txt](../Scan/scan_16_pullback_quality.txt) | no config keys; hard-coded rule uses `atr_21ema_zone`, `atr_50sma_zone`, `weekly_return`, `dcr_percent`, drawdown, and volume-cooling bounds |
| `Reclaim scan` | `Reclaim` | [../Scan/scan_17_reclaim.txt](../Scan/scan_17_reclaim.txt) | no config keys; hard-coded rule uses reclaim-location, recent-pullback, and trigger-confirmation bounds |
| `RS Acceleration` | `RS Accel` | [../Scan/scan_12_rs_acceleration.md](../Scan/scan_12_rs_acceleration.md) | `rs_acceleration_rs21_min=70.0`, plus hard-coded `rs21 > rs63` and `trend_base=true` |
| `Volume Accumulation` | `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) | `vol_accum_ud_ratio_min=1.5`, `vol_accum_rel_vol_min=1.0`, plus hard-coded `daily_change_pct > 0.0` |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- UI duplicate threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `required_plus_optional_min`; requires every scan in `Reclaim scan` plus at least `1` hit from optional scans `Pullback Quality scan, RS Acceleration, Volume Accumulation`

## Scan Role Mapping

| Role | Scan | Rationale |
|---|---|---|
| Core | `Pullback Quality scan` | Proves orderly pullback structure: volume cooling, proper drawdown depth, 21EMA proximity |
| Trigger | `Reclaim scan` | Detects the 21EMA reclaim event with volume + cross + recent pullback evidence |
| Confirmation | `RS Acceleration` | RS21 > RS63 confirms relative strength is accelerating, not decaying |
| Confirmation | `Volume Accumulation` | U/D volume ratio confirms institutional demand backing the move |

## Logic Structure

```
duplicate_rule.mode: required_plus_optional_min
required_scans: [Reclaim scan]
optional_scans: [Pullback Quality scan, RS Acceleration, Volume Accumulation]
optional_min_hits: 1
→ ticker must hit every required scan and 1+ optional scan
```

Representative hit patterns:

- `Reclaim scan` + `Pullback Quality scan` → reclaim following orderly pullback
- `Reclaim scan` + `RS Acceleration` → reclaim event with RS acceleration
- `Reclaim scan` + `Volume Accumulation` → reclaim confirmed by demand

## Setup Interpretation

- **Target phase**: pullback → reclaim two-stage process
- **Why effective in Confirmed Uptrend**: healthy pullbacks to 21EMA occur naturally in uptrends; reclaim entries from this zone offer the most reliable swing re-entries with market tailwind supporting follow-through

## Design Rationale

Pullback Quality and Reclaim are temporally sequential (in-pullback → reclaim event), so Reclaim is required while Pullback Quality remains an optional confirmation with RS Acceleration and Volume Accumulation. This avoids requiring same-day overlap between the pullback and reclaim phases while still targeting MA-area pullback reentry rather than high-zone contraction breakout.

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
