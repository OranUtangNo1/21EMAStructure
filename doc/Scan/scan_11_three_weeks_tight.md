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
- Reads only precomputed indicator fields.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("three_weeks_tight", False)
    and row.get("trend_base", False)
    and row.get("vcs", 0.0) >= config.three_weeks_tight_vcs_min
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `three_weeks_tight` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |
| `trend_base` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |
| `vcs` | `src/scoring/vcs.py::VCSCalculator.add_scores` | `0.0` | `>= three_weeks_tight_vcs_min` |

## Direct Config Dependencies

| Config key | Location | Default | Scan use |
|---|---|---|---|
| `three_weeks_tight_vcs_min` | `config/default.yaml::scan` | `50.0` | minimum VCS to pass |

## Upstream Field Definitions

- `three_weeks_tight` — weekly-resampled boolean, forward-filled to daily index. Computed in `IndicatorCalculator._calculate_three_weeks_tight()`:
  ```python
  diff_0_1 = abs(close_w - close_w.shift(1)) / close_w.shift(1) * 100.0
  diff_1_2 = abs(close_w.shift(1) - close_w.shift(2)) / close_w.shift(2) * 100.0
  three_weeks_tight = (diff_0_1 <= three_weeks_tight_pct_threshold) & (diff_1_2 <= three_weeks_tight_pct_threshold)
  ```
  Where `close_w` is the Friday weekly close and `three_weeks_tight_pct_threshold = 1.5` (config: `indicators.three_weeks_tight_pct_threshold`). Requires 3 consecutive weekly closes each within 1.5% of the prior week's close.
- `trend_base = (close > sma50) & (wma10_weekly > wma30_weekly)`
- `vcs` — contraction quality score (0–100). Composed of volatility component (max 40), range component (max 45), volume bonus (max 15), base score (5), and trend penalty (−15 if close < sma50).

## New Config Key Required

Add to `config/default.yaml` under the `scan:` block:

```yaml
scan:
  three_weeks_tight_vcs_min: 50.0
```

Add to `ScanConfig` dataclass in `src/scan/rules.py`:

```python
three_weeks_tight_vcs_min: float = 50.0
```

## Note on `enable_3wt`

`three_weeks_tight` is only computed when `indicators.enable_3wt = true` (default). If `enable_3wt` is `false`, the field is always `False` and this scan will never match. No guard is needed inside the scan function itself; the behavior is correct by construction.
