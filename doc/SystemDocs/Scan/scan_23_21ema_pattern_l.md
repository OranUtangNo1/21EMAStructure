# Scan Spec: 21EMA Pattern L

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `21EMA Pattern L` |
| UI display name | `21EMA PL` |
| Implementation owner | `src/scan/rules.py::_scan_21ema_pattern_l` |
| Output | `bool` |
| Direct scan config | none (v1 hard-coded thresholds) |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads only precomputed indicator fields.
- All conditions are combined with `AND`.
- Intended as a deep pullback reclaim trigger scan for stocks that pierced the 21EMA low band intraday and recovered by close.
- This scan replaces the broad legacy `21EMA scan` for the low-band defense pattern.

## Canonical Boolean Definition

```python
matched = bool(
    0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
    and -0.5 <= row.get("atr_21ema_zone", float("nan")) <= -0.1
    and row.get("atr_low_to_ema21_low", float("nan")) < 0.0
    and row.get("atr_21emaL_zone", float("nan")) > 0.0
    and row.get("high", 0.0) > row.get("prev_high", float("inf"))
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `atr_50sma_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.0 <= value <= 3.0` |
| `atr_21ema_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `-0.5 <= value <= -0.1` |
| `atr_low_to_ema21_low` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `value < 0.0` |
| `atr_21emaL_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `value > 0.0` |
| `high` | latest price row | `0.0` | `value > prev_high` |
| `prev_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("inf")` | comparison target for `high` |

## Direct Config Dependencies

None. `_scan_21ema_pattern_l` uses hard-coded thresholds only in v1.

## Upstream Field Definitions

- `atr_50sma_zone = (close - sma50) / atr`
- `atr_21ema_zone = (close - ema21_close) / atr`
- `atr_low_to_ema21_low = (low - ema21_low) / atr`
- `atr_21emaL_zone = (close - ema21_low) / atr`
- `ema21_low = EMA(low, 21)`
- `prev_high = high.shift(1)`

