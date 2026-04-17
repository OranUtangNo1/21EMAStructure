# Scan Spec: Three Weeks Tight

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Three Weeks Tight` |
| UI display name | `3WT` |
| Implementation owner | `src/scan/rules.py::_scan_three_weeks_tight` |
| Output | `bool` |
| Direct scan config | `three_weeks_tight_vcs_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads one indicator flag and the latest attached VCS score.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("three_weeks_tight", False)
    and row.get("vcs", 0.0) >= config.three_weeks_tight_vcs_min
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `three_weeks_tight` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |
| `vcs` | `src/scoring/vcs.py::VCSCalculator.add_scores` | `0.0` | `>= config.three_weeks_tight_vcs_min` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.three_weeks_tight_vcs_min` | `50.0` | minimum VCS score |

Related upstream producer config:

- `indicators.enable_3wt = true`
- `indicators.three_weeks_tight_pct_threshold = 1.5`

## Upstream Field Definitions

- Weekly bars are resampled on `W-FRI`.
- `three_weeks_tight` is computed from the latest three weekly closes:

```python
diff_0_1 = (close - close.shift(1)).abs() / close.shift(1).replace(0, np.nan) * 100.0
diff_1_2 = (close.shift(1) - close.shift(2)).abs() / close.shift(2).replace(0, np.nan) * 100.0
three_weeks_tight = (
    (diff_0_1 <= three_weeks_tight_pct_threshold)
    & (diff_1_2 <= three_weeks_tight_pct_threshold)
).fillna(False)
```

- The weekly boolean is forward-filled back to the daily index and stored as a daily `bool` field.
- `vcs` is the latest score attached by `VCSCalculator.add_scores()` from the per-symbol `calculate_series()` result.

## Missing-Field Behavior

- If `indicators.enable_3wt` is false, `three_weeks_tight` is always false and this scan never matches.
- Missing `vcs` values fall back to `0.0`, so the VCS threshold fails closed.
