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

Custom timing evaluator summary:

| Indicator | Score | Runtime condition |
| --- | ---: | --- |
| `pivot_trigger` | `100` | `structure_pivot_long_breakout_first_day` is true |
| `pivot_trigger` | `90` | `ct_trendline_break` is true or `hit_scans` contains `LL-HL Structure Trend Line Break` |
| `pivot_trigger` | `75` | close is above `structure_pivot_long_hl_price` |
| `pivot_trigger` | `25` | none of the above |
| `ma_reclaim` | `100` | `close_crossed_above_ema21` is true |
| `ma_reclaim` | `85` | `close_crossed_above_sma50` is true |
| `ma_reclaim` | `65` | close is at or above `ema21_close` |
| `ma_reclaim` | `20` | none of the above |

Custom setup evaluator summary:

| Indicator | Runtime inputs |
| --- | --- |
| `structure_reversal_quality` | active structure pivot plus first pivot, second pivot, and counter-trendline break evidence |
| `low_to_recovery_position` | distance from 52-week low and distance from 52-week high |
| `accumulation_evidence` | `Volume Accumulation`, Pocket Pivot evidence, and `pp_count_window` |
| `trend_repair` | EMA21/SMA50 reclaim state plus `atr_21ema_zone` and `atr_50sma_zone` |
| `rs_recovery` | composite of `rs21`, `weekly_return_rank`, and `quarterly_return_rank` |

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
