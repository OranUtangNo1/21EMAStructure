# Annotation Filter Spec: Industry Leadership Gate

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `Industry Leadership Gate` |
| Implementation owner | `src/scan/rules.py::_annotation_industry_leadership_gate` |
| Output | `bool` |
| Direct config dependencies | `scan.industry_leadership_min_score` |

## Canonical Boolean Definition

```python
industry_score = row.get("industry_score", float("nan"))
matched = bool(pd.notna(industry_score) and float(industry_score) >= config.industry_leadership_min_score)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `industry_score` | `src/scoring/industry.py::IndustryScorer` | `NaN` | must meet configured minimum |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.industry_leadership_min_score` | `70.0` | minimum industry leadership score |
