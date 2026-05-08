# Entry Signal Risk Plan Policy Matrix

This document defines the active direction for Entry Signal risk/reward planning.

## Shared Contract

Each Entry Signal must own one fixed risk plan policy. The evaluator R/R, Entry Plan SL/TP, entry zone, and plan rejection codes must all use that same policy for the signal.

The shared policy shape is:

- SL candidates: signal-specific invalidation structures plus ATR buffer.
- TP1 candidates: signal-specific structural reward targets plus a minimum-R/R validation target.
- TP2 plan: signal-specific trailing or extension plan.
- Entry zone: price range where TP1 meets the signal's minimum R/R.
- Rejection: unavailable SL/TP, SL above entry, TP below entry, weak SL quality, or excessive ATR risk.

## Status Matrix

| Signal key | SL policy | TP1 policy | TP2 plan | Status |
| --- | --- | --- | --- | --- |
| `orderly_pullback_entry` | Pullback low, then 21EMA low / 21EMA close fallback when risk is too wide | Detection 20d high, 52w high, current 20d high, high since detection, then R validation | 21EMA close trailing after TP1 or pool day 3 | Implemented |
| `pullback_resumption_entry` | Preset-specific support: 50SMA defense, reclaim pullback low, pullback low, or 21EMA support | Detection 20d high, current 20d high, high since detection, 52w high, then R validation | 10d low or 21EMA trailing after confirmation | Implemented |
| `momentum_acceleration_entry` | Acceleration-day low, then higher low after detection | 20d high, high since detection, 52w high, then R validation | 10d low trailing after TP1 or pool day 3 | Implemented |
| `accumulation_breakout_entry` | Breakout support: max detection low / resistance, then 21EMA, pool low, or VCP pivot fallback | 52w high, measured move, VCP measured move, then R validation | 10d low trailing after TP1 or pool day 3 | Implemented |
| `early_cycle_recovery_entry` | Structure-pivot higher low, then low since detection / detection low fallback | 20d high, SMA50, then R validation | Take 50% at TP1; 21EMA trailing before SMA50 reclaim, SMA50 trailing after reclaim | Implemented |
| `power_gap_pullback_entry` | Power-gap pullback support: max pool low / 21EMA low, then gap-day low proxy fallback | Max of 20d high / high since detection / detection high, 52w high, then R validation | 21EMA close trailing after TP1 or pool day 3 | Implemented |

## Implemented Policies

- Runtime owner: `src/signals/risk_plan_policy.py`
- `orderly_pullback_entry`: `build_orderly_pullback_risk_plan`
- `accumulation_breakout_entry`: `build_accumulation_breakout_risk_plan`
- `momentum_acceleration_entry`: `build_momentum_acceleration_risk_plan`
- `pullback_resumption_entry`: `build_pullback_resumption_risk_plan`
- `power_gap_pullback_entry`: `build_power_gap_pullback_risk_plan`
- `early_cycle_recovery_entry`: `build_early_cycle_recovery_risk_plan`

Any future Entry Signal precision work should first add the signal-specific policy in `risk_plan_policy.py`, then wire both the evaluator R/R and `src/signals/entry_plan.py` to that policy in the same change.
