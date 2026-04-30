# Annotation Filter Spec: Trend Base

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `Trend Base` |
| Implementation owner | `src/scan/rules.py::_annotation_trend_base` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
matched = bool(row.get("trend_base", False))
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `trend_base` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |
