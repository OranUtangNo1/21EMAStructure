# Scan Spec: Reclaim scan

## Canonical Metadata

| Item                 | Value                              |
| -------------------- | ---------------------------------- |
| Canonical name       | `Reclaim scan`                     |
| UI display name      | `Reclaim`                          |
| Implementation owner | `src/scan/rules.py::_scan_reclaim` |
| Output               | `bool`                             |
| Direct scan config   | none (v1 hard-coded thresholds)    |

## Evaluation Context

* Evaluated on one latest row after `enrich_with_scan_context()`.
* Reads only precomputed indicator fields.
* All conditions are combined with `AND`.
* Intended as a **reclaim / restart trigger scan** after a valid pullback.
* This scan is responsible for the **restart / reclaim judgment that was separated from the older 21EMA pullback draft**.
* This scan should generally be used **after or alongside** `Pullback Quality scan` or the trigger-oriented 21EMA pattern scans.
* This scan is not intended to represent a broad pullback candidate list; it is intended to identify **the reclaim event itself**.

## Canonical Boolean Definition

```python
weekly_return = row.get("weekly_return", float("nan"))
matched = bool(
    row.get("ema21_slope_5d_pct", float("nan")) > 0.0
    and row.get("sma50_slope_10d_pct", float("nan")) > 0.0
    and 0.0 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
    and 0.75 <= row.get("atr_50sma_zone", float("nan")) <= 4.0
    and -3.0 <= weekly_return <= 10.0
    and row.get("dcr_percent", 0.0) >= 60.0
    and 2.0 <= row.get("drawdown_from_20d_high_pct", float("nan")) <= 12.0
    and row.get("volume_ratio_20d", float("nan")) >= 1.10
    and row.get("close_crossed_above_ema21", False)
    and row.get("min_atr_21ema_zone_5d", float("nan")) <= -0.25
)
```

Intent / Scan Role

This scan is designed to identify the reclaim day after an orderly pullback.

A matched ticker should generally satisfy all of the following ideas:

The stock is still in an intact bullish structure.
The stock had recently pulled into / under the 21EMA area.
The stock has now moved back above the 21EMA.
The reclaim is happening with at least modest participation and a constructive close.
The setup still has enough recent pullback context that it is not just a random continuation bar.

This means the scan is intentionally trying to remove:

stocks that never actually pulled in,
stocks that are still below the 21EMA,
weak reclaim attempts with poor close quality,
extended continuation bars that no longer represent a reclaim.
Condition Design Notes
Trend integrity
ema21_slope_5d_pct > 0.0
sma50_slope_10d_pct > 0.0

These conditions prevent reclaim signals from firing inside flattening structures.

Reclaim location
0.0 <= atr_21ema_zone <= 1.0
0.75 <= atr_50sma_zone <= 4.0

These conditions ensure the stock is now back above the 21EMA, but not wildly extended.
The stock should still be in a reasonable post-pullback location.

Recent pullback evidence
2.0 <= drawdown_from_20d_high_pct <= 12.0
min_atr_21ema_zone_5d <= -0.25

These conditions are critical.
They prove that the stock had recently pulled in enough to make the current bar a reclaim event rather than just ordinary trend continuation.

Trigger confirmation
close_crossed_above_ema21 == True
volume_ratio_20d >= 1.10
dcr_percent >= 60.0

These conditions define the reclaim itself:

price crosses back above the 21EMA,
the move has at least some volume support,
the bar closes well enough to avoid weak reclaim attempts.
Return control
-3.0 <= weekly_return <= 10.0

This avoids both:

setups that remain too weak on a weekly basis,
bars that are already so extended that the reclaim is no longer the main feature.

Required Inputs
Field	Producer	Missing/default used by scan	Scan use
weekly_return	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	-3.0 <= value <= 10.0
dcr_percent	src/indicators/core.py::IndicatorCalculator.calculate	0.0	>= 60.0
atr_21ema_zone	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	0.0 <= value <= 1.0
atr_50sma_zone	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	0.75 <= value <= 4.0
ema21_slope_5d_pct	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	> 0.0
sma50_slope_10d_pct	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	> 0.0
drawdown_from_20d_high_pct	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	2.0 <= value <= 12.0
volume_ratio_20d	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	>= 1.10
close_crossed_above_ema21	src/indicators/core.py::IndicatorCalculator.calculate	False	must be True
min_atr_21ema_zone_5d	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	<= -0.25
Direct Config Dependencies

None. _scan_reclaim uses hard-coded thresholds only in v1.

Upstream Field Definitions
weekly_return = close.pct_change(5) * 100.0
dcr_percent = ((close - low) / (high - low)) * 100.0, zero-width range is filled with 50.0
atr_21ema_zone = (close - ema21_close) / atr
atr_50sma_zone = (close - sma50) / atr
ema21_slope_5d_pct = ((ema21_close / ema21_close.shift(5)) - 1.0) * 100.0
sma50_slope_10d_pct = ((sma50 / sma50.shift(10)) - 1.0) * 100.0
rolling_20d_close_high = close.rolling(20).max()
drawdown_from_20d_high_pct = ((rolling_20d_close_high - close) / rolling_20d_close_high) * 100.0
volume_ma20 = volume.rolling(20).mean()
volume_ratio_20d = volume / volume_ma20
close_crossed_above_ema21 = (close > ema21_close) & (close.shift(1) <= ema21_close.shift(1))
min_atr_21ema_zone_5d = atr_21ema_zone.rolling(5).min()
