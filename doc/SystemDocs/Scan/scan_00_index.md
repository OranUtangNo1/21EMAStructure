# Scan Documentation Index

`doc/SystemDocs/Scan/` documents the implemented scan families in `src/scan/rules.py::SCAN_RULE_REGISTRY`.
Use the per-scan files for boolean logic. Use the status matrix for the current runtime state.

## Purpose

- Keep one canonical document per scan.
- Separate exact scan logic from current enabled or disabled state.
- Keep scan docs stable even when runtime status changes in config.

## Common Evaluation Context

- Input unit: one latest row per ticker.
- The row is evaluated after `src/scan/rules.py::enrich_with_scan_context()`.
- All scan conditions are combined with `AND`.
- Missing field handling must match the documented `row.get(..., default)` behavior.
- Output contract: one boolean hit decision per ticker per scan.

## Source Files

- scan rules: `src/scan/rules.py`
- scan execution: `src/scan/runner.py`
- indicator producers: `src/indicators/core.py`
- defaults: `config/default/scan.yaml`

## Current Status Matrix

- [status_matrix.md](status_matrix.md)
- `Status` shows runtime enabled or disabled state.
- `Card` shows whether the scan is visible in Watchlist controls.
- `Startup` shows whether the scan is selected at app startup.

## Scan Specs

| File | Canonical scan name |
| --- | --- |
| [scan_01_21ema.md](scan_01_21ema.md) | `21EMA scan` |
| [scan_02_4pct_bullish.md](scan_02_4pct_bullish.md) | `4% bullish` |
| [scan_03_vol_up.md](scan_03_vol_up.md) | `Vol Up` |
| [scan_04_momentum97.md](scan_04_momentum97.md) | `Momentum 97` |
| [scan_05_97club.md](scan_05_97club.md) | `97 Club` |
| [scan_06_vcs.md](scan_06_vcs.md) | `VCS` |
| [scan_07_pocket_pivot.md](scan_07_pocket_pivot.md) | `Pocket Pivot` |
| [scan_08_pp_count.md](scan_08_pp_count.md) | `PP Count` |
| [scan_09_weekly20pct.md](scan_09_weekly20pct.md) | `Weekly 20% plus gainers` |
| [scan_10_near_52w_high.md](scan_10_near_52w_high.md) | `Near 52W High` |
| [scan_11_three_weeks_tight.md](scan_11_three_weeks_tight.md) | `Three Weeks Tight` |
| [scan_29_vcp_3t.md](scan_29_vcp_3t.md) | `VCP 3T` |
| [scan_12_rs_acceleration.md](scan_12_rs_acceleration.md) | `RS Acceleration` |
| [scan_13_vcs_52_high.md](scan_13_vcs_52_high.md) | `VCS 52 High` |
| [scan_14_vcs_52_low.md](scan_14_vcs_52_low.md) | `VCS 52 Low` |
| [scan_15_volume_accumulation.md](scan_15_volume_accumulation.md) | `Volume Accumulation` |
| [scan_16_pullback_quality.md](scan_16_pullback_quality.md) | `Pullback Quality scan` |
| [scan_17_reclaim.md](scan_17_reclaim.md) | `Reclaim scan` |
| [scan_19_sustained_leadership.md](scan_19_sustained_leadership.md) | `Sustained Leadership` |
| [scan_20_trend_reversal_setup.md](scan_20_trend_reversal_setup.md) | `Trend Reversal Setup` |
| [scan_21_structure_pivot.md](scan_21_structure_pivot.md) | `Structure Pivot` |
| [scan_22_21ema_pattern_h.md](scan_22_21ema_pattern_h.md) | `21EMA Pattern H` |
| [scan_23_21ema_pattern_l.md](scan_23_21ema_pattern_l.md) | `21EMA Pattern L` |
| [scan_24_llhl_1st_pivot.md](scan_24_llhl_1st_pivot.md) | `LL-HL Structure 1st Pivot` |
| [scan_25_llhl_2nd_pivot.md](scan_25_llhl_2nd_pivot.md) | `LL-HL Structure 2nd Pivot` |
| [scan_26_llhl_ct_break.md](scan_26_llhl_ct_break.md) | `LL-HL Structure Trend Line Break` |
| [scan_27_50sma_reclaim.md](scan_27_50sma_reclaim.md) | `50SMA Reclaim` |
| [scan_28_rs_new_high.md](scan_28_rs_new_high.md) | `RS New High` |

## Out Of Scope

Post-scan annotation filters are not scans. Their current implementation source is `src/scan/rules.py::ANNOTATION_FILTER_REGISTRY`.
