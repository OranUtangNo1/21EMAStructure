# Scan Spec: Pullback Quality scan

## Canonical Metadata

| Item                 | Value                                       |
| -------------------- | ------------------------------------------- |
| Canonical name       | `Pullback Quality scan`                     |
| UI display name      | `PB Quality`                                |
| Implementation owner | `src/scan/rules.py::_scan_pullback_quality` |
| Output               | `bool`                                      |
| Direct scan config   | none (v1 hard-coded thresholds)             |

## Evaluation Context

* Evaluated on one latest row after `enrich_with_scan_context()`.
* Reads only precomputed indicator fields.
* All conditions are combined with `AND`.
* Intended as a **strict orderly-pullback-quality scan**.
* This scan is responsible for the **pullback-quality judgment that was separated from the stricter draft of 21EMA scan**.
* This scan is **not** a reclaim / trigger scan.
* This scan is **narrower** than `21EMA scan`, and is intended to filter a broad 21EMA candidate list down to higher-quality pullbacks.

## Canonical Boolean Definition

```python
weekly_return = row.get("weekly_return", float("nan"))
matched = bool(
    row.get("ema21_slope_5d_pct", float("nan")) > 0.0
    and row.get("sma50_slope_10d_pct", float("nan")) > 0.0
    and -1.25 <= row.get("atr_21ema_zone", float("nan")) <= 0.25
    and 0.75 <= row.get("atr_50sma_zone", float("nan")) <= 3.5
    and -8.0 <= weekly_return <= 3.0
    and row.get("dcr_percent", 0.0) >= 50.0
    and 3.0 <= row.get("drawdown_from_20d_high_pct", float("nan")) <= 15.0
    and row.get("volume_ma5_to_ma20_ratio", float("nan")) <= 0.85
)
```

Intent / Scan Role

This scan is designed to identify orderly pullbacks in already-strong stocks.

A matched ticker should generally satisfy all of the following ideas:

The stock is still in an intact uptrend.
The stock has pulled back toward the 21EMA area, but has not broken the broader structure.
The pullback has some depth, but is still within a reasonable range.
Selling pressure appears controlled rather than disorderly.
Volume has cooled during the pullback, indicating a healthier reset.

This means the scan is intentionally trying to remove:

loose / broken pullbacks,
stocks that are too extended above the 21EMA,
stocks that are already reclaiming and should instead be handled by Reclaim scan.
Condition Design Notes
Trend integrity
ema21_slope_5d_pct > 0.0
sma50_slope_10d_pct > 0.0

These conditions ensure the moving averages are not flattening or rolling over.

Pullback location
-1.25 <= atr_21ema_zone <= 0.25
0.75 <= atr_50sma_zone <= 3.5

These conditions define the acceptable pullback area:

close enough to the 21EMA to qualify as a pullback,
still comfortably above the 50SMA,
not already too far back above the 21EMA.
Pullback depth
3.0 <= drawdown_from_20d_high_pct <= 15.0
-8.0 <= weekly_return <= 3.0

These conditions ensure the stock has actually pulled back, while avoiding:

no real reset,
excessively deep weakness.
Price action quality
dcr_percent >= 50.0

This avoids weak closes near the daily low and favors bars that show at least some intraday support.

Volume contraction
volume_ma5_to_ma20_ratio <= 0.85

This is the key condition that turns the scan from “21EMA location” into “pullback quality”.
The goal is to capture pullbacks where selling pressure is calming down rather than expanding.

Prior demand footprint

Required Inputs
Field	Producer	Missing/default used by scan	Scan use
weekly_return	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	-8.0 <= value <= 3.0
dcr_percent	src/indicators/core.py::IndicatorCalculator.calculate	0.0	>= 50.0
atr_21ema_zone	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	-1.25 <= value <= 0.25
atr_50sma_zone	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	0.75 <= value <= 3.5
ema21_slope_5d_pct	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	> 0.0
sma50_slope_10d_pct	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	> 0.0
drawdown_from_20d_high_pct	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	3.0 <= value <= 15.0
volume_ma5_to_ma20_ratio	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	<= 0.85
Direct Config Dependencies

None. _scan_pullback_quality uses hard-coded thresholds only in v1.

Upstream Field Definitions
weekly_return = close.pct_change(5) * 100.0
dcr_percent = ((close - low) / (high - low)) * 100.0, zero-width range is filled with 50.0
atr_21ema_zone = (close - ema21_close) / atr
atr_50sma_zone = (close - sma50) / atr
ema21_slope_5d_pct = ((ema21_close / ema21_close.shift(5)) - 1.0) * 100.0
sma50_slope_10d_pct = ((sma50 / sma50.shift(10)) - 1.0) * 100.0
rolling_20d_close_high = close.rolling(20).max()
drawdown_from_20d_high_pct = ((rolling_20d_close_high - close) / rolling_20d_close_high) * 100.0
volume_ma5 = volume.rolling(5).mean()
volume_ma20 = volume.rolling(20).mean()
volume_ma5_to_ma20_ratio = volume_ma5 / volume_ma20
