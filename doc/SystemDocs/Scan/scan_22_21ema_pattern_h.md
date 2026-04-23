# Scan Spec: 21EMA Pattern H

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `21EMA Pattern H` |
| UI display name | `21EMA PH` |
| Implementation owner | `src/scan/rules.py::_scan_21ema_pattern_h` |
| Output | `bool` |
| Direct scan config | none (v1 hard-coded thresholds) |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads only precomputed indicator fields.
- All conditions are combined with `AND`.
- Intended as a shallow pullback trigger scan for stocks holding near the 21EMA high band.
- This scan replaces the broad legacy `21EMA scan` for the strongest high-band pullback pattern.

## Canonical Boolean Definition

```python
matched = bool(
    0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
    and 0.3 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
    and row.get("atr_low_to_ema21_high", float("nan")) >= -0.2
    and row.get("high", 0.0) > row.get("prev_high", float("inf"))
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `atr_50sma_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.0 <= value <= 3.0` |
| `atr_21ema_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.3 <= value <= 1.0` |
| `atr_low_to_ema21_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `value >= -0.2` |
| `high` | latest price row | `0.0` | `value > prev_high` |
| `prev_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("inf")` | comparison target for `high` |

## Direct Config Dependencies

None. `_scan_21ema_pattern_h` uses hard-coded thresholds only in v1.

## Upstream Field Definitions

- `atr_50sma_zone = (close - sma50) / atr`
- `atr_21ema_zone = (close - ema21_close) / atr`
- `atr_low_to_ema21_high = (low - ema21_high) / atr`
- `ema21_high = EMA(high, 21)`
- `prev_high = high.shift(1)`

