# PP Count

## Canonical Metadata

- Canonical scan name: `PP Count`
- Implementation owner: `src/scan/rules.py::_scan_pp_count`
- Output type: boolean scan hit per ticker

## Evaluation Context

- Input unit: one latest row per ticker
- Evaluation occurs after `src/scan/rules.py::enrich_with_scan_context()`
- All conditions are combined with `AND`
- Missing values follow `row.get(..., default)` behavior exactly as implemented

## Canonical Boolean Definition

```python
row.get("pp_count_window", 0) >= config.pp_count_scan_min
and row.get("trend_base", False)
```

## Required Inputs

- `pp_count_window`
  - expected type: integer-like count
  - fallback used by implementation: `0`
- `trend_base`
  - expected type: boolean
  - fallback used by implementation: `False`

## Direct Config Dependencies

- `scan.pp_count_scan_min`

## Upstream Field Definitions

- `pp_count_window`
  - producer: `src/indicators/core.py`
  - definition: rolling sum of `pocket_pivot` over `indicators.pp_count_window_days`
- `trend_base`
  - producer: `src/indicators/core.py`
  - definition: `(close > sma50) and (wma10_weekly > wma30_weekly)`