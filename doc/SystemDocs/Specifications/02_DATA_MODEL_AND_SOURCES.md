# Data Model and Sources

## 1. Active Data-Source Architecture

### 1.1 Source split

| Source | Current role | Status |
| --- | --- | --- |
| Finviz screener | Weekly universe discovery and snapshot fields for name, sector, industry, market cap, EPS growth, revenue growth, earnings date, country, and exchange | Active default |
| Yahoo screener | Optional alternate weekly universe discovery path | Supported, not default |
| yfinance price provider | Daily OHLCV for active symbols, benchmark, VIX, radar ETFs, market ETFs, and factor ETFs | Active default |
| yfinance profile provider | Fallback profile source when a symbol is missing from the weekly snapshot | Active fallback |
| yfinance fundamental provider | Fallback fundamental source when a symbol is missing from the weekly snapshot | Active fallback |
| local cache | TTL handling, stale fallback, and fetch-status lineage | Active |
| local snapshot store | Weekly universe snapshots plus per-run artifacts | Active |
| SQLite tracking DB | Preset-hit detections, scan-hit history, forward closes, returns, and analysis views | Active |

### 1.2 Current design principles

- use a weekly coarse universe snapshot instead of rediscovering the full universe every run
- default to Finviz for weekly discovery, but keep the discovery provider replaceable
- use yfinance bulk downloads for price histories
- source profile and fundamental data from the weekly snapshot first, then fall back per symbol only when needed
- preserve fetch status, data quality, and saved run metadata as first-class outputs
- keep saved run bundles available through the pipeline restore helper for same-day reuse when the config path, manual-symbol input, and expected trade date still match
- store preset-hit performance tracking in SQLite rather than cumulative analysis CSVs

### 1.3 Benchmark and market symbols

- benchmark: `SPY`
- volatility symbol: `^VIX`
- Market Dashboard ETFs, RS Radar ETFs, and factor ETFs come from `config/default.yaml`

## 2. Active Universe Flow

### 2.1 Symbol resolution order

`ResearchPlatform.run()` resolves the active symbol set in this order:

1. manual symbols passed from the app
2. fresh weekly universe snapshot
3. live universe discovery
4. stale weekly universe snapshot
5. `app.default_symbols`

The returned `universe_mode` is one of:

- `manual`
- `weekly_snapshot_cached`
- `weekly_snapshot_live`
- `weekly_snapshot_stale`
- `default_symbols`
- `none`

### 2.2 Weekly universe discovery: Finviz path

Current default discovery uses `FinvizScreenerProvider`.

Implementation details:

- loops through configured exchanges
- requests Finviz screener rows with `Exchange=<exchange>` and `Market Cap. = +Small (over $300mln)`
- normalizes the returned rows
- applies code-side post-filters:
  - `market_cap >= universe_discovery.min_market_cap`
  - sector not in `universe_discovery.excluded_sectors`
  - keep at most `universe_discovery.max_symbols`

Default config values:

- provider: `finviz`
- exchanges: `NASDAQ`, `NYSE`, `AMEX`
- excluded sectors: `Healthcare`
- minimum market cap: `1B`
- maximum symbols: `2500`

The normalized Finviz snapshot carries:

- `ticker`
- `name`
- `sector`
- `industry`
- `country`
- `exchange`
- `market_cap`
- `eps_growth`
- `revenue_growth`
- `earnings_date`
- `source`
- `discovered_at`

### 2.3 Weekly universe discovery: Yahoo path

The code also supports `universe_discovery.provider: yahoo` through `YahooScreenerProvider`.

Provider-default Yahoo discovery behavior when selected:

- filters by configured exchanges
- applies market-cap, average-volume, and minimum-price screener constraints
- keeps only `quoteType == EQUITY`
- rejects rows where `typeDisp` is present and not `equity`
- sorts by `intradaymarketcap` descending by default

Yahoo discovery is implemented but is not the active default configuration.

### 2.4 Local screenable-universe filter

After price histories and indicators are available, `UniverseBuilder.filter()` applies the active local filter:

- `market_cap >= 1B`
- `avg_volume_50d >= 1M`
- `close >= 0.0`
- `adr_percent >= 3.5`
- `adr_percent <= 10.0`
- `sector != Healthcare`

This filtered set is the actual input to scan rules and annotation rules.

## 3. Data Loading Flow

### 3.1 Prices

`YFinancePriceDataProvider` currently fetches:

- active screening symbols
- benchmark (`SPY`)
- VIX (`^VIX`)
- RS Radar ETFs
- Market Dashboard ETFs
- factor ETFs

Key active behavior:

- batch size: `80`
- max retries: `3`
- request sleep: `2.0s`
- retry backoff multiplier: `2.0`
- stale-cache fallback allowed
- stale cached price series are refreshed with an incremental download period of `5d`
- `force_refresh=True` bypasses fresh-cache reuse, loads any existing cached price series as the merge/fallback base, and requests live yfinance data for the affected symbols
- yfinance console diagnostics are suppressed during price downloads; missing or incomplete symbols are surfaced through fetch status and Data Health instead

### 3.2 Profiles and fundamentals

Profile and fundamental loading is split into two stages:

1. build profile and fundamental batches from the weekly universe snapshot
2. fetch only the still-missing symbols from yfinance fallback providers

This means the active implementation does not fetch per-symbol profile or fundamental payloads when the weekly snapshot already provides those fields.

Snapshot-derived profile and fundamental statuses reuse fetch-state labels based on the current `universe_mode`:

- `weekly_snapshot_live` -> `live`
- `weekly_snapshot_cached` -> `cache_fresh`
- `weekly_snapshot_stale` -> `cache_stale`
- any non-snapshot mode -> `missing`

Those rows also carry the note `universe snapshot`.

### 3.3 Optional sample fallback

If `app.use_sample_data_if_fetch_fails` is true, the pipeline can synthesize sample price, profile, and fundamental data for missing symbols.

The current default config sets this to `false`, so sample fallback is inactive unless explicitly enabled.

## 4. Cache, Persistence, And Lineage

### 4.1 Active persistence locations

- price cache under `data_cache/`
- profile cache under `data_cache/`
- fundamental cache under `data_cache/`
- user preferences under `data_cache/user_preferences.yaml`
- weekly universe snapshots under `data_runs/universe_snapshots/`
- run artifacts under file-type folders keyed by trade-date date key, such as `data_runs/run_metadata/YYYYMMDD.json`, `data_runs/watchlist/YYYYMMDD.csv`, `data_runs/market_summary/YYYYMMDD.json`, and `data_runs/radar_summary/YYYYMMDD.json`
- scan-hit history and preset-hit tracking under `data_runs/tracking.db`

### 4.2 Current TTLs

- technical cache: `12h`
- profile cache: `168h`
- fundamental cache: `24h`
- universe snapshot TTL: `7d`

The app-level `Force price data refresh` run option bypasses the technical price-cache TTL for the active run. It does not clear cache files; existing cached rows are still used to merge incremental live data and to provide stale fallback if the live refresh fails.

### 4.3 Same-day saved-run restore helper

When persistence is enabled, `ResearchPlatform.load_latest_run_artifacts()` can reuse the latest saved run instead of rerunning the pipeline when all of these hold:

- `Force weekly universe refresh` is off
- the saved run metadata `config_path` matches the current resolved config path
- the saved run metadata `manual_symbols_input` matches the current symbol input, which is empty in the active UI
- the saved run `trade_date` matches the current expected trade date

The current expected trade date is derived from US/Eastern calendar date with a daily close cutoff and a weekday-only fallback. The Streamlit app uses this helper on startup and artifact-key changes when neither refresh control is forced. Explicit `Refresh data`, `Force weekly universe refresh`, or `Force price data refresh` bypass saved-run restore and recompute through `ResearchPlatform.run()`.

### 4.4 Fetch-status states

The implementation tracks per-symbol dataset status with these source states:

- `live`
- `cache_fresh`
- `cache_stale`
- `sample`
- `missing`

The app-level `data_source_label` then collapses the current run into:

- `live`
- `live + cache`
- `sample fallback`
- `live + sample fallback`
- `missing`
- `mixed`
- `no data`

## 5. Core Data Models In Active Use

### 5.1 Price history rows

Price-history columns normalized by the active price provider:

- `open`
- `high`
- `low`
- `close`
- `adjusted_close`
- `volume`

### 5.2 Snapshot enrichment fields

The active latest-row snapshot is built from indicator histories and then extended with:

- profile fields such as `name`, `market_cap`, `sector`, `industry`, and `ipo_date`
- fundamental fields such as `eps_growth`, `revenue_growth`, and `earnings_date`
- fetch-status source, note, and timestamp columns for price, profile, and fundamentals
- IPO timer and earnings-context fields
- data-quality fields
- indicator, scoring, and scan-context columns

### 5.3 Scan outputs

The active scan pipeline produces:

- `scan_hits` with `ticker`, `kind`, and `name`
- raw watchlist rows with scan-hit counts, annotation-hit counts, compatibility alias fields, and duplicate flags
- persisted watchlist rows with explicit aliases for scan and annotation matches:
  - `matched_scan_rules` mirrors `hit_scans`
  - `matched_annotation_filters` mirrors `annotation_hits`
  - `backend_duplicate_ticker` mirrors the raw/global `duplicate_ticker`
  - `backend_duplicate_rule` records the global duplicate rule basis
- display-oriented duplicate-ticker frames for the UI
- same-day earnings frames retained as artifacts, but not rendered by the active Watchlist UI

### 5.4 Tracking database rows

The active tracking database is `data_runs/tracking.db`.

Core tables:

- `detection`: one row per tracked preset hit, keyed by `hit_date x preset_name x ticker`
- `detection_scans`: bridge rows from tracked detections to scan names hit at detection time
- `detection_filters`: bridge rows from tracked detections to selected annotation filters
- `scan_hits`: date-level scan-hit history used by saved-run restore and watchlist reconstruction

Forward tracking fields are stored directly on `detection`:

- `close_at_hit`
- `close_at_1d`, `close_at_5d`, `close_at_10d`, `close_at_20d`
- `return_1d`, `return_5d`, `return_10d`, `return_20d`

Analysis views:

- `v_detection_detail`
- `v_preset_horizon_performance`
- `v_preset_scan_performance`
- `v_preset_summary`
- `v_scan_combo_performance`
- `v_preset_overlap`

### 5.5 Saved run artifacts

When `data.persist_research_snapshots` is true, the pipeline saves:

- `watchlist.csv`
- `run_metadata/YYYYMMDD.json`
- `market_summary/YYYYMMDD.json`
- `radar_summary/YYYYMMDD.json`
- date-level scan hits into `tracking.db`

The saved `watchlist.csv` is a scan-hit artifact, not a preset-hit artifact. A row means the ticker matched at least one enabled scan. Preset-hit CSVs are written separately under `data_runs/preset_exports/`.

Run metadata currently includes:

- `run_created_at`
- `config_path`
- `manual_symbols_input`
- `requested_symbols`
- `available_symbols`
- `trade_date`
- `data_source_label`
- `used_sample_data`
- `data_health_summary`
- `market_score`
- `market_label`
- `universe_mode`
- `universe_snapshot_path`

The current same-day saved-run restore path is intentionally compact. It restores the saved watchlist, scan hits from SQLite, market summary, radar summary, and metadata, then builds a minimal snapshot carrying the saved trade date. Full `snapshot`, `eligible_snapshot`, and `fetch_status` CSV restoration is not active in the current store implementation.

## 6. Active Provider Modules

- `src/data/finviz_provider.py`
  - Finviz discovery
  - snapshot-based profile and fundamental extraction
- `src/data/providers.py`
  - yfinance price, profile, and fundamental providers
  - optional Yahoo screener provider
- `src/data/universe.py`
  - local post-price universe filter
- `src/data/cache.py`
  - cache load, save, and stale fallback
- `src/data/store.py`
  - weekly universe snapshot and per-run artifact persistence
- `src/data/tracking_db.py`
  - SQLite path resolution, connection setup, schema initialization, and additive migrations
- `src/data/tracking_repository.py`
  - read APIs for tracking tables and analysis views
- `src/data/tracking_migration.py`
  - one-time backfill from legacy CSV tracking files into SQLite

## 7. Notes On Current Limitations

The live code does not yet implement:

- an FMP provider chain
- a strict common-stock security-master model
- an in-app historical comparison workflow over saved runs

Those remain future enhancements, not part of the active default implementation.
