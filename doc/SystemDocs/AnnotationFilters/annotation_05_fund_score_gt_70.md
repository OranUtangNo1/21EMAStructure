# Annotation Filter Spec: Fund Score > 70

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `Fund Score > 70` |
| Implementation owner | `src/scan/rules.py::_annotation_fund_score_gt_70` |
| Output | `bool` |
| Direct config dependencies | none (threshold is hard-coded) |

## Canonical Boolean Definition

```python
matched = bool(row.get("fundamental_score", 0.0) >= 70.0)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `fundamental_score` | `src/scoring/fundamental.py::FundamentalScorer.score` | `0.0` | must be `>= 70.0` |
