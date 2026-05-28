# Annotation Filter Spec: Trend Template

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `Trend Template` |
| Implementation owner | `src/scan/rules.py::_annotation_trend_template` |
| Output | `bool` |
| Direct config dependencies | `scan.trend_template_price_score_min`, `scan.trend_template_rs_min` |

## Canonical Boolean Definition

```python
matched = bool(
    row.get("trend_template_price_score", 0) >= config.trend_template_price_score_min
    and pd.notna(rs21)
    and float(rs21) >= config.trend_template_rs_min
)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `trend_template_price_score` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0` | must meet configured minimum |
| `raw_rs21` / `rs21` | `src/scoring/rs.py::RSScorer.score` | `NaN` | must meet configured minimum |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.trend_template_price_score_min` | `7` | minimum Trend Template price-condition count |
| `scan.trend_template_rs_min` | `70.0` | minimum 21-day RS percentile |
