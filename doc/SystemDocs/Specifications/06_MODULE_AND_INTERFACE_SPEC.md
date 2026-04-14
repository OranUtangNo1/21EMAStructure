# Module and Interface Spec

## 1. Design Split

The active codebase follows a stable three-part split:

- Config
- Calculator / Scorer / Evaluator
- Result

This keeps settings, reusable calculations, and display-ready outputs separate.

## 2. Active Module Ownership

### 2.1 Configuration

- `src/configuration.py`
  - loads YAML config files
  - resolves `includes`
  - supports both manifest files and config directories
- `config/default.yaml`
  - manifest entry point for active defaults
- `config/default/*.yaml`
  - section-level defaults for app, data, universe, indicators, scoring, scan, market, and radar

### 2.2 Data

- `src/data/finviz_provider.py`
  - default weekly universe discovery
  - snapshot-based profile and fundamental extraction
- `src/data/providers.py`
  - yfinance price, profile, and fundamental providers
  - optional Yahoo screener discovery provider
- `src/data/cache.py`
  - file-based cache with TTL and stale fallback
- `src/data/store.py`
  - universe snapshot persistence
  - per-run artifact persistence
  - latest saved-run loading for same-day restart reuse
- `src/data/universe.py`
  - post-price local eligible-universe filter
- `src/data/quality.py`
  - data-quality scoring, labels, and warning strings
- `src/data/models.py`
  - `SymbolProfile`
  - `FundamentalSnapshot`
- `src/data/results.py`
  - `FetchStatus`
  - price, profile, fundamental, universe-snapshot, and saved-run load result objects

### 2.3 Indicators

- `src/indicators/core.py`
  - 21EMA fields
  - SMA, weekly WMA, ATR, ADR, DCR
  - relative volume
  - RSI
  - weekly, monthly, quarterly returns
  - 52-week distance fields
  - up/down volume ratio
  - 3WT
  - pocket pivot and PP count
  - trend-base fields

### 2.4 Scoring

- `src/scoring/rs.py`
  - benchmark-relative strength by trailing ratio-window scoring
- `src/scoring/fundamental.py`
  - EPS and revenue-growth scoring
- `src/scoring/industry.py`
  - industry-level RS aggregation and normalization
- `src/scoring/hybrid.py`
  - hybrid ranking score and shorthand columns
- `src/scoring/vcs.py`
  - VCS series calculation and latest-score attachment

### 2.5 Scan

- `src/scan/rules.py`
  - `ScanConfig`
  - scan registries
  - annotation-filter registries
  - scan-context enrichment
- `src/scan/runner.py`
  - raw scan execution
  - watchlist aggregation
  - compatibility alias fields
  - backend duplicate marking

### 2.6 Dashboard

- `src/dashboard/watchlist.py`
  - watchlist table shaping
  - selected-scan projection
  - annotation-filter projection
  - duplicate-band projection
  - scan-card rebuilding
- `src/dashboard/radar.py`
  - ETF-based radar universe shaping
  - sector and industry leader tables
  - top daily and weekly mover tables
- `src/dashboard/market.py`
    - market condition scoring
    - ETF snapshot panels
    - factor-relative-strength tables
- `src/signals/rules.py`
    - entry signal registry
    - entry signal status config
    - signal-level evaluator functions
- `src/signals/runner.py`
    - duplicate-ticker universe assembly
    - entry-signal evaluation
    - signal result table shaping

### 2.7 App Layer

- `src/pipeline.py`
  - end-to-end orchestration
  - active artifact assembly
- `src/ui_preferences.py`
  - config-namespaced preference persistence
  - group persistence for current sidebar state
  - named collection persistence for watchlist preset records
- `app/main.py`
  - Streamlit entrypoint
  - page rendering
  - same-day saved-run reuse before pipeline recomputation
  - watchlist sidebar control state
  - watchlist preset save/load/update/delete UI with a 10-preset cap

### 2.8 Archived And Out-Of-Scope Modules

Final entry execution, chart-structure review for execution, sizing, and trade-management behavior remains archived and is not part of the active module graph.

Examples:

- final entry evaluators
- risk and exit evaluators
- position sizing calculators
- cockpit-style execution views

## 3. Core Interfaces

### 3.1 Configuration Interface

`load_settings(path)` currently supports:

- a manifest file with `includes`
- a config directory containing YAML fragments

The loader deep-merges dictionaries from included files and direct overrides.

### 3.2 Data Provider Interfaces

Abstract interfaces in `src/data/providers.py`:

- `PriceDataProvider.get_price_history(symbols, period, interval)`
- `ProfileDataProvider.get_profiles(symbols)`
- `FundamentalDataProvider.get_fundamentals(symbols)`
- `UniverseDiscoveryProvider.discover()`

Current concrete implementations:

- `YFinancePriceDataProvider`
- `YFinanceProfileDataProvider`
- `YFinanceFundamentalDataProvider`
- `FinvizScreenerProvider`
- `YahooScreenerProvider`

### 3.3 Pipeline Interface

`ResearchPlatform.run(symbols=None, force_universe_refresh=False)` returns `PlatformArtifacts`.

`ResearchPlatform.load_latest_run_artifacts(symbols=None, force_universe_refresh=False)` can also return `PlatformArtifacts` by reusing the latest same-day saved run when the current request matches the saved config path, manual-symbol input, and expected trade date.

The pipeline contract is:

1. resolve symbols
2. load price, profile, and fundamental data
3. calculate indicators
4. build the latest snapshot
5. attach status, score, earnings, and quality fields
6. filter the eligible universe
7. run scans and annotations
8. build watchlist, duplicate, radar, and market outputs
9. optionally persist run artifacts

### 3.4 Scan Interface

`ScanRunner.run(snapshot)` returns `ScanRunResult` with:

- `hits`
- `watchlist`

The scan layer contract is:

- input unit: one latest row per ticker
- scan hits create candidates
- annotation filters add flags and counts
- duplicate logic is scan-overlap based

### 3.5 Watchlist View Interface

`WatchlistViewModelBuilder` currently exposes:

- `build(watchlist)`
- `filter_by_annotation_filters(watchlist, selected_filter_names)`
- `apply_selected_scan_metrics(watchlist, hits, min_count, selected_scan_names, duplicate_rule=None)`
- `build_scan_cards(watchlist, hits, selected_scan_names)`
- `build_duplicate_tickers(watchlist, hits, min_count, selected_scan_names, selected_duplicate_subfilters, duplicate_rule=None)`
- `build_preset_export(preset_name, watchlist, hits, export_target, selected_scan_names, min_count, selected_annotation_filters, selected_duplicate_subfilters, duplicate_rule=None)`
- `build_earnings_today(snapshot)`

The active app uses raw `watchlist` plus `scan_hits` to rebuild cards and duplicate output from current sidebar selections.

### 3.6 Radar Interface

`RadarViewModelBuilder.build(etf_histories, benchmark_history)` returns `RadarResult` with:

- `sector_leaders`
- `industry_leaders`
- `top_daily`
- `top_weekly`
- `update_time`

### 3.7 Entry Signal Interface

`EntrySignalRunner` currently exposes:

- `build_default_universe(watchlist, hits, selected_scan_names, duplicate_threshold, selected_annotation_filters, selected_duplicate_subfilters, duplicate_rule)`
- `evaluate(universe, selected_signal_names)`

The entry signal layer is downstream of scan and preset duplicate logic. It does not evaluate all eligible tickers by default.

### 3.8 Market Interface

`MarketConditionScorer.score(stock_histories, market_histories, benchmark_history)` returns `MarketConditionResult`.

The scorer supports these calculation modes:

- `etf`
- `active_symbols`
- `blended`

## 4. Result Objects

### 4.1 PlatformArtifacts

The active pipeline bundle includes:

- `snapshot`
- `eligible_snapshot`
- `watchlist`
- `duplicate_tickers`
- `watchlist_cards`
- `earnings_today`
- `scan_hits`
- `benchmark_history`
- `vix_history`
- `market_result`
- `radar_result`
- `used_sample_data`
- `data_source_label`
- `fetch_status`
- `data_health_summary`
- `run_directory`
- `universe_mode`
- `resolved_symbols`
- `universe_snapshot_path`
- `artifact_origin`

`watchlist_cards` is still produced by the pipeline, but the active UI rebuilds cards from raw watchlist data so current sidebar selections can be applied.

### 4.2 ScanRunResult

`ScanRunResult` contains:

- `hits`
- `watchlist`

`hits` currently uses the columns:

- `ticker`
- `kind`
- `name`

### 4.3 RadarResult

`RadarResult` contains:

- `sector_leaders`
- `industry_leaders`
- `top_daily`
- `top_weekly`
- `update_time`

### 4.4 MarketConditionResult

`MarketConditionResult` contains:

- trade-date and score fields
- label history fields
- `component_scores`
- `breadth_summary`
- `performance_overview`
- `high_vix_summary`
- `market_snapshot`
- `leadership_snapshot`
- `external_snapshot`
- `factors_vs_sp500`
- `s5th_series`
- `vix_close`
- `update_time`

### 4.5 Data Status Models

`FetchStatus` records:

- `symbol`
- `dataset`
- `source`
- `has_data`
- `fetched_at`
- `note`

## 5. Implementation Rules

- keep config, calculation, and result concerns separate
- keep the active scope limited to screening outputs
- keep fetch status and data-quality fields as product behavior
- keep watchlist generation scan-driven
- keep page-local UI projection in the dashboard layer, not the scan engine
