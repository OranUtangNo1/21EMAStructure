# Scan Spec: Vol Up

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Vol Up` |
| UI display name | `Vol Up` |
| Implementation owner | `src/scan/rules.py::_scan_vol_up` |
| Output | `bool` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("rel_volume", 0.0) >= config.relative_volume_vol_up_threshold
    and row.get("daily_change_pct", 0.0) > 0.0
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `rel_volume` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `>= config.relative_volume_vol_up_threshold` |
| `daily_change_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `> 0.0` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.relative_volume_vol_up_threshold` | `1.5` | lower bound for `rel_volume` |

Hard-coded threshold in code:
- `daily_change_pct > 0.0`

## Upstream Field Definitions

- `rel_volume = volume / avg_volume_50d`
- `daily_change_pct = close.pct_change() * 100.0`
