# Annotation Filter Spec: Mature / Late Stage Risk Filter

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `Mature / Late Stage Risk Filter` |
| Implementation owner | `src/scan/rules.py::_annotation_mature_late_stage_risk_filter` |
| Output | `bool` |
| Direct config dependencies | `scan.stage2_price_score_min`, `scan.stage2_rs_min`, `scan.mature_stage_max_days_since_start`, `scan.mature_stage_dist_from_52w_low_max`, `scan.mature_stage_atr_from_50sma_max` |

## Canonical Boolean Definition

```python
matched = bool(
    _stage2_confirmed_pass(row, config)
    and _mature_stage_risk_pass(row, config)
)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `stage_label` | `src/indicators/core.py::IndicatorCalculator.calculate` | empty string | Stage 2 confirmation and Stage 4 rejection |
| `trend_template_price_score` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0` | Stage 2 confirmation |
| `raw_rs21` / `rs21` | `src/scoring/rs.py::RSScorer.score` | `NaN` | Stage 2 confirmation |
| `days_since_stage2_start` | `src/indicators/core.py::IndicatorCalculator.calculate` | `NaN` | maturity guard |
| `dist_from_52w_low` | `src/indicators/core.py::IndicatorCalculator.calculate` | `NaN` | extension guard |
| `atr_pct_from_50sma` | `src/indicators/core.py::IndicatorCalculator.calculate` | `NaN` | 50SMA extension guard |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.stage2_price_score_min` | `5` | Stage 2 confirmation minimum |
| `scan.stage2_rs_min` | `60.0` | Stage 2 confirmation RS minimum |
| `scan.mature_stage_max_days_since_start` | `252` | late-stage duration guard |
| `scan.mature_stage_dist_from_52w_low_max` | `250.0` | maximum extension from 52-week low |
| `scan.mature_stage_atr_from_50sma_max` | `7.0` | maximum ATR distance from 50SMA |
