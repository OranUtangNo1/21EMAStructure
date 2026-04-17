# Watchlist And Preset Ticker Detection Architecture

## Scope
- This document covers only the ticker detection flow for Today's Watchlist and watchlist presets.
- Included: scan execution model, annotation filter model, preset application model, duplicate ticker decision model.
- Excluded: per-scan formula details, per-filter threshold details, and UI behavior.

## Core Modules
- `src/pipeline.py`
  - Orchestrates end-to-end run and produces `PlatformArtifacts`.
  - Invokes scan stage and watchlist projection stage.
- `src/scan/rules.py`
  - Defines scan rule registry, annotation filter registry, and watchlist preset config schema.
  - Owns duplicate rule schema (`min_count` and `required_plus_optional_min`).
- `src/scan/runner.py`
  - Executes scan rules and annotation filters per ticker.
  - Produces normalized outputs: `hits` and `watchlist`.
- `src/dashboard/watchlist.py`
  - Applies annotation filters, selected scan scope, and duplicate rules to derive final ticker sets.
  - Builds duplicate ticker table and scan-card ticker subsets.

## Data Contract Between Stages
- Input to scan stage: `eligible_snapshot` (one latest row per ticker with indicators and scores).
- `ScanRunner` output:
  - `hits`: long-form table of scan matches (`ticker`, `kind`, `name`).
  - `watchlist`: ticker-indexed frame with scan context plus annotation boolean columns.
- Watchlist builder output:
  - Filtered/projected watchlist for selected preset or current control state.
  - Duplicate ticker table based on selected scans and duplicate rule.

## Detection Flow
1. Pipeline builds `eligible_snapshot` from data, indicators, and scoring layers.
2. `ScanRunner.run()` evaluates all enabled scan rules per ticker and records positive scan hits.
3. In the same pass, annotation filters are evaluated per ticker and stored as boolean columns in watchlist rows.
4. `ScanRunner` keeps only tickers with at least one scan hit and computes scan hit counts.
5. `WatchlistViewModelBuilder.filter_by_annotation_filters()` applies selected annotation filters as post-scan gates.
6. `WatchlistViewModelBuilder.apply_selected_scan_metrics()` projects overlap counts for selected scan set.
7. `WatchlistViewModelBuilder.build_duplicate_tickers()` applies duplicate rule logic and returns final duplicate ticker list.

## Scan Model (Conceptual)
- Scans are primary candidate generators.
- Each scan is an independently named boolean rule in `SCAN_RULE_REGISTRY`.
- A ticker enters the watchlist candidate pool only through positive scan hits.

## Annotation Filter Model (Conceptual)
- Annotation filters are post-scan constraints, not primary generators.
- Filters are evaluated for all tickers, then applied only when a preset/control selects them.
- Effective behavior is intersection across selected filters (AND semantics).

## Preset Model (Conceptual)
- Presets define:
  - selected scan names,
  - selected annotation filters,
  - duplicate threshold and duplicate rule mode.
- Preset rules are validated against active scan/filter definitions at config load time.
- Presets may be auto-disabled when they reference inactive scans.

## Duplicate Ticker Decision Model
- Mode `min_count`:
  - ticker is duplicate when unique hit count across selected scans is at least `min_count`.
- Mode `required_plus_optional_min`:
  - ticker must hit all required scans and at least `optional_min_hits` optional scans.
- Duplicate decision always runs on scan hits after annotation-filter projection.

## Change-Safe Extension Points
- Add or change scan logic in `SCAN_RULE_REGISTRY` and associated evaluator in `src/scan/rules.py`.
- Add or change annotation logic in `ANNOTATION_FILTER_REGISTRY` and column mapping in `ANNOTATION_FILTER_COLUMN_NAMES`.
- Change preset semantics through `WatchlistPresetConfig` and `DuplicateRuleConfig`.
- Keep tests aligned in:
  - `tests/test_scan.py`
  - `tests/test_configuration.py`
  - `tests/test_app_watchlist_presets.py`
