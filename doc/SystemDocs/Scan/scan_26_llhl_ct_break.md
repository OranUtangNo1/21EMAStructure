# Scan Spec: LL-HL Structure Trend Line Break

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `LL-HL Structure Trend Line Break` |
| UI display name | `CT Break` |
| Implementation owner | `src/scan/rules.py::_scan_llhl_ct_break` |
| Output | `bool` |
| Direct scan config | none |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(row.get("ct_trendline_break", False))
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `ct_trendline_break` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

None. `_scan_llhl_ct_break` uses hard-coded rule terms only.

## Upstream Field Definitions

- `ct_trendline_break` is computed only when `structure_pivot_long_active == False`.
- Uses the two latest confirmed pivot highs from the configured structure-pivot length range.
- Safety condition: `latest_pivot_high < previous_pivot_high` must hold (descending resistance line only).
- `ct_trendline_break = (close > ct_trendline_value) and (prev_close <= prev_ct_trendline_value)`.
