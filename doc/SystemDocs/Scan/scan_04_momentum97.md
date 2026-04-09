# Scan Spec: Momentum 97

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Momentum 97` |
| UI display name | `Momentum 97` |
| Implementation owner | `src/scan/rules.py::_scan_momentum_97` |
| Output | `bool` |

## Evaluation Context

- Evaluated on one latest row after `src/scan/rules.py::enrich_with_scan_context`.
- `weekly_return_rank` and `quarterly_return_rank` are cross-sectional ranks over the current scan input snapshot.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("weekly_return_rank", 0.0) >= config.momentum_97_weekly_rank
    and row.get("quarterly_return_rank", 0.0) >= config.momentum_97_quarterly_rank
    and row.get("trend_base", False)
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `weekly_return_rank` | `src/scan/rules.py::enrich_with_scan_context` | `0.0` | `>= config.momentum_97_weekly_rank` |
| `quarterly_return_rank` | `src/scan/rules.py::enrich_with_scan_context` | `0.0` | `>= config.momentum_97_quarterly_rank` |
| `trend_base` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.momentum_97_weekly_rank` | `97.0` | lower bound for `weekly_return_rank` |
| `scan.momentum_97_quarterly_rank` | `85.0` | lower bound for `quarterly_return_rank` |

## Upstream Field Definitions

- `weekly_return = close.pct_change(5) * 100.0`
- `quarterly_return = close.pct_change(63) * 100.0`
- `weekly_return_rank = percent_rank(snapshot["weekly_return"])`
- `quarterly_return_rank = percent_rank(snapshot["quarterly_return"])`
- `percent_rank` owner: `src/utils.py::percent_rank`
- `trend_base = (close > sma50) & (wma10_weekly > wma30_weekly)`
