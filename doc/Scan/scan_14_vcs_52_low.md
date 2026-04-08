# Scan Spec: VCS 52 Low

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `VCS 52 Low` |
| UI display name | `VCS 52 Low` |
| Implementation owner | `src/scan/rules.py::_scan_vcs_52_low` |
| Output | `bool` |
| Direct scan config | `scan.vcs_52_low_vcs_min`, `scan.vcs_52_low_rs21_min`, `scan.vcs_52_low_dist_max`, `scan.vcs_52_low_dist_from_52w_high_max` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads a precomputed VCS score, 21-day RS, distance from the 52-week low, and distance from the 52-week high.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("vcs", 0.0) >= config.vcs_52_low_vcs_min
    and _raw_rs(row, 21) > config.vcs_52_low_rs21_min
    and row.get("dist_from_52w_low", float("nan")) <= config.vcs_52_low_dist_max
    and row.get("dist_from_52w_high", float("nan")) <= config.vcs_52_low_dist_from_52w_high_max
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `vcs` | `src/scoring/vcs.py::VCSCalculator.add_scores` | `0.0` | `>= vcs_52_low_vcs_min` |
| `raw_rs21` with `rs21` fallback via `_raw_rs(row, 21)` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` | `> vcs_52_low_rs21_min` |
| `dist_from_52w_low` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `<= vcs_52_low_dist_max` |
| `dist_from_52w_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `<= vcs_52_low_dist_from_52w_high_max` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.vcs_52_low_vcs_min` | `60.0` | minimum VCS score |
| `scan.vcs_52_low_rs21_min` | `80.0` | minimum raw RS21 threshold, using a strict `>` comparison |
| `scan.vcs_52_low_dist_max` | `25.0` | upper bound for distance above the 52-week low |
| `scan.vcs_52_low_dist_from_52w_high_max` | `-65.0` | upper bound for distance from the 52-week high |

## Upstream Field Definitions

- `dist_from_52w_low = ((close / low_52w) - 1.0) * 100.0`
- `dist_from_52w_high = ((close / high_52w) - 1.0) * 100.0`
- `low_52w = low.rolling(252).min()`
- `high_52w = high.rolling(252).max()`
- `_raw_rs(row, 21)` uses `raw_rs21` when present and falls back to `rs21`
- `vcs` is the configured contraction-quality score from `VCSCalculator`
