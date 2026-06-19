# Parameter Catalog

## 1. Principle

The active implementation keeps thresholds, weights, universes, and modes rooted at `config/default.yaml`.
That entry file is a manifest which includes section-level files under `config/default/`.
This catalog focuses on parameters used by the current UI and runtime workflow.

Archived final discretionary execution, sizing, and trade-management parameters are out of scope for this file. The implemented `entry_signals` timing layer and Analysis database behavior are documented because they are present in the active config and UI.

## 2. App and persistence

### app.default_symbols
- default symbol list used only when manual symbols and reusable weekly snapshots are unavailable

### app.benchmark_symbol
- current default: `SPY`

### app.vix_symbol
- current default: `^VIX`

### app.price_period
- current default: `3y`

### app.cache_dir
- current default: `data_cache`

### app.snapshot_dir
- current default: `data_runs/legacy_pipeline`

### app.user_preferences_path
- current default: `data_cache/user_preferences.yaml`
- stores persisted watchlist control selections and config-namespaced watchlist preset records

### app.use_sample_data_if_fetch_fails
- current default: `false`
- when true, the pipeline can synthesize sample price, profile, and fundamental data for missing symbols

## 3. Data and cache

### data.price_cache_dir
- current default: `C:/reository/shared_market_cache`
- stores shared price and market time-series cache files such as `prices_AAPL_1d.csv`
- is separate from `app.cache_dir`, which remains project-local for non-price cache and user preference defaults

### data.technical_cache_ttl_hours
- current default: `12`
- bypassed for price histories when the app's `Force price data refresh` run option passes `force_price_refresh=True`; this does not clear cache files

### data.profile_cache_ttl_hours
- current default: `168`

### data.fundamental_cache_ttl_hours
- current default: `24`

### data.allow_stale_cache_on_failure
- current default: `true`

### data.persist_research_snapshots
- current default: `true`

### data.retention.eligible_snapshot_runs
- current default: `5`
- after each successful run save, keeps only the latest N date-keyed files in `data_runs/eligible_snapshot/`

### data.retention.run_metadata_runs
- current default: `5`
- after each successful run save, keeps only the latest N date-keyed files in `data_runs/run_metadata/`

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
- used when refreshing symbols that have cached price history, including force-refresh runs that keep cached rows as the merge/fallback base

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

### indicators.sma_medium_period
- current default: `150`
- used for Stage/Trend Template context as the daily proxy for Weinstein's 30-week moving average

### indicators.sma_long_period
- current default: `200`

### indicators.sma_long_slope_lookback
- current default: `21`
- used to confirm the 200-day moving average slope over roughly one trading month

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
- current default: `30`

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

### indicators.pp_count_window_days
- current default: `20`

### indicators.pocket_pivot_lookback
- current default: `10`

### indicators.structure_pivot_min_length
- current default: `2`

### indicators.structure_pivot_max_length
- current default: `10`

### indicators.structure_pivot_priority_mode
- current default: `tightest`

### indicators.structure_pivot_include_short
- current default: `false`

### indicators.resistance_test_lookback
- current default: `20`

### indicators.resistance_zone_width_atr
- current default: `0.5`

### indicators.resistance_test_count_window
- current default: `20`

### indicators.vcp_* fields
- `vcp_prior_uptrend_lookback`: `126`
- `vcp_prior_uptrend_min_pct`: `30.0`
- `vcp_t1_window`: `20`
- `vcp_t1_shift`: `16`
- `vcp_t2_window`: `10`
- `vcp_t2_shift`: `6`
- `vcp_t3_window`: `5`
- `vcp_t3_shift`: `1`
- `vcp_pivot_lookback`: `20`
- `vcp_tight_daily_range_pct`: `3.0`
- `vcp_base_lookback`: `50`
- `vcp_tight_window`: `10`
- `vcp_contraction_ratio`: `0.78`
- `vcp_adr_ceiling`: `3.5`
- `vcp_range_ceiling`: `12.0`
- `vcp_vdu_ratio`: `0.75`
- `vcp_proximity_band`: `0.08`

### indicators Stage/Trend Template derived fields
- `sma150`
- `sma150_slope_1m_pct`
- `sma200_slope_1m_pct`
- `high_3y`
- `dist_from_3y_high`
- `trend_template_price_score`
- `trend_template_price_setup`
- `stage_label`

## 6. Scoring

### scoring.rs
- `benchmark_symbol`: `SPY`
- `rs_lookbacks`: `[5, 21, 63, 126]`
- `rs_normalization_method`: `percentile`
- `rs_strong_threshold`: `80`
- `rs_weak_threshold`: `39`
- `rs_new_high_tolerance`: `1.0`

When `rs_normalization_method = percentile`, the current implementation uses the trailing-window percent-rank of the symbol's own `price_ratio = close / SPY` series.
RS scoring also emits `rs_ratio_52w_high`, `rs_ratio_at_52w_high`, `rs_ratio_3y_high`, and `rs_ratio_at_3y_high`.

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
- `sustained_rs21_min`: `80.0`
- `sustained_rs63_min`: `70.0`
- `sustained_rs126_min`: `60.0`
- `reversal_dist_52w_low_max`: `40.0`
- `reversal_dist_52w_high_min`: `-40.0`
- `reversal_rs21_min`: `50.0`
- `structure_pivot_breakout_rel_volume_min`: `1.4`
- `structure_pivot_include_gap_up_breakouts`: `true`
- `pp_count_scan_min`: `3`
- `pp_count_annotation_min`: `2`
- `rs_new_high_price_dist_max`: `-5.0`
- `rs_new_high_price_dist_min`: `-30.0`
- `rs_3y_new_high_price_dist_max`: `-5.0`
- `rs_3y_new_high_price_dist_min`: `-35.0`
- `trend_template_price_score_min`: `7`
- `trend_template_rs_min`: `70.0`
- `stage2_price_score_min`: `5`
- `stage2_rs_min`: `60.0`
- `duplicate_min_count`: `3`
- `high_eps_growth_rank_threshold`: `90.0`
- `earnings_warning_days`: `7`

### Watchlist and cards
- `watchlist_sort_mode`: `hybrid_score`
- `scan_status_map`: per-scan runtime status map
  - `enabled`: evaluate the scan and keep it available to watchlist card selection and preset composition
  - `disabled`: skip scan evaluation and remove it from watchlist card selection and preset composition
- `enabled_scan_rules`: enabled scan family list loaded by the current config
- `default_selected_scan_names`: startup-selected watchlist cards for the watchlist controls
- `annotation_filter_status_map`: per-annotation-filter runtime status map
  - `enabled`: keep the filter available for UI selection, runtime evaluation, and preset loading
  - `disabled`: keep the filter definition in config but remove it from UI selection and runtime evaluation
- `enabled_annotation_filters`: startup-enabled post-scan filters; current default is empty
- `enabled_list_rules`: compatibility alias still accepted for annotation rules
- misplaced scan names inside `enabled_annotation_filters` are coerced into the enabled scan rule set during config loading
- `annotation_filters`: available annotation-filter definitions and display names
- default annotation filter names include:
  - `Stage 2 Quality Score`
  - `Mature / Late Stage Risk Filter`
  - `Industry Leadership Gate`
  - `Recent Power Gap`
  - `Trend Template`
- older annotation filter evaluators remain available to custom configs through `ANNOTATION_FILTER_REGISTRY`, but are not included in the default UI filter set
- `watchlist_presets`: built-in watchlist preset definitions loaded into the watchlist preset picker
  - each preset supports `preset_name`, `selected_scan_names`, `selected_annotation_filters`, `selected_duplicate_subfilters`, `duplicate_threshold`, optional `duplicate_rule`, and `preset_status`
  - `duplicate_rule.mode: min_count` uses `min_count` scan hits
  - `duplicate_rule.mode: required_plus_optional_min` requires every scan in `required_scans` plus at least `optional_min_hits` hits from `optional_scans`
  - `duplicate_rule.mode: grouped_threshold` requires every scan in `required_scans` plus every group threshold in `optional_groups`
  - each grouped threshold item supports `group_name`, `scans`, and `min_hits`
  - duplicate-rule scan references must stay within the preset's `selected_scan_names`
  - `preset_status: enabled` shows the preset in the UI and includes it in preset export output when that export is run
  - `preset_status: hidden_enabled` hides the preset from the UI and still includes it in preset export output when that export is run
  - `preset_status: disabled` hides the preset from the UI and excludes it from preset export output
  - preset-selected annotation filters that are not currently enabled are dropped during config loading
  - a built-in preset that references any non-enabled scan is forced to `preset_status: disabled`
  - compatibility `export_enabled: false` is still accepted and maps to `preset_status: disabled`
- `preset_csv_export`: preset CSV export settings
  - `enabled`: current default `false`; turn startup automatic batch export on or off after full pipeline recompute
  - `output_dir`: root output directory for day-based export folders
  - preset export writes `preset_summary.csv` and `preset_hits.csv` for active built-in presets and saved custom presets
  - `write_details`: whether to also write the wide `preset_details.csv`
  - `top_ticker_limit`: compatibility setting; `preset_summary.csv` writes one row per output ticker and lists matching presets in `hit_presets`
- `card_sections`: scan-based card definitions, display names, and optional `sort_columns`

## 8. Entry signals

The `entry_signals` section controls the Entry Signals tab.

- `output.mode`: current default `latest_only`; supported values are `daily_history`, `latest_only`, `on_demand`, and `disabled`
  - `latest_only`: artifact-load export writes `data_runs/legacy_pipeline/entry_signals/latest_evaluations.csv`
  - `daily_history`: artifact-load export writes `data_runs/legacy_pipeline/entry_signals/YYYYMMDD_evaluations.csv`
  - `on_demand` or `disabled`: startup export evaluates signals but suppresses review CSV writes
- `context_guard`: optional cross-signal safety layer applied after the signal-specific evaluator
  - `enabled`: turn the shared guard on or off
  - `weak_market_score_threshold`: cap detected signals below `Signal Detected` when `market_score` is below this value
  - `signal_overrides`: optional per-signal lower-bound override for `weak_market_score_threshold`
  - `cap_below_signal_detected`: keep guarded rows visible but force their display bucket below `Signal Detected`
  - `earnings.warning_field`: boolean row field used for near-term earnings warning, currently `earnings_in_7d`
  - `earnings.today_field`: boolean row field used for same-day earnings warning, currently `earnings_today`
- `signal_status_map`: per-entry-signal runtime status map
  - `enabled`: keep the signal available for UI selection and evaluation
  - `disabled`: keep the logic in code but remove it from UI selection and evaluation
- `default_selected_signal_names`: startup-selected entry signals for the Entry Signals tab
  - any default-selected signal that is currently disabled is dropped during config loading

Current built-in entry signal names:

- `orderly_pullback_entry`
- `pullback_resumption_entry`
- `momentum_acceleration_entry`
- `accumulation_breakout_entry`
- `power_gap_pullback_entry`

Each entry signal definition may include an `action` section. These thresholds drive `Action Bucket` classification on the Entry Signal page.

```yaml
action:
  entry_ready:
    entry_strength_min: 50
    timing_min: 50
    risk_reward_min: 50
    rr_ratio_min: 2.0
    setup_maturity_min: 40
  watch_setup:
    setup_maturity_min: 45
    risk_reward_min: 30
```

The thresholds are signal-specific. Missing `action` values fall back to the defaults shown above. Entry Signal `Missing Piece` text is derived from these thresholds plus each evaluator's maturity/timing detail scores and risk/reward values, so a low timing score should point to the weak trigger component where available.

The same `entry_ready.rr_ratio_min` value is used as the minimum acceptable `R/R Current` or `R/R Ideal` for generated entry plans. EntrySignal strategies choose signal-specific SL and TP1 candidate structures; pullback-style signals prioritize structural and moving-average support plus nearby resistance, while momentum and breakout-style signals can use 2R, measured-move, and momentum targets before falling back to broad resistance. `Max Entry Price` is derived from TP1, SL, and the minimum R/R so the UI can show `Wait Pullback` candidates whose current close is too extended but whose entry zone would satisfy the threshold. TP2 is not price-calculated in the current active system and is displayed as the future trailing-stop plan. Stop-loss generation applies the configured ATR buffer, a minimum 1 ATR distance in the plan layer, and a round-number buffer. Plan failures and downgrades are exposed as reject codes so excluded entries can be reviewed later.

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
- `risk_on_ratio_numerator_symbol`: `IWO`
- `risk_on_ratio_denominator_symbol`: `IWN`
- `risk_on_ratio_high_window`: `756`
- `risk_on_ratio_ma_windows`: `[20, 50, 200]`
- `market_auxiliary_symbols.vix9d_symbol`: `^VIX9D`
- `market_auxiliary_symbols.vix3m_symbol`: `^VIX3M`
- `market_auxiliary_symbols.credit_high_yield_symbol`: `HYG`
- `market_auxiliary_symbols.credit_investment_grade_symbol`: `LQD`
- `market_auxiliary_symbols.credit_treasury_symbol`: `IEF`
- `market_auxiliary_symbols.credit_high_yield_oas_symbol`: `BAMLH0A0HYM2`
- `drawdown_window`: `252`
- `index_state.symbols`: `[SPY, QQQ]`
- `index_state.rally_low_lookback`: `25`
- `index_state.ftd_min_gain_pct`: `1.7`
- `index_state.ftd_min_rally_day`: `4`
- `index_state.distribution_decline_pct`: `-0.2`
- `index_state.distribution_lookback`: `25`
- `index_state.distribution_pressure_count`: `5`

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
- `external_etfs`: display-only external ETF universe
- `factor_etfs`: factor-comparison ETF universe

Market Dashboard does not fetch or compute the former leadership ETF snapshot by default. Sector and industry leadership ranking belongs to RS Radar. Market Dashboard does compute `sector_relative_strength` for configured sector ETFs in the core universe so market documents can read sector rotation rank deltas.

### Market document
- `market_report.output.mode`: current default `latest_only`; supported values are `daily_history`, `latest_only`, `on_demand`, and `disabled`
- `market_report.output.write_json`: current default `true`; writes the AI-input market document JSON using the configured output mode
- `market_report.output.write_markdown`: current default `false`; Markdown compatibility input is not written by default
- `market_report.horizons.short_days`: current default `5`
- `market_report.horizons.medium_days`: current default `21`
- `market_report.horizons.long_days`: current default `63`
- `market_report.regime.score_improving_1w`: current default `3.0`
- `market_report.regime.score_deteriorating_1w`: current default `-3.0`
- `market_report.regime.score_improving_1m`: current default `5.0`
- `market_report.regime.score_deteriorating_1m`: current default `-5.0`
- `market_report.regime.neutral_score_floor`: current default `40.0`; lower bound used by market action mode classification
- `market_report.regime.positive_score_floor`: current default `60.0`; positive-score threshold used by market action mode classification
- `market_report.breadth.strong_level`: current default `70.0`
- `market_report.breadth.weak_level`: current default `50.0`
- `market_report.breadth.s2w_high_active_level`: current default `30.0`
- `market_report.breadth.s2w_high_weak_level`: current default `15.0`
- `market_report.volatility.vix_low_level`: current default `12.0`
- `market_report.volatility.vix_neutral_level`: current default `17.0`
- `market_report.volatility.vix_elevated_level`: current default `25.0`
- `market_report.volatility.vix_stress_level`: current default `30.0`
- `market_report.risk.safe_haven_positive_threshold`: current default `2.0`
- `market_report.risk.safe_haven_negative_threshold`: current default `-2.0`
- `market_report.risk.high_distance_warning_pct`: current default `-5.0`
- `market_report.confidence.minimum_required_metric_coverage`: current default `0.8`
- `market_report.confidence.disagreement_penalty`: current default `0.2`

### Market context
- `market_context.output.dir`: current default `data_runs/service_outputs/market_context`
- `market_context.output.mode`: current default `latest_only`; supported values are `daily_history`, `latest_only`, `on_demand`, and `disabled`
- `market_context.output.write_markdown`: current default `false`; Markdown compatibility input is not written by default
- `market_context.output.write_json`: current default `true`; writes JSON using the configured output mode
- `market_context.industry_top_n`: current default `8`; controls the fixed top industry count rendered in `INDUSTRY_RS`
- emitted schema: `v1.0.1`
- `INDUSTRY_RS` row format: `tactRS|structRS63|dRank1W|majors`
- `INDUSTRY_RS.dRank1W`: prior full-universe `STRUCT RS` rank minus current full-universe `STRUCT RS` rank; emits `NA` when comparable structural-rank history is unavailable

### Compressed tape
- `compressed_tape.enabled`: current default `true`
- `compressed_tape.output_dir`: current default `data_runs/documents/compressed_tape`
- `compressed_tape.t0_days`: current default `15`
- `compressed_tape.t1_days`: current default `50`
- `compressed_tape.events_lookback_days`: current default `50`
- `compressed_tape.volume_window`: current default `50`
- `compressed_tape.max_events`: current default `8`
- `compressed_tape.validate_snapshot_last_close`: current default `false`; standalone tape export does not require snapshot close matching unless this is enabled

### Stock card
- `stock_card.enabled`: current default `true`
- `stock_card.output_dir`: current default `data_runs/documents/stock_cards`
- `stock_card.write_markdown`: current default `true`; writes the compatibility Markdown stock-card rendering
- `stock_card.write_json`: current default `true`; writes the canonical AI/system stock-card JSON payload
- `stock_card.validate_snapshot_last_close`: current default `false`; standalone stock-card export does not require snapshot close matching unless this is enabled
- `stock_card.compressed_tape.*`: nested compressed-tape settings used for the embedded `TAPE` section
- emitted schema: `card-v1.0.2`
- stock-card metadata resolves `INDUSTRY_ETF` from configured industry major stocks first, then profile/snapshot industry names when a known industry-to-ETF mapping is available
- non-pivot setup candidates expire when current close is more than 2% above the candidate basis
- current-day pivot breakouts are prioritized over pullback candidates when the final close clears the prior 65-day high
- structural stop candidates must be within -8% of basis and at least `max(1.0 * ATR14, 2.5%)` below basis

## 10. RS Radar

### Radar parameters
- `top_movers_count`: `3`
- `overall_rs_weights`: `[1.0, 2.0, 2.0]`
- `structural_rs_weights`: `[1.0, 1.0]`
- `near_high_threshold_pct`: `0.5`

### Radar universes
- `sector_etfs`: configured sector ETF list
- `industry_etfs`: configured industry ETF list with optional `major_stocks`; current default count is 35

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

- eligible snapshot table
- optional watchlist table when `data.persist_watchlist_snapshot` is true
- run metadata
- weekly universe snapshots
- market summary JSON
- market document JSON
- market document Markdown
- radar summary JSON
- date-level scan-hit history in `data_runs/tracking.db`

`data.persist_watchlist_snapshot` defaults to `false`. The saved-run restore path rebuilds the watchlist from `eligible_snapshot` and stored scan hits when the raw watchlist table is not persisted.

The current implementation also maintains preset-hit tracking data in `data_runs/tracking.db`:

- detection rows for export-enabled built-in preset duplicate hits
- detection-to-scan bridge rows
- detection-to-filter bridge rows
- horizon closes and returns for 1D, 5D, 10D, 20D, and 21D
- SQLite views used by Analysis and repository read APIs

Analysis UI constants currently live in `app/main.py`, not in YAML:

- horizons: `1`, `5`, `10`, `20`
- market environments: `bull`, `neutral`, `weak`, `bear`
- benchmark choices: `SPY`, `QQQ`, `IWM`
