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
  - stop reference: `depth_adaptive`
  - stop source priority: `50SMA Defense -> Reclaim Trigger -> Pullback Trigger`
  - reward priority: `snapshot_rolling_20d_close_high -> rolling_20d_close_high -> high_52w -> measured_move`

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
- Candidates with less than `1.5 ATR` of reward room have their risk/reward score capped, which prevents low-upside pullbacks from reaching `Signal Detected`.
