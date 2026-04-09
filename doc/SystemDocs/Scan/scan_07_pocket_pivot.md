# Scan Spec: Pocket Pivot

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Pocket Pivot` |
| UI display name | `Pocket Pivot` |
| Implementation owner | `src/scan/rules.py::_scan_pocket_pivot` |
| Output | `bool` |
| Direct scan config | none |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("close", 0.0) > row.get("sma50", float("inf"))
    and row.get("pocket_pivot", False)
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `close` | latest price row | `0.0` | `> sma50` |
| `sma50` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("inf")` | upper comparison target |
| `pocket_pivot` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

None. `_scan_pocket_pivot` uses hard-coded rule terms only.

## Upstream Field Definitions

- `sma50 = close.rolling(50).mean()`
- `prior_volume_high = volume.rolling(pocket_pivot_lookback).max().shift(1)`
- `pocket_pivot = (close > open) & (volume > prior_volume_high)`
- default `pocket_pivot_lookback = 10` under `indicators.pocket_pivot_lookback`
