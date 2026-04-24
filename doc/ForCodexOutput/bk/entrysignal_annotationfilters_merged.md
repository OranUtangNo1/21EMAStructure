# Entry Signal Status Matrix

Source of truth:
- config: `config/default/entry_signals.yaml -> entry_signals.signal_status_map`
- runtime: `src/signals/rules.py::EntrySignalConfig`

Column meaning:
- `Status`: available at runtime after config load.
- `Startup`: selected by default on the Entry Signal page.

Current totals:
- enabled: 5
- disabled: 0
- startup selected: 5

| Entry signal | Status | Startup |
| --- | --- | --- |
| `Pocket Pivot Entry` | `enabled` | `yes` |
| `Structure Pivot Breakout Entry` | `enabled` | `yes` |
| `Pullback Low-Risk Zone` | `enabled` | `yes` |
| `Volume Reclaim Entry` | `enabled` | `yes` |
| `Resistance Breakout Entry` | `enabled` | `yes` |


# Entry Signal Documentation Index

`doc/SystemDocs/EntrySignal/` documents active entry-signal definitions in `src/signals/rules.py::ENTRY_SIGNAL_REGISTRY`.

## Purpose

- Keep one canonical document per entry signal.
- Record exact evaluator logic and required inputs.
- Keep signal docs aligned with Entry Signal page output.

## Common Evaluation Context

- Input unit: one latest row per ticker from selected signal universe.
- Evaluated by `src/signals/runner.py::EntrySignalRunner.evaluate`.
- Output contract: one boolean hit decision per signal per ticker.

## Current Status Matrix

- [status_matrix.md](status_matrix.md)
- `Status` shows runtime enabled or disabled state.
- `Startup` shows whether the signal is selected by default on page load.

## Active Entry Signals

| File | Canonical signal name | Implementation owner |
|---|---|---|
| [signal_01_pocket_pivot_entry.md](signal_01_pocket_pivot_entry.md) | `Pocket Pivot Entry` | `src/signals/rules.py::_pocket_pivot_entry` |
| [signal_02_structure_pivot_breakout_entry.md](signal_02_structure_pivot_breakout_entry.md) | `Structure Pivot Breakout Entry` | `src/signals/rules.py::_structure_pivot_breakout_entry` |
| [signal_03_pullback_low_risk_zone.md](signal_03_pullback_low_risk_zone.md) | `Pullback Low-Risk Zone` | `src/signals/rules.py::_pullback_low_risk_zone` |
| [signal_04_volume_reclaim_entry.md](signal_04_volume_reclaim_entry.md) | `Volume Reclaim Entry` | `src/signals/rules.py::_volume_reclaim_entry` |
| [signal_05_resistance_breakout_entry.md](signal_05_resistance_breakout_entry.md) | `Resistance Breakout Entry` | `src/signals/rules.py::_resistance_breakout_entry` |


# Entry Signal Spec: Pocket Pivot Entry

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical signal name | `Pocket Pivot Entry` |
| Implementation owner | `src/signals/rules.py::_pocket_pivot_entry` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
matched = _as_bool(row.get("pocket_pivot")) and _gt(row.get("close"), row.get("sma50"))
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `pocket_pivot` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be true |
| `close` | price row | missing -> false via `_gt` | must be `> sma50` |
| `sma50` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gt` | reference line |


# Entry Signal Spec: Structure Pivot Breakout Entry

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical signal name | `Structure Pivot Breakout Entry` |
| Implementation owner | `src/signals/rules.py::_structure_pivot_breakout_entry` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
matched = _as_bool(row.get("structure_pivot_long_breakout_first_day"))
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `structure_pivot_long_breakout_first_day` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be true |


# Entry Signal Spec: Pullback Low-Risk Zone

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical signal name | `Pullback Low-Risk Zone` |
| Implementation owner | `src/signals/rules.py::_pullback_low_risk_zone` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
matched = (
    (_as_bool(row.get("atr_21ema_zone")) or _as_bool(row.get("atr_50sma_zone")))
    and _gt(row.get("rs21"), 50.0)
    and not _lt(row.get("dcr_percent"), 30.0)
)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `atr_21ema_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | falsey -> no support-zone signal | near-support proxy |
| `atr_50sma_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | falsey -> no support-zone signal | near-support proxy |
| `rs21` | `src/scoring/rs.py::RSScorer.score` | missing -> false via `_gt` | must be `> 50.0` |
| `dcr_percent` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> not low by `_lt` helper | must not be `< 30.0` |


# Entry Signal Spec: Volume Reclaim Entry

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical signal name | `Volume Reclaim Entry` |
| Implementation owner | `src/signals/rules.py::_volume_reclaim_entry` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
matched = (
    _gt(row.get("close"), row.get("sma50"))
    and _gte(row.get("rel_volume"), 1.4)
    and _gt(row.get("daily_change_pct"), 0.0)
)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `close` | price row | missing -> false via `_gt` | must be `> sma50` |
| `sma50` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gt` | reclaim reference |
| `rel_volume` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gte` | must be `>= 1.4` |
| `daily_change_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gt` | must be positive |


# Entry Signal Spec: Resistance Breakout Entry

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical signal name | `Resistance Breakout Entry` |
| Implementation owner | `src/signals/rules.py::_resistance_breakout_entry` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
matched = bool(
    _gte(row.get("resistance_test_count"), 2.0)
    and _gt(row.get("close"), row.get("resistance_level_lookback"))
    and _gte(row.get("breakout_body_ratio"), 0.6)
    and _gte(row.get("rel_volume"), 1.5)
)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `resistance_test_count` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gte` | must be `>= 2.0` |
| `close` | price row | missing -> false via `_gt` | must break resistance |
| `resistance_level_lookback` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gt` | breakout level |
| `breakout_body_ratio` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gte` | must be `>= 0.6` |
| `rel_volume` | `src/indicators/core.py::IndicatorCalculator.calculate` | missing -> false via `_gte` | must be `>= 1.5` |


# Annotation Filter Status Matrix

Source of truth:
- config: `config/default/scan.yaml -> scan.annotation_filter_status_map`
- runtime: `src/scan/rules.py::ScanConfig.from_dict`

Column meaning:
- `Status`: available at runtime after config load.
- `Startup`: selected by default in Watchlist controls.

Current totals:
- enabled: 7
- disabled: 0
- startup selected: 0

| Annotation filter | Status | Startup |
| --- | --- | --- |
| `RS 21 >= 63` | `enabled` | `no` |
| `High Est. EPS Growth` | `enabled` | `no` |
| `PP Count (20d)` | `enabled` | `no` |
| `Trend Base` | `enabled` | `no` |
| `Fund Score > 70` | `enabled` | `no` |
| `Resistance Tests >= 2` | `enabled` | `no` |
| `Recent Power Gap` | `enabled` | `no` |


# Annotation Filter Documentation Index

`doc/SystemDocs/AnnotationFilters/` documents active annotation filters evaluated by `src/scan/rules.py::ANNOTATION_FILTER_REGISTRY`.

## Purpose

- Keep one canonical document per annotation filter.
- Record exact boolean logic as implemented.
- Clarify config-driven vs hard-coded thresholds.

## Common Evaluation Context

- Input unit: one latest row per ticker after `enrich_with_scan_context()`.
- Annotation filters do not create watchlist candidates by themselves.
- Output contract: one boolean pass/fail per ticker per filter.

## Current Status Matrix

- [status_matrix.md](status_matrix.md)
- `Status` shows runtime enabled or disabled state.
- `Startup` shows whether the filter is selected by default in Watchlist controls.

## Active Annotation Filters

| File | Canonical annotation filter | Implementation owner |
|---|---|---|
| [annotation_01_rs21_gte_63.md](annotation_01_rs21_gte_63.md) | `RS 21 >= 63` | `src/scan/rules.py::_annotation_rs21_gte_63` |
| [annotation_02_high_est_eps_growth.md](annotation_02_high_est_eps_growth.md) | `High Est. EPS Growth` | `src/scan/rules.py::_annotation_high_eps_growth` |
| [annotation_03_pp_count_20d.md](annotation_03_pp_count_20d.md) | `PP Count (20d)` | `src/scan/rules.py::_annotation_pp_count_20d` |
| [annotation_04_trend_base.md](annotation_04_trend_base.md) | `Trend Base` | `src/scan/rules.py::_annotation_trend_base` |
| [annotation_05_fund_score_gt_70.md](annotation_05_fund_score_gt_70.md) | `Fund Score > 70` | `src/scan/rules.py::_annotation_fund_score_gt_70` |
| [annotation_06_resistance_tests_gte_2.md](annotation_06_resistance_tests_gte_2.md) | `Resistance Tests >= 2` | `src/scan/rules.py::_annotation_resistance_tests_gte_2` |
| [annotation_07_recent_power_gap.md](annotation_07_recent_power_gap.md) | `Recent Power Gap` | `src/scan/rules.py::_annotation_recent_power_gap` |


# Annotation Filter Spec: RS 21 >= 63

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `RS 21 >= 63` |
| Implementation owner | `src/scan/rules.py::_annotation_rs21_gte_63` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
rs21 = _raw_rs(row, 21)
matched = bool(pd.notna(rs21) and float(rs21) >= 63.0)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `raw_rs21` (fallback `rs21`) | `src/scoring/rs.py::RSScorer.score` | `float("nan")` via `_raw_rs` | must be `>= 63.0` |


# Annotation Filter Spec: High Est. EPS Growth

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `High Est. EPS Growth` |
| Implementation owner | `src/scan/rules.py::_annotation_high_eps_growth` |
| Output | `bool` |
| Direct config dependencies | `scan.high_eps_growth_rank_threshold` |

## Canonical Boolean Definition

```python
matched = bool(row.get("eps_growth_rank", 0.0) >= config.high_eps_growth_rank_threshold)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `eps_growth_rank` | `src/scan/rules.py::enrich_with_scan_context` | `0.0` | compare against configured threshold |

## Direct Config Dependencies

| Config key | Default |
|---|---|
| `scan.high_eps_growth_rank_threshold` | `90.0` |


# Annotation Filter Spec: PP Count (20d)

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `PP Count (20d)` |
| Accepted alias | `3+ Pocket Pivots (20d)` |
| Implementation owner | `src/scan/rules.py::_annotation_pp_count_20d` |
| Output | `bool` |
| Direct config dependencies | `scan.pp_count_annotation_min` |

## Canonical Boolean Definition

```python
matched = bool(row.get("pp_count_window", 0) >= config.pp_count_annotation_min)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `pp_count_window` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0` | compare against configured threshold |

## Direct Config Dependencies

| Config key | Default |
|---|---|
| `scan.pp_count_annotation_min` | `2` |


# Annotation Filter Spec: Trend Base

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `Trend Base` |
| Implementation owner | `src/scan/rules.py::_annotation_trend_base` |
| Output | `bool` |
| Direct config dependencies | none |

## Canonical Boolean Definition

```python
matched = bool(row.get("trend_base", False))
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `trend_base` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |


# Annotation Filter Spec: Fund Score > 70

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `Fund Score > 70` |
| Implementation owner | `src/scan/rules.py::_annotation_fund_score_gt_70` |
| Output | `bool` |
| Direct config dependencies | none (threshold is hard-coded) |

## Canonical Boolean Definition

```python
matched = bool(row.get("fundamental_score", 0.0) >= 70.0)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `fundamental_score` | `src/scoring/fundamental.py::FundamentalScorer.score` | `0.0` | must be `>= 70.0` |


# Annotation Filter Spec: Resistance Tests >= 2

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `Resistance Tests >= 2` |
| Implementation owner | `src/scan/rules.py::_annotation_resistance_tests_gte_2` |
| Output | `bool` |
| Direct config dependencies | none (threshold is hard-coded) |

## Canonical Boolean Definition

```python
matched = bool(row.get("resistance_test_count", 0.0) >= 2.0)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `resistance_test_count` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | must be `>= 2.0` |


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
