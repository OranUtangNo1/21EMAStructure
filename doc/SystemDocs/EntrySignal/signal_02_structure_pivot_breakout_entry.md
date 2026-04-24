# Entry Signal Spec: Structure Pivot Breakout Entry

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical signal name | `Structure Pivot Breakout Entry` |
| Implementation owner | `src/signals/rules.py::_structure_pivot_breakout_entry` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
matched = _as_bool(row.get("structure_pivot_long_breakout_first_day"))
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `structure_pivot_long_breakout_first_day` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be true |
