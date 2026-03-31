# Implementation Plan

## 1. Current Product State

The active screening product is already implemented at the MVP-plus stage. The current codebase includes:

- weekly universe discovery and persistence
- daily data loading with cache and lineage tracking
- full indicator stack required by the active scans
- nine scan rules and annotation lists
- duplicate ticker aggregation from scan overlap
- Market Dashboard, RS Radar, and Today's Watchlist

This document therefore focuses on the current execution order and the next work phases, not on an unimplemented greenfield plan.

## 2. Current Execution Order

### Phase A: Weekly Universe Discovery

Current behavior:

1. discover a weekly universe snapshot with Finviz
2. persist the snapshot locally
3. reuse the latest snapshot until refresh is required

Primary modules:

- `src/data/finviz_provider.py`
- `src/data/store.py`
- `src/pipeline.py`

### Phase B: Daily Data Realization

Current behavior:

1. resolve symbols from the latest weekly snapshot or manual override
2. load daily price history from Yahoo Finance
3. load or backfill profile and fundamental fields
4. apply local universe filters
5. preserve fetch status and source labels

Primary modules:

- `src/data/providers.py`
- `src/data/cache.py`
- `src/data/universe.py`
- `src/pipeline.py`

### Phase C: Indicator And Scoring Calculation

Current behavior:

1. calculate the technical indicator stack
2. calculate SPY-relative strength
3. calculate fundamental, industry, hybrid, and VCS scores
4. enrich the snapshot with scan context columns

Primary modules:

- `src/indicators/core.py`
- `src/scoring/rs.py`
- `src/scoring/fundamental.py`
- `src/scoring/industry.py`
- `src/scoring/hybrid.py`
- `src/scoring/vcs.py`
- `src/scan/rules.py`

### Phase D: Candidate Extraction

Current behavior:

1. execute the nine active scan rules
2. build the watchlist as the union of scan hits
3. compute annotation-style list hits
4. mark duplicate tickers from scan overlap
5. sort the watchlist according to configured mode

Primary modules:

- `src/scan/rules.py`
- `src/scan/runner.py`
- `src/dashboard/watchlist.py`

### Phase E: Dashboard Packaging

Current behavior:

1. build the Market Dashboard artifacts
2. build the RS Radar artifacts
3. build the watchlist card artifacts
4. render the three pages in Streamlit

Primary modules:

- `src/dashboard/market.py`
- `src/dashboard/radar.py`
- `src/dashboard/watchlist.py`
- `app/main.py`

## 3. Completed Milestones

Completed in the active product:

- screening-only scope alignment
- duplicate ticker logic based on scan overlap
- scan-card watchlist presentation
- RS Radar integration inside the dashboard
- Market Dashboard integration inside the dashboard
- weekly universe snapshot workflow
- data-quality visibility in the UI

## 4. Next Implementation Phases

### Phase F: Provider Hardening

Priority tasks:

- add an optional secondary provider path
- improve instrument classification for common-stock purity
- keep weekly discovery and daily scan execution cleanly separated

### Phase G: Historical Review Workflow

Priority tasks:

- compare saved runs inside the app
- inspect recurring duplicate tickers across dates
- inspect changes in sector and industry leadership over time

### Phase H: Formula Governance

Priority tasks:

- keep documentation synchronized with code and config changes
- review the behavior of research formulas against real usage
- make parameter changes easier to audit across runs

## 5. Explicit Non-Goals For The Active Plan

The following are not part of the active implementation plan:

- entry evaluation workflows
- structure-pivot workflows
- position sizing workflows
- phased exit workflows
- trade execution workflows

These remain out of scope for the active screening product.

## 6. Practical Validation Questions

The next rounds of work should continue to test these questions:

- is the weekly universe of sufficient quality for the daily scan workflow?
- are duplicate tickers a useful prioritization signal?
- does the current market score align with practical market review?
- do RS Radar tables surface useful sector and industry leadership?
- do VCS and Hybrid improve candidate prioritization without overfitting?
