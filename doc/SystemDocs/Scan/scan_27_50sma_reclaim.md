# Scan Spec: 50SMA Reclaim

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `50SMA Reclaim` |
| UI display name | `50SMA Reclaim` |
| Implementation owner | `src/scan/rules.py::_scan_50sma_reclaim` |
| Output | `bool` |
| Direct scan config | none (v1 hard-coded thresholds) |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads only precomputed indicator fields.
- All conditions are combined with `AND`.
- Intended as a reclaim trigger when price crosses back above 50SMA after a deeper pullback.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("sma50_slope_10d_pct", float("nan")) > 0.0
    and 0.0 <= row.get("atr_50sma_zone", float("nan")) <= 1.0
    and row.get("close_crossed_above_sma50", False)
    and row.get("min_atr_50sma_zone_5d", float("nan")) <= -0.25
    and row.get("dcr_percent", 0.0) >= 60.0
    and row.get("volume_ratio_20d", float("nan")) >= 1.10
    and 3.0 <= row.get("drawdown_from_20d_high_pct", float("nan")) <= 20.0
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `sma50_slope_10d_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `> 0.0` |
| `atr_50sma_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.0 <= value <= 1.0` |
| `close_crossed_above_sma50` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |
| `min_atr_50sma_zone_5d` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `<= -0.25` |
| `dcr_percent` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `>= 60.0` |
| `volume_ratio_20d` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `>= 1.10` |
| `drawdown_from_20d_high_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `3.0 <= value <= 20.0` |

## Direct Config Dependencies

None. `_scan_50sma_reclaim` uses hard-coded thresholds only in v1.

## Upstream Field Definitions

- `sma50_slope_10d_pct = ((sma50 / sma50.shift(10)) - 1.0) * 100.0`
- `atr_50sma_zone = (close - sma50) / atr`
- `close_crossed_above_sma50 = (close > sma50) & (close.shift(1) <= sma50.shift(1))`
- `min_atr_50sma_zone_5d = atr_50sma_zone.rolling(5).min()`
- `dcr_percent = ((close - low) / (high - low)) * 100.0`
- `volume_ratio_20d = volume / volume.rolling(20).mean()`
- `drawdown_from_20d_high_pct = ((close.rolling(20).max() - close) / close.rolling(20).max()) * 100.0`
