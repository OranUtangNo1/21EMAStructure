# Scan and Watchlist Spec

## 1. Purpose

This document defines the stable backend watchlist workflow and the current UI projection rules built on top of it.

Important principle:

- backend watchlist generation is stable product behavior
- the concrete scan family can change through config and implementation updates
- exact per-scan formulas live under `doc/SystemDocs/Scan/`
- the watchlist page adds a display-layer projection on top of the raw watchlist

Primary scan reference:

- `doc/SystemDocs/Scan/scan_00_index.md`

## 2. Backend Watchlist Workflow

### 2.1 Eligible snapshot

Before any scan or annotation rule runs, `UniverseBuilder.filter()` applies the active local universe filter.

Current default filter:

- `market_cap >= 1B`
- `avg_volume_50d >= 1M`
- `close >= 0.0`
- `adr_percent` between `3.5` and `10.0`
- sector exclusion: `Healthcare`

All scan rules and annotation rules run only on this eligible snapshot.

### 2.2 Scan-context enrichment

`ScanRunner.run()` first calls `enrich_with_scan_context()` on the eligible snapshot.

Current enrichment fields:

- `weekly_return_rank = percent_rank(weekly_return)`
- `quarterly_return_rank = percent_rank(quarterly_return)`
- `eps_growth_rank = percent_rank(eps_growth)` when `eps_growth` exists, otherwise `NaN`

These are cross-sectional ranks over the current eligible snapshot.

### 2.3 Watchlist eligibility

The raw watchlist candidate set is determined only by enabled scan rules.

Current implemented rule:

- evaluate all enabled scan rules on the eligible snapshot
- create one `scan_hits` row per matched scan per ticker
- compute `scan_hit_count` per ticker
- keep only tickers where `scan_hit_count > 0`

This means:

- scan hits create watchlist candidates
- annotation hits do not create watchlist candidates by themselves

### 2.4 Annotation evaluation

The application also evaluates configured annotation filters on the same eligible snapshot.

Current implemented behavior:

- annotation filters are defined by `scan.annotation_filters`
- the default config ships five available filters:
  - `RS 21 >= 63`
  - `High Est. EPS Growth`
  - `PP Count (20d)`
  - `Trend Base`
  - `Fund Score > 70`
- the default config enables none of them at runtime because `enabled_annotation_filters` is `[]`
- annotation results are attached to the raw watchlist as:
  - one boolean column per configured filter
  - `annotation_hits`
  - `annotation_hit_count`

Compatibility fields remain in the raw watchlist:

- `hit_lists = hit_scans`
- `list_overlap_count = scan_hit_count`
- `hit_count = scan_hit_count`

These compatibility aliases do not represent a separate list engine.

### 2.5 Duplicate tickers

Backend duplicate logic is based on scan overlap only.

Current implemented rule:

- `scan_hit_count = number of raw scan hits for the ticker`
- `overlap_count = scan_hit_count`
- `duplicate_ticker = scan_hit_count >= duplicate_min_count`

The backend duplicate flag is not derived from annotation filters.

### 2.6 Watchlist sorting

The runner sorts the final raw watchlist after scan eligibility and duplicate marking.

Default config uses `watchlist_sort_mode: hybrid_score`.

This produces the default priority:

1. `hybrid_score`
2. `overlap_count`
3. `vcs`
4. `rs21`

If `watchlist_sort_mode = overlap_then_hybrid`, the priority becomes:

1. `overlap_count`
2. `hybrid_score`
3. `vcs`
4. `rs21`

## 3. Current Today's Watchlist UI Projection

### 3.1 Sidebar-driven state

The page builds a projected watchlist from raw artifacts plus page-local controls.

Current controls:

- required scan cards
- optional scan cards
- selected annotation filters
- selected duplicate subfilters
- optional threshold

These values are persisted under the `watchlist_controls` group in the user-preferences store and are namespaced by the resolved config path.

Named presets come from two sources:

- built-in presets defined in `scan.watchlist_presets`
- saved presets stored under the `watchlist_presets` group in the same namespace

Current preset behavior:

- record shape: `schema_version`, `kind`, `values`
- `kind` is currently `watchlist_controls`
- `values` stores the watchlist control fields plus an editable `duplicate_rule` payload
- the active UI supports save, load, update, and delete
- built-in presets use `preset_status` to control UI visibility and automatic export participation
- only built-in presets with `preset_status: enabled` appear in the preset picker
- built-in presets with `preset_status: enabled` or `preset_status: hidden_enabled` are included in automatic preset CSV export and preset-hit listing
- saved custom presets are included in preset-hit listing and preset CSV export
- built-in presets with `preset_status: disabled` are skipped by the preset picker, preset-hit listing, and automatic preset CSV export
- built-in presets can be loaded and exported but not deleted or updated from the UI
- at most 10 presets are stored per config namespace
- preset load drops any saved preset that references scan names no longer available in the current config
- invalid annotation filters are ignored during preset load
- optional threshold is clamped to the optional-card count
- `selected_scan_names` remains the persisted union of required scans and condition-group scans for compatibility

### 3.2 Annotation-filter projection

`WatchlistViewModelBuilder.filter_by_annotation_filters()` applies selected annotation filters with `AND` semantics.

Current implemented behavior:

- no selected filters -> raw watchlist passes through unchanged
- one or more selected filters -> keep only rows where every selected boolean annotation column is true
- missing annotation columns are treated as false

This projection narrows the displayed watchlist only. It does not rewrite raw scan hits.

### 3.3 Selected-scan projection

`WatchlistViewModelBuilder.apply_selected_scan_metrics()` recalculates display-only overlap state from selected scan names.

Current projected fields:

- `selected_scan_hit_count`
- `selected_overlap_count`
- `duplicate_ticker`
- `overlap_count`

Current implemented behavior:

- selected scans are filtered from raw `scan_hits`
- `duplicate_ticker` is recalculated from the current duplicate rule
- supported duplicate-rule modes:
  - `min_count`
  - `required_plus_optional_min`
  - `grouped_threshold`
- `grouped_threshold` requires every scan in `required_scans` and every configured `optional_groups` threshold
- each `optional_groups` item has `group_name`, `scans`, and `min_hits`
- the UI builds `grouped_threshold` when condition groups are configured
- legacy `required_plus_optional_min` remains accepted and maps to one condition group in the UI
- the UI uses `min_count` for simple optional-only legacy selections
- `overlap_count` is overwritten with the selected-scan overlap count
- if no scan cards are selected, the projection forces:
  - `selected_scan_hit_count = 0`
  - `selected_overlap_count = 0`
  - `overlap_count = 0`
  - `duplicate_ticker = False`

This means the card-level duplicate flag shown in the UI is a projected session value, not always the raw backend duplicate flag.

### 3.4 Duplicate band

The duplicate band is a second display-layer projection on top of the projected watchlist.

Current implemented behavior:

- start from the projected watchlist after annotation filtering and selected-scan recomputation
- keep only rows where projected `duplicate_ticker` is true
- optional duplicate subfilters run after thresholding
- current supported duplicate subfilter:
  - `Top3 HybridRS`

`Top3 HybridRS` sorts by:

1. `hybrid_score`
2. `selected_scan_hit_count`
3. `selected_overlap_count`
4. `vcs` when present

and keeps the top three rows.

Preset-hit behavior uses each preset's own annotation filters and duplicate rule.

The Watchlist page exposes a `Preset Hits` panel that lists tickers that satisfy any active built-in or saved custom preset.

`preset_summary.csv` uses one row per output ticker. The `hit_presets` column lists the built-in and custom presets that emitted that ticker, and the selected scan, annotation, duplicate-threshold, and duplicate-rule columns summarize the unique settings across those hit presets.

`preset_hits.csv` uses one row per `preset_name x ticker` hit and includes `preset_source`, matched scans, selected scans, annotation filters, duplicate threshold, duplicate-rule mode, and score columns when available.

`preset_details.csv` uses one row per preset and preserves the legacy wide format with `Duplicate Tickers` and `<display_name> Hit Tickers` columns.

Automatic preset CSV export runs after a full pipeline recompute and writes under `scan.preset_csv_export.output_dir` using the trade-date folder. Saved-run restore does not create new preset CSV files. The Watchlist page also has a manual `Write preset CSV files` action that writes the same files.

### 3.5 Preset tracking database

The app also maintains a cumulative SQLite tracking store for built-in watchlist presets that are export-enabled.

Current implemented behavior:

- database path: `data_runs/tracking.db`
- rows are written only for duplicate tickers produced by each export-enabled preset's own duplicate rule
- detection grain is `hit_date x preset_name x ticker`
- the database enforces one active row per `preset_name x ticker`
- detection rows store detection-time fields such as `market_env`, `close_at_hit`, `rs21_at_hit`, `vcs_at_hit`, `atr_at_hit`, `hybrid_score_at_hit`, and `duplicate_hit_count`
- hit scan names are stored in `detection_scans`
- selected annotation filters are stored in `detection_filters`
- forward horizons are fixed at `1d`, `5d`, `10d`, and `20d`
- forward closes are stored as `close_at_1d`, `close_at_5d`, `close_at_10d`, and `close_at_20d`
- forward returns are stored as `return_1d`, `return_5d`, `return_10d`, and `return_20d`
- horizon dates are calculated from `hit_date + BDay(horizon_days)`
- return fields are updated on later runs when price history for the target date or a later available trading day exists
- a detection is closed after the 20D horizon is filled
- date-level scan-hit history is stored in the same database table `scan_hits`

Legacy CSVs under `data_runs/preset_effectiveness/` are migration inputs only. They are not the current authoritative tracking store.

### 3.6 Scan-card grid

The watchlist page rebuilds scan cards from raw `scan_hits` plus the projected watchlist. It does not use the prebuilt `artifacts.watchlist_cards`.

Current implemented behavior:

- cards are built from `scan.card_sections`
- only scan-based cards are supported
- selected scan names determine which cards render
- each card shows ticker symbols only
- card ticker order follows each section's configured `sort_columns`

## 4. Current Scan Reference Model

The numbered specifications do not duplicate scan-level formulas.

Instead:

- one scan is documented in one file under `doc/SystemDocs/Scan/`
- `doc/SystemDocs/Scan/scan_00_index.md` is the entry point
- scan availability is controlled by `scan_status_map`
- only scans marked `enabled` are evaluated and exposed through watchlist card selection
- legacy `enabled_scan_rules` is still accepted as a backward-compatible active-scan list
- available annotation-filter definitions are controlled by `annotation_filters`
- startup-enabled annotation filters come from `enabled_annotation_filters`
- the legacy config alias `enabled_list_rules` is still accepted for backward compatibility
- if `enabled_annotation_filters` mistakenly includes scan names, the loader moves those names into the enabled scan rule set and keeps only real annotation filters in the enabled annotation set
- built-in presets that reference any non-enabled scan are forced to `preset_status: disabled`

## 5. Active Watchlist Outputs

### 5.1 Raw backend watchlist fields

The raw watchlist produced by `ScanRunner.run()` currently carries these backend-oriented fields when available:

- `hit_scans`
- `scan_hit_count`
- `overlap_count`
- `hit_lists`
- `list_overlap_count`
- `hit_count`
- `duplicate_ticker`
- `annotation_hits`
- `annotation_hit_count`
- one boolean column per configured annotation filter

Raw `duplicate_ticker` is the backend/global duplicate flag:

```text
scan_hit_count >= scan.duplicate_min_count
```

It is calculated across all enabled scan hits, not from the current Watchlist UI preset or selected-card state.

`annotation_hits` lists only annotation filters that matched that ticker. The boolean annotation columns contain the full per-filter true/false state.

### 5.2 Display watchlist table fields

`WatchlistViewModelBuilder.build()` currently exposes these columns when present:

- `name`
- `sector`
- `industry`
- `watchlist_candidate_reason`
- `H`, `F`, `I`, `21`, `63`, `126`
- `rs5`
- `overlap_count`
- `scan_hit_count`
- `annotation_hit_count`
- `backend_duplicate_ticker`
- `backend_duplicate_rule`
- `duplicate_ticker`
- `hit_scans`
- `matched_scan_rules`
- `annotation_hits`
- `matched_annotation_filters`
- `vcs`
- `dist_from_52w_high`
- `dist_from_52w_low`
- `ud_volume_ratio`
- `earnings`
- `pp_count_window`
- `ema21_low_pct`
- `atr_21ema_zone`
- `atr_50sma_zone`
- `three_weeks_tight`
- `atr_pct_from_50sma`
- `price_data_source`
- `fundamental_data_source`
- `data_quality_label`
- `data_quality_score`
- `data_warning`
- one boolean column per configured annotation filter

`backend_duplicate_ticker` and `backend_duplicate_rule` are explicit persistence aliases for the raw/global duplicate calculation. `duplicate_ticker` remains for backward compatibility and is still overwritten by UI projection when current controls are applied.

`matched_scan_rules` is an explicit alias of `hit_scans`. `matched_annotation_filters` is an explicit alias of `annotation_hits`; it intentionally differs by ticker because it lists only the annotation filters that evaluated true for that ticker.

## 6. Watchlist Generation Sequence

Current end-to-end sequence:

1. resolve the active symbols
2. load prices, profile data, and fundamentals
3. build indicator histories
4. build the latest snapshot
5. apply status, score, earnings, and data-quality enrichment
6. apply the local universe filter
7. enrich the eligible snapshot with scan-context ranks
8. evaluate enabled scan rules and configured annotation filters
9. keep only symbols with `scan_hit_count > 0`
10. mark backend duplicate tickers from scan overlap
11. sort the raw watchlist
12. in the app, project the raw watchlist through required and optional scan names, annotation filters, duplicate subfilters, and the current duplicate rule

## 7. Configurable Areas

The active implementation keeps these areas configurable:

- scan thresholds
- enabled scan rules
- available annotation filters
- enabled annotation filters
- card sections and their display names
- built-in watchlist presets
- startup-selected watchlist cards loaded as optional cards
- backend duplicate minimum count
- watchlist sort mode
- universe thresholds
- UI-selected required and optional scan subsets for display and duplicate counting
- UI-selected annotation filters for display narrowing
- UI optional threshold for the current page session
- UI duplicate-only subfilters for the current page session
