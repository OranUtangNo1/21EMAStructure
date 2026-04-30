# Entry Signal Spec: Pullback Low-Risk Zone

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical signal name | `Pullback Low-Risk Zone` |
| Implementation owner | `src/signals/rules.py::_pullback_low_risk_zone` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
matched = (
    (_as_bool(row.get("atr_21ema_zone")) or _as_bool(row.get("atr_50sma_zone")))
    and _gt(row.get("rs21"), 50.0)
    and not _lt(row.get("dcr_percent"), 30.0)
)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `atr_21ema_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | falsey -> no support-zone signal | near-support proxy |
| `atr_50sma_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | falsey -> no support-zone signal | near-support proxy |
| `rs21` | `src/scoring/rs.py::RSScorer.score` | missing -> false via `_gt` | must be `> 50.0` |
| `dcr_percent` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> not low by `_lt` helper | must not be `< 30.0` |
