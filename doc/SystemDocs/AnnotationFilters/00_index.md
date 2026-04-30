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
