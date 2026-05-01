# EntrySignal SystemDocs Combined

---
## BEGIN DOCUMENT 1: `00_index.md`

# Entry Signal Documentation Index

`doc/SystemDocs/EntrySignal/` documents the active Entry Signal workflow implemented by `src/signals/rules.py`, `src/signals/runner.py`, `src/signals/evaluators/`, and the tracking DB signal tables.

## Purpose

- Keep one canonical document per active Entry Signal definition.
- Record pool source presets, detection window, invalidation rules, snapshot fields, scoring axes, and display thresholds.
- Keep Entry Signal docs aligned with the current Streamlit page and tracking DB persistence.

## Common Workflow

- Pool source of truth: preset duplicate output from the current pipeline run.
- Pool persistence: `signal_pool_entry`.
- Daily evaluation persistence: `signal_evaluation`.
- Pool lifecycle: `active`, `invalidated`, `expired`, `orphaned`.
- Daily score axes: `setup_maturity_score`, `timing_score`, `risk_reward_score`.
- Integrated score: `entry_strength`.
- Page buckets: `Signal Detected`, `Approaching`, `Tracking`.

## Current Status Matrix

- [status_matrix.md](status_matrix.md)

## Active Entry Signals

| File | Signal key | Display name | Implementation owner |
| --- | --- | --- | --- |
| [signal_01_orderly_pullback_entry.md](signal_01_orderly_pullback_entry.md) | `orderly_pullback_entry` | `Orderly Pullback Entry` | `src/signals/evaluators/orderly_pullback.py` |
| [signal_02_pullback_resumption_entry.md](signal_02_pullback_resumption_entry.md) | `pullback_resumption_entry` | `Pullback Resumption Entry` | `src/signals/evaluators/pullback_resumption.py` |
| [signal_03_momentum_acceleration_entry.md](signal_03_momentum_acceleration_entry.md) | `momentum_acceleration_entry` | `Momentum Acceleration Entry` | `src/signals/evaluators/momentum_acceleration.py` |
| [signal_04_accumulation_breakout_entry.md](signal_04_accumulation_breakout_entry.md) | `accumulation_breakout_entry` | `Accumulation Breakout Entry` | `src/signals/evaluators/accumulation_breakout.py` |
| [signal_05_early_cycle_recovery_entry.md](signal_05_early_cycle_recovery_entry.md) | `early_cycle_recovery_entry` | `Early Cycle Recovery Entry` | `src/signals/evaluators/early_cycle_recovery.py` |
| [signal_06_power_gap_pullback_entry.md](signal_06_power_gap_pullback_entry.md) | `power_gap_pullback_entry` | `Power Gap Pullback Entry` | `src/signals/evaluators/power_gap_pullback.py` |

## END DOCUMENT 1: `00_index.md`
---

---
## BEGIN DOCUMENT 2: `signal_01_orderly_pullback_entry.md`

# Orderly Pullback Entry

Signal key: `orderly_pullback_entry`

## Workflow

- Pool source presets: `Orderly Pullback`, `Trend Pullback`
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

## END DOCUMENT 2: `signal_01_orderly_pullback_entry.md`
---

---
## BEGIN DOCUMENT 3: `signal_02_pullback_resumption_entry.md`

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

## END DOCUMENT 3: `signal_02_pullback_resumption_entry.md`
---

---
## BEGIN DOCUMENT 4: `signal_03_momentum_acceleration_entry.md`

# Momentum Acceleration Entry

## Identity

- Signal key: `momentum_acceleration_entry`
- Display name: `Momentum Acceleration Entry`
- Version: `1.0`
- Runtime owner: `src/signals/evaluators/momentum_acceleration.py`
- Config owner: `config/default/entry_signals.yaml`
- Status: `enabled`
- Startup selected: `yes`

## Pool Definition

- Preset source: `Momentum Ignition`
- Detection window: `3` business days
- Pool persistence: `signal_pool_entry`
- Daily evaluation persistence: `signal_evaluation`

Pool snapshot fields:
- `close`
- `high`
- `low`
- `atr`
- `rs21`
- `vcs`
- `weekly_return_rank`
- `rel_volume`
- `daily_change_pct`
- `dcr_percent`
- `dist_from_52w_high`
- `pp_count_window`

Pool tracking fields:
- `low_since_detection`
- `high_since_detection`

Invalidation rules:
- `daily_change_pct < -4.0`
- `close < sma50`
- `weekly_return_rank < 80.0`

## Scoring Axes

Setup maturity weight in entry strength: `0.20`

Setup maturity indicators:
- `vcs_quality`: `vcs`, weight `0.40`
- `pp_density`: `pp_count_window`, weight `0.30`
- `momentum_rank`: `weekly_return_rank`, weight `0.30`

Timing weight in entry strength: `0.45`

Timing indicators:
- `acceleration_event`: custom evaluator, weight `0.35`
- `volume_confirmation`: `rel_volume`, weight `0.30`
- `close_quality`: `dcr_percent`, weight `0.20`
- `follow_through`: custom evaluator, weight `0.15`

Risk/reward weight in entry strength: `0.35`

Risk/reward behavior:
- Stop reference: acceleration-day snapshot `low`
- ATR buffer: `0.25`
- Minimum stop distance: `0.25 ATR`
- Primary target: `entry + 2R`
- Secondary fallback target: `entry * 1.08`
- R/R score is capped at `35` when risk exceeds `2.0 ATR`.

## Climax Guard

The evaluator flags a climax warning and caps the final entry strength below `Signal Detected` when any condition is true:
- `rel_volume >= 5.0`
- `dist_from_52w_high >= -1.0` and `daily_change_pct >= 6.0`
- First pool day and `dcr_percent < 50.0`

This allows the candidate to remain visible as `Approaching` while avoiding a high-confidence entry label on exhaustion-style moves.

## Display Thresholds

- `Signal Detected`: `entry_strength >= 55`
- `Approaching`: `entry_strength >= 40`
- `Tracking`: `entry_strength < 40`

## Runtime Notes

- Pool candidates are created only from duplicate output of the `Momentum Ignition` preset.
- `acceleration_event` rewards a current 4% bullish move with sufficient relative volume, or falls back to PP density / hit-scan evidence.
- `follow_through` is neutral on the detection day and becomes more important after the first business day in the pool.

## END DOCUMENT 4: `signal_03_momentum_acceleration_entry.md`
---

---
## BEGIN DOCUMENT 5: `signal_04_accumulation_breakout_entry.md`

# Accumulation Breakout Entry

## Identity

- Signal key: `accumulation_breakout_entry`
- Display name: `Accumulation Breakout Entry`
- Version: `1.0`
- Runtime owner: `src/signals/evaluators/accumulation_breakout.py`
- Config owner: `config/default/entry_signals.yaml`
- Status: `enabled`
- Startup selected: `yes`

## Pool Definition

- Preset sources: `Accumulation Breakout`, `RS Breakout Setup`
- Detection window: `5` business days
- Pool persistence: `signal_pool_entry`
- Daily evaluation persistence: `signal_evaluation`

Pool snapshot fields:
- `close`
- `open`
- `high`
- `low`
- `atr`
- `ema21_close`
- `sma50`
- `rs21`
- `vcs`
- `rel_volume`
- `volume_ratio_20d`
- `dcr_percent`
- `daily_change_pct`
- `weekly_return_rank`
- `quarterly_return_rank`
- `rolling_20d_close_high`
- `resistance_level_lookback`
- `resistance_test_count`
- `breakout_body_ratio`
- `dist_from_52w_high`
- `high_52w`
- `pp_count_window`
- `pocket_pivot`
- `hit_scans`

Pool tracking fields:
- `low_since_detection`
- `high_since_detection`

Invalidation rules:
- `close < sma50`
- `rs21 < 45.0`
- `weekly_return_rank < 70.0`
- `daily_change_pct < -5.0`

## Scoring Axes

Setup maturity weight in entry strength: `0.30`

Setup maturity indicators:
- `vcs_quality`: `vcs`, weight `0.25`
- `rs_leadership`: custom RS and momentum rank composite, weight `0.25`
- `accumulation_quality`: Pocket Pivot, PP density, and Volume Accumulation evidence, weight `0.20`
- `base_tightness`: VCS, drawdown, EMA cloud width, and Three Weeks Tight evidence, weight `0.15`
- `resistance_context`: breakout clearance, resistance tests, and breakout body ratio, weight `0.15`

Timing weight in entry strength: `0.35`

Timing indicators:
- `breakout_event`: custom resistance / 20-day high breakout evaluator, weight `0.35`
- `volume_confirmation`: `rel_volume`, weight `0.25`
- `close_quality`: `dcr_percent`, weight `0.20`
- `follow_through`: custom post-detection continuation evaluator, weight `0.20`

Risk/reward weight in entry strength: `0.35`

Risk/reward behavior:
- Entry reference: current `close`
- Stop reference: adaptive max of breakout-day low, EMA21-buffer stop, and low-since-detection stop
- ATR buffer: `0.25`
- Minimum stop distance: `0.50 ATR`
- Primary target: `entry + 2R`
- Secondary target: `high_52w` when it is sufficiently above entry
- R/R score is capped when risk exceeds `2.0 ATR` or reward is less than `1.5 ATR`.

## Guardrails

The evaluator caps the final entry strength below `Signal Detected` when any condition is true:
- `close < snapshot.low`
- `risk_in_atr > 2.0`
- `rr_ratio < 1.5`
- `rel_volume >= 5.0` and `daily_change_pct >= 6.0`
- `dist_from_52w_high >= -1.0` and `daily_change_pct >= 6.0`
- `dcr_percent < 50.0`

The guardrail detail is written into `Timing Detail` using keys such as `climax_warning`, `risk_cap_reason`, `low_dcr_warning`, or `breakout_failure`.

## Display Thresholds

- `Signal Detected`: `entry_strength >= 55`
- `Approaching`: `entry_strength >= 38`
- `Tracking`: `entry_strength < 38`

## Runtime Notes

- This signal covers the initial base / accumulation breakout phase.
- It differs from pullback signals by evaluating breakout clearance and accumulation evidence rather than moving-average pullback quality.
- It differs from `momentum_acceleration_entry` by requiring breakout context and stricter R/R gating instead of established momentum continuation.

## END DOCUMENT 5: `signal_04_accumulation_breakout_entry.md`
---

---
## BEGIN DOCUMENT 6: `signal_05_early_cycle_recovery_entry.md`

# Early Cycle Recovery Entry

## Identity

- Signal key: `early_cycle_recovery_entry`
- Display name: `Early Cycle Recovery Entry`
- Version: `1.0`
- Runtime owner: `src/signals/evaluators/early_cycle_recovery.py`
- Config owner: `config/default/entry_signals.yaml`
- Status: `enabled`
- Startup selected: `yes`

## Pool Definition

- Preset sources: `Early Cycle Recovery`, `Screening Thesis`
- Detection window: `8` business days
- Pool persistence: `signal_pool_entry`
- Daily evaluation persistence: `signal_evaluation`

Pool snapshot fields:
- `close`
- `open`
- `high`
- `low`
- `atr`
- `ema21_close`
- `sma50`
- `sma200`
- `rs21`
- `vcs`
- `rel_volume`
- `volume_ratio_20d`
- `dcr_percent`
- `daily_change_pct`
- `weekly_return_rank`
- `quarterly_return_rank`
- `dist_from_52w_low`
- `dist_from_52w_high`
- `atr_21ema_zone`
- `atr_50sma_zone`
- `close_crossed_above_ema21`
- `close_crossed_above_sma50`
- `sma50_slope_10d_pct`
- `structure_pivot_long_active`
- `structure_pivot_long_breakout_first_day`
- `structure_pivot_long_hl_price`
- `structure_pivot_1st_break`
- `structure_pivot_2nd_break`
- `ct_trendline_break`
- `pocket_pivot`
- `pp_count_window`
- `hit_scans`

Pool tracking fields:
- `low_since_detection`
- `high_since_detection`

Invalidation rules:
- `rs21 < 35.0`
- `daily_change_pct < -5.0`
- `close < sma50 * 0.95`

## Scoring Axes

Setup maturity weight in entry strength: `0.35`

Setup maturity indicators:
- `structure_reversal_quality`: structure pivot and trendline break evidence, weight `0.35`
- `low_to_recovery_position`: distance from 52-week low/high, weight `0.20`
- `accumulation_evidence`: Volume Accumulation, Pocket Pivot, and PP density, weight `0.20`
- `trend_repair`: EMA21/SMA50 reclaim and ATR zones, weight `0.15`
- `rs_recovery`: RS21 and return-rank recovery, weight `0.10`

Timing weight in entry strength: `0.35`

Timing indicators:
- `pivot_trigger`: structure pivot breakout or close above higher-low reference, weight `0.35`
- `ma_reclaim`: EMA21/SMA50 reclaim state, weight `0.25`
- `volume_confirmation`: `rel_volume`, weight `0.20`
- `close_quality`: `dcr_percent`, weight `0.20`

Risk/reward weight in entry strength: `0.30`

Risk/reward behavior:
- Entry reference: current `close`
- Stop reference: `structure_pivot_long_hl_price - 0.25 ATR`, falling back to `low_since_detection - 0.25 ATR`
- Minimum stop distance: `0.50 ATR`
- Primary target: `entry + 2R`
- Secondary target: `rolling_20d_close_high` when sufficiently above entry
- R/R score is capped when `risk_in_atr > 2.25`.

## Guardrails

The evaluator caps the final entry strength below `Signal Detected` when any condition is true:
- `close < snapshot.low`
- `close < structure_pivot_long_hl_price`
- `risk_in_atr > 2.25`
- `rr_ratio < 1.5`
- `rel_volume >= 5.0` and `daily_change_pct >= 6.0`
- `dcr_percent < 50.0`
- `rs21 < 35.0` or `weekly_return_rank < 50.0`

Guardrail reasons are written into `Timing Detail` using keys such as `recovery_failure`, `pivot_failure`, `risk_cap_reason`, `climax_warning`, `low_dcr_warning`, or `rs_weakness`.

## Display Thresholds

- `Signal Detected`: `entry_strength >= 52`
- `Approaching`: `entry_strength >= 35`
- `Tracking`: `entry_strength < 35`

## Runtime Notes

- This signal targets the early recovery phase before full trend confirmation.
- It intentionally does not invalidate all SMA50-under candidates, because early-cycle setups may form before complete SMA50 recovery.
- It differs from breakout and momentum signals by prioritizing structure reversal and low-risk pivot references.

## END DOCUMENT 6: `signal_05_early_cycle_recovery_entry.md`
---

---
## BEGIN DOCUMENT 7: `signal_06_power_gap_pullback_entry.md`

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
- Stop reference: `min(low_since_detection, ema21_low) - 0.25 ATR`
- Minimum stop distance: `0.50 ATR`
- Primary target: `rolling_20d_close_high` when it gives sufficient reward
- Secondary target: `entry + 2R`
- Fallback target: `high_52w`
- R/R score is capped when `risk_in_atr > 2.0`.

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

## END DOCUMENT 7: `signal_06_power_gap_pullback_entry.md`
---

---
## BEGIN DOCUMENT 8: `status_matrix.md`

# Entry Signal Status Matrix

Source of truth:
- config: `config/default/entry_signals.yaml -> entry_signals.signal_status_map`
- runtime: `src/signals/rules.py::EntrySignalConfig`

Column meaning:
- `Status`: available at runtime after config load.
- `Startup`: selected by default on the Entry Signal page.

Current totals:
- enabled: 6
- disabled: 0
- startup selected: 6

| Entry signal | Status | Startup |
| --- | --- | --- |
| `orderly_pullback_entry` | `enabled` | `yes` |
| `pullback_resumption_entry` | `enabled` | `yes` |
| `momentum_acceleration_entry` | `enabled` | `yes` |
| `accumulation_breakout_entry` | `enabled` | `yes` |
| `early_cycle_recovery_entry` | `enabled` | `yes` |
| `power_gap_pullback_entry` | `enabled` | `yes` |

## END DOCUMENT 8: `status_matrix.md`
---
