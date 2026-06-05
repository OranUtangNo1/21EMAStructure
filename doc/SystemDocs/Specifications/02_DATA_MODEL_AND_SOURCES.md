# Data Model and Sources

## 1. Active Data-Source Architecture

### 1.1 Source split

| Source | Current role | Status |
| --- | --- | --- |
| Finviz screener | Weekly universe discovery and snapshot fields for name, sector, industry, market cap, EPS growth, revenue growth, earnings date, country, and exchange | Active default |
| Yahoo screener | Optional alternate weekly universe discovery path | Supported, not default |
| yfinance price provider | Daily OHLCV for active symbols, benchmark, VIX, radar ETFs, market ETFs, and factor ETFs | Active default |
| FRED CSV provider | Daily market-external series for Market Dashboard diagnostics, currently high-yield OAS (`BAMLH0A0HYM2`) | Active auxiliary |
| yfinance profile provider | Fallback profile source when a symbol is missing from the weekly snapshot | Active fallback |
| yfinance fundamental provider | Fallback fundamental source when a symbol is missing from the weekly snapshot | Active fallback |
| local cache | TTL handling, stale fallback, and fetch-status lineage | Active |
| local snapshot store | Weekly universe snapshots plus per-run artifacts | Active |
| SQLite tracking DB | Preset-hit detections, scan-hit history, forward closes, returns, and analysis views | Active |

### 1.2 Current design principles

- use a weekly coarse universe snapshot instead of rediscovering the full universe every run
- default to Finviz for weekly discovery, but keep the discovery provider replaceable
- use yfinance bulk downloads for price histories
- use FRED CSV downloads only for configured market-external diagnostic series that are not yfinance symbols
- source profile and fundamental data from the weekly snapshot first, then fall back per symbol only when needed
- preserve fetch status, data quality, and saved run metadata as first-class outputs
- keep saved run bundles available through the pipeline restore helper for same-day reuse when the config path, manual-symbol input, and expected trade date still match
- store preset-hit performance tracking in SQLite rather than cumulative analysis CSVs

### 1.3 Benchmark and market symbols

- benchmark: `SPY`
- volatility symbol: `^VIX`
- Market Dashboard ETFs, RS Radar ETFs, factor ETFs, yfinance auxiliary diagnostic symbols, and FRED diagnostic series come from `config/default.yaml`

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
- yfinance auxiliary diagnostics such as VIX9D, VIX3M, and credit ETFs

Key active behavior:

- batch size: `80`
- max retries: `3`
- request sleep: `2.0s`
- retry backoff multiplier: `2.0`
- stale-cache fallback allowed
- stale cached price series are refreshed with an incremental download period of `5d`
- `force_refresh=True` bypasses fresh-cache reuse, loads any existing cached price series as the merge/fallback base, and requests live yfinance data for the affected symbols

`FredSeriesProvider` fetches configured FRED series through `fredgraph.csv`, normalizes each series into OHLC-like history with the FRED value in `close`, `adjusted_close`, `open`, `high`, and `low`, and stores `volume=0.0`. It currently feeds the high-yield OAS series (`BAMLH0A0HYM2`) into Market Dashboard credit diagnostics. FRED fetch status uses dataset `market_external` and the same cache/stale fallback model as other provider outputs.
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
- run artifacts under file-type folders keyed by trade-date date key, such as `data_runs/run_metadata/YYYYMMDD.json`, `data_runs/eligible_snapshot/YYYYMMDD.csv`, `data_runs/market_summary/YYYYMMDD.json`, `data_runs/market_documents/YYYYMMDD.json`, `data_runs/market_documents/YYYYMMDD.md`, `data_runs/market_reports/YYYYMMDD.md`, and `data_runs/radar_summary/YYYYMMDD.json`
- scan-hit history and preset-hit tracking under `data_runs/tracking.db`
- EntrySignal startup exports under `data_runs/entry_signals/`

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

The current expected trade date is derived from US/Eastern calendar date with a daily close cutoff and a weekday-only fallback. The Streamlit app uses this helper on startup and artifact-key changes when neither refresh control is forced. Explicit `Refresh data`, `Force weekly universe refresh`, `Force price data refresh`, or `Recompute from cache` bypass saved-run restore and recompute through `ResearchPlatform.run()`. `Recompute from cache` does not bypass price-cache TTL by itself; it is intended to rebuild local run artifacts and tracking rows from the current cache state.

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
- `signal_pool_entry`: active and historical EntrySignal pool entries derived from preset duplicates
- `signal_evaluation`: daily EntrySignal evaluation rows, including score components, stop/target metrics, and the mechanical Entry Plan fields used to explain inclusion or exclusion
- `signal_entry_event`: distinct valid `Ready Now` EntrySignal events with action bucket, normalized market environment, forward returns, TP1/SL hits, first outcome, result R, and 20D / 21D excursion fields

Forward tracking fields are stored directly on `detection`:

- `close_at_hit`
- `close_at_1d`, `close_at_5d`, `close_at_10d`, `close_at_20d`, `close_at_21d`
- `return_1d`, `return_5d`, `return_10d`, `return_20d`, `return_21d`
- `max_gain_20d`, `max_drawdown_20d`, `max_gain_21d`, `max_drawdown_21d`

`detection.market_env` stores the normalized analysis buckets `bull`, `neutral`, `weak`, or `bear`. Source labels such as `Bullish`, `Positive`, `Negative`, and `Bearish` are normalized before insertion so Analysis filters do not drop current market records.

EntrySignal tracking persists the user-facing Entry Plan fields needed for later review: `plan_status`, `plan_type`, `entry_type`, `entry_price`, `current_price`, `entry_zone_low`, `entry_zone_high`, `max_entry_price`, `distance_to_entry_zone_pct`, `stop_loss`, `tp1`, `tp2`, `rr_tp1`, `rr_current`, `rr_ideal`, `tp2_plan`, `trigger_condition`, `plan_verdict`, `plan_reject_codes`, `plan_reject_reason`, `sl_quality`, `sl_source`, `sl_basis`, `sl_safety`, `tp1_source`, `plan_invalidation`, `plan_note`, and `plan_detail`.

Ready `signal_entry_event` rows are refreshed from future OHLC bars after `event_date`. The outcome fields include `action_bucket`, `market_env`, `close_at_1d`, `close_at_5d`, `close_at_10d`, `close_at_20d`, `close_at_21d`, `return_1d`, `return_5d`, `return_10d`, `return_20d`, `return_21d`, `hit_sl`, `hit_tp1`, `hit_sl_date`, `hit_tp1_date`, `first_outcome`, `first_outcome_date`, `days_to_first_outcome`, `outcome_r`, `max_gain_20d`, `max_drawdown_20d`, `max_gain_21d`, and `max_drawdown_21d`.

Analysis views:

- `v_detection_detail`
- `v_preset_horizon_performance`
- `v_preset_scan_performance`
- `v_preset_summary`
- `v_scan_combo_performance`
- `v_signal_entry_performance`
- `v_preset_overlap`

### 5.5 Saved run artifacts

When `data.persist_research_snapshots` is true, the pipeline saves:

- `eligible_snapshot/YYYYMMDD.csv`
- `run_metadata/YYYYMMDD.json`
- `market_summary/YYYYMMDD.json`
- `market_documents/YYYYMMDD.json`
- `market_documents/YYYYMMDD.md`
- `radar_summary/YYYYMMDD.json`
- date-level scan hits into `tracking.db`

`eligible_snapshot` is retained as the inspectable scan universe and saved-run restore base. The raw watchlist CSV is optional and controlled by `data.persist_watchlist_snapshot`; the default is false. When the watchlist CSV is absent, same-day saved-run restore rebuilds the watchlist from `eligible_snapshot` and stored scan hits. Preset-hit CSVs remain separate under `data_runs/preset_exports/`.

`market_documents/YYYYMMDD.json` is generated deterministically from the saved market summary, RS Radar industry leadership rows, and recent same-folder market summaries. It is an AI-input market document, not the final human-facing report. The document stores `schema_version=market_document.v1`, executive context, section facts, evidence source fields, trajectory summaries, significance flags, recent transitions, watchpoint candidates, analysis boundaries, missing inputs, and a data appendix. When `industry_leaders` are available, the document includes an `industry_leadership` section for industry-level RS leadership, 52W HIGH, acceleration, sustained leadership, and weak-industry context. The market summary and document include `volatility_term_structure`, `credit_risk_proxy`, and `index_state_summary` diagnostics when the configured auxiliary/index symbols are available. The saved market summary also includes `breadth_momentum_summary`, `breadth_internal_summary`, and `drawdown_summary`; report prose consumption for those fields is a later report-improvement phase. `market_documents/YYYYMMDD.md` renders the same market document for AI/skill input. The final human-facing report is owned by a report-writing skill and is written to `market_reports/YYYYMMDD.md`.

After the Streamlit artifact load syncs EntrySignal pools, the app evaluates the startup-selected entry signals and writes inspectable exports under `data_runs/entry_signals/`:

- `YYYYMMDD_evaluations.csv`

This CSV export mirrors the current Entry Signal evaluation output for review and diagnostics. Bucket-specific CSV and summary JSON write paths remain available in the runner but are disabled by default for startup exports. The authoritative pool, evaluation, and entry-event history remains `data_runs/tracking.db`.

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

The current same-day saved-run restore path restores the saved `eligible_snapshot`, `watchlist`, scan hits from SQLite, market summary, market document metadata, radar summary, and metadata. It still does not restore full `snapshot` or `fetch_status` CSVs; when those are unavailable, the pipeline builds a minimal snapshot carrying the saved trade date.

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
