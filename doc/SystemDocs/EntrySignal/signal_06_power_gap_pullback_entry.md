# Power Gap Pullback Entry

## Identity

- Signal key: `power_gap_pullback_entry`
- Display name: `Power Gap Pullback Entry`
- Version: `1.0`
- Runtime owner: `src/signals/evaluators/power_gap_pullback.py`
- Config owner: `config/default/entry_signals.yaml`
- Status: `enabled`
- Startup selected: `yes`

## Pool Definition

- Preset source: `Power Gap Pullback`
- Detection window: `10` business days
- Pool persistence: `signal_pool_entry`
- Daily evaluation persistence: `signal_evaluation`

Pool snapshot fields:
- `close`
- `open`
- `high`
- `low`
- `atr`
- `ema21_close`
- `ema21_high`
- `ema21_low`
- `sma50`
- `rs21`
- `vcs`
- `rel_volume`
- `volume_ratio_20d`
- `volume_ma5_to_ma20_ratio`
- `dcr_percent`
- `daily_change_pct`
- `drawdown_from_20d_high_pct`
- `days_since_power_gap`
- `power_gap_up_pct`
- `ema21_low_pct`
- `atr_21ema_zone`
- `atr_low_to_ema21_high`
- `atr_low_to_ema21_low`
- `rolling_20d_close_high`
- `high_52w`
- `dist_from_52w_high`
- `pocket_pivot`
- `pp_count_window`
- `hit_scans`

Pool tracking fields:
- `low_since_detection`
- `high_since_detection`

Invalidation rules:
- `close < sma50`
- `drawdown_from_20d_high_pct > 18.0`
- `rs21 < 45.0`
- `days_since_power_gap > 20.0`
- `daily_change_pct < -5.0`

## Scoring Axes

Setup maturity weight in entry strength: `0.35`

Setup maturity indicators:
- `gap_quality`: power gap size, relative volume, and close quality, weight `0.25`
- `pullback_orderliness`: volume dry-up, drawdown depth, and 21EMA zone, weight `0.30`
- `support_proximity`: low-to-EMA support zones and EMA21 low proximity, weight `0.20`
- `rs_resilience`: RS21 and weekly return rank, weight `0.15`
- `accumulation_return`: Pocket Pivot, Volume Accumulation, and PP density, weight `0.10`

Timing weight in entry strength: `0.35`

Timing indicators:
- `reclaim_trigger`: Reclaim scan, EMA21 reclaim, or 21EMA Pattern evidence, weight `0.35`
- `volume_reentry`: rel-volume / 20D-volume confirmation and Pocket Pivot evidence, weight `0.25`
- `close_quality`: `dcr_percent`, weight `0.20`
- `pullback_age`: days since power gap, weight `0.20`

Risk/reward weight in entry strength: `0.30`

Risk/reward behavior:
- Entry reference: current `close`
- Runtime policy owner: `src/signals/risk_plan_policy.py::build_power_gap_pullback_risk_plan`
- Stop reference: `max(low_since_detection, ema21_low) - 0.25 ATR`
- Stop fallback: detection `low - 0.15 ATR` as a gap-day-low proxy when the primary support is unusable
- Minimum stop distance: `0.50 ATR`
- Maximum practical risk: `2.0 ATR`
- TP1 priority: max of `rolling_20d_close_high`, `high_since_detection`, and detection `high`
- TP1 fallback: `high_52w`, then `rr_validation_target`
- Minimum structural TP1 R/R: `1.5R`
- TP2 plan: after TP1, trail with 21EMA close; exit on two consecutive closes below 21EMA
- Evaluator R/R, Entry Plan SL/TP, entry zone, and plan rejection codes use the same policy.

## Guardrails

The evaluator caps the final entry strength below `Signal Detected` when any condition is true:
- `days_since_power_gap <= 1.0`
- `close < low_since_detection`
- `drawdown_from_20d_high_pct > 18.0`
- `risk_in_atr > 2.0`
- `rr_ratio < 1.5`
- `rel_volume >= 5.0` and `daily_change_pct >= 6.0`
- `dcr_percent < 50.0`

Guardrail reasons are written into `Timing Detail` using keys such as `gap_chase_warning`, `gap_failure`, `risk_cap_reason`, `climax_warning`, or `low_dcr_warning`.

## Display Thresholds

- `Signal Detected`: `entry_strength >= 52`
- `Approaching`: `entry_strength >= 35`
- `Tracking`: `entry_strength < 35`

## Runtime Notes

- This signal targets the first orderly pullback after a power gap.
- It intentionally rejects gap-day chase entries and waits for support/reclaim behavior.
- It differs from generic pullback signals by requiring power-gap context and by scoring pullback age explicitly.
