# 09. Current Status And Roadmap

## 1. Summary

As of March 31, 2026, the active OraTek system is a working screening and candidate extraction platform. The implemented outputs are:

1. Market Dashboard
2. RS Radar
3. Today's Watchlist

The current implementation already covers:

- weekly universe discovery and snapshot persistence
- daily price loading with cache and data lineage labels
- local indicator and scoring calculation
- nine scan rules for candidate extraction
- duplicate ticker detection from scan overlap
- market, radar, and watchlist Streamlit views

The active system does not implement trade entry, position sizing, or exit management as product behavior. Those topics remain archived research material.

## 2. Implemented System State

### 2.1 Data Layer

Implemented modules:

- `src/data/finviz_provider.py`
- `src/data/providers.py`
- `src/data/cache.py`
- `src/data/store.py`
- `src/data/universe.py`

Current behavior:

- weekly universe discovery uses Finviz by default
- daily price data is loaded from Yahoo Finance
- profile and fundamental fields are taken from the weekly snapshot when available and filled from Yahoo fallback providers when missing
- cache lineage is preserved as `live`, `cache_fresh`, `cache_stale`, `snapshot`, `sample`, or `missing`
- run metadata and snapshots are persisted under `data_runs/`

### 2.2 Indicator And Scoring Layer

Implemented modules:

- `src/indicators/core.py`
- `src/scoring/rs.py`
- `src/scoring/fundamental.py`
- `src/scoring/industry.py`
- `src/scoring/hybrid.py`
- `src/scoring/vcs.py`

Current behavior:

- 21EMA, SMA, ATR, ADR, DCR, RSI, return horizons, pocket pivot, PP count, trend base, and 3WT are computed from daily price history
- raw RS and normalized RS are computed versus SPY
- fundamental, industry, hybrid, and VCS values are computed with configurable research formulas

### 2.3 Candidate Extraction Layer

Implemented modules:

- `src/scan/rules.py`
- `src/scan/runner.py`
- `src/dashboard/watchlist.py`

Current behavior:

- nine scan rules are executed against the eligible universe
- the watchlist is the union of all scan hits
- duplicate tickers are determined from scan overlap only
- list-style annotations are computed separately and do not control watchlist eligibility

### 2.4 Dashboard Layer

Implemented modules:

- `src/dashboard/market.py`
- `src/dashboard/radar.py`
- `src/dashboard/watchlist.py`
- `app/main.py`

Current behavior:

- Market Dashboard is active
- RS Radar is active
- Today's Watchlist is active
- the old chart, cockpit, and entry workflow are not part of the active application

## 3. What Is Still Research-Oriented

The following parts are implemented but should still be treated as configurable research logic, not fixed truth:

- exact fundamental score formula
- exact industry score aggregation formula
- hybrid missing-value handling policy and weights
- VCS formula details
- market condition component design and thresholds
- universe discovery heuristics from third-party providers

These areas are intentionally parameterized in `config/default.yaml` and modularized in the scoring and dashboard packages.

## 4. Main Remaining Gaps

### 4.1 Provider Depth

Current implementation is good enough for screening workflows, but provider depth is still limited.

Remaining gaps:

- no FMP provider chain yet
- no dedicated security master for strict common-stock classification
- universe quality still depends on screener heuristics and local exclusion rules

### 4.2 Historical Review Workflow

The system writes run artifacts, but comparison workflows are still thin.

Remaining gaps:

- no dedicated run-to-run comparison UI
- no daily watchlist archive explorer in the app
- no historical scan hit trend view

### 4.3 Formula Review And Calibration

Several indicators and scores are implemented as reasonable defaults, but they still require ongoing review against real use.

Examples:

- VCS maturity thresholds
- industry RS weighting scheme
- market score weights and labeling thresholds
- scan thresholds for momentum or earnings-sensitive environments

## 5. Near-Term Roadmap

### 5.1 Data Hardening

Priority tasks:

1. add an optional secondary provider path
2. improve security-type filtering for the weekly universe
3. keep weekly universe discovery and daily scan execution separated

### 5.2 Research Workflow Improvement

Priority tasks:

1. add historical run comparison views
2. add review tools for duplicate tickers and recurring scan hits
3. make trend changes in sector and industry leaders easier to compare across dates

### 5.3 Formula Governance

Priority tasks:

1. document active formulas from code whenever they change
2. keep parameter catalog synchronized with `config/default.yaml`
3. treat changes in scoring formulas as product-level behavior changes

## 6. Scope Boundary

The current active scope remains:

- market environment monitoring
- sector and industry RS monitoring
- candidate extraction and ranking

The current active scope does not include:

- trade execution logic
- entry confirmation workflow
- stop placement workflow
- position sizing workflow
- phased exit workflow

Those topics remain out of scope for the active screening product and belong to archived materials.
