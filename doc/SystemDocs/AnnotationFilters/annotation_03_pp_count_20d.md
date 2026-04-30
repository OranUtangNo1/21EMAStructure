# Annotation Filter Spec: PP Count (20d)

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `PP Count (20d)` |
| Accepted alias | `3+ Pocket Pivots (20d)` |
| Implementation owner | `src/scan/rules.py::_annotation_pp_count_20d` |
| Output | `bool` |
| Direct config dependencies | `scan.pp_count_annotation_min` |

## Canonical Boolean Definition

```python
matched = bool(row.get("pp_count_window", 0) >= config.pp_count_annotation_min)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `pp_count_window` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0` | compare against configured threshold |

## Direct Config Dependencies

| Config key | Default |
|---|---|
| `scan.pp_count_annotation_min` | `2` |
