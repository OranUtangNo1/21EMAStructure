# Scan Spec: VCP 3T

## Canonical Metadata

| Item | Value |
| --- | --- |
| Canonical name | `VCP 3T` |
| UI display name | `VCP 3T` |
| Implementation owner | `src/scan/rules.py::_scan_vcp_3t` |
| Indicator owner | `src/indicators/core.py::_calculate_vcp_3t_fields` |
| Runtime status | `enabled` |

## Purpose

Detects the breakout day of a VCP-style three-tightening contraction pattern:

- prior uptrend before the base
- T1 depth wider than T2, and T2 wider than T3
- final T3 range is tight, normally around 5-7%
- recent volume dried up before the breakout
- current close breaks above the prior pivot without being extended

## Rule Logic

```python
matched = (
    vcp_prior_uptrend_pct >= scan.vcp3t_prior_uptrend_min_pct
    and vcp_t1_depth_pct >= scan.vcp3t_t1_min_depth_pct
    and vcp_t2_depth_pct < vcp_t1_depth_pct * scan.vcp3t_t2_to_t1_max_ratio
    and vcp_t3_depth_pct < vcp_t2_depth_pct * scan.vcp3t_t3_to_t2_max_ratio
    and vcp_t3_depth_pct <= scan.vcp3t_t3_max_depth_pct
    and vcp_tight_days >= scan.vcp3t_tight_days_min
    and vcp_volume_dryup_ratio <= scan.vcp3t_volume_dryup_max_ratio
    and vcp_pivot_breakout
    and 0 <= vcp_pivot_proximity_pct <= scan.vcp3t_pivot_extension_max_pct
    and volume_ratio_20d >= scan.vcp3t_breakout_volume_ratio_min
    and dcr_percent >= scan.vcp3t_dcr_min
    and raw_rs21 >= scan.vcp3t_rs21_min
)
```

## Required Inputs

| Field | Source | Meaning |
| --- | --- | --- |
| `vcp_t1_depth_pct` | `IndicatorCalculator` | depth of the older T1 contraction window |
| `vcp_t2_depth_pct` | `IndicatorCalculator` | depth of the middle T2 contraction window |
| `vcp_t3_depth_pct` | `IndicatorCalculator` | depth of the recent T3 contraction window |
| `vcp_prior_uptrend_pct` | `IndicatorCalculator` | gain into the base from the prior lookback low |
| `vcp_tight_days` | `IndicatorCalculator` | count of tight daily ranges in the final T3 window |
| `vcp_volume_dryup_ratio` | `IndicatorCalculator` | final T3 average volume divided by prior 20D average volume |
| `vcp_pivot_price` | `IndicatorCalculator` | prior high over the configured pivot lookback |
| `vcp_pivot_breakout` | `IndicatorCalculator` | current close crosses above the pivot price |
| `vcp_pivot_proximity_pct` | `IndicatorCalculator` | current close distance from pivot |
| `volume_ratio_20d` | `IndicatorCalculator` | breakout-day volume participation |
| `dcr_percent` | `IndicatorCalculator` | breakout-day close quality |
| `raw_rs21` / `rs21` | RS scoring | short-term relative strength filter |

## Config Keys

| Key | Default | Role |
| --- | ---: | --- |
| `scan.vcp3t_prior_uptrend_min_pct` | `30.0` | minimum advance before the base |
| `scan.vcp3t_t1_min_depth_pct` | `10.0` | minimum T1 contraction depth |
| `scan.vcp3t_t2_to_t1_max_ratio` | `0.85` | requires T2 to be smaller than T1 |
| `scan.vcp3t_t3_to_t2_max_ratio` | `0.75` | requires T3 to be smaller than T2 |
| `scan.vcp3t_t3_max_depth_pct` | `7.0` | maximum final contraction depth |
| `scan.vcp3t_tight_days_min` | `3` | minimum tight candles in T3 |
| `scan.vcp3t_volume_dryup_max_ratio` | `0.8` | maximum dry-up volume ratio before breakout |
| `scan.vcp3t_pivot_extension_max_pct` | `5.0` | max close extension above pivot |
| `scan.vcp3t_breakout_volume_ratio_min` | `1.0` | minimum breakout-day volume vs 20D average |
| `scan.vcp3t_dcr_min` | `55.0` | minimum close location in daily range |
| `scan.vcp3t_rs21_min` | `60.0` | minimum short-term relative strength |

## Notes

- This scan is intentionally stricter than `VCS 52 High` because it requires the ordered T1 -> T2 -> T3 contraction sequence.
- It is breakout-day oriented. A pre-breakout "setup forming" detector would need a separate scan that allows `vcp_pivot_breakout == False`.
