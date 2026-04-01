# Scan Documentation Index

`doc/Scan` is the source of truth for active watchlist scan definitions.
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
- Defaults: `config/default.yaml`

## Active Scan Specs

| File | Canonical scan name | Implementation owner |
|---|---|---|
| [scan_01_21ema.md](scan_01_21ema.md) | `21EMA scan` | `src/scan/rules.py::_scan_21ema` |
| [scan_02_4pct_bullish.md](scan_02_4pct_bullish.md) | `4% bullish` | `src/scan/rules.py::_scan_bullish_4pct` |
| [scan_03_vol_up.md](scan_03_vol_up.md) | `Vol Up` | `src/scan/rules.py::_scan_vol_up` |
| [scan_04_momentum97.md](scan_04_momentum97.md) | `Momentum 97` | `src/scan/rules.py::_scan_momentum_97` |
| [scan_05_97club.md](scan_05_97club.md) | `97 Club` | `src/scan/rules.py::_scan_97_club` |
| [scan_06_vcs.md](scan_06_vcs.md) | `VCS` | `src/scan/rules.py::_scan_vcs` |
| [scan_07_pocket_pivot.md](scan_07_pocket_pivot.md) | `Pocket Pivot` | `src/scan/rules.py::_scan_pocket_pivot` |
| [scan_08_pp_count.md](scan_08_pp_count.md) | `PP Count` | `src/scan/rules.py::_scan_pp_count` |
| [scan_09_weekly20pct.md](scan_09_weekly20pct.md) | `Weekly 20% plus gainers` | `src/scan/rules.py::_scan_weekly_gainer` |

## Out Of Scope

Post-scan annotation filters are not scans. Their current implementation source is `src/scan/rules.py::ANNOTATION_FILTER_REGISTRY`.
