# Scan Spec: LL-HL Structure 1st Pivot

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `LL-HL Structure 1st Pivot` |
| UI display name | `LL-HL 1st` |
| Implementation owner | `src/scan/rules.py::_scan_llhl_1st_pivot` |
| Output | `bool` |
| Direct scan config | `scan.llhl_1st_rs21_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    _raw_rs(row, 21) >= config.llhl_1st_rs21_min
    and row.get("structure_pivot_1st_break", False)
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `raw_rs21` / `rs21` | `src/scoring/rs.py` | `nan` | `>= llhl_1st_rs21_min` |
| `structure_pivot_1st_break` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.llhl_1st_rs21_min` | `60.0` | RS lower bound |

## Upstream Field Definitions

- `structure_pivot_1st_pivot = hl_price + (swing_high - hl_price) * 0.618`
- `structure_pivot_1st_break = (close > structure_pivot_1st_pivot) and (prev_close <= structure_pivot_1st_pivot)`
