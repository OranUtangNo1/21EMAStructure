# Entry Signal Spec: Pocket Pivot Entry

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical signal name | `Pocket Pivot Entry` |
| Implementation owner | `src/signals/rules.py::_pocket_pivot_entry` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
matched = _as_bool(row.get("pocket_pivot")) and _gt(row.get("close"), row.get("sma50"))
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `pocket_pivot` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be true |
| `close` | price row | missing -> false via `_gt` | must be `> sma50` |
| `sma50` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gt` | reference line |
