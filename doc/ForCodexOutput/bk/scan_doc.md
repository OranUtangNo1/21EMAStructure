# Scan Status Matrix

Source of truth:
- config: `config/default/scan.yaml -> scan.scan_status_map`
- runtime: `src/scan/rules.py::ScanConfig.from_dict`

Column meaning:
- `Status`: enabled for scan evaluation.
- `Card`: visible in Watchlist scan controls after `card_sections` filtering.
- `Startup`: selected at app startup after `default_selected_scan_names` is filtered to active cards.

Current totals:
- enabled scan rules: 19
- visible scan cards: 18
- startup selected scans: 15

| Scan | Status | Card | Startup |
| --- | --- | --- | --- |
| `21EMA scan` | `enabled` | `no` | `no` |
| `21EMA Pattern H` | `enabled` | `yes` | `yes` |
| `21EMA Pattern L` | `enabled` | `yes` | `yes` |
| `Pullback Quality scan` | `enabled` | `yes` | `yes` |
| `Reclaim scan` | `enabled` | `yes` | `yes` |
| `4% bullish` | `enabled` | `yes` | `yes` |
| `Vol Up` | `disabled` | `no` | `no` |
| `Volume Accumulation` | `enabled` | `yes` | `yes` |
| `Momentum 97` | `enabled` | `yes` | `yes` |
| `97 Club` | `disabled` | `no` | `no` |
| `VCS` | `disabled` | `no` | `no` |
| `VCS 52 High` | `enabled` | `yes` | `yes` |
| `VCS 52 Low` | `enabled` | `yes` | `yes` |
| `Pocket Pivot` | `enabled` | `yes` | `yes` |
| `PP Count` | `enabled` | `yes` | `yes` |
| `Weekly 20% plus gainers` | `enabled` | `yes` | `yes` |
| `Near 52W High` | `disabled` | `no` | `no` |
| `Three Weeks Tight` | `disabled` | `no` | `no` |
| `RS Acceleration` | `disabled` | `no` | `no` |
| `Sustained Leadership` | `disabled` | `no` | `no` |
| `Trend Reversal Setup` | `enabled` | `yes` | `yes` |
| `Structure Pivot` | `disabled` | `no` | `no` |
| `LL-HL Structure 1st Pivot` | `enabled` | `yes` | `no` |
| `LL-HL Structure 2nd Pivot` | `enabled` | `yes` | `no` |
| `LL-HL Structure Trend Line Break` | `enabled` | `yes` | `no` |
| `50SMA Reclaim` | `enabled` | `yes` | `yes` |
| `RS New High` | `enabled` | `yes` | `yes` |


# Scan Documentation Index

`doc/SystemDocs/Scan` is the source of truth for active watchlist scan definitions.
Each file in this folder must allow a developer to reproduce the scan boolean logic without reading prose-heavy design docs.

## Operating Rules

- One scan per document.
- The canonical rule must be documented as executable-style logic.
- Hard-coded thresholds and config-driven thresholds must be separated.
- Upstream fields must name their producer and fallback behavior.
- Legacy list terminology is out of scope for this folder.

## Required Sections For Every Scan Doc

1. `Canonical Metadata`
2. `Evaluation Context`
3. `Canonical Boolean Definition`
4. `Required Inputs`
5. `Direct Config Dependencies`
6. `Upstream Field Definitions`

## Common Evaluation Context

- Input unit: one latest row per ticker.
- The row is evaluated after `src/scan/rules.py::enrich_with_scan_context()`.
- All scan conditions are combined with `AND`.
- Missing field handling must be documented exactly as implemented by `row.get(..., default)`.
- Output contract: one boolean hit decision per ticker per scan.

## Source Files

- Scan rules: `src/scan/rules.py`
- Scan execution: `src/scan/runner.py`
- Indicator producers: `src/indicators/core.py`
- RS producer: `src/scoring/rs.py`
- VCS producer: `src/scoring/vcs.py`
- Hybrid producer: `src/scoring/hybrid.py`
- Defaults: `config/default/scan.yaml`

## Active Scan Specs

The default config currently enables `19` scan families.

| File | Canonical scan name | Implementation owner |
|---|---|---|
| [scan_02_4pct_bullish.md](scan_02_4pct_bullish.md) | `4% bullish` | `src/scan/rules.py::_scan_bullish_4pct` |
| [scan_04_momentum97.md](scan_04_momentum97.md) | `Momentum 97` | `src/scan/rules.py::_scan_momentum_97` |
| [scan_05_97club.md](scan_05_97club.md) | `97 Club` | `src/scan/rules.py::_scan_97_club` |
| [scan_07_pocket_pivot.md](scan_07_pocket_pivot.md) | `Pocket Pivot` | `src/scan/rules.py::_scan_pocket_pivot` |
| [scan_08_pp_count.md](scan_08_pp_count.md) | `PP Count` | `src/scan/rules.py::_scan_pp_count` |
| [scan_09_weekly20pct.md](scan_09_weekly20pct.md) | `Weekly 20% plus gainers` | `src/scan/rules.py::_scan_weekly_gainer` |
| [scan_10_near_52w_high.md](scan_10_near_52w_high.md) | `Near 52W High` | `src/scan/rules.py::_scan_near_52w_high` |
| [scan_11_three_weeks_tight.md](scan_11_three_weeks_tight.md) | `Three Weeks Tight` | `src/scan/rules.py::_scan_three_weeks_tight` |
| [scan_12_rs_acceleration.md](scan_12_rs_acceleration.md) | `RS Acceleration` | `src/scan/rules.py::_scan_rs_acceleration` |
| [scan_13_vcs_52_high.md](scan_13_vcs_52_high.md) | `VCS 52 High` | `src/scan/rules.py::_scan_vcs_52_high` |
| [scan_14_vcs_52_low.md](scan_14_vcs_52_low.md) | `VCS 52 Low` | `src/scan/rules.py::_scan_vcs_52_low` |
| [scan_15_volume_accumulation.md](scan_15_volume_accumulation.md) | `Volume Accumulation` | `src/scan/rules.py::_scan_volume_accumulation` |
| [scan_16_pullback_quality.md](scan_16_pullback_quality.md) | `Pullback Quality scan` | `src/scan/rules.py::_scan_pullback_quality` |
| [scan_17_reclaim.md](scan_17_reclaim.md) | `Reclaim scan` | `src/scan/rules.py::_scan_reclaim` |
| [scan_19_sustained_leadership.md](scan_19_sustained_leadership.md) | `Sustained Leadership` | `src/scan/rules.py::_scan_sustained_leadership` |
| [scan_20_trend_reversal_setup.md](scan_20_trend_reversal_setup.md) | `Trend Reversal Setup` | `src/scan/rules.py::_scan_trend_reversal_setup` |
| [scan_21_structure_pivot.md](scan_21_structure_pivot.md) | `Structure Pivot` | `src/scan/rules.py::_scan_structure_pivot` |
| [scan_22_21ema_pattern_h.md](scan_22_21ema_pattern_h.md) | `21EMA Pattern H` | `src/scan/rules.py::_scan_21ema_pattern_h` |
| [scan_23_21ema_pattern_l.md](scan_23_21ema_pattern_l.md) | `21EMA Pattern L` | `src/scan/rules.py::_scan_21ema_pattern_l` |

## Disabled Default Scan Specs

These scan definitions remain documented and implemented, but `config/default/scan.yaml` disables them by default because their screening role overlaps with other active scans.

| File | Canonical scan name | Implementation owner |
|---|---|---|
| [scan_01_21ema.md](scan_01_21ema.md) | `21EMA scan` | `src/scan/rules.py::_scan_21ema` |
| [scan_03_vol_up.md](scan_03_vol_up.md) | `Vol Up` | `src/scan/rules.py::_scan_vol_up` |
| [scan_06_vcs.md](scan_06_vcs.md) | `VCS` | `src/scan/rules.py::_scan_vcs` |

## Out Of Scope

Post-scan annotation filters are not scans. Their current implementation source is `src/scan/rules.py::ANNOTATION_FILTER_REGISTRY`.

The active annotation set includes:

| Annotation filter | Canonical condition |
|---|---|
| `RS 21 >= 63` | `_raw_rs(row, 21) >= 63.0` |
| `High Est. EPS Growth` | `eps_growth_rank >= high_eps_growth_rank_threshold` |
| `PP Count (20d)` | `pp_count_window >= pp_count_annotation_min` |
| `Trend Base` | `trend_base == True` |
| `Fund Score > 70` | `fundamental_score >= 70.0` |

# Scan Spec: 21EMA scan

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `21EMA scan` |
| UI display name | `21EMA` |
| Implementation owner | `src/scan/rules.py::_scan_21ema` |
| Output | `bool` |
| Direct scan config | none |
| Default status | disabled in `config/default/scan.yaml` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads only precomputed indicator fields.
- All conditions are combined with `AND`.
- This is a retained legacy scan. It remains implemented and documented, but the default config disables it in favor of `21EMA Pattern H` and `21EMA Pattern L`.

## Canonical Boolean Definition

```python
weekly_return = row.get("weekly_return", float("nan"))
matched = bool(
    weekly_return >= 0.0
    and weekly_return <= 15.0
    and row.get("dcr_percent", 0.0) > 20.0
    and -0.5 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
    and 0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `weekly_return` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.0 <= value <= 15.0` |
| `dcr_percent` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `> 20.0` |
| `atr_21ema_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `-0.5 <= value <= 1.0` |
| `atr_50sma_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.0 <= value <= 3.0` |

## Direct Config Dependencies

None. `_scan_21ema` uses hard-coded thresholds only.

## Upstream Field Definitions

- `weekly_return = close.pct_change(5) * 100.0`
- `dcr_percent = ((close - low) / (high - low)) * 100.0`, zero-width range is filled with `50.0`
- `atr_21ema_zone = (close - ema21_close) / atr`
- `atr_50sma_zone = (close - sma50) / atr`

# Scan Spec: 4% bullish

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `4% bullish` |
| UI display name | `4% bullish` |
| Implementation owner | `src/scan/rules.py::_scan_bullish_4pct` |
| Output | `bool` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads intraday bar and volume fields only.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("rel_volume", 0.0) >= config.relative_volume_bullish_threshold
    and row.get("daily_change_pct", 0.0) >= config.daily_gain_bullish_threshold
    and row.get("from_open_pct", 0.0) > 0.0
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `rel_volume` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `>= config.relative_volume_bullish_threshold` |
| `daily_change_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `>= config.daily_gain_bullish_threshold` |
| `from_open_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `> 0.0` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.relative_volume_bullish_threshold` | `1.0` | lower bound for `rel_volume` |
| `scan.daily_gain_bullish_threshold` | `4.0` | lower bound for `daily_change_pct` |

## Upstream Field Definitions

- `rel_volume = volume / avg_volume_50d`
- `daily_change_pct = close.pct_change() * 100.0`
- `from_open_pct = (close - open) / open * 100.0`

# Scan Spec: Vol Up

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Vol Up` |
| UI display name | `Vol Up` |
| Implementation owner | `src/scan/rules.py::_scan_vol_up` |
| Default config status | `disabled` |
| Disable reason | role overlap with active volume and momentum scans |
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

# Scan Spec: Momentum 97

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Momentum 97` |
| UI display name | `Momentum 97` |
| Implementation owner | `src/scan/rules.py::_scan_momentum_97` |
| Output | `bool` |

## Evaluation Context

- Evaluated on one latest row after `src/scan/rules.py::enrich_with_scan_context`.
- `weekly_return_rank` and `quarterly_return_rank` are cross-sectional ranks over the current scan input snapshot.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("weekly_return_rank", 0.0) >= config.momentum_97_weekly_rank
    and row.get("quarterly_return_rank", 0.0) >= config.momentum_97_quarterly_rank
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `weekly_return_rank` | `src/scan/rules.py::enrich_with_scan_context` | `0.0` | `>= config.momentum_97_weekly_rank` |
| `quarterly_return_rank` | `src/scan/rules.py::enrich_with_scan_context` | `0.0` | `>= config.momentum_97_quarterly_rank` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.momentum_97_weekly_rank` | `97.0` | lower bound for `weekly_return_rank` |
| `scan.momentum_97_quarterly_rank` | `85.0` | lower bound for `quarterly_return_rank` |

## Upstream Field Definitions

- `weekly_return = close.pct_change(5) * 100.0`
- `quarterly_return = close.pct_change(63) * 100.0`
- `weekly_return_rank = percent_rank(snapshot["weekly_return"])`
- `quarterly_return_rank = percent_rank(snapshot["quarterly_return"])`
- `percent_rank` owner: `src/utils.py::percent_rank`

# Scan Spec: 97 Club

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `97 Club` |
| UI display name | `97 Club` |
| Implementation owner | `src/scan/rules.py::_scan_97_club` |
| Output | `bool` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- `_raw_rs(row, 21)` reads `raw_rs21` first and falls back to `rs21`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
raw_rs21 = _raw_rs(row, 21)
matched = bool(
    row.get("hybrid_score", 0.0) >= config.club_97_hybrid_threshold
    and raw_rs21 >= config.club_97_rs21_threshold
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `hybrid_score` | `src/scoring/hybrid.py::HybridScoreCalculator.score` | `0.0` | `>= config.club_97_hybrid_threshold` |
| `raw_rs21` | `src/scoring/rs.py::RSScorer.score` | fallback to `rs21`, then `nan` | `>= config.club_97_rs21_threshold` |
| `rs21` | `src/scoring/rs.py::RSScorer.score` | `nan` | fallback only |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.club_97_hybrid_threshold` | `90.0` | lower bound for `hybrid_score` |
| `scan.club_97_rs21_threshold` | `97.0` | lower bound for `raw_rs21` |

## Upstream Field Definitions

- `hybrid_score` is the weighted average of `rs21`, `rs63`, `rs126`, `fundamental_score`, and `industry_score`
- default hybrid weights: `1.0, 2.0, 2.0, 2.0, 3.0`
- default missing policy: `fill_neutral_50`
- hybrid owner: `src/scoring/hybrid.py::HybridScoreCalculator.score`
- `raw_rs21` owner: `src/scoring/rs.py::RSScorer.score`

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

# Scan Spec: Pocket Pivot

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Pocket Pivot` |
| UI display name | `Pocket Pivot` |
| Implementation owner | `src/scan/rules.py::_scan_pocket_pivot` |
| Output | `bool` |
| Direct scan config | none |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("close", 0.0) > row.get("sma50", float("inf"))
    and row.get("pocket_pivot", False)
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `close` | latest price row | `0.0` | `> sma50` |
| `sma50` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("inf")` | upper comparison target |
| `pocket_pivot` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

None. `_scan_pocket_pivot` uses hard-coded rule terms only.

## Upstream Field Definitions

- `sma50 = close.rolling(50).mean()`
- `prior_volume_high = volume.rolling(pocket_pivot_lookback).max().shift(1)`
- `pocket_pivot = (close > open) & (volume > prior_volume_high)`
- default `pocket_pivot_lookback = 10` under `indicators.pocket_pivot_lookback`

# PP Count

## Canonical Metadata

- Canonical scan name: `PP Count`
- Implementation owner: `src/scan/rules.py::_scan_pp_count`
- Output type: boolean scan hit per ticker

## Evaluation Context

- Input unit: one latest row per ticker
- Evaluation occurs after `src/scan/rules.py::enrich_with_scan_context()`
- All conditions are combined with `AND`
- Missing values follow `row.get(..., default)` behavior exactly as implemented

## Canonical Boolean Definition

```python
row.get("pp_count_window", 0) >= config.pp_count_scan_min
```

## Required Inputs

- `pp_count_window`
  - expected type: integer-like count
  - fallback used by implementation: `0`

## Direct Config Dependencies

- `scan.pp_count_scan_min`

## Upstream Field Definitions

- `pp_count_window`
  - producer: `src/indicators/core.py`
  - definition: rolling sum of `pocket_pivot` over `indicators.pp_count_window_days`

# Scan Spec: Weekly 20% plus gainers

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Weekly 20% plus gainers` |
| UI display name | `Weekly 20%+ Gainers` |
| Implementation owner | `src/scan/rules.py::_scan_weekly_gainer` |
| Output | `bool` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- The scan uses one field and one threshold.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("weekly_return", 0.0) >= config.weekly_gainer_threshold
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `weekly_return` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `>= config.weekly_gainer_threshold` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.weekly_gainer_threshold` | `20.0` | lower bound for `weekly_return` |

## Upstream Field Definitions

- `weekly_return = close.pct_change(5) * 100.0`

# Scan Spec: Near 52W High

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Near 52W High` |
| UI display name | `Near 52W High` |
| Implementation owner | `src/scan/rules.py::_scan_near_52w_high` |
| Output | `bool` |
| Direct scan config | `near_52w_high_threshold_pct`, `near_52w_high_hybrid_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads precomputed indicator fields and scan-layer scores.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    pd.notna(row.get("high_52w", float("nan")))
    and row.get("high_52w", 0.0) > 0.0
    and row.get("close", 0.0) >= row.get("high_52w", float("inf")) * (1.0 - config.near_52w_high_threshold_pct / 100.0)
    and row.get("hybrid_score", 0.0) >= config.near_52w_high_hybrid_min
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `high_52w` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` and `0.0` | must be present and positive; used for the 52-week-high distance check |
| `close` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | compared against the thresholded `high_52w` value |
| `hybrid_score` | `src/scoring/hybrid.py::HybridScoreCalculator.score` | `0.0` | `>= near_52w_high_hybrid_min` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.near_52w_high_threshold_pct` | `5.0` | max distance from the 52-week high (%) |
| `scan.near_52w_high_hybrid_min` | `70.0` | minimum hybrid score |

## Upstream Field Definitions

- `high_52w = high.rolling(252).max()`
- `close` is the latest daily close from the indicator history
- `hybrid_score` is the configured weighted composite of RS, fundamental, and industry components

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

# Scan Spec: RS Acceleration

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `RS Acceleration` |
| UI display name | `RS Accel` |
| Implementation owner | `src/scan/rules.py::_scan_rs_acceleration` |
| Output | `bool` |
| Direct scan config | `rs_acceleration_rs21_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads only precomputed scoring fields.
- `rs21` and `rs63` are the app RS fields, not RSI fields.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
rs21 = row.get("rs21", float("nan"))
rs63 = row.get("rs63", float("nan"))
matched = bool(
    pd.notna(rs21)
    and pd.notna(rs63)
    and float(rs21) > float(rs63)
    and float(rs21) >= config.rs_acceleration_rs21_min
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `rs21` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` with explicit `notna` guard | `rs21 > rs63` and `>= rs_acceleration_rs21_min` |
| `rs63` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` with explicit `notna` guard | `rs21 > rs63` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.rs_acceleration_rs21_min` | `70.0` | minimum absolute floor for `rs21` |

## Upstream Field Definitions

- `rs21` and `rs63` come from `RSScorer.score()`.
- Each RS field is computed from the symbol's own trailing `close / benchmark_close` ratio history.
- With the current default normalization method (`percentile`), the score is:

```python
ratio = stock_close / benchmark_close
window = ratio.tail(lookback)
rs_value = (window.le(window.iloc[-1]).sum() / len(window)) * 100.0
```

## Relationship To The Annotation Filter

The annotation filter `RS 21 >= 63` is broader than this scan.

- annotation filter: `rs21 >= 63`
- this scan: `rs21 > rs63` and `rs21 >= rs_acceleration_rs21_min`

The scan is therefore an acceleration condition, not just a simple RS floor.

# Scan Spec: VCS 52 High

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `VCS 52 High` |
| UI display name | `VCS 52 High` |
| Implementation owner | `src/scan/rules.py::_scan_vcs_52_high` |
| Output | `bool` |
| Direct scan config | `scan.vcs_52_high_vcs_min`, `scan.vcs_52_high_rs21_min`, `scan.vcs_52_high_dist_max` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads a precomputed VCS score, 21-day RS, and distance from the 52-week high.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("vcs", 0.0) >= config.vcs_52_high_vcs_min
    and _raw_rs(row, 21) > config.vcs_52_high_rs21_min
    and row.get("dist_from_52w_high", float("nan")) >= config.vcs_52_high_dist_max
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `vcs` | `src/scoring/vcs.py::VCSCalculator.add_scores` | `0.0` | `>= vcs_52_high_vcs_min` |
| `raw_rs21` with `rs21` fallback via `_raw_rs(row, 21)` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` | `> vcs_52_high_rs21_min` |
| `dist_from_52w_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `>= vcs_52_high_dist_max` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.vcs_52_high_vcs_min` | `55.0` | minimum VCS score |
| `scan.vcs_52_high_rs21_min` | `25.0` | minimum raw RS21 threshold, using a strict `>` comparison |
| `scan.vcs_52_high_dist_max` | `-20.0` | lower bound for proximity to the 52-week high |

## Upstream Field Definitions

- `dist_from_52w_high = ((close / high_52w) - 1.0) * 100.0`
- `high_52w = high.rolling(252).max()`
- `_raw_rs(row, 21)` uses `raw_rs21` when present and falls back to `rs21`
- `vcs` is the configured contraction-quality score from `VCSCalculator`

# Scan Spec: VCS 52 Low

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `VCS 52 Low` |
| UI display name | `VCS 52 Low` |
| Implementation owner | `src/scan/rules.py::_scan_vcs_52_low` |
| Output | `bool` |
| Direct scan config | `scan.vcs_52_low_vcs_min`, `scan.vcs_52_low_rs21_min`, `scan.vcs_52_low_dist_max`, `scan.vcs_52_low_dist_from_52w_high_max` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads a precomputed VCS score, 21-day RS, distance from the 52-week low, and distance from the 52-week high.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("vcs", 0.0) >= config.vcs_52_low_vcs_min
    and _raw_rs(row, 21) > config.vcs_52_low_rs21_min
    and row.get("dist_from_52w_low", float("nan")) <= config.vcs_52_low_dist_max
    and row.get("dist_from_52w_high", float("nan")) <= config.vcs_52_low_dist_from_52w_high_max
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `vcs` | `src/scoring/vcs.py::VCSCalculator.add_scores` | `0.0` | `>= vcs_52_low_vcs_min` |
| `raw_rs21` with `rs21` fallback via `_raw_rs(row, 21)` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` | `> vcs_52_low_rs21_min` |
| `dist_from_52w_low` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `<= vcs_52_low_dist_max` |
| `dist_from_52w_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `<= vcs_52_low_dist_from_52w_high_max` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.vcs_52_low_vcs_min` | `60.0` | minimum VCS score |
| `scan.vcs_52_low_rs21_min` | `80.0` | minimum raw RS21 threshold, using a strict `>` comparison |
| `scan.vcs_52_low_dist_max` | `25.0` | upper bound for distance above the 52-week low |
| `scan.vcs_52_low_dist_from_52w_high_max` | `-65.0` | upper bound for distance from the 52-week high |

## Upstream Field Definitions

- `dist_from_52w_low = ((close / low_52w) - 1.0) * 100.0`
- `dist_from_52w_high = ((close / high_52w) - 1.0) * 100.0`
- `low_52w = low.rolling(252).min()`
- `high_52w = high.rolling(252).max()`
- `_raw_rs(row, 21)` uses `raw_rs21` when present and falls back to `rs21`
- `vcs` is the configured contraction-quality score from `VCSCalculator`

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

# Scan Spec: Pullback Quality scan

## Canonical Metadata

| Item                 | Value                                       |
| -------------------- | ------------------------------------------- |
| Canonical name       | `Pullback Quality scan`                     |
| UI display name      | `PB Quality`                                |
| Implementation owner | `src/scan/rules.py::_scan_pullback_quality` |
| Output               | `bool`                                      |
| Direct scan config   | none (v1 hard-coded thresholds)             |

## Evaluation Context

* Evaluated on one latest row after `enrich_with_scan_context()`.
* Reads only precomputed indicator fields.
* All conditions are combined with `AND`.
* Intended as a **strict orderly-pullback-quality scan**.
* This scan is responsible for the **pullback-quality judgment that was separated from the older 21EMA pullback draft**.
* This scan is **not** a reclaim / trigger scan.
* This scan is intended to combine with trigger-oriented 21EMA pattern scans or reclaim scans when a preset needs both pullback quality and a trigger.

## Canonical Boolean Definition

```python
weekly_return = row.get("weekly_return", float("nan"))
matched = bool(
    row.get("ema21_slope_5d_pct", float("nan")) > 0.0
    and row.get("sma50_slope_10d_pct", float("nan")) > 0.0
    and -1.25 <= row.get("atr_21ema_zone", float("nan")) <= 0.25
    and 0.75 <= row.get("atr_50sma_zone", float("nan")) <= 3.5
    and -8.0 <= weekly_return <= 3.0
    and row.get("dcr_percent", 0.0) >= 50.0
    and 3.0 <= row.get("drawdown_from_20d_high_pct", float("nan")) <= 15.0
    and row.get("volume_ma5_to_ma20_ratio", float("nan")) <= 0.85
)
```

Intent / Scan Role

This scan is designed to identify orderly pullbacks in already-strong stocks.

A matched ticker should generally satisfy all of the following ideas:

The stock is still in an intact uptrend.
The stock has pulled back toward the 21EMA area, but has not broken the broader structure.
The pullback has some depth, but is still within a reasonable range.
Selling pressure appears controlled rather than disorderly.
Volume has cooled during the pullback, indicating a healthier reset.

This means the scan is intentionally trying to remove:

loose / broken pullbacks,
stocks that are too extended above the 21EMA,
stocks that are already reclaiming and should instead be handled by Reclaim scan.
Condition Design Notes
Trend integrity
ema21_slope_5d_pct > 0.0
sma50_slope_10d_pct > 0.0

These conditions ensure the moving averages are not flattening or rolling over.

Pullback location
-1.25 <= atr_21ema_zone <= 0.25
0.75 <= atr_50sma_zone <= 3.5

These conditions define the acceptable pullback area:

close enough to the 21EMA to qualify as a pullback,
still comfortably above the 50SMA,
not already too far back above the 21EMA.
Pullback depth
3.0 <= drawdown_from_20d_high_pct <= 15.0
-8.0 <= weekly_return <= 3.0

These conditions ensure the stock has actually pulled back, while avoiding:

no real reset,
excessively deep weakness.
Price action quality
dcr_percent >= 50.0

This avoids weak closes near the daily low and favors bars that show at least some intraday support.

Volume contraction
volume_ma5_to_ma20_ratio <= 0.85

This is the key condition that turns the scan from “21EMA location” into “pullback quality”.
The goal is to capture pullbacks where selling pressure is calming down rather than expanding.

Prior demand footprint

Required Inputs
Field	Producer	Missing/default used by scan	Scan use
weekly_return	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	-8.0 <= value <= 3.0
dcr_percent	src/indicators/core.py::IndicatorCalculator.calculate	0.0	>= 50.0
atr_21ema_zone	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	-1.25 <= value <= 0.25
atr_50sma_zone	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	0.75 <= value <= 3.5
ema21_slope_5d_pct	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	> 0.0
sma50_slope_10d_pct	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	> 0.0
drawdown_from_20d_high_pct	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	3.0 <= value <= 15.0
volume_ma5_to_ma20_ratio	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	<= 0.85
Direct Config Dependencies

None. _scan_pullback_quality uses hard-coded thresholds only in v1.

Upstream Field Definitions
weekly_return = close.pct_change(5) * 100.0
dcr_percent = ((close - low) / (high - low)) * 100.0, zero-width range is filled with 50.0
atr_21ema_zone = (close - ema21_close) / atr
atr_50sma_zone = (close - sma50) / atr
ema21_slope_5d_pct = ((ema21_close / ema21_close.shift(5)) - 1.0) * 100.0
sma50_slope_10d_pct = ((sma50 / sma50.shift(10)) - 1.0) * 100.0
rolling_20d_close_high = close.rolling(20).max()
drawdown_from_20d_high_pct = ((rolling_20d_close_high - close) / rolling_20d_close_high) * 100.0
volume_ma5 = volume.rolling(5).mean()
volume_ma20 = volume.rolling(20).mean()
volume_ma5_to_ma20_ratio = volume_ma5 / volume_ma20

# Scan Spec: Reclaim scan

## Canonical Metadata

| Item                 | Value                              |
| -------------------- | ---------------------------------- |
| Canonical name       | `Reclaim scan`                     |
| UI display name      | `Reclaim`                          |
| Implementation owner | `src/scan/rules.py::_scan_reclaim` |
| Output               | `bool`                             |
| Direct scan config   | none (v1 hard-coded thresholds)    |

## Evaluation Context

* Evaluated on one latest row after `enrich_with_scan_context()`.
* Reads only precomputed indicator fields.
* All conditions are combined with `AND`.
* Intended as a **reclaim / restart trigger scan** after a valid pullback.
* This scan is responsible for the **restart / reclaim judgment that was separated from the older 21EMA pullback draft**.
* This scan should generally be used **after or alongside** `Pullback Quality scan` or the trigger-oriented 21EMA pattern scans.
* This scan is not intended to represent a broad pullback candidate list; it is intended to identify **the reclaim event itself**.

## Canonical Boolean Definition

```python
weekly_return = row.get("weekly_return", float("nan"))
matched = bool(
    row.get("ema21_slope_5d_pct", float("nan")) > 0.0
    and row.get("sma50_slope_10d_pct", float("nan")) > 0.0
    and 0.0 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
    and 0.75 <= row.get("atr_50sma_zone", float("nan")) <= 4.0
    and -3.0 <= weekly_return <= 10.0
    and row.get("dcr_percent", 0.0) >= 60.0
    and 2.0 <= row.get("drawdown_from_20d_high_pct", float("nan")) <= 12.0
    and row.get("volume_ratio_20d", float("nan")) >= 1.10
    and row.get("close_crossed_above_ema21", False)
    and row.get("min_atr_21ema_zone_5d", float("nan")) <= -0.25
)
```

Intent / Scan Role

This scan is designed to identify the reclaim day after an orderly pullback.

A matched ticker should generally satisfy all of the following ideas:

The stock is still in an intact bullish structure.
The stock had recently pulled into / under the 21EMA area.
The stock has now moved back above the 21EMA.
The reclaim is happening with at least modest participation and a constructive close.
The setup still has enough recent pullback context that it is not just a random continuation bar.

This means the scan is intentionally trying to remove:

stocks that never actually pulled in,
stocks that are still below the 21EMA,
weak reclaim attempts with poor close quality,
extended continuation bars that no longer represent a reclaim.
Condition Design Notes
Trend integrity
ema21_slope_5d_pct > 0.0
sma50_slope_10d_pct > 0.0

These conditions prevent reclaim signals from firing inside flattening structures.

Reclaim location
0.0 <= atr_21ema_zone <= 1.0
0.75 <= atr_50sma_zone <= 4.0

These conditions ensure the stock is now back above the 21EMA, but not wildly extended.
The stock should still be in a reasonable post-pullback location.

Recent pullback evidence
2.0 <= drawdown_from_20d_high_pct <= 12.0
min_atr_21ema_zone_5d <= -0.25

These conditions are critical.
They prove that the stock had recently pulled in enough to make the current bar a reclaim event rather than just ordinary trend continuation.

Trigger confirmation
close_crossed_above_ema21 == True
volume_ratio_20d >= 1.10
dcr_percent >= 60.0

These conditions define the reclaim itself:

price crosses back above the 21EMA,
the move has at least some volume support,
the bar closes well enough to avoid weak reclaim attempts.
Return control
-3.0 <= weekly_return <= 10.0

This avoids both:

setups that remain too weak on a weekly basis,
bars that are already so extended that the reclaim is no longer the main feature.

Required Inputs
Field	Producer	Missing/default used by scan	Scan use
weekly_return	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	-3.0 <= value <= 10.0
dcr_percent	src/indicators/core.py::IndicatorCalculator.calculate	0.0	>= 60.0
atr_21ema_zone	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	0.0 <= value <= 1.0
atr_50sma_zone	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	0.75 <= value <= 4.0
ema21_slope_5d_pct	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	> 0.0
sma50_slope_10d_pct	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	> 0.0
drawdown_from_20d_high_pct	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	2.0 <= value <= 12.0
volume_ratio_20d	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	>= 1.10
close_crossed_above_ema21	src/indicators/core.py::IndicatorCalculator.calculate	False	must be True
min_atr_21ema_zone_5d	src/indicators/core.py::IndicatorCalculator.calculate	float("nan")	<= -0.25
Direct Config Dependencies

None. _scan_reclaim uses hard-coded thresholds only in v1.

Upstream Field Definitions
weekly_return = close.pct_change(5) * 100.0
dcr_percent = ((close - low) / (high - low)) * 100.0, zero-width range is filled with 50.0
atr_21ema_zone = (close - ema21_close) / atr
atr_50sma_zone = (close - sma50) / atr
ema21_slope_5d_pct = ((ema21_close / ema21_close.shift(5)) - 1.0) * 100.0
sma50_slope_10d_pct = ((sma50 / sma50.shift(10)) - 1.0) * 100.0
rolling_20d_close_high = close.rolling(20).max()
drawdown_from_20d_high_pct = ((rolling_20d_close_high - close) / rolling_20d_close_high) * 100.0
volume_ma20 = volume.rolling(20).mean()
volume_ratio_20d = volume / volume_ma20
close_crossed_above_ema21 = (close > ema21_close) & (close.shift(1) <= ema21_close.shift(1))
min_atr_21ema_zone_5d = atr_21ema_zone.rolling(5).min()

# Scan Spec: Sustained Leadership

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Sustained Leadership` |
| UI display name | `RS Leader` |
| Implementation owner | `src/scan/rules.py::_scan_sustained_leadership` |
| Output | `bool` |
| Direct scan config | `scan.sustained_rs21_min`, `scan.sustained_rs63_min`, `scan.sustained_rs126_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads multi-horizon RS fields.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
rs21 = _raw_rs(row, 21)
rs63 = row.get("rs63", float("nan"))
rs126 = row.get("rs126", float("nan"))

matched = bool(
    pd.notna(rs21)
    and float(rs21) >= config.sustained_rs21_min
    and pd.notna(rs63)
    and float(rs63) >= config.sustained_rs63_min
    and pd.notna(rs126)
    and float(rs126) >= config.sustained_rs126_min
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `raw_rs21` with `rs21` fallback via `_raw_rs(row, 21)` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` | `>= sustained_rs21_min` |
| `rs63` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` | `>= sustained_rs63_min` |
| `rs126` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` | `>= sustained_rs126_min` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.sustained_rs21_min` | `80.0` | lower bound for 21-day RS |
| `scan.sustained_rs63_min` | `70.0` | lower bound for 63-day RS |
| `scan.sustained_rs126_min` | `60.0` | lower bound for 126-day RS |

## Upstream Field Definitions

- `_raw_rs(row, 21)` uses `raw_rs21` when present and falls back to `rs21`
- `rs63` and `rs126` are percentile-style relative-strength outputs from `RSScorer`

# Scan Spec: Trend Reversal Setup

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Trend Reversal Setup` |
| UI display name | `Reversal Setup` |
| Implementation owner | `src/scan/rules.py::_scan_trend_reversal_setup` |
| Output | `bool` |
| Direct scan config | `scan.reversal_dist_52w_low_max`, `scan.reversal_dist_52w_high_min`, `scan.reversal_rs21_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads price-vs-moving-average state, SMA slope, 52-week distance fields, RS, and pocket-pivot count.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
pocket_pivot_count = row.get("pp_count_30d", row.get("pp_count_window", 0))
raw_rs21 = _raw_rs(row, 21)

matched = bool(
    row.get("close", 0.0) > row.get("sma50", float("inf"))
    and row.get("sma50", float("inf")) <= row.get("sma200", float("inf"))
    and row.get("sma50_slope_10d_pct", float("nan")) > 0.0
    and row.get("dist_from_52w_low", float("nan")) <= config.reversal_dist_52w_low_max
    and row.get("dist_from_52w_high", float("nan")) >= config.reversal_dist_52w_high_min
    and raw_rs21 >= config.reversal_rs21_min
    and pocket_pivot_count >= 1
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `close` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `> sma50` |
| `sma50` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("inf")` | compared against `close` and `sma200` |
| `sma200` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("inf")` | upper bound for `sma50` |
| `sma50_slope_10d_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `> 0.0` |
| `dist_from_52w_low` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `<= reversal_dist_52w_low_max` |
| `dist_from_52w_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `>= reversal_dist_52w_high_min` |
| `raw_rs21` with `rs21` fallback via `_raw_rs(row, 21)` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` | `>= reversal_rs21_min` |
| `pp_count_30d` with `pp_count_window` fallback | `src/indicators/core.py::IndicatorCalculator.calculate` | `0` | `>= 1` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.reversal_dist_52w_low_max` | `40.0` | upper bound for distance from the 52-week low |
| `scan.reversal_dist_52w_high_min` | `-40.0` | lower bound for distance from the 52-week high |
| `scan.reversal_rs21_min` | `50.0` | lower bound for 21-day RS |

## Upstream Field Definitions

- `sma50 = close.rolling(50).mean()`
- `sma200 = close.rolling(200).mean()`
- `sma50_slope_10d_pct = ((sma50 / sma50.shift(10)) - 1.0) * 100.0`
- `dist_from_52w_low = ((close / low_52w) - 1.0) * 100.0`
- `dist_from_52w_high = ((close / high_52w) - 1.0) * 100.0`
- `_raw_rs(row, 21)` uses `raw_rs21` when present and falls back to `rs21`
- pocket-pivot count comes from `pp_count_30d` when present, otherwise `pp_count_window`

# Scan Spec: Structure Pivot

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Structure Pivot` |
| UI display name | `Structure Pivot` |
| Implementation owner | `src/scan/rules.py::_scan_structure_pivot` |
| Output | `bool` |
| Direct scan config | none |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads the bullish LL-HL structure flag produced by `src/indicators/core.py::IndicatorCalculator.calculate`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(row.get("structure_pivot_long_active", False))
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `structure_pivot_long_active` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | bullish LL-HL structure must be active |

## Direct Config Dependencies

- none

## Upstream Field Definitions

- `structure_pivot_long_active` is produced from a multi-length LL-HL structure scan over daily history.
- Lengths are controlled by `indicators.structure_pivot_min_length` and `indicators.structure_pivot_max_length`.
- Priority selection is controlled by `indicators.structure_pivot_priority_mode`.
- A long structure becomes active when a confirmed pivot low is followed by a higher pivot low and a valid pivot price exists between them.
- The latest structure is invalidated if current low breaks below the higher low before breakout.

# Scan Spec: 21EMA Pattern H

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `21EMA Pattern H` |
| UI display name | `21EMA PH` |
| Implementation owner | `src/scan/rules.py::_scan_21ema_pattern_h` |
| Output | `bool` |
| Direct scan config | none (v1 hard-coded thresholds) |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads only precomputed indicator fields.
- All conditions are combined with `AND`.
- Intended as a shallow pullback trigger scan for stocks holding near the 21EMA high band.
- This scan replaces the broad legacy `21EMA scan` for the strongest high-band pullback pattern.

## Canonical Boolean Definition

```python
matched = bool(
    0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
    and 0.3 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
    and row.get("atr_low_to_ema21_high", float("nan")) >= -0.2
    and row.get("high", 0.0) > row.get("prev_high", float("inf"))
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `atr_50sma_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.0 <= value <= 3.0` |
| `atr_21ema_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.3 <= value <= 1.0` |
| `atr_low_to_ema21_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `value >= -0.2` |
| `high` | latest price row | `0.0` | `value > prev_high` |
| `prev_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("inf")` | comparison target for `high` |

## Direct Config Dependencies

None. `_scan_21ema_pattern_h` uses hard-coded thresholds only in v1.

## Upstream Field Definitions

- `atr_50sma_zone = (close - sma50) / atr`
- `atr_21ema_zone = (close - ema21_close) / atr`
- `atr_low_to_ema21_high = (low - ema21_high) / atr`
- `ema21_high = EMA(high, 21)`
- `prev_high = high.shift(1)`

# Scan Spec: 21EMA Pattern L

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `21EMA Pattern L` |
| UI display name | `21EMA PL` |
| Implementation owner | `src/scan/rules.py::_scan_21ema_pattern_l` |
| Output | `bool` |
| Direct scan config | none (v1 hard-coded thresholds) |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads only precomputed indicator fields.
- All conditions are combined with `AND`.
- Intended as a deep pullback reclaim trigger scan for stocks that pierced the 21EMA low band intraday and recovered by close.
- This scan replaces the broad legacy `21EMA scan` for the low-band defense pattern.

## Canonical Boolean Definition

```python
matched = bool(
    0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
    and -0.5 <= row.get("atr_21ema_zone", float("nan")) <= -0.1
    and row.get("atr_low_to_ema21_low", float("nan")) < 0.0
    and row.get("atr_21emaL_zone", float("nan")) > 0.0
    and row.get("high", 0.0) > row.get("prev_high", float("inf"))
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `atr_50sma_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.0 <= value <= 3.0` |
| `atr_21ema_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `-0.5 <= value <= -0.1` |
| `atr_low_to_ema21_low` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `value < 0.0` |
| `atr_21emaL_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `value > 0.0` |
| `high` | latest price row | `0.0` | `value > prev_high` |
| `prev_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("inf")` | comparison target for `high` |

## Direct Config Dependencies

None. `_scan_21ema_pattern_l` uses hard-coded thresholds only in v1.

## Upstream Field Definitions

- `atr_50sma_zone = (close - sma50) / atr`
- `atr_21ema_zone = (close - ema21_close) / atr`
- `atr_low_to_ema21_low = (low - ema21_low) / atr`
- `atr_21emaL_zone = (close - ema21_low) / atr`
- `ema21_low = EMA(low, 21)`
- `prev_high = high.shift(1)`

# Scan Spec: LL-HL Structure 1st Pivot

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `LL-HL Structure 1st Pivot` |
| UI display name | `LL-HL 1st` |
| Implementation owner | `src/scan/rules.py::_scan_llhl_1st_pivot` |
| Output | `bool` |
| Direct scan config | `scan.llhl_1st_rs21_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    _raw_rs(row, 21) >= config.llhl_1st_rs21_min
    and row.get("structure_pivot_1st_break", False)
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `raw_rs21` / `rs21` | `src/scoring/rs.py` | `nan` | `>= llhl_1st_rs21_min` |
| `structure_pivot_1st_break` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.llhl_1st_rs21_min` | `60.0` | RS lower bound |

## Upstream Field Definitions

- `structure_pivot_1st_pivot = hl_price + (swing_high - hl_price) * 0.618`
- `structure_pivot_1st_break = (close > structure_pivot_1st_pivot) and (prev_close <= structure_pivot_1st_pivot)`

# Scan Spec: LL-HL Structure 2nd Pivot

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `LL-HL Structure 2nd Pivot` |
| UI display name | `LL-HL 2nd` |
| Implementation owner | `src/scan/rules.py::_scan_llhl_2nd_pivot` |
| Output | `bool` |
| Direct scan config | `scan.llhl_2nd_rs21_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    _raw_rs(row, 21) >= config.llhl_2nd_rs21_min
    and row.get("structure_pivot_2nd_break", False)
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `raw_rs21` / `rs21` | `src/scoring/rs.py` | `nan` | `>= llhl_2nd_rs21_min` |
| `structure_pivot_2nd_break` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.llhl_2nd_rs21_min` | `60.0` | RS lower bound |

## Upstream Field Definitions

- `structure_pivot_2nd_pivot = structure_pivot_swing_high`
- `structure_pivot_2nd_break = (close > structure_pivot_2nd_pivot) and (prev_close <= structure_pivot_2nd_pivot)`

# Scan Spec: LL-HL Structure Trend Line Break

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `LL-HL Structure Trend Line Break` |
| UI display name | `CT Break` |
| Implementation owner | `src/scan/rules.py::_scan_llhl_ct_break` |
| Output | `bool` |
| Direct scan config | none |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(row.get("ct_trendline_break", False))
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `ct_trendline_break` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

None. `_scan_llhl_ct_break` uses hard-coded rule terms only.

## Upstream Field Definitions

- `ct_trendline_break` is computed only when `structure_pivot_long_active == False`.
- Uses the two latest confirmed pivot highs from the configured structure-pivot length range.
- Safety condition: `latest_pivot_high < previous_pivot_high` must hold (descending resistance line only).
- `ct_trendline_break = (close > ct_trendline_value) and (prev_close <= prev_ct_trendline_value)`.

# Scan Spec: 50SMA Reclaim

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `50SMA Reclaim` |
| UI display name | `50SMA Reclaim` |
| Implementation owner | `src/scan/rules.py::_scan_50sma_reclaim` |
| Output | `bool` |
| Direct scan config | none (v1 hard-coded thresholds) |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads only precomputed indicator fields.
- All conditions are combined with `AND`.
- Intended as a reclaim trigger when price crosses back above 50SMA after a deeper pullback.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("sma50_slope_10d_pct", float("nan")) > 0.0
    and 0.0 <= row.get("atr_50sma_zone", float("nan")) <= 1.0
    and row.get("close_crossed_above_sma50", False)
    and row.get("min_atr_50sma_zone_5d", float("nan")) <= -0.25
    and row.get("dcr_percent", 0.0) >= 60.0
    and row.get("volume_ratio_20d", float("nan")) >= 1.10
    and 3.0 <= row.get("drawdown_from_20d_high_pct", float("nan")) <= 20.0
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `sma50_slope_10d_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `> 0.0` |
| `atr_50sma_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.0 <= value <= 1.0` |
| `close_crossed_above_sma50` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |
| `min_atr_50sma_zone_5d` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `<= -0.25` |
| `dcr_percent` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `>= 60.0` |
| `volume_ratio_20d` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `>= 1.10` |
| `drawdown_from_20d_high_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `3.0 <= value <= 20.0` |

## Direct Config Dependencies

None. `_scan_50sma_reclaim` uses hard-coded thresholds only in v1.

## Upstream Field Definitions

- `sma50_slope_10d_pct = ((sma50 / sma50.shift(10)) - 1.0) * 100.0`
- `atr_50sma_zone = (close - sma50) / atr`
- `close_crossed_above_sma50 = (close > sma50) & (close.shift(1) <= sma50.shift(1))`
- `min_atr_50sma_zone_5d = atr_50sma_zone.rolling(5).min()`
- `dcr_percent = ((close - low) / (high - low)) * 100.0`
- `volume_ratio_20d = volume / volume.rolling(20).mean()`
- `drawdown_from_20d_high_pct = ((close.rolling(20).max() - close) / close.rolling(20).max()) * 100.0`

# Scan Spec: RS New High

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `RS New High` |
| UI display name | `RS New High` |
| Implementation owner | `src/scan/rules.py::_scan_rs_new_high` |
| Output | `bool` |
| Direct scan config | `scan.rs_new_high_price_dist_max`, `scan.rs_new_high_price_dist_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads precomputed RS-ratio new-high state plus price distance from 52-week high.
- All conditions are combined with `AND`.
- Intended to detect RS-leading divergence where RS reaches a new high before price does.

## Canonical Boolean Definition

```python
matched = bool(
    row.get("rs_ratio_at_52w_high", False)
    and row.get("dist_from_52w_high", float("nan")) <= config.rs_new_high_price_dist_max
    and row.get("dist_from_52w_high", float("nan")) >= config.rs_new_high_price_dist_min
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `rs_ratio_at_52w_high` | `src/scoring/rs.py::RSScorer.score` | `False` | must be `True` |
| `dist_from_52w_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | within configured range |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.rs_new_high_price_dist_max` | `-5.0` | price must be at or below this distance from 52-week high |
| `scan.rs_new_high_price_dist_min` | `-30.0` | price must be at or above this distance from 52-week high |

## Upstream Field Definitions

- `rs_ratio = close / benchmark_close`
- `rs_ratio_52w_high = rs_ratio.rolling(252, min_periods=126).max()`
- `rs_ratio_at_52w_high = rs_ratio >= rs_ratio_52w_high * (1.0 - rs_new_high_tolerance / 100.0)`
- `dist_from_52w_high = ((close / high_52w) - 1.0) * 100.0`


