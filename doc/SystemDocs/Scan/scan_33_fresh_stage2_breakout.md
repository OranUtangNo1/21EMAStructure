# Scan Spec: Fresh Stage 2 Breakout

## Canonical Metadata

| Item | Value |
| --- | --- |
| Canonical name | `Fresh Stage 2 Breakout` |
| UI display name | `Fresh Stage 2` |
| Implementation owner | `src/scan/rules.py::_scan_fresh_stage2_breakout` |
| Indicator owner | `src/indicators/core.py` |
| Runtime status | `enabled` |

## Purpose

Detects recent transitions into Stage 2 with breakout evidence. It is intended to surface early Stage 2 candidates after a base or transition period, while still requiring RS and demand confirmation.

## Rule Logic

```python
matched = (
    Stage 2 Confirmed
    and Mature / Late Stage Risk Filter passes
    and 0 <= days_since_stage2_start <= scan.fresh_stage2_max_days_since_start
    and stage_base_days_3m >= scan.fresh_stage2_min_base_days_3m
    and raw_rs21 >= scan.fresh_stage2_rs_min
    and close > sma50
    and (
        vcp_pivot_breakout
        or structure_pivot_long_breakout_first_day
        or dist_from_52w_high >= -5.0
    )
    and volume_ratio_20d >= scan.fresh_stage2_volume_ratio_min
    and dcr_percent >= scan.fresh_stage2_dcr_min
)
```

## Config Keys

| Key | Default | Role |
| --- | ---: | --- |
| `scan.fresh_stage2_max_days_since_start` | `21` | maximum age of the Stage 2 transition |
| `scan.fresh_stage2_min_base_days_3m` | `20` | minimum recent base/transition days before Stage 2 |
| `scan.fresh_stage2_rs_min` | `70.0` | minimum short-term RS |
| `scan.fresh_stage2_volume_ratio_min` | `1.2` | minimum breakout-day volume participation |
| `scan.fresh_stage2_dcr_min` | `60.0` | minimum close location in the daily range |

