# Scan Spec: Sustained Leadership

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Sustained Leadership` |
| UI display name | `RS Leader` |
| Implementation owner | `src/scan/rules.py::_scan_sustained_leadership` |
| Output | `bool` |
| Direct scan config | `scan.sustained_rs21_min`, `scan.sustained_rs63_min`, `scan.sustained_rs126_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads multi-horizon RS fields and trend-base state.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
rs21 = _raw_rs(row, 21)
rs63 = row.get("rs63", float("nan"))
rs126 = row.get("rs126", float("nan"))

matched = bool(
    pd.notna(rs21)
    and float(rs21) >= config.sustained_rs21_min
    and pd.notna(rs63)
    and float(rs63) >= config.sustained_rs63_min
    and pd.notna(rs126)
    and float(rs126) >= config.sustained_rs126_min
    and row.get("trend_base", False)
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `raw_rs21` with `rs21` fallback via `_raw_rs(row, 21)` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` | `>= sustained_rs21_min` |
| `rs63` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` | `>= sustained_rs63_min` |
| `rs126` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` | `>= sustained_rs126_min` |
| `trend_base` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.sustained_rs21_min` | `80.0` | lower bound for 21-day RS |
| `scan.sustained_rs63_min` | `70.0` | lower bound for 63-day RS |
| `scan.sustained_rs126_min` | `60.0` | lower bound for 126-day RS |

## Upstream Field Definitions

- `_raw_rs(row, 21)` uses `raw_rs21` when present and falls back to `rs21`
- `rs63` and `rs126` are percentile-style relative-strength outputs from `RSScorer`
- `trend_base = bool(close > sma50 and wma10_weekly > wma30_weekly)`
