# Scan Spec: LL-HL Structure 2nd Pivot

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `LL-HL Structure 2nd Pivot` |
| UI display name | `LL-HL 2nd` |
| Implementation owner | `src/scan/rules.py::_scan_llhl_2nd_pivot` |
| Output | `bool` |
| Direct scan config | `scan.llhl_2nd_rs21_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    _raw_rs(row, 21) >= config.llhl_2nd_rs21_min
    and row.get("structure_pivot_2nd_break", False)
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `raw_rs21` / `rs21` | `src/scoring/rs.py` | `nan` | `>= llhl_2nd_rs21_min` |
| `structure_pivot_2nd_break` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.llhl_2nd_rs21_min` | `60.0` | RS lower bound |

## Upstream Field Definitions

- `structure_pivot_2nd_pivot = structure_pivot_swing_high`
- `structure_pivot_2nd_break = (close > structure_pivot_2nd_pivot) and (prev_close <= structure_pivot_2nd_pivot)`
