# Scan Spec: Pocket Pivot

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Pocket Pivot` |
| UI display name | `Pocket Pivot` |
| Implementation owner | `src/scan/rules.py::_scan_pocket_pivot` |
| Output | `bool` |
| Direct scan config | `scan.pocket_pivot_pp_count_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(row.get("pp_count_window", 0) >= config.pocket_pivot_pp_count_min)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `pp_count_window` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0` | `>= pocket_pivot_pp_count_min` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.pocket_pivot_pp_count_min` | `1` | minimum recent pocket-pivot count |

## Upstream Field Definitions

- `prior_volume_high = volume.rolling(pocket_pivot_lookback).max().shift(1)`
- `pocket_pivot = (close > open) & (volume > prior_volume_high)`
- `pp_count_window = pocket_pivot.rolling(pp_count_window_days).sum().fillna(0).astype(int)`
- default `pocket_pivot_lookback = 10`, `pp_count_window_days = 20` under `indicators.*`
