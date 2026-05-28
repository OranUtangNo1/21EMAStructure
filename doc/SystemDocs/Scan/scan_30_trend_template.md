# Scan Spec: Trend Template

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Trend Template` |
| UI display name | `Trend Template` |
| Implementation owner | `src/scan/rules.py::_scan_trend_template` |
| Output | `bool` |
| Direct scan config | `scan.trend_template_price_score_min`, `scan.trend_template_rs_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Uses the precomputed Trend Template price-condition score from `IndicatorCalculator`.
- Adds RS confirmation through `raw_rs21` / `rs21`.
- All conditions are combined with `AND`.
- The scan is a watchlist-quality filter, not an entry timing signal.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("trend_template_price_score", 0) >= config.trend_template_price_score_min
    and pd.notna(_raw_rs(row, 21))
    and float(_raw_rs(row, 21)) >= config.trend_template_rs_min
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `trend_template_price_score` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0` | must meet configured minimum |
| `raw_rs21` / `rs21` | `src/scoring/rs.py::RSScorer.score` | `NaN` | must meet configured minimum |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.trend_template_price_score_min` | `7` | minimum number of satisfied price-template conditions |
| `scan.trend_template_rs_min` | `70.0` | minimum RS confirmation |

## Price-Template Conditions

`trend_template_price_score` counts these seven daily conditions:

- `close > sma150` and `close > sma200`
- `sma150 > sma200`
- `sma200_slope_1m_pct > 0`
- `sma50 > sma150` and `sma50 > sma200`
- `close > sma50`
- `dist_from_52w_low >= 30.0`
- `dist_from_52w_high >= -25.0`
