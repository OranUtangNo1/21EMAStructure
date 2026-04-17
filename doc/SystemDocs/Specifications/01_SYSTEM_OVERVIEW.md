# System Overview

## 1. Product Definition

OraTek is an active screening, candidate extraction, and preset-performance review platform for growth-stock research. The implemented product produces five active app outputs:

1. Market Dashboard
2. RS Radar
3. Today's Watchlist
4. Entry Signals
5. Tracking Analytics

The application helps the user review market context, inspect sector and industry leadership, surface candidate tickers that satisfy one or more scan conditions, evaluate implemented entry-timing signals on selected candidate universes, and analyze the forward performance of preset hits.

## 2. Active Scope

The active product scope is limited to:

- weekly universe discovery and reuse
- daily data loading, lineage tracking, and quality visibility
- indicator and scoring calculation
- scan-based candidate extraction
- post-scan watchlist projection in the UI
- duplicate-ticker prioritization from scan overlap
- Market Dashboard, RS Radar, Today's Watchlist, Entry Signals, and Tracking Analytics rendering
- SQLite-backed preset-hit tracking for 1, 5, 10, and 20 business-day outcomes

## 3. Out-Of-Scope Areas

The active product does not implement:

- final entry confirmation
- chart-structure review for execution
- position sizing
- stop placement
- exit management
- portfolio-level risk management

Those topics remain archived research material and are not active application behavior.

## 4. Current End-To-End Workflow

### 4.1 Symbol Resolution And Weekly Universe Discovery

`ResearchPlatform.run()` resolves the active symbol set in this order:

1. manual symbols passed from the app
2. fresh weekly universe snapshot when `universe_discovery.enabled` and `use_snapshot_when_no_manual_symbols` are both true
3. live universe discovery
4. stale weekly universe snapshot when live discovery fails
5. `app.default_symbols`

The default weekly discovery provider is Finviz. The code also supports a Yahoo screener path through `universe_discovery.provider`.

### 4.2 Daily Data Loading

For the resolved universe, the application loads:

- stock price history
- benchmark history (`SPY` by default)
- VIX history (`^VIX` by default)
- RS Radar ETF histories
- Market Dashboard ETF histories
- factor ETF histories

The app can request `Force Price Data Refresh`, which bypasses the price-cache TTL for this run while still using existing cached price rows as a merge base and fallback when live refresh fails.

Profile and fundamental fields are sourced from the current weekly universe snapshot first, then filled from Yahoo Finance fallback providers when missing.

### 4.3 Snapshot, Indicators, Scores, And Data Quality

The pipeline:

1. calculates the indicator history for every available symbol
2. builds a latest-row snapshot
3. attaches fetch-status source, note, and timestamp columns
4. calculates RS, Fundamental, Industry, Hybrid, and VCS scores
5. derives IPO and earnings context fields
6. appends data-quality fields

### 4.4 Candidate Extraction

The application evaluates the configured enabled scan rules on the eligible universe. The default config currently enables 18 scan families.

Tickers enter the raw watchlist only when they pass at least one scan. Annotation filters are also evaluated, but they add flags and counts only; they do not create watchlist candidates on their own.

### 4.5 Duplicate Highlighting And UI Projection

The backend marks `duplicate_ticker` when `scan_hit_count >= duplicate_min_count`.

The Today's Watchlist page then applies page-local projection on top of the raw watchlist:

- selected required and optional scan cards
- selected annotation filters
- selected duplicate subfilters
- current duplicate rule

This UI projection recalculates overlap and duplicate state for the current session without changing the underlying scan hits.

### 4.6 Tracking Persistence

Each pipeline recompute syncs preset duplicate hits into `data_runs/tracking.db` for built-in presets that are export-enabled. The tracking grain is detection-oriented:

- `hit_date x preset_name x ticker` is unique
- only one active detection is allowed per `preset_name x ticker`
- repeated same-preset hits for the same active ticker do not create a new active tracking row
- forward prices and returns are filled for 1, 5, 10, and 20 business-day target horizons when price history becomes available

Legacy CSV files under `data_runs/preset_effectiveness/` can be backfilled into the database through the migration helper, but SQLite is the current tracking store.

### 4.7 Dashboard Rendering

The active views consume the same run artifacts plus the tracking database where relevant:

- Market Dashboard summarizes breadth, performance, factor leadership, and ETF snapshots
- RS Radar summarizes sector and industry ETF leadership plus top RS movers
- Today's Watchlist rebuilds scan cards and duplicate bands from raw watchlist rows plus current sidebar controls
- Entry Signals evaluates enabled entry-timing signals on the page-selected signal universe: preset duplicates, current-selection duplicates, both duplicate sources, Today's Watchlist, or the eligible universe
- Tracking Analytics reads detection detail from SQLite, filters by preset universe, horizon, hit-date range, market environment, and benchmark, and displays preset ranking plus row-level detail

## 5. Core Design Principles

### 5.1 Code And Config Are Authoritative

The source of truth for current behavior is:

- implementation in `src/` and `app/`
- runtime defaults rooted at `config/default.yaml`
- section-level defaults split under `config/default/`

### 5.2 Replaceable Research Logic

Non-public or uncertain logic remains configurable rather than fixed. This includes:

- universe discovery provider choice
- fundamental scoring details
- industry scoring details
- VCS details
- market condition component tuning
- scan thresholds and sort preferences

### 5.3 Data Lineage Is Product Behavior

Fetch status and source labels are not incidental logging. The product exposes fetch-state lineage such as `live`, `cache_fresh`, `cache_stale`, `sample`, and `missing`, and it collapses those states into short app labels such as `live`, `live + cache`, `sample fallback`, `live + sample fallback`, `missing`, or `mixed`.

### 5.4 Analysis Is Derived From Recorded Detections

Preset performance analysis is based on recorded preset-hit detections, not on the current preset definition alone. If a preset is renamed or its scan composition changes later, old detections remain analyzable as historical records but their interpretation depends on the recorded `preset_name`, hit scans, filters, and market environment available at detection time.

## 6. Active System Layers

### 6.1 Data Layer

Responsibilities:

- weekly universe discovery
- price, profile, and fundamental loading
- cache reuse and stale-cache fallback
- universe snapshot persistence
- run snapshot persistence
- SQLite tracking database initialization, migration, and read access

### 6.2 Indicator And Scoring Layer

Responsibilities:

- technical indicator calculation
- SPY-relative strength calculation
- fundamental, industry, hybrid, and VCS scoring
- latest-row quality and context fields

### 6.3 Scan Layer

Responsibilities:

- scan evaluation
- annotation evaluation
- watchlist aggregation
- duplicate marking

### 6.4 Dashboard And App Layer

Responsibilities:

- Market Dashboard result shaping
- RS Radar result shaping
- watchlist projection and ticker-card rendering
- entry-signal result shaping
- preset-effectiveness sync and tracking analytics display
- page-local control persistence for the watchlist sidebar

## 7. Current Implementation Stance

The active OraTek product should be understood as a working screener with configurable research formulas. It is not a trade execution engine. The core problem it solves is daily screening and prioritization, not final discretionary trade management.
