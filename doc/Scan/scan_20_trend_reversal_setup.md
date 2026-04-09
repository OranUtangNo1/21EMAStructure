# Scan Spec: Trend Reversal Setup

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Trend Reversal Setup` |
| UI display name | `Reversal Setup` |
| Implementation owner | `src/scan/rules.py::_scan_trend_reversal_setup` |
| Output | `bool` |
| Direct scan config | `scan.reversal_dist_52w_low_max`, `scan.reversal_dist_52w_high_min`, `scan.reversal_rs21_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads price-vs-moving-average state, SMA slope, 52-week distance fields, RS, and pocket-pivot count.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
pocket_pivot_count = row.get("pp_count_30d", row.get("pp_count_window", 0))
raw_rs21 = _raw_rs(row, 21)

matched = bool(
    row.get("close", 0.0) > row.get("sma50", float("inf"))
    and row.get("sma50", float("inf")) <= row.get("sma200", float("inf"))
    and row.get("sma50_slope_10d_pct", float("nan")) > 0.0
    and row.get("dist_from_52w_low", float("nan")) <= config.reversal_dist_52w_low_max
    and row.get("dist_from_52w_high", float("nan")) >= config.reversal_dist_52w_high_min
    and raw_rs21 >= config.reversal_rs21_min
    and pocket_pivot_count >= 1
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `close` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `> sma50` |
| `sma50` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("inf")` | compared against `close` and `sma200` |
| `sma200` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("inf")` | upper bound for `sma50` |
| `sma50_slope_10d_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `> 0.0` |
| `dist_from_52w_low` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `<= reversal_dist_52w_low_max` |
| `dist_from_52w_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `>= reversal_dist_52w_high_min` |
| `raw_rs21` with `rs21` fallback via `_raw_rs(row, 21)` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` | `>= reversal_rs21_min` |
| `pp_count_30d` with `pp_count_window` fallback | `src/indicators/core.py::IndicatorCalculator.calculate` | `0` | `>= 1` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.reversal_dist_52w_low_max` | `40.0` | upper bound for distance from the 52-week low |
| `scan.reversal_dist_52w_high_min` | `-40.0` | lower bound for distance from the 52-week high |
| `scan.reversal_rs21_min` | `50.0` | lower bound for 21-day RS |

## Upstream Field Definitions

- `sma50 = close.rolling(50).mean()`
- `sma200 = close.rolling(200).mean()`
- `sma50_slope_10d_pct = ((sma50 / sma50.shift(10)) - 1.0) * 100.0`
- `dist_from_52w_low = ((close / low_52w) - 1.0) * 100.0`
- `dist_from_52w_high = ((close / high_52w) - 1.0) * 100.0`
- `_raw_rs(row, 21)` uses `raw_rs21` when present and falls back to `rs21`
- pocket-pivot count comes from `pp_count_30d` when present, otherwise `pp_count_window`
