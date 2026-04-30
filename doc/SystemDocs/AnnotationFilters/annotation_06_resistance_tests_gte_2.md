# Annotation Filter Spec: Resistance Tests >= 2

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `Resistance Tests >= 2` |
| Implementation owner | `src/scan/rules.py::_annotation_resistance_tests_gte_2` |
| Output | `bool` |
| Direct config dependencies | none (threshold is hard-coded) |

## Canonical Boolean Definition

```python
matched = bool(row.get("resistance_test_count", 0.0) >= 2.0)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `resistance_test_count` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | must be `>= 2.0` |
