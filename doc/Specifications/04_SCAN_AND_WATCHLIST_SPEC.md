# Scan and Watchlist Spec

## 1. Purpose

This document defines the stable watchlist-generation workflow.

Important principle:

- the watchlist workflow is stable product behavior
- the concrete scan family can change over time through config and implementation updates
- detailed scan definitions are not duplicated in this specification
- exact per-scan definitions live under `doc/Scan/`

Primary scan reference:

- `doc/Scan/scan_00_index.md`

That index links to one document per scan.

---

## 2. Stable watchlist workflow

### 2.1 Eligible snapshot

Before any scan or annotation rule runs, `UniverseBuilder.filter()` applies the active local universe filter.

Current default filter:

- `market_cap >= 1B`
- `avg_volume_50d >= 1M`
- `close >= min_price` where the current default is `0.0`
- `adr_percent` between `3.5` and `10.0`
- sector exclusion: `Healthcare`

All scan rules and annotation rules run only on this eligible snapshot.

### 2.2 Watchlist eligibility

The watchlist candidate set is determined only by enabled scan rules.

Current implemented rule:

- evaluate all enabled scan rules on the eligible snapshot
- create `scan_hit_count` for each ticker
- keep only tickers where `scan_hit_count > 0`

This means:

- scan hits create watchlist candidates
- annotation hits do not create watchlist candidates by themselves

### 2.3 Supporting annotations

The application also evaluates configured annotation rules on the same eligible snapshot.

Current implemented behavior:

- annotation rules are still evaluated in the scan pipeline
- annotation results are not used to populate the watchlist overlap aliases
- `hit_lists` now mirrors `hit_scans` for compatibility
- `list_overlap_count` now mirrors `scan_hit_count` for compatibility

The current annotation family and scan-to-list relationships are documented in `doc/Scan/scan_00_index.md`.

### 2.4 Duplicate tickers

Backend duplicate logic is based on scan overlap only.

Current implemented rule:

- `scan_hit_count = number of unique scan hits for the ticker`
- `overlap_count = scan_hit_count`
- `hit_lists = hit_scans` as a compatibility alias
- `list_overlap_count = scan_hit_count` as a compatibility alias
- `duplicate_ticker = scan_hit_count >= duplicate_min_count`

The backend duplicate flag is not derived from annotation lists.

### 2.5 Watchlist sorting

The runner sorts the final watchlist after scan eligibility and duplicate marking.

Default config uses `watchlist_sort_mode: hybrid_score`.

This produces the active default sort priority:

1. `hybrid_score`
2. `overlap_count`
3. `vcs`
4. `rs21`

If `watchlist_sort_mode = overlap_then_hybrid`, the sort priority becomes:

1. `overlap_count`
2. `hybrid_score`
3. `vcs`
4. `rs21`

---

## 3. Watchlist UI behavior

### 3.1 Card rendering

The Today's Watchlist page renders scan cards only.

Current implemented behavior:

- cards are built from `scan.card_sections`
- each card corresponds to one configured scan name
- each card shows the subset of watchlist rows that hit that scan
- detailed card meaning is defined by the referenced scan document in `doc/Scan/`

### 3.2 Card selection

The UI allows the user to choose which configured scan cards are active in the current view.

Current implemented behavior:

- selected cards control which watchlist cards are displayed
- this selection does not change the underlying watchlist candidate set
- unselected cards are hidden from the page, but their symbols remain in the watchlist if they passed any enabled scan

### 3.3 Duplicate band in the UI

The UI duplicate band is a presentation-layer recomputation based on selected cards.

Current implemented behavior:

- the page recomputes duplicate tickers from raw scan hits filtered to the currently selected cards
- the page allows a user-selected duplicate threshold
- this UI threshold does not change backend watchlist eligibility
- this UI threshold does not rewrite the stored `duplicate_ticker` field on raw watchlist rows

Therefore two duplicate concepts coexist:

- backend duplicate flag: fixed by `duplicate_min_count` in the scan config
- UI duplicate band: recalculated from selected cards plus the current sidebar threshold

---

## 4. Current scan reference model

The numbered specifications no longer duplicate scan-level formulas.

Instead:

- one scan is documented in one file under `doc/Scan/`
- `doc/Scan/scan_00_index.md` is the entry point
- active scan availability is controlled by `enabled_scan_rules`
- active annotation availability is controlled by `enabled_list_rules`

This structure is intended to reduce maintenance when scan types are added, removed, renamed, or reworked.

---

## 5. Watchlist generation sequence

Current end-to-end sequence:

1. resolve the active symbols
2. load prices, profile data, and fundamentals
3. build indicator histories
4. build the latest snapshot
5. apply scoring: RS, Fundamental, Industry, Hybrid, VCS
6. apply the local universe filter
7. evaluate enabled scan rules and enabled annotation rules
8. keep only symbols with `scan_hit_count > 0`
9. mark backend duplicate tickers from scan overlap
10. sort the watchlist
11. build scan cards, the duplicate band, and earnings rows for the UI

---

## 6. Active watchlist outputs

The display-oriented watchlist table currently exposes these fields when available:

- `name`
- `sector`
- `industry`
- `H`, `F`, `I`, `21`, `63`, `126`
- `rs5`
- `overlap_count`
- `scan_hit_count`
- `list_overlap_count`
- `duplicate_ticker`
- `hit_scans`
- `hit_lists`
- `vcs`
- `earnings`
- `pp_count_30d`
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

---

## 7. Configurable areas

The active implementation keeps these areas configurable:

- scan thresholds
- enabled scan rules
- enabled annotation rules
- card sections and their display names
- backend duplicate minimum count
- watchlist sort mode
- universe thresholds
- UI-selected card subset for display and duplicate-band counting
- UI duplicate threshold for the current page session
