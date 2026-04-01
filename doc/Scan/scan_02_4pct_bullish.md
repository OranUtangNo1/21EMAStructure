# Scan Spec: 4% bullish

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `4% bullish` |
| UI display name | `4% bullish` |
| Implementation owner | `src/scan/rules.py::_scan_bullish_4pct` |
| Output | `bool` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- `_raw_rs(row, 21)` reads `raw_rs21` first and falls back to `rs21`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
raw_rs21 = _raw_rs(row, 21)
matched = bool(
    row.get("rel_volume", 0.0) >= config.relative_volume_bullish_threshold
    and row.get("daily_change_pct", 0.0) >= config.daily_gain_bullish_threshold
    and row.get("from_open_pct", 0.0) > 0.0
    and raw_rs21 > 60.0
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `rel_volume` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `>= config.relative_volume_bullish_threshold` |
| `daily_change_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `>= config.daily_gain_bullish_threshold` |
| `from_open_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `> 0.0` |
| `raw_rs21` | `src/scoring/rs.py::RSScorer.score` | fallback to `rs21`, then `nan` | `> 60.0` |
| `rs21` | `src/scoring/rs.py::RSScorer.score` | `nan` | fallback only |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.relative_volume_bullish_threshold` | `1.0` | lower bound for `rel_volume` |
| `scan.daily_gain_bullish_threshold` | `4.0` | lower bound for `daily_change_pct` |

Hard-coded threshold in code:
- `raw_rs21 > 60.0`

## Upstream Field Definitions

- `rel_volume = volume / avg_volume_50d`
- `daily_change_pct = close.pct_change() * 100.0`
- `from_open_pct = (close - open) / open * 100.0`
- `raw_rs21` is the 21-bar trailing percentile score of `price_ratio = stock_close / benchmark_close` within the symbol's own ratio history. Owner: `src/scoring/rs.py::RSScorer._score_ratio_window`.
