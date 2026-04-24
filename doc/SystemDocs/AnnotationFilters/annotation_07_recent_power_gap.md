# Annotation Filter Spec: Recent Power Gap

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `Recent Power Gap` |
| Implementation owner | `src/scan/rules.py::_annotation_recent_power_gap` |
| Output | `bool` |
| Direct config dependencies | `scan.power_gap_annotation_min_pct`, `scan.power_gap_annotation_max_days` |

## Canonical Boolean Definition

```python
power_gap_up_pct = row.get("power_gap_up_pct", float("nan"))
days_since = row.get("days_since_power_gap", float("nan"))
matched = bool(
    pd.notna(power_gap_up_pct)
    and power_gap_up_pct >= config.power_gap_annotation_min_pct
    and pd.notna(days_since)
    and days_since <= config.power_gap_annotation_max_days
)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `power_gap_up_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | compare against min gap threshold |
| `days_since_power_gap` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | compare against max-days threshold |

## Direct Config Dependencies

| Config key | Default |
|---|---|
| `scan.power_gap_annotation_min_pct` | `10.0` |
| `scan.power_gap_annotation_max_days` | `20` |
