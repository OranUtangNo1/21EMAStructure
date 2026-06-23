# Modularization Work Plan

## Status

Optional reference plan for the large modularization refactor.

## Principles

- Improve each functional part as an independent, reusable object.
- Prefer explicit service inputs and outputs over implicit app or database state.
- Make every calculation date-addressable with `as_of_date`.
- Keep price data as the common dependency for downstream analysis.
- Allow modules to be recombined by CLI commands, scripts, tests, and future automation.
- Preserve inspectability: outputs should record source data, config path, and effective date.
- Preserve the current module-owned `data_runs/service_outputs/` layout as the canonical calculation-output structure.
- Replace global application-state restoration with validated reuse of only the upstream artifacts required by a downstream service.

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

## Invocation Surface Direction

The target system has no GUI and does not restore UI or application session state.
Users invoke services through CLI commands or other explicit service clients.

Responsibilities:

- accept explicit service actions
- resolve the selected config path
- resolve the selected universe, ticker file, or ticker list
- resolve `as_of_date`
- print the produced artifact and manifest paths
- call service APIs without initializing unrelated services

Non-responsibilities:

- no business logic ownership
- no automatic work at process startup
- no DB requirement for basic module execution
- no reconstruction of global `PlatformArtifacts` or prior UI state

The previous result is reviewed directly from the producing service's latest completed artifact.
Persisted calculation outputs are reused only as validated inputs to declared downstream services or explicitly retained historical analysis.
The target path and reuse contract is defined in `03_SERVICE_ARTIFACT_AND_REUSE_CONTRACT.md`.

## Reference Work Order

1. Create shared price schema and date-slicing contract.
2. Add shared price-data read/write helpers.
3. Normalize current output paths, remove legacy/GUI-only output directories, and enforce the output reuse contract.
4. Add `PriceDataService`.
5. Add `StockCardService` with `as_of_date` support.
6. Add `SnapshotService`.
7. Add `ScanService` and preset-hit outputs from snapshots.
8. Add `MarketService` for market, RS Radar, and Market Context.
9. Split DB-dependent entry-signal behavior from pure entry-signal evaluation.
10. Refactor `ResearchPlatform` into a temporary thin compatibility facade over the services.
11. Expose CLI/service actions that do not depend on `app/main.py`.
12. Remove global saved-run and UI/session restoration after service artifact consumers migrate.
13. Add performance-verification workflows that compose the same services across historical dates.

## Planning And Documentation Policy

This work plan is a reference, not an implementation gate.
Do not update it or the numbered SystemDocs as a routine prerequisite or follow-up to code changes.
Update planning or specification documents only when the user explicitly requests it or when a material design decision requires a durable record before implementation can proceed safely.
