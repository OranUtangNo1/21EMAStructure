# Orderly Pullback Entry

Signal key: `orderly_pullback_entry`

## Workflow

- Pool source preset: `Pullback Trigger`
- Detection window: `10` business days
- Pool tracking fields: `low_since_detection`, `high_since_detection`
- Snapshot fields at detection:
  - `close`
  - `ema21_close`
  - `ema21_low`
  - `sma50`
  - `rs21`
  - `atr`
  - `drawdown_from_20d_high_pct`
  - `volume_ma5_to_ma20_ratio`
  - `atr_21ema_zone`
  - `atr_50sma_zone`
  - `rolling_20d_close_high`
  - `high_52w`
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
  - runtime owner: `src/signals/risk_plan_policy.py`
  - policy builder: `build_orderly_pullback_risk_plan`
  - evaluator R/R and Entry Plan SL/TP both use the same policy result.
  - stop source priority:
    - primary: `low_since_detection - 0.25 ATR`
    - fallback: `ema21_low - 0.25 ATR` when the pullback low risk is too wide
    - fallback proxy: `ema21_close - 0.50 ATR` when `ema21_low` is unavailable
  - reward priority: `snapshot_rolling_20d_close_high -> high_52w -> rolling_20d_close_high -> high_since_detection -> rr_validation_target`

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

- `Pullback Trigger` is the active preset source for this signal.
- The common Entry Signal context guard can cap otherwise detected rows below `Signal Detected` when `market_score < 30.0`, `earnings_in_7d` is true, or `earnings_today` is true.
- Structural TP1 candidates must provide at least `1.5R`; otherwise the policy falls back to the minimum-R/R validation target.
- Entry Ready currently keeps `rr_ratio_min = 2.0`; lowering this to `1.5R` requires separate detection-quality review.
- SL risk above `1.8 ATR` is rejected.
- Entry zone lower bound is `SL + 0.4 ATR`; upper bound is the maximum entry price that still satisfies the signal's Entry Ready R/R threshold to TP1.
- TP2 plan is 21EMA close trailing after TP1, or from pool day 3 when no structural TP1 is available.
