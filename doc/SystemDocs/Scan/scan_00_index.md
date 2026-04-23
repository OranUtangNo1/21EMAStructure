# Scan Documentation Index

`doc/SystemDocs/Scan` is the source of truth for active watchlist scan definitions.
Each file in this folder must allow a developer to reproduce the scan boolean logic without reading prose-heavy design docs.

## Operating Rules

- One scan per document.
- The canonical rule must be documented as executable-style logic.
- Hard-coded thresholds and config-driven thresholds must be separated.
- Upstream fields must name their producer and fallback behavior.
- Legacy list terminology is out of scope for this folder.

## Required Sections For Every Scan Doc

1. `Canonical Metadata`
2. `Evaluation Context`
3. `Canonical Boolean Definition`
4. `Required Inputs`
5. `Direct Config Dependencies`
6. `Upstream Field Definitions`

## Common Evaluation Context

- Input unit: one latest row per ticker.
- The row is evaluated after `src/scan/rules.py::enrich_with_scan_context()`.
- All scan conditions are combined with `AND`.
- Missing field handling must be documented exactly as implemented by `row.get(..., default)`.
- Output contract: one boolean hit decision per ticker per scan.

## Source Files

- Scan rules: `src/scan/rules.py`
- Scan execution: `src/scan/runner.py`
- Indicator producers: `src/indicators/core.py`
- RS producer: `src/scoring/rs.py`
- VCS producer: `src/scoring/vcs.py`
- Hybrid producer: `src/scoring/hybrid.py`
- Defaults: `config/default/scan.yaml`

## Active Scan Specs

The default config currently enables `22` scan families.

| File | Canonical scan name | Implementation owner |
|---|---|---|
| [scan_02_4pct_bullish.md](scan_02_4pct_bullish.md) | `4% bullish` | `src/scan/rules.py::_scan_bullish_4pct` |
| [scan_04_momentum97.md](scan_04_momentum97.md) | `Momentum 97` | `src/scan/rules.py::_scan_momentum_97` |
| [scan_05_97club.md](scan_05_97club.md) | `97 Club` | `src/scan/rules.py::_scan_97_club` |
| [scan_07_pocket_pivot.md](scan_07_pocket_pivot.md) | `Pocket Pivot` | `src/scan/rules.py::_scan_pocket_pivot` |
| [scan_08_pp_count.md](scan_08_pp_count.md) | `PP Count` | `src/scan/rules.py::_scan_pp_count` |
| [scan_09_weekly20pct.md](scan_09_weekly20pct.md) | `Weekly 20% plus gainers` | `src/scan/rules.py::_scan_weekly_gainer` |
| [scan_10_near_52w_high.md](scan_10_near_52w_high.md) | `Near 52W High` | `src/scan/rules.py::_scan_near_52w_high` |
| [scan_11_three_weeks_tight.md](scan_11_three_weeks_tight.md) | `Three Weeks Tight` | `src/scan/rules.py::_scan_three_weeks_tight` |
| [scan_12_rs_acceleration.md](scan_12_rs_acceleration.md) | `RS Acceleration` | `src/scan/rules.py::_scan_rs_acceleration` |
| [scan_13_vcs_52_high.md](scan_13_vcs_52_high.md) | `VCS 52 High` | `src/scan/rules.py::_scan_vcs_52_high` |
| [scan_14_vcs_52_low.md](scan_14_vcs_52_low.md) | `VCS 52 Low` | `src/scan/rules.py::_scan_vcs_52_low` |
| [scan_15_volume_accumulation.md](scan_15_volume_accumulation.md) | `Volume Accumulation` | `src/scan/rules.py::_scan_volume_accumulation` |
| [scan_16_pullback_quality.md](scan_16_pullback_quality.md) | `Pullback Quality scan` | `src/scan/rules.py::_scan_pullback_quality` |
| [scan_17_reclaim.md](scan_17_reclaim.md) | `Reclaim scan` | `src/scan/rules.py::_scan_reclaim` |
| [scan_19_sustained_leadership.md](scan_19_sustained_leadership.md) | `Sustained Leadership` | `src/scan/rules.py::_scan_sustained_leadership` |
| [scan_20_trend_reversal_setup.md](scan_20_trend_reversal_setup.md) | `Trend Reversal Setup` | `src/scan/rules.py::_scan_trend_reversal_setup` |
| [scan_21_structure_pivot.md](scan_21_structure_pivot.md) | `Structure Pivot` | `src/scan/rules.py::_scan_structure_pivot` |
| [scan_22_21ema_pattern_h.md](scan_22_21ema_pattern_h.md) | `21EMA Pattern H` | `src/scan/rules.py::_scan_21ema_pattern_h` |
| [scan_23_21ema_pattern_l.md](scan_23_21ema_pattern_l.md) | `21EMA Pattern L` | `src/scan/rules.py::_scan_21ema_pattern_l` |
| [scan_24_llhl_1st_pivot.md](scan_24_llhl_1st_pivot.md) | `LL-HL Structure 1st Pivot` | `src/scan/rules.py::_scan_llhl_1st_pivot` |
| [scan_25_llhl_2nd_pivot.md](scan_25_llhl_2nd_pivot.md) | `LL-HL Structure 2nd Pivot` | `src/scan/rules.py::_scan_llhl_2nd_pivot` |
| [scan_26_llhl_ct_break.md](scan_26_llhl_ct_break.md) | `LL-HL Structure Trend Line Break` | `src/scan/rules.py::_scan_llhl_ct_break` |

## Disabled Default Scan Specs

These scan definitions remain documented and implemented, but `config/default/scan.yaml` disables them by default because their screening role overlaps with other active scans.

| File | Canonical scan name | Implementation owner |
|---|---|---|
| [scan_01_21ema.md](scan_01_21ema.md) | `21EMA scan` | `src/scan/rules.py::_scan_21ema` |
| [scan_03_vol_up.md](scan_03_vol_up.md) | `Vol Up` | `src/scan/rules.py::_scan_vol_up` |
| [scan_06_vcs.md](scan_06_vcs.md) | `VCS` | `src/scan/rules.py::_scan_vcs` |

## Out Of Scope

Post-scan annotation filters are not scans. Their current implementation source is `src/scan/rules.py::ANNOTATION_FILTER_REGISTRY`.

The active annotation set includes:

| Annotation filter | Canonical condition |
|---|---|
| `RS 21 >= 63` | `_raw_rs(row, 21) >= 63.0` |
| `High Est. EPS Growth` | `eps_growth_rank >= high_eps_growth_rank_threshold` |
| `PP Count (20d)` | `pp_count_window >= pp_count_annotation_min` |
| `Trend Base` | `trend_base == True` |
| `Fund Score > 70` | `fundamental_score >= 70.0` |
| `Resistance Tests >= 2` | `resistance_test_count >= 2` |
