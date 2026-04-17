# Scan Spec: VCS

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `VCS` |
| UI display name | `VCS` |
| Implementation owner | `src/scan/rules.py::_scan_vcs` |
| Default config status | `disabled` |
| Disable reason | role overlap with active VCS-derived structure scans |
| Output | `bool` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- The scan reads the final `vcs` score only. The score itself is owned by `src/scoring/vcs.py::VCSCalculator.calculate_series`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("vcs", 0.0) >= config.vcs_min_threshold
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `vcs` | `src/scoring/vcs.py::VCSCalculator.calculate_series` | `0.0` | `>= config.vcs_min_threshold` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.vcs_min_threshold` | `60.0` | lower bound for `vcs` |

## Upstream Field Definitions

`vcs` is produced by `src/scoring/vcs.py::VCSCalculator.calculate_series`.

Canonical scorer outline:

```python
true_range = max(high - low, abs(high - prev_close), abs(low - prev_close))
tr_short = SMA(true_range, len_short with variable warmup)
tr_long_avg = SMA(true_range, len_long with variable warmup)
ratio_atr = tr_short / tr_long_avg

std_short = STD(close, len_short with variable warmup)
std_long_avg = STD(close, len_long with variable warmup)
ratio_std = std_short / std_long_avg

vol_short_avg = SMA(volume, 5)
vol_avg = SMA(volume, len_volume with variable warmup)
vol_ratio = vol_short_avg / vol_avg

efficiency = abs(close - close.shift(len_short)) / SUM(true_range, len_short with variable warmup)
trend_factor = clip(1 - efficiency * trend_penalty_weight, lower=0)

low_recent = LOWEST(low, len_short with variable warmup)
low_base = LOWEST(low, hl_lookback).shift(len_short)
is_higher_low = True if there is not enough history else (low_recent >= low_base)

score_atr = clip((1 - ratio_atr) * sensitivity, lower=0)
score_std = clip((1 - ratio_std) * sensitivity, lower=0)
score_vol = clip(1 - vol_ratio, lower=0)

raw_score = score_atr * 0.4 + score_std * 0.4 + score_vol * 0.2
filtered_score = raw_score * trend_factor
physics_score = clip(filtered_score * 100, upper=100)
smooth_physics = EMA(physics_score, span=3)

is_tight = smooth_physics >= 70
days_tight = consecutive_true_count(is_tight)
weighted_physics_score = smooth_physics * ((100 - bonus_max) / 100)
consistency_score = clip(days_tight, upper=bonus_max)
total_score = weighted_physics_score + consistency_score
vcs = total_score if is_higher_low else total_score * penalty_factor
vcs = clip(vcs, 0, 100)
```

Current default scorer params from `config/default.yaml`:
- `len_short=13`
- `len_long=63`
- `len_volume=50`
- `hl_lookback=63`
- `sensitivity=2.0`
- `trend_penalty_weight=1.0`
- `penalty_factor=0.75`
- `bonus_max=15.0`
