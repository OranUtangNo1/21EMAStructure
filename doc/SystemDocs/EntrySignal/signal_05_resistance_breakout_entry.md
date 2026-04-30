# Entry Signal Spec: Resistance Breakout Entry

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical signal name | `Resistance Breakout Entry` |
| Implementation owner | `src/signals/rules.py::_resistance_breakout_entry` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
matched = bool(
    _gte(row.get("resistance_test_count"), 2.0)
    and _gt(row.get("close"), row.get("resistance_level_lookback"))
    and _gte(row.get("breakout_body_ratio"), 0.6)
    and _gte(row.get("rel_volume"), 1.5)
)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `resistance_test_count` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gte` | must be `>= 2.0` |
| `close` | price row | missing -> false via `_gt` | must break resistance |
| `resistance_level_lookback` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gt` | breakout level |
| `breakout_body_ratio` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gte` | must be `>= 0.6` |
| `rel_volume` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gte` | must be `>= 1.5` |
