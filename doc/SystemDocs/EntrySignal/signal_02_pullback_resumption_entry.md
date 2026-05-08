# Pullback Resumption Entry

Signal key: `pullback_resumption_entry`

## Workflow

- Pool source presets: `Pullback Trigger`, `50SMA Defense`, `Reclaim Trigger`
- Detection window: `7` business days
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
  - `high_52w`
  - `high`

## Invalidation

- `close < sma50 * 0.97`
- `drawdown_from_20d_high_pct > 20.0`
- `rs21 < 40.0`

## Scoring

- `setup_maturity`
  - `pullback_depth_rr_quality`
  - `volume_dry_up`
  - `rs_resilience`
  - `trend_health`
- `timing`
  - `pattern_trigger`
  - `ma_reclaim_event`
  - `volume_confirmation`
  - `demand_footprint`
- `risk_reward`
  - runtime owner: `src/signals/risk_plan_policy.py`
  - policy builder: `build_pullback_resumption_risk_plan`
  - evaluator R/R and Entry Plan SL/TP both use the same policy result.
  - stop source priority:
    - `50SMA Defense`: `sma50_defense - 0.50 ATR`, then `pullback_low - 0.25 ATR`
    - `Reclaim Trigger`: `reclaim_pullback_low - 0.35 ATR`, then `ema21_reclaim - 0.35 ATR`
    - `Pullback Trigger`: `pullback_low - 0.25 ATR`, then `ema21_support - 0.50 ATR`
  - reward priority: `snapshot_rolling_20d_close_high -> rolling_20d_close_high -> high_since_detection -> high_52w -> rr_validation_target`

## Integrated Output

- Entry strength weights:
  - `setup_maturity = 0.35`
  - `timing = 0.40`
  - `risk_reward = 0.25`
- Floor gate:
  - `min_axis_threshold = 15`
  - `capped_strength = 30`
- Display thresholds:
  - `Signal Detected >= 48`
  - `Approaching >= 32`
  - `Tracking < 32`

## R/R Guardrails

- `50SMA Defense` receives the highest pullback-depth score only when the current row confirms positive SMA50 slope, a 50SMA reclaim event, strong close quality, and an ATR zone near the 50SMA.
- Structural TP1 candidates must provide at least `1.5R`; otherwise the policy falls back to the minimum-R/R validation target.
- Entry Ready uses `rr_ratio_min = 1.8`.
- SL risk above `2.5 ATR` is rejected.
- `50SMA Defense` SL quality requires positive `sma50_slope_10d_pct` and strong close quality; pullback-low SL quality weakens when `dcr_percent < 45.0`.
- Entry zone lower bound is `SL + 0.5 ATR`; upper bound is the maximum entry price that still satisfies the signal's minimum R/R to TP1.
- Candidates with less than `1.5 ATR` of reward room have their risk/reward score capped, which prevents low-upside pullbacks from reaching `Signal Detected`.
