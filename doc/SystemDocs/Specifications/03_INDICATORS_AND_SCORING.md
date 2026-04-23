# Indicators and Scoring

## 1. Purpose

This document describes the indicator and scoring behavior currently implemented in code.

## 2. Core Technical Indicators

### 2.1 21EMA Structure

Implemented fields:

- `ema21_high = EMA(high, 21)`
- `ema21_low = EMA(low, 21)`
- `ema21_close = EMA(close, 21)`
- `ema21_cloud_width = ema21_high - ema21_low`

Interpretation:

- `ema21_low` is the low-based 21EMA and is not replaced with a close-based EMA
- the 21EMA cloud is represented by the band between `ema21_high` and `ema21_low`
- current code uses the underlying fields rather than a dedicated chart module

### 2.2 Moving Averages

Implemented fields:

- `sma50 = rolling_mean(close, 50)`
- `sma200 = rolling_mean(close, 200)`
- `wma10_weekly = weighted_moving_average(weekly_close, 10)`
- `wma30_weekly = weighted_moving_average(weekly_close, 30)`

### 2.3 ATR

Implemented field:

- `atr`

Formula:

- `true_range = max(high - low, abs(high - prev_close), abs(low - prev_close))`
- `atr = EMA(true_range, alpha = 1 / atr_period)`

Default parameter:

- `atr_period = 14`

### 2.4 ADR Percent

Implemented field:

- `adr_percent`

Default formula:

- `adr_percent = (rolling_mean(high / low, adr_period) - 1.0) * 100`

Alternative formulas can be selected through config, but the active default is `sma_high_low_ratio`.

Default parameters:

- `adr_period = 20`
- `min_adr_percent = 3.5`
- `max_adr_percent = 10.0`

### 2.5 DCR Percent

Implemented field:

- `dcr_percent`

Formula:

- `dcr_percent = (close - low) / (high - low) * 100`
- when the daily range is zero, the value falls back to `50`

### 2.6 Relative Volume

Implemented field:

- `rel_volume = volume / avg_volume_50d`

Supporting field:

- `avg_volume_50d = rolling_mean(volume, 50)`

### 2.7 52-Week Distance Fields

Implemented fields:

- `high_52w = rolling_max(high, 252)`
- `low_52w = rolling_min(low, 252)`
- `dist_from_52w_high = ((close / high_52w) - 1.0) * 100`
- `dist_from_52w_low = ((close / low_52w) - 1.0) * 100`

Interpretation:

- `dist_from_52w_high` is zero at the 52-week high and negative below it
- `dist_from_52w_low` is zero at the 52-week low and positive above it
- both distance fields use the current close relative to the rolling 252-session extreme

### 2.8 Up/Down Volume Ratio

Implemented field:

- `ud_volume_ratio`

Formula:

- `up_volume = volume` when `close >= prev_close`, else `0`
- `down_volume = volume` when `close < prev_close`, else `0`
- `sum_up = rolling_sum(up_volume, ud_volume_period)`
- `sum_down = rolling_sum(down_volume, ud_volume_period)`
- `ud_volume_ratio = sum_up / max(sum_down, 1.0)`

Default parameter:

- `ud_volume_period = 50`

### 2.9 RSI

Implemented fields:

- `rsi21`
- `rsi63`

Formula:

- Wilder-style RSI using exponentially weighted average gains and losses
- neutral fallback is `50` when both gains and losses are zero

Default parameters:

- `rsi_short_period = 21`
- `rsi_long_period = 63`

### 2.10 Return Horizons And Daily Change

Implemented fields:

- `daily_change_pct = close.pct_change() * 100`
- `from_open_pct = (close - open) / open * 100`
- `weekly_return = close.pct_change(5) * 100`
- `monthly_return = close.pct_change(21) * 100`
- `quarterly_return = close.pct_change(63) * 100`

### 2.11 Breakout Quality Fields

Implemented fields:

- `resistance_level_lookback = rolling_max(high, resistance_test_lookback).shift(1)`
- `resistance_test_count`
- `breakout_body_ratio = (close - open) / (high - low)`

`resistance_test_count` formula:

- `resistance_zone_threshold = atr * resistance_zone_width_atr`
- `tested = (high >= resistance_level_lookback - resistance_zone_threshold) and (close < resistance_level_lookback)`
- `resistance_test_count = rolling_sum(tested, resistance_test_count_window, min_periods=resistance_test_count_window)`

Edge handling:

- `resistance_level_lookback` uses `shift(1)` to avoid same-day self-reference
- `breakout_body_ratio` uses directional body; bearish bars are negative
- when `high == low`, `breakout_body_ratio` is `NaN`

Default parameters:

- `resistance_test_lookback = 20`
- `resistance_zone_width_atr = 0.5`
- `resistance_test_count_window = 20`

## 3. Zone And Structure Metrics

### 3.1 ATR Distance Zones

Implemented fields:

- `atr_21ema_zone = (close - ema21_close) / atr`
- `atr_21emaH_zone = (close - ema21_high) / atr`
- `atr_21emaL_zone = (close - ema21_low) / atr`
- `atr_low_to_ema21_high = (low - ema21_high) / atr`
- `atr_low_to_ema21_low = (low - ema21_low) / atr`
- `atr_10wma_zone = (close - wma10_weekly) / atr`
- `atr_50sma_zone = (close - sma50) / atr`
- `prev_high = high.shift(1)`

Derived labels:

- `atr_21ema_label`: `below`, `good`, `extended`, or `unknown`
- `atr_50sma_label`: `good`, `extended`, or `unknown`

Default thresholds:

- 21EMA zone good range: `-0.5` to `1.0`
- 50SMA extended threshold: above `3.0`

### 3.2 21EMA Low Percent

Implemented field:

- `ema21_low_pct`

Formula:

- if `close >= ema21_low`: `(close - ema21_low) / ema21_low * 100`
- else: `(close - ema21_low) / close * 100`

Derived field:

- `ema21_low_size_bucket` with values `full`, `reduced`, `avoid`, or `unknown`

Default thresholds:

- `full` when `ema21_low_pct <= 5.0`
- `reduced` when `ema21_low_pct <= 8.0`
- `avoid` otherwise

### 3.3 ATR Percent From 50SMA

Implemented fields:

- `atr_pct_from_50sma`
- `overheat`

Formula:

- `gain_from_ma_pct = (close / sma50) - 1.0`
- `atr_pct_daily = atr / close`
- `atr_pct_from_50sma = gain_from_ma_pct / atr_pct_daily`

Default threshold:

- `overheat = atr_pct_from_50sma >= 7.0`

### 3.4 Three Weeks Tight

Implemented field:

- `three_weeks_tight`

Formula:

- resample daily bars to weekly close on `W-FRI`
- compute the absolute percent difference between the latest two weekly closes
- compute the absolute percent difference between the previous two weekly closes
- mark `True` only if both differences are less than or equal to the configured threshold

Default parameters:

- `enable_3wt = true`
- `three_weeks_tight_pct_threshold = 1.5`

### 3.5 Pocket Pivot And PP Count

Implemented fields:

- `pocket_pivot`
- `pp_count_window`

Pocket Pivot formula:

- candle is green: `close > open`
- volume is greater than the maximum volume of the prior rolling lookback window

PP Count formula:

- rolling sum of `pocket_pivot` over `pp_count_window_days`

Default parameters:

- `pocket_pivot_lookback = 10`
- `pp_count_window_days = 20`

### 3.6 Trend Base

Implemented field:

- `trend_base = (close > sma50) and (wma10_weekly > wma30_weekly)`

## 4. Relative Strength

### 4.1 Raw RS And RS Fields

Implemented fields:

- `raw_rs5`, `raw_rs21`, `raw_rs63`, `raw_rs126`
- `rs5`, `rs21`, `rs63`, `rs126`
- `price_ratio`

Current implementation behavior:

- benchmark symbol defaults to `SPY`
- align stock close and benchmark close on date index
- compute `price_ratio = stock_close / benchmark_close`
- for each lookback window, take the trailing ratio window
- when `rs_normalization_method = percentile`, score the window with Pine-style percentrank semantics:
  `count(window values <= current value) / window length * 100`
- for other normalization methods, normalize the trailing window and use the most recent normalized value as the score for that lookback
- there is no cross-sectional RS normalization at this stage; the score is derived from the symbol's own ratio history

In the current implementation, `rs*` is equal to `raw_rs*`.

Default parameters:

- `benchmark_symbol = SPY`
- `rs_lookbacks = [5, 21, 63, 126]`
- `rs_normalization_method = percentile`
- `rs_strong_threshold = 80`
- `rs_weak_threshold = 39`

## 5. Fundamental Score

Implemented fields:

- `eps_growth_score`
- `revenue_growth_score`
- `fundamental_score`

Current default behavior:

- normalize `eps_growth` and `revenue_growth` across the current snapshot with the configured method
- fill missing normalized values with `50` when `missing_fundamental_policy = fill_neutral`
- compute the weighted average using `eps_weight` and `revenue_weight`

Default parameters:

- `eps_weight = 1.0`
- `revenue_weight = 1.0`
- `fundamental_normalization_method = percentile`
- `missing_fundamental_policy = fill_neutral`

## 6. Industry Score

Implemented field:

- `industry_score`

Current default behavior:

- group the snapshot by `industry`
- use `rs21` as the input metric by default
- aggregate each industry with the configured method
- normalize aggregated industry values across industries
- map the normalized industry score back to each ticker

Default parameters:

- `industry_aggregation_method = mean`
- `industry_rs_input_metric = rs21`
- `industry_score_normalization_method = percentile`

Supported aggregation modes in code:

- `mean`
- `median`
- `market_cap_weighted_mean`

Supported input metric behavior in code:

- `rs21`
- `rs63`
- `rs126`
- any other input metric falls back to `(rs21 + 2*rs63 + 2*rs126) / 5` before industry normalization

## 7. Hybrid Score

Implemented fields:

- `hybrid_score`
- `H`
- `F`
- `I`
- `21`
- `63`
- `126`

Current default formula:

```text
Hybrid = (
  rs21 * 1 +
  rs63 * 2 +
  rs126 * 2 +
  fundamental_score * 2 +
  industry_score * 3
) / 10
```

Current default missing-value policy:

- `fill_neutral_50`
- missing components are replaced with `50` before the weighted average

Other supported code paths:

- `drop_symbol`
- weighted renormalization over non-missing components

## 8. VCS

Implemented field:

- `vcs`

Current default behavior:

- follow the published Pine VCS workflow
- use variable-length windows in early bars:
  `len_short = min(bar_count, configured len_short)`,
  `len_long = min(bar_count, configured len_long)`,
  `len_volume = min(bar_count, configured len_volume)`
- compute `true_range = max(high - low, abs(high - prev_close), abs(low - prev_close))`
- compute `ratio_atr = sma(true_range, len_short) / sma(true_range, len_long)`
- compute `ratio_std = stdev(close, len_short) / stdev(close, len_long)`
- compute `vol_ratio = sma(volume, 5) / sma(volume, len_volume)`
- compute `efficiency = abs(close - close[len_short]) / sum(true_range, len_short)`
- compute `trend_factor = max(0, 1 - efficiency * trend_penalty_weight)`
- compute the structural higher-low test with:
  - `low_recent = lowest(low, len_short)`
  - `low_base = lowest(low, hl_lookback)[len_short]`
  - `is_higher_low = low_recent >= low_base` once enough history exists
- build the raw score as:
  - `s_atr = max(0, 1 - ratio_atr) * sensitivity`
  - `s_std = max(0, 1 - ratio_std) * sensitivity`
  - `s_vol = max(0, 1 - vol_ratio)`
  - `raw_score = s_atr * 0.4 + s_std * 0.4 + s_vol * 0.2`
- convert to physics and consistency layers:
  - `filtered_score = raw_score * trend_factor`
  - `physics_score = min(100, filtered_score * 100)`
  - `smooth_physics = ema(physics_score, 3)`
  - `days_tight = consecutive count of smooth_physics >= 70`
  - `weighted_physics_score = smooth_physics * ((100 - bonus_max) / 100)`
  - `consistency_score = min(bonus_max, days_tight)`
  - `total_score = weighted_physics_score + consistency_score`
- apply the higher-low penalty:
  - `final_score = total_score` when `is_higher_low`
  - `final_score = total_score * penalty_factor` otherwise
- fill missing values with `0` and clip the final score to `[0, 100]`

Default parameters:

- `vcs_threshold_candidate = 60.0`
- `vcs_threshold_priority = 80.0`
- `len_short = 13`
- `len_long = 63`
- `len_volume = 50`
- `hl_lookback = 63`
- `sensitivity = 2.0`
- `trend_penalty_weight = 1.0`
- `penalty_factor = 0.75`
- `bonus_max = 15.0`

## 9. Interpretation Notes

Important distinctions in the active codebase:

- RSI is a price-momentum oscillator and is separate from SPY-relative RS
- RS percentile scoring is time-series based and uses each symbol's own benchmark-relative ratio history
- raw RS and normalized RS currently collapse to the same value because the scorer returns the normalized ratio-window endpoint directly
- fundamental, industry, hybrid, and VCS are configurable research layers, not fixed external standards
