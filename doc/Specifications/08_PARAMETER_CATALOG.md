# Parameter Catalog

## 1. Principle

The active implementation keeps thresholds, weights, universes, and modes rooted at `config/default.yaml`.
That entry file is a manifest which includes section-level files under `config/default/`.
This catalog lists the parameters that are active in the current codebase.

Archived entry, structure, sizing, and trade-management parameters are out of scope for this file.

---

## 2. App and persistence

### app.default_symbols
- default symbol list used only when manual symbols and weekly snapshots are unavailable

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

### app.use_sample_data_if_fetch_fails
- current default: `false`

---

## 3. Data and cache

### technical_cache_ttl_hours
- current default: `12`

### profile_cache_ttl_hours
- current default: `168`

### fundamental_cache_ttl_hours
- current default: `24`

### allow_stale_cache_on_failure
- current default: `true`

### persist_research_snapshots
- current default: `true`

### price_batch_size
- current default: `80`

### price_max_retries
- current default: `3`

### price_request_sleep_seconds
- current default: `2.0`

### price_retry_backoff_multiplier
- current default: `2.0`

### price_incremental_period
- current default: `5d`

---

## 4. Universe discovery and local universe filter

### universe_discovery.provider
- current default: `finviz`

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

---

## 5. Indicators

### ema_period
- current default: `21`

### sma_short_period
- current default: `50`

### sma_long_period
- current default: `200`

### atr_period
- current default: `14`

### adr_period
- current default: `20`

### adr_formula
- current default: `sma_high_low_ratio`

### dcr_formula
- current default: `closing_range`

### relvol_period
- current default: `50`

### ud_volume_period
- current default: `50`

### rsi_short_period
- current default: `21`

### rsi_long_period
- current default: `63`

### weekly_short_wma_period
- current default: `10`

### weekly_long_wma_period
- current default: `30`

### three_weeks_tight_pct_threshold
- current default: `1.5`

### enable_3wt
- current default: `true`

### atr_21ema_good_min
- current default: `-0.5`

### atr_21ema_good_max
- current default: `1.0`

### atr_50sma_good_max
- current default: `3.0`

### ema21_low_pct_full_max
- current default: `5.0`

### ema21_low_pct_reduce_max
- current default: `8.0`

### atr_pct_from_50sma_overheat
- current default: `7.0`

### show_overheat_dot
- current default: `true`

### pp_count_window_days
- current default: `30`

### pocket_pivot_lookback
- current default: `10`

---

## 6. Scoring

### RS
- `benchmark_symbol`: `SPY`
- `rs_lookbacks`: `[5, 21, 63, 126]`
- `rs_normalization_method`: `percentile`
- `rs_strong_threshold`: `80`
- `rs_weak_threshold`: `39`

When `rs_normalization_method = percentile`, the current implementation uses the trailing-window percentrank of the symbol's own `price_ratio = close / SPY` series.

### Fundamental
- `eps_weight`: `1.0`
- `revenue_weight`: `1.0`
- `fundamental_normalization_method`: `percentile`
- `missing_fundamental_policy`: `fill_neutral`

### Industry
- `industry_aggregation_method`: `mean`
- `industry_rs_input_metric`: `rs21`
- `industry_score_normalization_method`: `percentile`

### Hybrid
- `rs_weights`: `[1.0, 2.0, 2.0]`
- `fundamental_weight`: `2.0`
- `industry_weight`: `3.0`
- `hybrid_missing_value_policy`: `fill_neutral_50`

### VCS
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

---

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
- `vcs_52_high_vcs_min`: `60.0`
- `vcs_52_high_rs21_min`: `60.0`
- `vcs_52_high_dist_max`: `-15.0`
- `vcs_52_low_vcs_min`: `60.0`
- `vcs_52_low_rs21_min`: `60.0`
- `vcs_52_low_dist_max`: `25.0`
- `vol_accum_ud_ratio_min`: `1.5`
- `vol_accum_rel_vol_min`: `1.0`
- `weekly_gainer_threshold`: `20.0`
- `near_52w_high_threshold_pct`: `5.0`
- `near_52w_high_hybrid_min`: `70.0`
- `three_weeks_tight_vcs_min`: `50.0`
- `rs_acceleration_rs21_min`: `70.0`
- `duplicate_min_count`: `3`
- `high_eps_growth_rank_threshold`: `90.0`
- `earnings_warning_days`: `7`

### Watchlist and cards
- `watchlist_sort_mode`: `hybrid_score`
- `enabled_scan_rules`: active scan family names
- `default_selected_scan_names`: startup-selected watchlist cards for the sidebar multiselect
- `enabled_annotation_filters`: active annotation-rule names
- `enabled_list_rules`: legacy alias still accepted for annotation rules
- `card_sections`: scan-based card definitions and display names

---

## 8. Market Dashboard

### Thresholds
- `bullish_threshold`: `80.0`
- `positive_threshold`: `60.0`
- `neutral_threshold`: `40.0`
- `negative_threshold`: `20.0`

### Component weights
- `pct_above_sma10`: `0.12`
- `pct_above_sma20`: `0.12`
- `pct_above_sma50`: `0.14`
- `pct_above_sma200`: `0.14`
- `pct_sma20_gt_sma50`: `0.10`
- `pct_sma50_gt_sma200`: `0.10`
- `pct_positive_1m`: `0.10`
- `pct_positive_ytd`: `0.08`
- `pct_2w_high`: `0.05`
- `vix_score`: `0.05`

### Universes
- `market_condition_etf_universe`: Core universe used for `Market Score` with 19 ETF items
- `leadership_etfs`: display-only leadership universe with 14 ETF items
- `external_etfs`: display-only external universe with 3 ETF items
- `factor_etfs`: `VUG`, `VTV`, `VYM`, `MGC`, `VO`, `VB`, `MTUM`
- `QQQ`, `QQQE`, `RSP`, `DIA`, `IWM`, and the sector ETFs retain direct contact with source fragments; the remaining market-universe additions are implementation-side design decisions

---

## 9. RS Radar

### Radar parameters
- `top_movers_count`: `3`
- `overall_rs_weights`: `[1.0, 2.0, 2.0]`
- `near_high_threshold_pct`: `0.5`

### Radar universes
- `sector_etfs`: configured sector ETF list
- `industry_etfs`: configured industry ETF list with `major_stocks`

---

## 10. Persisted research outputs

The current implementation persists these run-level artifacts when persistence is enabled:

- latest snapshot
- eligible snapshot
- watchlist table
- fetch status table
- run metadata
- weekly universe snapshots
