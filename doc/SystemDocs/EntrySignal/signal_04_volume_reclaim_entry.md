# Entry Signal Spec: Volume Reclaim Entry

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical signal name | `Volume Reclaim Entry` |
| Implementation owner | `src/signals/rules.py::_volume_reclaim_entry` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
matched = (
    _gt(row.get("close"), row.get("sma50"))
    and _gte(row.get("rel_volume"), 1.4)
    and _gt(row.get("daily_change_pct"), 0.0)
)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `close` | price row | missing -> false via `_gt` | must be `> sma50` |
| `sma50` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gt` | reclaim reference |
| `rel_volume` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gte` | must be `>= 1.4` |
| `daily_change_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gt` | must be positive |
