# Annotation Filter Spec: RS 21 >= 63

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `RS 21 >= 63` |
| Implementation owner | `src/scan/rules.py::_annotation_rs21_gte_63` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
rs21 = _raw_rs(row, 21)
matched = bool(pd.notna(rs21) and float(rs21) >= 63.0)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `raw_rs21` (fallback `rs21`) | `src/scoring/rs.py::RSScorer.score` | `float("nan")` via `_raw_rs` | must be `>= 63.0` |
