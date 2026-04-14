# Parameter Catalog

## 1. Principle

The active implementation keeps thresholds, weights, universes, and modes rooted at `config/default.yaml`.
That entry file is a manifest which includes section-level files under `config/default/`.
This catalog lists the parameters that are active in the current codebase and calls out shipped keys that are currently inactive.

Archived final-entry, chart-structure, sizing, and trade-management parameters are out of scope for this file. The implemented `entry_signals` timing layer is documented because it is present in the active config and UI.

## 2. App and persistence

### app.default_symbols
- default symbol list used only when manual symbols and reusable weekly snapshots are unavailable

### app.benchmark_symbol
- current default: `SPY`

### app.vix_symbol
- current default: `^VIX`

### app.price_period
- current default: `1y`

### app.cache_dir
- current default: `data_cache`

### app.snapshot_dir
- current default: `data_runs`

### app.user_preferences_path
- current default: `data_cache/user_preferences.yaml`
- stores persisted watchlist sidebar selections and config-namespaced watchlist preset records

### app.use_sample_data_if_fetch_fails
- current default: `false`
- when true, the pipeline can synthesize sample price, profile, and fundamental data for missing symbols

### app.refresh_on_start
- present in `config/default/app.yaml`
- currently not consumed by active code

## 3. Data and cache

### data.technical_cache_ttl_hours
- current default: `12`

### data.profile_cache_ttl_hours
- current default: `168`

### data.fundamental_cache_ttl_hours
- current default: `24`

### data.allow_stale_cache_on_failure
- current default: `true`

### data.persist_research_snapshots
- current default: `true`

### data.price_batch_size
- current default: `80`

### data.price_max_retries
- current default: `3`

### data.price_request_sleep_seconds
- current default: `2.0`

### data.price_retry_backoff_multiplier
- current default: `2.0`

### data.price_incremental_period
- current default: `5d`
- used when refreshing symbols that only have stale cached price history

## 4. Universe discovery and local universe filter

### universe_discovery.enabled
- current default: `true`

### universe_discovery.provider
- current default: `finviz`
- supported active values in code: `finviz`, `yahoo`

### universe_discovery.use_snapshot_when_no_manual_symbols
- current default: `true`

### universe_discovery.snapshot_ttl_days
- current default: `7`

### universe_discovery.allowed_exchanges
- current default: `NASDAQ`, `NYSE`, `AMEX`

### universe_discovery.excluded_sectors
- current default: `Healthcare`

### universe_discovery.max_symbols
- current default: `2500`

### universe_discovery.min_market_cap
- current default: `1B`

### universe.min_market_cap
- current default: `1B`

### universe.min_avg_volume_50d
- current default: `1M`

### universe.min_price
- current default: `0.0`

### universe.min_adr_percent
- current default: `3.5`

### universe.max_adr_percent
- current default: `10.0`

### universe.excluded_sectors
- current default: `Healthcare`

## 5. Indicators

### indicators.ema_period
- current default: `21`

### indicators.sma_short_period
- current default: `50`

### indicators.sma_long_period
- current default: `200`

### indicators.atr_period
- current default: `14`

### indicators.adr_period
- current default: `20`

### indicators.adr_formula
- current default: `sma_high_low_ratio`

### indicators.dcr_formula
- current default: `closing_range`
- the active indicator code currently always computes the closing-range formula

### indicators.relvol_period
- current default: `50`

### indicators.ud_volume_period
- current default: `50`

### indicators.rsi_short_period
- current default: `21`

### indicators.rsi_long_period
- current default: `63`

### indicators.weekly_short_wma_period
- current default: `10`

### indicators.weekly_long_wma_period
- current default: `20`

### indicators.three_weeks_tight_pct_threshold
- current default: `1.5`

### indicators.enable_3wt
- current default: `true`

### indicators.atr_21ema_good_min
- current default: `-0.5`

### indicators.atr_21ema_good_max
- current default: `1.0`

### indicators.atr_50sma_good_max
- current default: `3.0`

### indicators.ema21_low_pct_full_max
- current default: `5.0`

### indicators.ema21_low_pct_reduce_max
- current default: `8.0`

### indicators.atr_pct_from_50sma_overheat
- current default: `7.0`

### indicators.show_overheat_dot
- current default: `true`
- currently not consumed by active UI code

### indicators.pp_count_window_days
- current default: `20`

### indicators.pocket_pivot_lookback
- current default: `10`

## 6. Scoring

### scoring.rs
- `benchmark_symbol`: `SPY`
- `rs_lookbacks`: `[5, 21, 63, 126]`
- `rs_normalization_method`: `percentile`
- `rs_strong_threshold`: `80`
- `rs_weak_threshold`: `39`

When `rs_normalization_method = percentile`, the current implementation uses the trailing-window percent-rank of the symbol's own `price_ratio = close / SPY` series.

### scoring.fundamental
- `eps_weight`: `1.0`
- `revenue_weight`: `1.0`
- `fundamental_normalization_method`: `percentile`
- `missing_fundamental_policy`: `fill_neutral`

### scoring.industry
- `industry_aggregation_method`: `mean`
- `industry_rs_input_metric`: `rs21`
- `industry_score_normalization_method`: `percentile`

### scoring.hybrid
- `rs_weights`: `[1.0, 2.0, 2.0]`
- `fundamental_weight`: `2.0`
- `industry_weight`: `3.0`
- `hybrid_missing_value_policy`: `fill_neutral_50`

### scoring.vcs
- `vcs_threshold_candidate`: `60.0`
- `vcs_threshold_priority`: `80.0`
- `len_short`: `13`
- `len_long`: `63`
- `len_volume`: `50`
- `hl_lookback`: `63`
- `sensitivity`: `2.0`
- `trend_penalty_weight`: `1.0`
- `penalty_factor`: `0.75`
- `bonus_max`: `15.0`

## 7. Scan and watchlist

### Scan thresholds
- `daily_gain_bullish_threshold`: `4.0`
- `relative_volume_bullish_threshold`: `1.0`
- `relative_volume_vol_up_threshold`: `1.5`
- `momentum_97_weekly_rank`: `97.0`
- `momentum_97_quarterly_rank`: `85.0`
- `club_97_hybrid_threshold`: `90.0`
- `club_97_rs21_threshold`: `97.0`
- `vcs_min_threshold`: `60.0`
- `vcs_52_high_vcs_min`: `55.0`
- `vcs_52_high_rs21_min`: `25.0`
- `vcs_52_high_dist_max`: `-20.0`
- `vcs_52_high_require_trend_base`: `true`
- `vcs_52_low_vcs_min`: `60.0`
- `vcs_52_low_rs21_min`: `80.0`
- `vcs_52_low_dist_max`: `25.0`
- `vcs_52_low_dist_from_52w_high_max`: `-65.0`
- `vol_accum_ud_ratio_min`: `1.5`
- `vol_accum_rel_vol_min`: `1.0`
- `weekly_gainer_threshold`: `20.0`
- `near_52w_high_threshold_pct`: `5.0`
- `near_52w_high_hybrid_min`: `70.0`
- `three_weeks_tight_vcs_min`: `50.0`
- `rs_acceleration_rs21_min`: `70.0`
- `fund_demand_fundamental_min`: `70.0`
- `fund_demand_rs21_min`: `60.0`
- `fund_demand_rel_vol_min`: `1.0`
- `sustained_rs21_min`: `80.0`
- `sustained_rs63_min`: `70.0`
- `sustained_rs126_min`: `60.0`
- `reversal_dist_52w_low_max`: `40.0`
- `reversal_dist_52w_high_min`: `-40.0`
- `reversal_rs21_min`: `50.0`
- `pp_count_scan_min`: `3`
- `pp_count_annotation_min`: `2`
- `duplicate_min_count`: `3`
- `high_eps_growth_rank_threshold`: `90.0`
- `earnings_warning_days`: `7`

### Watchlist and cards
- `watchlist_sort_mode`: `hybrid_score`
- `scan_status_map`: per-scan runtime status map
  - `enabled`: evaluate the scan and keep it available to watchlist card selection and preset composition
  - `disabled`: skip scan evaluation and remove it from watchlist card selection and preset composition
- `enabled_scan_rules`: legacy enabled scan family list still accepted for backward compatibility
- `default_selected_scan_names`: startup-selected watchlist cards for the sidebar multiselect
- `enabled_annotation_filters`: startup-enabled post-scan filters; current default is empty
- `enabled_list_rules`: legacy alias still accepted for annotation rules
- misplaced scan names inside `enabled_annotation_filters` are coerced into the enabled scan rule set during config loading
- `annotation_filters`: available annotation-filter definitions and display names
- `watchlist_presets`: built-in watchlist preset definitions loaded into the sidebar preset picker
  - each preset supports `preset_name`, `selected_scan_names`, `selected_annotation_filters`, `selected_duplicate_subfilters`, `duplicate_threshold`, optional `duplicate_rule`, and `preset_status`
  - `duplicate_rule.mode: min_count` uses `min_count` scan hits
  - `duplicate_rule.mode: required_plus_optional_min` requires every scan in `required_scans` plus at least `optional_min_hits` hits from `optional_scans`
  - duplicate-rule scan references must stay within the preset's `selected_scan_names`
  - `preset_status: enabled` shows the preset in the UI and includes it in automatic preset exports
  - `preset_status: hidden_enabled` hides the preset from the UI and still includes it in automatic preset exports
  - `preset_status: disabled` hides the preset from the UI and excludes it from automatic preset exports
  - a built-in preset that references any non-enabled scan is forced to `preset_status: disabled`
  - legacy `export_enabled: false` is still accepted and maps to `preset_status: disabled`
- `preset_csv_export`: automatic preset CSV export settings
  - `enabled`: turn automatic batch export on or off
  - `output_dir`: root output directory for day-based export folders
  - `write_details`: whether to also write `preset_details.csv`
  - `top_ticker_limit`: legacy setting retained for compatibility; `preset_summary.csv` now writes one row per output ticker and lists matching presets in `hit_presets`
- `card_sections`: scan-based card definitions, display names, and optional `sort_columns`

## 8. Entry signals

The `entry_signals` section controls the Entry Signals tab.

- `signal_status_map`: per-entry-signal runtime status map
  - `enabled`: keep the signal available for UI selection and evaluation
  - `disabled`: keep the logic in code but remove it from UI selection and evaluation
- `default_selected_signal_names`: startup-selected entry signals for the Entry Signals tab

Current built-in entry signal names:

- `Pocket Pivot Entry`
- `Structure Pivot Breakout Entry`
- `Pullback Low-Risk Zone`
- `Volume Reclaim Entry`

## 9. Market Dashboard

### Scoring mode and thresholds
- `calculation_mode`: current default `etf`; supported values are `etf`, `active_symbols`, `blended`
- `etf_weight`: current default `0.5`
- `active_symbols_weight`: current default `0.5`
- `bullish_threshold`: `80.0`
- `positive_threshold`: `60.0`
- `neutral_threshold`: `40.0`
- `negative_threshold`: `20.0`
- `vix_neutral_level`: `17.0`
- `vix_score_slope`: `5.0`
- `safe_haven_risk_on_symbol`: `SPY`
- `safe_haven_risk_off_symbol`: `TLT`
- `safe_haven_window`: `20`
- `safe_haven_score_scale`: `4.0`

### Component weights
- `pct_above_sma20`: `0.12`
- `pct_above_sma50`: `0.14`
- `pct_above_sma200`: `0.14`
- `pct_sma50_gt_sma200`: `0.08`
- `pct_positive_1m`: `0.09`
- `pct_positive_3m`: `0.08`
- `pct_2w_high`: `0.05`
- `safe_haven_score`: `0.15`
- `vix_score`: `0.15`

### Universes
- `market_condition_etf_universe`: core ETF universe used for market scoring
- `leadership_etfs`: display-only leadership ETF universe
- `external_etfs`: display-only external ETF universe
- `factor_etfs`: factor-comparison ETF universe

## 10. RS Radar

### Radar parameters
- `top_movers_count`: `3`
- `overall_rs_weights`: `[1.0, 2.0, 2.0]`
- `near_high_threshold_pct`: `0.5`

### Radar universes
- `sector_etfs`: configured sector ETF list
- `industry_etfs`: configured industry ETF list with optional `major_stocks`

## 11. Inactive shipped config block

### optional.enable_darvas_retest_filter
- current default: `false`
- present in the manifest include set
- not consumed by active screening code

### optional.enable_trend_regime_filter
- current default: `false`
- present in the manifest include set
- not consumed by active screening code

## 12. Persisted research outputs

When persistence is enabled, the current implementation saves these run-level artifacts:

- latest snapshot
- eligible snapshot
- watchlist table
- fetch-status table
- run metadata
- weekly universe snapshots
