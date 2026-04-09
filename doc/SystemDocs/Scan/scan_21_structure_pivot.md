# Scan Spec: Structure Pivot

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Structure Pivot` |
| UI display name | `Structure Pivot` |
| Implementation owner | `src/scan/rules.py::_scan_structure_pivot` |
| Output | `bool` |
| Direct scan config | none |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads the bullish LL-HL structure flag produced by `src/indicators/core.py::IndicatorCalculator.calculate`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(row.get("structure_pivot_long_active", False))
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `structure_pivot_long_active` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | bullish LL-HL structure must be active |

## Direct Config Dependencies

- none

## Upstream Field Definitions

- `structure_pivot_long_active` is produced from a multi-length LL-HL structure scan over daily history.
- Lengths are controlled by `indicators.structure_pivot_min_length` and `indicators.structure_pivot_max_length`.
- Priority selection is controlled by `indicators.structure_pivot_priority_mode`.
- A long structure becomes active when a confirmed pivot low is followed by a higher pivot low and a valid pivot price exists between them.
- The latest structure is invalidated if current low breaks below the higher low before breakout.
