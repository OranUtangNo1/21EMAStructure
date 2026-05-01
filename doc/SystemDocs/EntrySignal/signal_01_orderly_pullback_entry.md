# Orderly Pullback Entry

Signal key: `orderly_pullback_entry`

## Workflow

- Pool source preset: `Pullback Trigger`
- Detection window: `10` business days
- Pool tracking fields: `low_since_detection`, `high_since_detection`
- Snapshot fields at detection:
  - `close`
  - `ema21_close`
  - `sma50`
  - `rs21`
  - `atr`
  - `drawdown_from_20d_high_pct`
  - `volume_ma5_to_ma20_ratio`
  - `atr_21ema_zone`
  - `atr_50sma_zone`
  - `rolling_20d_close_high`
  - `high`

## Invalidation

- `close < sma50`
- `drawdown_from_20d_high_pct > 20.0`
- `rs21 < 40.0`
- `sma50_slope_10d_pct <= 0.0`

## Scoring

- `setup_maturity`
  - `volume_exhaustion`
  - `support_convergence`
  - `pullback_duration`
  - `trend_integrity`
  - `rs_resilience`
- `timing`
  - `ema_reclaim_event`
  - `volume_confirmation`
  - `close_quality`
  - `micro_structure_breakout`
  - `demand_footprint`
- `risk_reward`
  - stop reference: `low_since_detection`
  - reward priority: `snapshot_rolling_20d_close_high -> high_52w -> measured_move`

## Integrated Output

- Entry strength weights:
  - `setup_maturity = 0.25`
  - `timing = 0.40`
  - `risk_reward = 0.35`
- Floor gate:
  - `min_axis_threshold = 20`
  - `capped_strength = 30`
- Display thresholds:
  - `Signal Detected >= 50`
  - `Approaching >= 35`
  - `Tracking < 35`

## Runtime Notes

- `Pullback Trigger` is the active preset source for this signal. It avoids the disabled `Orderly Pullback` / `Trend Pullback` preset dependency chain while retaining the same orderly pullback entry evaluator.
- The common Entry Signal context guard can cap otherwise detected rows below `Signal Detected` when `market_score < 30.0`, `earnings_in_7d` is true, or `earnings_today` is true.
