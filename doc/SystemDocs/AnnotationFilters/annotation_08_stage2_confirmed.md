# Annotation Filter Spec: Stage 2 Confirmed

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `Stage 2 Confirmed` |
| Implementation owner | `src/scan/rules.py::_annotation_stage2_confirmed` |
| Output | `bool` |
| Direct config dependencies | `scan.stage2_price_score_min`, `scan.stage2_rs_min` |

## Canonical Boolean Definition

```python
matched = bool(
    str(row.get("stage_label", "")) == "stage2_candidate"
    and row.get("trend_template_price_score", 0) >= config.stage2_price_score_min
    and pd.notna(rs21)
    and float(rs21) >= config.stage2_rs_min
)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `stage_label` | `src/indicators/core.py::IndicatorCalculator.calculate` | empty string | must equal `stage2_candidate` |
| `trend_template_price_score` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0` | must meet configured minimum |
| `raw_rs21` / `rs21` | `src/scoring/rs.py::RSScorer.score` | `NaN` | must meet configured minimum |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.stage2_price_score_min` | `5` | minimum Trend Template price-condition count |
| `scan.stage2_rs_min` | `60.0` | minimum 21-day RS percentile |
