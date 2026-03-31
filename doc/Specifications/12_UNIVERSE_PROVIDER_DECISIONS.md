# 12. Universe And Provider Decisions

## 1. Current Decision Summary

The active implementation uses a practical low-cost stack for screening:

- Finviz for weekly universe discovery
- Yahoo Finance for daily price history
- Yahoo fallback providers for profile and fundamental fields when the weekly snapshot does not supply them
- local cache and local run snapshots for persistence

This is the current implemented provider stack.

## 2. Current Universe Workflow

### 2.1 Weekly Discovery

The default weekly discovery path is:

1. run the Finviz screener
2. apply the configured discovery filters
3. save the resulting snapshot under `data_runs/universe_snapshots/`
4. reuse the latest snapshot until the refresh interval expires or a manual refresh is requested

### 2.2 Daily Scan Execution

The daily scan path is:

1. resolve symbols from the latest weekly snapshot
2. load price history for those symbols
3. merge profile and fundamental data
4. apply the local eligible-universe filter
5. calculate indicators and scores
6. run the nine scans

This separation between weekly discovery and daily scan execution is active in the code.

## 3. Current Discovery Filters

The current default discovery filters come from `config/default.yaml`.

Implemented defaults:

- provider: `finviz`
- exchanges: `NASDAQ`, `NYSE`, `AMEX`
- excluded sector: `Healthcare`
- minimum market cap: `1000000000`
- maximum symbols: `2500`
- refresh cadence: weekly

These are discovery-stage filters, not the final eligible-universe rules.

## 4. Current Eligible-Universe Filter

After prices are loaded, the application applies a local filter before scans run.

Current implemented conditions:

- market cap >= 1B
- average volume 50d >= 1M
- close >= configured minimum price
- ADR percent between 3.5 and 10.0
- sector is not Healthcare

This is the actual daily screening universe used by the scan layer.

## 5. Why The Current Stack Exists

The current stack is a pragmatic implementation choice.

Benefits:

- low cost
- fast enough for the current product scope
- simple local caching model
- enough data to run the active scans and dashboards

Tradeoffs:

- no strict security master
- no guaranteed common-stock-only reference layer
- provider behavior can drift over time
- fallback coverage is practical rather than institutional-grade

## 6. What Is Not Yet Active

The following ideas exist as future directions, but are not part of the current implementation:

- FMP provider chain
- Nasdaq-backed security master
- strict common-stock canonical universe provider
- richer provider redundancy for profile and fundamentals

These should be treated as future enhancements, not current behavior.

## 7. Current Operational Interpretation

The current provider strategy should be interpreted as:

- good enough for daily screening research and candidate extraction
- intentionally modular so that providers can be replaced later
- not yet the final state for institutional-quality universe management

That is the current implementation stance.
