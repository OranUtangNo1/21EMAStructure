# Scan Documentation Index

`doc/SystemDocs/Scan/` documents the current active scan families used by the default OraTek workflow.
Use the per-scan files for boolean logic. Use the status matrix for current runtime visibility and startup selection.

## Purpose

- Keep one canonical document per active scan.
- Keep scan docs aligned with `config/default/scan.yaml`.
- Exclude disabled, recovery, bottom-fishing, and other non-current scan families from SystemDocs.

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
- `Status` shows active runtime state.
- `Card` shows whether the scan is visible in Watchlist controls.
- `Startup` shows whether the scan is selected at app startup.

## Scan Specs

| File | Canonical scan name |
| --- | --- |
| [scan_01_21ema.md](scan_01_21ema.md) | `21EMA scan` |
| [scan_02_4pct_bullish.md](scan_02_4pct_bullish.md) | `4% bullish` |
| [scan_04_momentum97.md](scan_04_momentum97.md) | `Momentum 97` |
| [scan_07_pocket_pivot.md](scan_07_pocket_pivot.md) | `Pocket Pivot` |
| [scan_08_pp_count.md](scan_08_pp_count.md) | `PP Count` |
| [scan_09_weekly20pct.md](scan_09_weekly20pct.md) | `Weekly 20% plus gainers` |
| [scan_29_vcp_3t.md](scan_29_vcp_3t.md) | `VCP 3T` |
| [scan_13_vcs_52_high.md](scan_13_vcs_52_high.md) | `VCS 52 High` |
| [scan_15_volume_accumulation.md](scan_15_volume_accumulation.md) | `Volume Accumulation` |
| [scan_16_pullback_quality.md](scan_16_pullback_quality.md) | `Pullback Quality scan` |
| [scan_17_reclaim.md](scan_17_reclaim.md) | `Reclaim scan` |
| [scan_22_21ema_pattern_h.md](scan_22_21ema_pattern_h.md) | `21EMA Pattern H` |
| [scan_23_21ema_pattern_l.md](scan_23_21ema_pattern_l.md) | `21EMA Pattern L` |
| [scan_24_llhl_1st_pivot.md](scan_24_llhl_1st_pivot.md) | `LL-HL Structure 1st Pivot` |
| [scan_25_llhl_2nd_pivot.md](scan_25_llhl_2nd_pivot.md) | `LL-HL Structure 2nd Pivot` |
| [scan_26_llhl_ct_break.md](scan_26_llhl_ct_break.md) | `LL-HL Structure Trend Line Break` |
| [scan_27_50sma_reclaim.md](scan_27_50sma_reclaim.md) | `50SMA Reclaim` |
| [scan_28_rs_new_high.md](scan_28_rs_new_high.md) | `RS New High` |
| [scan_31_rs_3y_new_high.md](scan_31_rs_3y_new_high.md) | `RS 3Y New High` |
| [scan_32_rs_leads_price_setup.md](scan_32_rs_leads_price_setup.md) | `RS Leads Price Setup` |
| [scan_30_trend_template.md](scan_30_trend_template.md) | `Trend Template` |
| [scan_33_fresh_stage2_breakout.md](scan_33_fresh_stage2_breakout.md) | `Fresh Stage 2 Breakout` |

## Out Of Scope

Post-scan annotation filters are not scans. Their current implementation source is `src/scan/rules.py::ANNOTATION_FILTER_REGISTRY`.
Stage 2 strictness is currently exposed through `Stage 2 Quality Score`, `Mature / Late Stage Risk Filter`, and `Industry Leadership Gate`.
