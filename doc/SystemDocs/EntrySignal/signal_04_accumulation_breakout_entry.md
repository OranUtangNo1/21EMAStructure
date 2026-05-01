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

- Preset sources: `Accumulation Breakout`, `RS Breakout Setup`, `VCP 3T Breakout`
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
- `vcp_t1_depth_pct`
- `vcp_t2_depth_pct`
- `vcp_t3_depth_pct`
- `vcp_prior_uptrend_pct`
- `vcp_pivot_price`
- `vcp_pivot_proximity_pct`
- `vcp_volume_dryup_ratio`
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

Custom timing evaluator summary:

| Indicator | Score | Runtime condition |
| --- | ---: | --- |
| `breakout_event` | `70` | breakout reference is missing and `hit_scans` contains `RS New High` or `VCS 52 High` |
| `breakout_event` | `20` | breakout reference is missing and no RS/VCS breakout evidence exists |
| `breakout_event` | `100` | close is `0.0%` to `3.0%` above the breakout reference |
| `breakout_event` | `75` | close is `3.0%` to `6.0%` above the breakout reference |
| `breakout_event` | `55` | close is within `1.0%` below the breakout reference |
| `breakout_event` | `20` | none of the above |
| `follow_through` | `50` | first pool day |
| `follow_through` | `100` | after first pool day, current close is above detection close and `daily_change_pct > 0.0` |
| `follow_through` | `75` | high since detection is above detection high |
| `follow_through` | `30` | second pool day without stronger follow-through |
| `follow_through` | `15` | later pool day without stronger follow-through |

Custom setup evaluator summary:

| Indicator | Runtime inputs |
| --- | --- |
| `rs_leadership` | composite of `rs21`, `weekly_return_rank`, and `quarterly_return_rank` |
| `accumulation_quality` | Pocket Pivot evidence, `pp_count_window`, and `Volume Accumulation` hit evidence |
| `base_tightness` | `vcs`, `drawdown_from_20d_high_pct`, `ema21_cloud_width`, and `three_weeks_tight` |
| `resistance_context` | close clearance against breakout reference, `resistance_test_count`, and `breakout_body_ratio` |

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
