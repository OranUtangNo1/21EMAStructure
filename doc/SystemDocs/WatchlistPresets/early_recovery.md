# Watchlist Preset Spec: Early Recovery

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Early Recovery` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |
| Market environment | `Correction` |

## Current Config Payload

```yaml
preset_name: Early Recovery
selected_scan_names: [Trend Reversal Setup, Structure Pivot, VCS 52 Low, Volume Accumulation]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 2
preset_status: enabled
```

## Pre-Scan Context

- preset-specific pre-scan filters: none
- shared pre-scan universe filter: active global `UniverseBuilder.filter()` rules only
- shared scan-context enrichment: `weekly_return_rank`, `quarterly_return_rank`, `eps_growth_rank`

## Selected Scans

| Scan name | Card display | Scan reference | Direct threshold summary |
|---|---|---|---|
| `Trend Reversal Setup` | `Reversal Setup` | [../Scan/scan_20_trend_reversal_setup.md](../Scan/scan_20_trend_reversal_setup.md) | `reversal_dist_52w_low_max=40.0`, `reversal_dist_52w_high_min=-40.0`, `reversal_rs21_min=50.0`, plus hard-coded `sma50 <= sma200`, `sma50_slope_10d_pct > 0.0`, `pocket_pivot_count >= 1` |
| `Structure Pivot` | `Structure Pivot` | [../Scan/scan_21_structure_pivot.md](../Scan/scan_21_structure_pivot.md) | no config keys; requires `structure_pivot_long_active=true` (bullish LL→HL structure confirmed) |
| `VCS 52 Low` | `VCS 52 Low` | [../Scan/scan_14_vcs_52_low.md](../Scan/scan_14_vcs_52_low.md) | `vcs_52_low_vcs_min=60.0`, `vcs_52_low_rs21_min=80.0`, `vcs_52_low_dist_max=25.0`, `vcs_52_low_dist_from_52w_high_max=-65.0` |
| `Volume Accumulation` | `Volume Accumulation` | [../Scan/scan_15_volume_accumulation.md](../Scan/scan_15_volume_accumulation.md) | `vol_accum_ud_ratio_min=1.5`, `vol_accum_rel_vol_min=1.0`, plus hard-coded `daily_change_pct > 0.0` |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- UI duplicate threshold after preset load: `2`
- preset status: `enabled`
- duplicate rule: none; uses default `min_count`

## Scan Role Mapping

| Role | Scan | Rationale |
|---|---|---|
| Core | `Trend Reversal Setup` | SMA50 ≤ SMA200 but SMA50 turning up + close > SMA50 + PP present; structural reversal conditions |
| Core | `Structure Pivot` | Bullish LL→HL structure confirmed; bottom is forming higher lows |
| Confirmation | `VCS 52 Low` | Volatility contraction near 52-week lows with RS21 ≥ 80; quality tightening after damage |
| Confirmation | `Volume Accumulation` | U/D volume ratio shows institutional accumulation beginning |

## Logic Structure

```
duplicate_threshold: 2
→ ticker must hit ≥ 2 of [Trend Reversal Setup, Structure Pivot, VCS 52 Low, Volume Accumulation]
```

Representative hit patterns:

- `Trend Reversal Setup` + `Structure Pivot` → SMA structure reversal + HL confirmation (strongest bottoming signal)
- `Trend Reversal Setup` + `Volume Accumulation` → structural reversal with institutional accumulation
- `VCS 52 Low` + `Structure Pivot` → low-zone contraction + structural pivot (next-cycle leader candidate)
- `VCS 52 Low` + `Volume Accumulation` → low-zone contraction + institutional demand entering

## Setup Interpretation

- **Target phase**: late correction → early recovery; detecting the earliest structural change in beaten-down names
- **Why effective in Correction**: most stocks continue declining; those where SMA50 is turning up, higher lows are forming, volatility is contracting, and volume shows accumulation are the most likely next-cycle leaders
- **Very early detection**: this preset identifies candidates well before trend_base becomes true, making it complementary to all Uptrend and Under Pressure presets

## Design Rationale

Trend Reversal Setup's `sma50 <= sma200` condition is unique to this preset — all other presets require `trend_base` (close > sma50 + bullish weekly MA structure), which excludes dead-cross stocks entirely. Structure Pivot's LL→HL detection operates at the price structure level independent of MA state. VCS 52 Low requires the stock to be within 25% of the 52-week low and more than 65% below the 52-week high — the polar opposite of VCS 52 High used in Base Breakout. Volume Accumulation is shared with Trend Pullback but the co-occurring scans guarantee no ticker overlap (trend_base stocks vs dead-cross stocks).

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
