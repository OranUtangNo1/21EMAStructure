# System Overview

## 1. Product Definition

OraTek is an active screening and candidate extraction platform for growth-stock research. The implemented product produces four active app outputs:

1. Market Dashboard
2. RS Radar
3. Today's Watchlist
4. Entry Signals

The application helps the user review market context, inspect sector and industry leadership, surface candidate tickers that satisfy one or more scan conditions, and evaluate implemented entry-timing signals on duplicate-ticker candidates.

## 2. Active Scope

The active product scope is limited to:

- weekly universe discovery and reuse
- daily data loading, lineage tracking, and quality visibility
- indicator and scoring calculation
- scan-based candidate extraction
- post-scan watchlist projection in the UI
- duplicate-ticker prioritization from scan overlap
- Market Dashboard, RS Radar, Today's Watchlist, and Entry Signals rendering

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

The application evaluates the configured enabled scan rules on the eligible universe. The default config currently enables 21 scan families.

Tickers enter the raw watchlist only when they pass at least one scan. Annotation filters are also evaluated, but they add flags and counts only; they do not create watchlist candidates on their own.

### 4.5 Duplicate Highlighting And UI Projection

The backend marks `duplicate_ticker` when `scan_hit_count >= duplicate_min_count`.

The Today's Watchlist page then applies page-local projection on top of the raw watchlist:

- selected scan cards
- selected annotation filters
- selected duplicate subfilters
- current duplicate threshold

This UI projection recalculates overlap and duplicate state for the current session without changing the underlying scan hits.

### 4.6 Dashboard Rendering

The four active views consume the same run artifacts:

- Market Dashboard summarizes breadth, performance, factor leadership, and ETF snapshots
- RS Radar summarizes sector and industry ETF leadership plus top RS movers
- Today's Watchlist rebuilds scan cards and duplicate bands from raw watchlist rows plus current sidebar controls
- Entry Signals evaluates enabled entry-timing signals on duplicate tickers sourced from export-enabled presets and the current watchlist selection

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

## 6. Active System Layers

### 6.1 Data Layer

Responsibilities:

- weekly universe discovery
- price, profile, and fundamental loading
- cache reuse and stale-cache fallback
- universe snapshot persistence
- run snapshot persistence

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
- page-local control persistence for the watchlist sidebar

## 7. Current Implementation Stance

The active OraTek product should be understood as a working screener with configurable research formulas. It is not a trade execution engine. The core problem it solves is daily screening and prioritization, not final discretionary trade management.
