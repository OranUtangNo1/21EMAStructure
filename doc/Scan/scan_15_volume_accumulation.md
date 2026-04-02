# Scan Spec: Volume Accumulation

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Volume Accumulation` |
| UI display name | `Volume Accumulation` |
| Implementation owner | `src/scan/rules.py::_scan_volume_accumulation` |
| Output | `bool` |
| Direct scan config | `vol_accum_ud_ratio_min`, `vol_accum_rel_vol_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads a multi-day up/down volume ratio plus current-day participation and direction.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("ud_volume_ratio", 0.0) >= config.vol_accum_ud_ratio_min
    and row.get("rel_volume", 0.0) >= config.vol_accum_rel_vol_min
    and row.get("daily_change_pct", 0.0) > 0.0
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `ud_volume_ratio` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `>= vol_accum_ud_ratio_min` |
| `rel_volume` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `>= vol_accum_rel_vol_min` |
| `daily_change_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | hard-coded `> 0.0` positive-day check |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.vol_accum_ud_ratio_min` | `1.5` | minimum up/down volume ratio |
| `scan.vol_accum_rel_vol_min` | `1.0` | minimum current relative volume |

Hard-coded rule in code:
- `daily_change_pct > 0.0`

## Upstream Field Definitions

- `rel_volume = volume / avg_volume_50d`
- `up_volume = volume` when `close >= prev_close`, else `0.0`
- `down_volume = volume` when `close < prev_close`, else `0.0`
- `ud_volume_ratio = rolling_sum(up_volume, ud_volume_period) / max(rolling_sum(down_volume, ud_volume_period), 1.0)`
