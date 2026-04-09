# Scan Spec: Fundamental Demand

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Fundamental Demand` |
| UI display name | `Fund Demand` |
| Implementation owner | `src/scan/rules.py::_scan_fundamental_demand` |
| Output | `bool` |
| Direct scan config | `scan.fund_demand_fundamental_min`, `scan.fund_demand_rs21_min`, `scan.fund_demand_rel_vol_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads precomputed score, RS, volume, and trend-base fields.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
raw_rs21 = _raw_rs(row, 21)

matched = bool(
    row.get("fundamental_score", 0.0) >= config.fund_demand_fundamental_min
    and raw_rs21 >= config.fund_demand_rs21_min
    and row.get("rel_volume", 0.0) >= config.fund_demand_rel_vol_min
    and row.get("daily_change_pct", 0.0) > 0.0
    and row.get("trend_base", False)
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `fundamental_score` | `src/scoring/fundamental.py::FundamentalScorer.score` | `0.0` | `>= fund_demand_fundamental_min` |
| `raw_rs21` with `rs21` fallback via `_raw_rs(row, 21)` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` | `>= fund_demand_rs21_min` |
| `rel_volume` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `>= fund_demand_rel_vol_min` |
| `daily_change_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `> 0.0` |
| `trend_base` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.fund_demand_fundamental_min` | `70.0` | lower bound for `fundamental_score` |
| `scan.fund_demand_rs21_min` | `60.0` | lower bound for 21-day RS |
| `scan.fund_demand_rel_vol_min` | `1.0` | lower bound for `rel_volume` |

## Upstream Field Definitions

- `fundamental_score` is the percentile-based composite fundamental score from `FundamentalScorer`
- `_raw_rs(row, 21)` uses `raw_rs21` when present and falls back to `rs21`
- `rel_volume` is the latest volume divided by the configured moving-average volume baseline
- `daily_change_pct = ((close / close.shift(1)) - 1.0) * 100.0`
- `trend_base = bool(close > sma50 and wma10_weekly > wma30_weekly)`
