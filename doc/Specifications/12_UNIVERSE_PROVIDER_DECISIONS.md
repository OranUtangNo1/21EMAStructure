# 12. Universe And Provider Decisions

## 1. Current Decision Summary

The active implementation uses a practical low-cost stack for screening:

- Finviz for default weekly universe discovery
- Yahoo screener as an optional alternate discovery path
- Yahoo Finance for daily price history
- Yahoo fallback providers for profile and fundamental fields when the weekly snapshot does not supply them
- local cache and local run snapshots for persistence

This is the current implemented provider stack.

## 2. Current Universe Workflow

### 2.1 Weekly Discovery

The default weekly discovery path is:

1. reuse the latest fresh snapshot when available
2. otherwise run the configured discovery provider
3. save the resulting snapshot under `data_runs/universe_snapshots/`
4. reuse the latest snapshot until the refresh interval expires or a manual refresh is requested
5. fall back to the latest stale snapshot if live discovery fails

This separation between reusable weekly discovery and daily scan execution is active in the code.

### 2.2 Daily Scan Execution

The daily scan path is:

1. resolve symbols from manual input, snapshots, live discovery, or default symbols
2. load price history for those symbols plus benchmark, VIX, radar ETFs, market ETFs, and factor ETFs
3. merge profile and fundamental data
4. apply the local eligible-universe filter
5. calculate indicators and scores
6. run the enabled scans

## 3. Current Discovery Filters

### 3.1 Finviz defaults

Implemented defaults from `config/default/universe_discovery.yaml`:

- provider: `finviz`
- exchanges: `NASDAQ`, `NYSE`, `AMEX`
- excluded sector: `Healthcare`
- minimum market cap: `1000000000`
- maximum symbols: `2500`
- snapshot TTL: `7 days`

Finviz discovery also starts from the screener-side market-cap bucket `+Small (over $300mln)` and then applies the code-side `min_market_cap` filter after normalization.

### 3.2 Yahoo screener support

When `provider = yahoo`, the code supports these active behaviors:

- exchange-scoped screener queries
- market-cap, average-volume, and minimum-price query constraints
- `quoteType == EQUITY` enforcement
- rejection of non-equity `typeDisp` values
- max-symbol truncation after normalization

Yahoo discovery is implemented but not selected by the default config.

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
- clean reuse of weekly discovery results across daily runs

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
