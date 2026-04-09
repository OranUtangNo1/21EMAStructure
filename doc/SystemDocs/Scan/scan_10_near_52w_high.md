# Scan Spec: Near 52W High

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Near 52W High` |
| UI display name | `Near 52W High` |
| Implementation owner | `src/scan/rules.py::_scan_near_52w_high` |
| Output | `bool` |
| Direct scan config | `near_52w_high_threshold_pct`, `near_52w_high_hybrid_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads precomputed indicator fields and scan-layer scores.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    pd.notna(row.get("high_52w", float("nan")))
    and row.get("high_52w", 0.0) > 0.0
    and row.get("close", 0.0) >= row.get("high_52w", float("inf")) * (1.0 - config.near_52w_high_threshold_pct / 100.0)
    and row.get("hybrid_score", 0.0) >= config.near_52w_high_hybrid_min
    and row.get("trend_base", False)
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `high_52w` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` and `0.0` | must be present and positive; used for the 52-week-high distance check |
| `close` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | compared against the thresholded `high_52w` value |
| `hybrid_score` | `src/scoring/hybrid.py::HybridScoreCalculator.score` | `0.0` | `>= near_52w_high_hybrid_min` |
| `trend_base` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.near_52w_high_threshold_pct` | `5.0` | max distance from the 52-week high (%) |
| `scan.near_52w_high_hybrid_min` | `70.0` | minimum hybrid score |

## Upstream Field Definitions

- `high_52w = high.rolling(252).max()`
- `close` is the latest daily close from the indicator history
- `hybrid_score` is the configured weighted composite of RS, fundamental, and industry components
- `trend_base = (close > sma50) & (wma10_weekly > wma30_weekly)`
