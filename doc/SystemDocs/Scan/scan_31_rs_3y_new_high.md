# Scan Spec: RS 3Y New High

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `RS 3Y New High` |
| UI display name | `RS 3Y New High` |
| Implementation owner | `src/scan/rules.py::_scan_rs_3y_new_high` |
| Output | `bool` |
| Direct scan config | `scan.rs_3y_new_high_price_dist_max`, `scan.rs_3y_new_high_price_dist_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads precomputed 3-year RS-ratio new-high state plus price distance from 52-week high.
- All conditions are combined with `AND`.
- Intended to detect long-term RS leadership where RS is at a 3-year high while price has not yet fully reclaimed its 52-week high.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("rs_ratio_at_3y_high", False)
    and row.get("dist_from_52w_high", float("nan")) <= config.rs_3y_new_high_price_dist_max
    and row.get("dist_from_52w_high", float("nan")) >= config.rs_3y_new_high_price_dist_min
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `rs_ratio_at_3y_high` | `src/scoring/rs.py::RSScorer.score` | `False` | must be `True` |
| `dist_from_52w_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | within configured range |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.rs_3y_new_high_price_dist_max` | `-5.0` | price must be at or below this distance from 52-week high |
| `scan.rs_3y_new_high_price_dist_min` | `-35.0` | price must be at or above this distance from 52-week high |

## Upstream Field Definitions

- `rs_ratio = close / benchmark_close`
- `rs_ratio_3y_high = rs_ratio.rolling(756, min_periods=504).max()`
- `rs_ratio_at_3y_high = rs_ratio >= rs_ratio_3y_high * (1.0 - rs_new_high_tolerance / 100.0)`
- `dist_from_52w_high = ((close / high_52w) - 1.0) * 100.0`
