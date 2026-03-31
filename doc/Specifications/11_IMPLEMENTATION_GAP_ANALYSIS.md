# Implementation Gap Analysis

## Purpose

This document compares the current active documentation set against the current codebase.
It is focused on the active screening scope, not the archived entry and trade-management system.

Reference date: March 27, 2026.

---

## Executive Summary

The codebase already has a usable data pipeline, indicator engine, scan engine, and basic dashboard shell.
However, it is still aligned with the older broader scope, not the newly clarified screening-only scope.

The largest gaps are:

1. The app still exposes chart, cockpit, entry, sizing, and exit workflows that are now outside the active system scope.
2. The current UI does not match the documented three-output workflow.
3. The data layer does not yet implement the documented symbol-list and provider-chain model.
4. The RS implementation does not match the updated documented RS definition.
5. The market dashboard and RS Radar are still much smaller than the documented target.

---

## Status Matrix

| Area | Docs expectation | Current code status | Assessment |
| --- | --- | --- | --- |
| System scope | Screening and candidate extraction only | App and pipeline still include chart, cockpit, entry, structure, sizing, and exit outputs | Misaligned |
| Data providers | `yfinance` + FMP starter + Nasdaq backup list | `yfinance` only in active provider layer | Partial |
| Symbol list workflow | Dedicated `SymbolListProvider` and full common-stock universe build | User-entered symbol list only; no symbol-list provider | Missing |
| Scan universe | Built from common-stock universe with filters | Built only from requested symbols after indicator calculation | Partial |
| Indicators | Broadly match docs | Most core indicators exist | Mostly aligned |
| Raw RS definition | Percentile rank of a symbol's own historical SPY ratio series | Current code uses ratio return over lookback, then cross-sectional normalization across symbols | Misaligned |
| Hybrid RS layer | Separate from raw RS and used for ranking | Hybrid exists, but raw RS vs Hybrid RS distinction is not implemented explicitly | Partial |
| 9 scans | All implemented | All nine families exist | Implemented with formula gaps |
| 7 lists | Internal-only duplicate-ticker support | Implemented in runner, not shown directly | Aligned in structure |
| Duplicate tickers | Based on 7 lists only | Implemented from list hits | Implemented |
| Today's Watchlist UI | Scan-based card grid | Detailed table view | Missing target UI |
| Market Dashboard | 43 ETF breadth, snapshot, S5TH, factors, time-axis scores | Small breadth summary + VIX only | Missing target UI |
| RS Radar | Dedicated sector/industry leadership page | Not present | Missing |
| Archived scope isolation | Entry/risk logic preserved but outside active workflow | Code still imports and runs entry/risk/structure modules in active pipeline | Misaligned |

---

## Detailed Findings

### 1. Scope boundary is not yet enforced in code

The docs now define the active system as a three-output screener.
The active app and pipeline still execute scope-external logic.

Current evidence:

- `app/main.py` still exposes `Chart + Cockpit`
- `src/pipeline.py` still imports and runs:
  - `src/entry/evaluator.py`
  - `src/risk/position_sizing.py`
  - `src/risk/exits.py`
  - `src/structure/pivot.py`
- `src/dashboard/watchlist.py` still adds `candidate_status` and `entry_notes`

Implication:

The code is still shaped like a broader research platform, while the docs now define a narrower screening system.
The first cleanup step should be to stop using entry/risk outputs in the active app flow.

### 2. UI is behind the documented workflow

The active docs describe three output screens:

- Market Dashboard
- RS Radar
- Today's Watchlist

Current app behavior:

- `Watchlist` page exists, but is a table, not a scan-card grid
- `Chart + Cockpit` page still exists, but is out of scope
- `Market Dashboard` exists in reduced form only
- `RS Radar` page does not exist

Implication:

The current UI is the largest user-visible gap.
If the goal is to match the updated workflow quickly, the UI should be realigned before adding more scoring complexity.

### 3. Data ingestion workflow is smaller than documented

The updated docs expect:

- `yfinance` and FMP starter as the main provider chain
- Nasdaq API as backup for symbol lists
- a `SymbolListProvider`
- universe construction from a broad common-stock list

Current implementation:

- active provider layer contains only `YFinancePriceDataProvider`, `YFinanceProfileDataProvider`, and `YFinanceFundamentalDataProvider`
- no `FMP` provider class in the active provider module
- no `SymbolListProvider`
- no full-US common-stock universe build in the active pipeline
- the app currently depends on user-entered symbols in the sidebar

Implication:

The code is still operating as a curated-symbol research tool, not a true screener over the documented scan universe.
This is the most important backend gap after UI scope alignment.

### 4. RS implementation no longer matches the docs

The updated docs now define `old RS` as:

1. `ratio = ticker_close / benchmark_close`
2. evaluate the symbol against its own historical ratio series
3. convert that position into a percentile rank from 0 to 100

Current implementation in `src/scoring/rs.py` does something else:

- computes `ratio.pct_change(lookback)`
- takes the latest ratio return value
- normalizes that column across symbols using `normalize_series`

This is not the documented method.
It is a cross-sectional normalization of recent ratio returns, not a percentile rank within a symbol's own ratio history.

Implication:

The current `rs21`, `rs63`, and related fields cannot be treated as doc-compliant raw RS.
This affects:

- raw RS conditions inside the scans
- the documented old RS versus Hybrid RS distinction
- interpretation of `RS 1M > 60` and `RS 1M > 97`

### 5. Hybrid and raw RS are not clearly separated

The docs now describe a two-layer model:

- raw RS for scan conditions
- Hybrid RS for ranking, 97 Club, and internal list generation

Current code:

- has `rs*` columns
- has `hybrid_score`
- does not explicitly model a separate `raw RS` layer versus a `Hybrid RS` layer in naming and downstream usage

Implication:

The logic may still work mechanically, but the semantics are muddy.
This should be made explicit in the snapshot schema and scan code.

### 6. Scan implementation is close, but not fully aligned

What is already good:

- all 9 scan families exist
- list generation exists
- duplicate tickers are based on list hits
- Momentum 97 uses cross-sectional return ranks, which aligns with the updated docs

Remaining mismatches:

- `97 Club` currently uses `hybrid_score` and `rs21`; docs distinguish `Hybrid RS` and raw `RS 1M`
- `VCS` scan currently uses `rs21 > 60`; docs describe raw RS usage
- `High Est. EPS Growth` list uses a fixed threshold, while docs describe upper-universe names more loosely
- some formulas still reflect initial heuristics rather than the latest documented semantics

Implication:

The scan layer is not the farthest behind, but it should be revisited after the RS layer is corrected.

### 7. Universe defaults and config do not fully match the docs

Examples:

- docs now frame ADR as `3.5 to 10` for the scan universe
- current config still has `min_adr_percent: 2.0` and `max_adr_percent: 15.0`
- docs move entry/risk concerns out of scope
- current config still contains `structure`, `entry`, `risk`, and `optional` sections used by the active pipeline

Implication:

The config file still reflects the older broader platform scope.
This should be split into:

- active screening config
- archived or future entry-system config

### 8. Market Dashboard target is much larger than current implementation

Docs target:

- 43 ETF market conditions
- breadth and trend metrics
- performance overview
- HIGH & VIX
- Market Snapshot
- S5TH chart
- Factors vs SP500
- time-axis scores for 1D, 1W, 1M, and 3M ago

Current implementation in `src/dashboard/market.py`:

- computes a small breadth summary from the current snapshot
- optionally includes a simple VIX-based component
- does not produce:
  - time-axis scores
  - Market Snapshot items
  - factor analysis
  - S5TH chart data
  - 43 ETF universe scoring

Implication:

The current market page is still an MVP placeholder.

### 9. RS Radar is documented but not implemented

The docs describe:

- sector leaders
- industry leaders
- 4-axis RS
- RS change rates
- MAJOR STOCKS
- Top 3 RS% Change

Current codebase:

- no dedicated RS Radar page in `app/main.py`
- no dedicated radar builder module matching the docs
- no active output model for the documented tables

Implication:

This is a net-new active-scope deliverable, not a small refinement.

### 10. Archived docs and active code are only partially separated

The docs say entry/structure/risk work has been isolated to `archived/`.
The document copies do exist under `archived/`.
But the active code path still runs those modules.

Implication:

The documentation and the codebase are now describing two different scopes.
Either the active pipeline must be slimmed down, or the docs must say that these modules remain active but non-primary.
The cleaner option is to slim the active pipeline.

---

## Recommended Work Order

### Priority 1: Enforce scope in the active app

- Remove `Chart + Cockpit` from the active app flow
- Stop wiring entry, pivot, sizing, and exit outputs into the active watchlist pipeline
- Keep those modules available, but outside the active screening workflow

### Priority 2: Align the UI with the docs

- Replace the watchlist table with scan-based card grids
- Add Earnings for today
- Add a real RS Radar page
- Expand the Market Dashboard toward the documented output model

### Priority 3: Fix the data-ingestion shape

- add `SymbolListProvider`
- add FMP-backed list/profile/fundamental support
- move from manual symbol input toward true universe-based screening

### Priority 4: Correct the RS semantics

- implement doc-compliant raw RS
- model Hybrid RS explicitly
- update scans and list generation to use the right RS layer

### Priority 5: Clean config and snapshot schema

- split screening-scope config from archived entry/risk config
- make raw RS and Hybrid RS naming explicit in outputs
- keep parameterization, but align defaults with the docs

---

## Short Conclusion

The project has enough code to support the screening system direction, but the active implementation still reflects the older, larger platform.
The next step should not be more indicators or more entry logic.
The next step should be to realign the active codebase with the new documented scope and outputs.
