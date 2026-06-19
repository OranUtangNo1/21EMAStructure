# Modularization Work Plan

## Status

Active planning document for the large modularization refactor.

## Principles

- Improve each functional part as an independent, reusable object.
- Prefer explicit service inputs and outputs over implicit app or database state.
- Make every calculation date-addressable with `as_of_date`.
- Keep price data as the common dependency for downstream analysis.
- Allow modules to be recombined by the current app, scripts, tests, and future applications.
- Preserve inspectability: outputs should record source data, config path, and effective date.

## DB Pause Decision

Database-dependent tracking is paused for the refactor unless a task explicitly re-enables it.

Paused areas:

- preset-effectiveness tracking writes
- signal pool synchronization
- signal evaluation persistence
- tracking refresh jobs
- Analysis views that require SQLite tracking tables

The DB code should not be deleted in the first phase. It should be isolated behind optional service boundaries or feature flags so the rest of the system can run without DB state.

## Target Service Boundaries

### PriceDataService

Purpose:

- fetch and normalize price data
- write/read shared price histories
- support US equities first and Japanese equities later

Inputs:

- ticker list or universe file
- period or date range
- force refresh flag

Outputs:

- canonical `PriceHistory` objects
- fetch status
- metadata records

### SnapshotService

Purpose:

- build date-addressable indicator and scoring snapshots from shared price data

Inputs:

- price histories
- `as_of_date`
- benchmark history when RS is required
- optional profile/fundamental data

Outputs:

- one latest row per ticker as of the requested date
- indicator and score fields
- data quality fields

### ScanService

Purpose:

- evaluate scan rules against a snapshot
- keep one scan as one boolean output
- compose each scan from named internal issue booleans
- generate scan-hit records and preset hit views

Inputs:

- snapshot
- scan config
- optional preset selection

Outputs:

- scan-hit table
- preset-hit table
- aggregate issue diagnostics by date, scan, and issue

External consumers should depend on `scan` and `preset` outputs. Issue-level ticker rows are internal implementation detail and should not be stored as full public artifacts because the row volume can grow quickly.

### StockCardService

Purpose:

- generate the current stock-card format from a ticker price history
- support historical cards by `as_of_date`
- emit a canonical AI/system JSON payload for chart-analysis consumers while keeping Markdown as a compatibility rendering

Inputs:

- ticker
- canonical `PriceHistory`
- `as_of_date`
- optional metadata

Outputs:

- stock-card Markdown document
- stock-card JSON payload and JSON file
- output path or in-memory document payload

The JSON payload is the forward-compatible contract. Markdown is a rendering layer and may be disabled later when downstream consumers no longer require it.

### MarketService

Purpose:

- calculate market condition and RS Radar outputs from shared price data
- keep market component definitions extensible

Inputs:

- market and ETF histories
- benchmark history
- `as_of_date`
- market/radar/context config

Outputs:

- market condition result
- radar result

`market_context` is a downstream interpretation layer. It should read market/radar-style outputs and emit structured AI/system context instead of merging all module outputs into one package.

The CLI user-facing market entrypoint should be unified as a market-environment action. Internally, market, radar, market-report input, and market_context remain separate modules/artifacts, but interactive users should not need to choose between market and radar as separate menu actions.

The interactive CLI price-fetch flow should optimize for the most frequent operation: default-universe daily incremental update with minimal input. Detailed price-fetch settings are optional. Interactive tasks should return to the main menu after completion, cancellation, or handled errors, and long-running price-fetch and scan tasks should emit coarse progress messages.

### EntrySignalService

Purpose:

- evaluate entry-signal readiness from current or historical snapshots without requiring DB pool state

Inputs:

- snapshot
- scan hits or preset hits
- selected signal definitions
- `as_of_date`

Outputs:

- Entry Ready / Watch Setup / Needs Review decisions
- entry-plan fields
- diagnostic details

Tracking persistence, if needed later, should be a separate optional service.

## Main Dashboard Direction

The main dashboard should become a lightweight launcher and status manager.

Responsibilities:

- accept button actions
- manage selected config path
- manage selected universe or ticker file
- manage `as_of_date`
- show last update state and artifact paths
- call service APIs

Non-responsibilities:

- no business logic ownership
- no automatic expensive work at startup
- no DB requirement for basic module execution

## Phased Work Order

1. Create shared price schema and date-slicing contract.
2. Add shared price-data read/write helpers.
3. Add `PriceDataService`.
4. Add `StockCardService` with `as_of_date` support.
5. Add `SnapshotService`.
6. Add `ScanService` and preset-hit outputs from snapshots.
7. Add `MarketService` for market, RS Radar, and Market Context.
8. Split DB-dependent entry-signal behavior from pure entry-signal evaluation.
9. Refactor `ResearchPlatform` into a thin compatibility facade over the services.
10. Refactor `app/main.py` into a launcher/status UI over the services.
11. Add performance-verification workflows that compose the same services across historical dates.

## Documentation Sync Rule

For this refactor, update this folder before or alongside implementation changes that affect:

- shared data schema
- service boundaries
- DB pause behavior
- `as_of_date` calculation contracts
- dashboard responsibilities
- module output contracts

When a planned contract becomes implemented behavior, also update the relevant numbered SystemDocs specification.
