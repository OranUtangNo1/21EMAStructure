# Scan Spec: 21EMA scan

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `21EMA scan` |
| UI display name | `21EMA` |
| Implementation owner | `src/scan/rules.py::_scan_21ema` |
| Output | `bool` |
| Direct scan config | none |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads only precomputed indicator fields.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
weekly_return = row.get("weekly_return", float("nan"))
matched = bool(
    weekly_return >= 0.0
    and weekly_return <= 15.0
    and row.get("dcr_percent", 0.0) > 20.0
    and -0.5 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
    and 0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `weekly_return` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.0 <= value <= 15.0` |
| `dcr_percent` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `> 20.0` |
| `atr_21ema_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `-0.5 <= value <= 1.0` |
| `atr_50sma_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.0 <= value <= 3.0` |

## Direct Config Dependencies

None. `_scan_21ema` uses hard-coded thresholds only.

## Upstream Field Definitions

- `weekly_return = close.pct_change(5) * 100.0`
- `dcr_percent = ((close - low) / (high - low)) * 100.0`, zero-width range is filled with `50.0`
- `atr_21ema_zone = (close - ema21_close) / atr`
- `atr_50sma_zone = (close - sma50) / atr`
