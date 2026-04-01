# Scan Spec: Weekly 20% plus gainers

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Weekly 20% plus gainers` |
| UI display name | `Weekly 20%+ Gainers` |
| Implementation owner | `src/scan/rules.py::_scan_weekly_gainer` |
| Output | `bool` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- The scan uses one field and one threshold.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("weekly_return", 0.0) >= config.weekly_gainer_threshold
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `weekly_return` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `>= config.weekly_gainer_threshold` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.weekly_gainer_threshold` | `20.0` | lower bound for `weekly_return` |

## Upstream Field Definitions

- `weekly_return = close.pct_change(5) * 100.0`
