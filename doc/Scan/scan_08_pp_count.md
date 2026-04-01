# Scan Spec: PP Count

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `PP Count` |
| UI display name | `3+ Pocket Pivots (30d)` |
| Implementation owner | `src/scan/rules.py::_scan_pp_count` |
| Output | `bool` |
| Direct scan config | none |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("pp_count_30d", 0) > 3
    and row.get("trend_base", False)
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `pp_count_30d` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0` | `> 3` |
| `trend_base` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

None. The `> 3` threshold is hard-coded in `_scan_pp_count`.

Upstream producer config that affects `pp_count_30d`:
- `indicators.pp_count_window_days = 30`
- `indicators.pocket_pivot_lookback = 10`

## Upstream Field Definitions

- `prior_volume_high = volume.rolling(pocket_pivot_lookback).max().shift(1)`
- `pocket_pivot = (close > open) & (volume > prior_volume_high)`
- `pp_count_30d = pocket_pivot.rolling(pp_count_window_days).sum().fillna(0).astype(int)`
- `trend_base = (close > sma50) & (wma10_weekly > wma30_weekly)`
