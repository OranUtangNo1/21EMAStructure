# Implementation Plan

## 1. Current Product State

The active screening product is already implemented at the MVP-plus stage. The current codebase includes:

- weekly universe discovery and persistence
- daily data loading with cache and lineage tracking
- full indicator stack required by the active scans
- configurable scan rules and annotation filters
- duplicate ticker aggregation from scan overlap
- Market Dashboard, RS Radar, and Today's Watchlist
- watchlist sidebar preference persistence

This document therefore focuses on the current execution order and the next work phases, not on an unimplemented greenfield plan.

## 2. Current Execution Order

### Phase A: Weekly Universe Discovery

Current behavior:

1. reuse a fresh saved weekly universe snapshot when available
2. otherwise discover a weekly universe live
3. persist the new snapshot locally
4. fall back to the latest stale snapshot if live discovery fails

Primary modules:

- `src/data/finviz_provider.py`
- `src/data/providers.py`
- `src/data/store.py`
- `src/pipeline.py`

Notes:

- Finviz is the default discovery provider
- Yahoo screener discovery is also supported by code

### Phase B: Daily Data Realization

Current behavior:

1. resolve symbols from manual input, snapshots, live discovery, or default symbols
2. load daily price history for active symbols plus benchmark, VIX, radar ETFs, market ETFs, and factor ETFs
3. build profile and fundamental batches from the universe snapshot
4. backfill still-missing profile and fundamental rows from Yahoo Finance
5. apply local universe filters
6. preserve fetch status and source labels

Primary modules:

- `src/data/providers.py`
- `src/data/cache.py`
- `src/data/universe.py`
- `src/data/quality.py`
- `src/pipeline.py`

### Phase C: Indicator And Scoring Calculation

Current behavior:

1. calculate the technical indicator stack
2. calculate SPY-relative strength
3. calculate fundamental, industry, hybrid, and VCS scores
4. derive IPO and earnings context
5. append data-quality fields

Primary modules:

- `src/indicators/core.py`
- `src/scoring/rs.py`
- `src/scoring/fundamental.py`
- `src/scoring/industry.py`
- `src/scoring/hybrid.py`
- `src/scoring/vcs.py`
- `src/pipeline.py`

### Phase D: Candidate Extraction

Current behavior:

1. enrich the eligible snapshot with cross-sectional scan context
2. execute the configured enabled scan rules
3. evaluate the configured annotation filters
4. build the watchlist as the union of scan hits
5. compute annotation flags and hit counts
6. mark duplicate tickers from scan overlap
7. sort the watchlist according to configured mode

Primary modules:

- `src/scan/rules.py`
- `src/scan/runner.py`
- `src/dashboard/watchlist.py`

Notes:

- the default config currently enables 15 scan families
- annotation filters do not create candidates by themselves

### Phase E: Dashboard Packaging

Current behavior:

1. build Market Dashboard artifacts
2. build RS Radar artifacts
3. build raw watchlist, duplicate, and earnings artifacts
4. in the app, rebuild watchlist cards and duplicate output from current sidebar selections
5. render the three Streamlit pages

Primary modules:

- `src/dashboard/market.py`
- `src/dashboard/radar.py`
- `src/dashboard/watchlist.py`
- `src/ui_preferences.py`
- `app/main.py`

## 3. Completed Milestones

Completed in the active product:

- screening-only scope alignment
- duplicate ticker logic based on scan overlap
- scan-card watchlist presentation
- watchlist post-scan filter projection
- RS Radar integration
- Market Dashboard integration
- weekly universe snapshot workflow
- data-quality visibility in the UI

## 4. Next Implementation Phases

### Phase F: Provider Hardening

Priority tasks:

- add an optional secondary provider path beyond the current stack
- improve instrument classification for common-stock purity
- keep weekly discovery and daily scan execution cleanly separated

### Phase G: Historical Review Workflow

Priority tasks:

- compare saved runs inside the app
- inspect recurring duplicate tickers across dates
- inspect changes in sector and industry leadership over time

### Phase H: Formula Governance And Config Cleanup

Priority tasks:

- keep documentation synchronized with code and config changes
- review research formulas against real usage
- prune or clearly mark config keys that are present but inactive in the active scope

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
- do watchlist post-scan filters and duplicate subfilters remain inspectable?
- do VCS and Hybrid improve candidate prioritization without overfitting?
