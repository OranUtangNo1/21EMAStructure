# Annotation Filter Spec: Stage 2 Quality Score

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `Stage 2 Quality Score` |
| Implementation owner | `src/scan/rules.py::_annotation_stage2_quality_score` |
| Output | `bool` |
| Direct config dependencies | `scan.stage2_price_score_min`, `scan.stage2_rs_min`, `scan.stage2_quality_min_score` |

## Canonical Boolean Definition

```python
matched = bool(
    _stage2_confirmed_pass(row, config)
    and _stage2_quality_score(row, config) >= config.stage2_quality_min_score
)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `stage_label` | `src/indicators/core.py::IndicatorCalculator.calculate` | empty string | Stage 2 confirmation |
| `trend_template_price_score` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0` | Stage 2 confirmation and quality score |
| `raw_rs21` / `rs21` | `src/scoring/rs.py::RSScorer.score` | `NaN` | Stage 2 confirmation and RS component |
| `raw_rs63` / `rs63` | `src/scoring/rs.py::RSScorer.score` | `NaN` | RS component when available |
| `sma150_slope_1m_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | slope component |
| `sma200_slope_1m_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | slope component |
| `dist_from_52w_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `-25.0` | location component |
| `dist_from_52w_low` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | location component |
| `ud_volume_ratio` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | demand component |
| `pp_count_window` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | demand component |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.stage2_price_score_min` | `5` | Stage 2 confirmation minimum |
| `scan.stage2_rs_min` | `60.0` | Stage 2 confirmation RS minimum |
| `scan.stage2_quality_min_score` | `75.0` | minimum composite quality score |
