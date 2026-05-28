# Annotation Filter Spec: Stage 4 Avoid

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `Stage 4 Avoid` |
| Implementation owner | `src/scan/rules.py::_annotation_stage4_avoid` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
matched = bool(str(row.get("stage_label", "")) == "stage4_avoid")
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `stage_label` | `src/indicators/core.py::IndicatorCalculator.calculate` | empty string | must equal `stage4_avoid` |
