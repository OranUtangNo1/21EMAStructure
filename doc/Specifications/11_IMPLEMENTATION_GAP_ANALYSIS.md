# 11. Implementation Gap Analysis

## 1. Executive Summary

The major scope-alignment work has already been completed. The active codebase now behaves as a screening and candidate extraction product with three active outputs:

1. Market Dashboard
2. RS Radar
3. Today's Watchlist

The largest remaining gaps are no longer about removing out-of-scope entry logic. The current gaps are about data rigor, provider depth, historical review workflow, and cleanup of legacy config surfaces.

## 2. Status Matrix

| Area | Current status | Notes |
| --- | --- | --- |
| Screening-only product scope | Implemented | Active app is limited to Market Dashboard, RS Radar, and Today's Watchlist |
| Watchlist projection UI | Implemented | Selected scans, post-scan filters, duplicate subfilters, and duplicate threshold all work in the active page |
| Duplicate ticker logic | Implemented | Backend is scan-overlap based; UI can reproject from selected scan cards |
| RS Radar | Implemented | Sector and industry ETF tables plus top RS movers |
| Market Dashboard | Implemented | Composite score, breadth, ETF snapshots, and factor panels; S5TH remains in the result object but is not rendered |
| Weekly universe snapshot | Implemented | Finviz discovery with local persistence; Yahoo screener is also supported |
| Daily price loading | Implemented | Yahoo Finance provider with cache lineage |
| Common-stock security master | Not implemented | No strict master source yet |
| Secondary provider chain | Not implemented | No FMP path yet |
| Historical review UI | Partial | Run artifacts exist, but review tooling is thin |
| Legacy config cleanup | Partial | Some shipped keys are not part of active runtime behavior |
| Formula maturity | Partial | Several formulas remain configurable research logic |

## 3. Gaps Closed Since The Earlier Scope

The following gaps were present in earlier versions and are now effectively closed in the active application.

### 3.1 Scope Alignment

Resolved:

- chart and cockpit pages are no longer part of the active application flow
- entry and risk modules are outside the active product scope
- watchlist behavior is driven by scan results rather than entry-evaluation concepts

### 3.2 Duplicate Logic Alignment

Resolved:

- duplicate tickers are derived from scan overlap
- the active page can reproject duplicate counting from selected scan cards without mutating raw scan output
- annotation filters no longer control watchlist eligibility

### 3.3 Dashboard Alignment

Resolved:

- RS Radar is active inside the app
- Market Dashboard is active inside the app
- watchlist cards are scan-based and driven by current sidebar controls

## 4. Active Remaining Gaps

### 4.1 Universe Quality And Instrument Classification

Current code uses a practical but heuristic approach:

- weekly discovery from Finviz by default
- optional Yahoo screener support
- post-load local filters
- no dedicated instrument master

Impact:

- common-stock purity is improved, but not guaranteed by a strict reference source
- future provider expansion is still desirable

### 4.2 Provider Redundancy

Current code depends mainly on:

- Finviz for default weekly universe discovery
- Yahoo Finance for prices and fallback profile and fundamental fields

Impact:

- screening works today
- resilience is weaker than it would be with an additional provider path

### 4.3 Historical Review And Comparison

Current code persists artifacts but does not yet provide a strong review workflow.

Missing capabilities:

- compare two historical runs in-app
- inspect recurring duplicate tickers across dates
- review how sector or industry leadership changed over time

### 4.4 Research Formula Governance

Current code already parameterizes formulas, but several components still need ongoing validation.

Examples:

- hybrid weighting behavior under missing data
- VCS thresholds
- market condition score composition
- sector and industry RS aggregation choices

### 4.5 Legacy Config Surface

The active config set still contains shipped keys that are not part of current runtime behavior.

Current examples:

- `app.refresh_on_start`
- `indicators.show_overheat_dot`
- `optional.enable_darvas_retest_filter`
- `optional.enable_trend_regime_filter`

Impact:

- runtime behavior is still correct
- documentation and maintenance are noisier than necessary

## 5. Priority Order For Future Work

### 5.1 Highest Priority

1. strengthen universe quality and instrument classification
2. add a secondary provider path
3. add historical run-comparison tools

### 5.2 Medium Priority

1. improve observability for trend changes across runs
2. refine formula documentation whenever code changes
3. clean up or clearly mark inactive config knobs

### 5.3 Lower Priority

1. optional provider expansion beyond the current stack
2. deeper archival tooling for non-active research modules

## 6. Conclusion

The active implementation is no longer missing its core product shape. The current work is mostly hardening work:

- better reference data
- stronger provider resilience
- stronger historical review workflows
- continued formula review
- cleaner active config boundaries

That is the correct interpretation of the present implementation gap.
