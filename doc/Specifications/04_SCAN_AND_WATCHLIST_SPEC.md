# Scan and Watchlist Spec

## 1. Active pre-scan universe filter

Before any scan rule runs, `UniverseBuilder.filter()` applies the active local universe filter:

- `market_cap >= 1B`
- `avg_volume_50d >= 1M`
- `close >= min_price` where the current default is `0.0`
- `adr_percent` between `3.5` and `10.0`
- sector exclusion: `Healthcare`

The scan rules themselves run only on this eligible snapshot.

---

## 2. Active 9 scan rules

### 2.1 21EMA scan

`True` when all conditions are met:

- `weekly_return >= 0.0`
- `weekly_return <= 15.0`
- `dcr_percent > 20.0`
- `-0.5 <= atr_21ema_zone <= 1.0`
- `0.0 <= atr_50sma_zone <= 3.0`
- `pp_count_30d > 1`
- `trend_base == True`

### 2.2 4% bullish

`True` when all conditions are met:

- `rel_volume >= 1.0`
- `daily_change_pct >= 4.0`
- `from_open_pct > 0.0`
- `raw_rs21 > 60.0`

### 2.3 Vol Up

`True` when all conditions are met:

- `rel_volume >= 1.5`
- `daily_change_pct > 0.0`

### 2.4 Momentum 97

`True` when all conditions are met:

- `weekly_return_rank >= 97.0`
- `quarterly_return_rank >= 85.0`
- `trend_base == True`

`weekly_return_rank` and `quarterly_return_rank` are cross-sectional percentile ranks created by `enrich_with_scan_context()`.

### 2.5 97 Club

`True` when all conditions are met:

- `hybrid_score >= 90.0`
- `raw_rs21 >= 97.0`
- `trend_base == True`

### 2.6 VCS

`True` when all conditions are met:

- `vcs >= 60.0`
- `raw_rs21 > 60.0`

### 2.7 Pocket Pivot

`True` when all conditions are met:

- `close > sma50`
- `pocket_pivot == True`

`pocket_pivot` itself is calculated in the indicator layer as:

- green candle: `close > open`
- current `volume > max(volume over prior pocket_pivot_lookback days)`

### 2.8 PP Count

`True` when all conditions are met:

- `pp_count_30d > 3`
- `trend_base == True`

### 2.9 Weekly 20% plus gainers

`True` when:

- `weekly_return >= 20.0`

---

## 3. Active 7 list annotations

The 7 lists are evaluated on the same eligible snapshot, but they do not decide watchlist eligibility.
They are stored as supporting annotations through `hit_lists` and `list_overlap_count`.

### 3.1 List rules currently evaluated

1. `Momentum 97`
   - `weekly_return_rank >= 97.0`
   - `quarterly_return_rank >= 85.0`

2. `Volatility Contraction Score`
   - `vcs >= 60.0`

3. `21EMA Watch`
   - `close >= ema21_low`
   - `ema21_low_pct <= 8.0`
   - `-0.5 <= atr_21ema_zone <= 1.0`

4. `4% Gainers`
   - `daily_change_pct >= 4.0`

5. `Relative Strength 21 > 63`
   - `rsi21 > rsi63`

6. `Vol Up Gainers`
   - `rel_volume >= 1.5`
   - `daily_change_pct > 0.0`

7. `High Est. EPS Growth`
   - `eps_growth_rank >= 90.0`

### 3.2 Important distinction

- 9 scans drive watchlist eligibility.
- 7 lists do not create watchlist candidates by themselves.
- list-only symbols are excluded from the final watchlist.

---

## 4. Duplicate tickers

### 4.1 Current definition

A duplicate ticker is any ticker that appears in `3` or more of the 9 scan rules.

In the active implementation:

- `scan_hit_count = number of unique scan hits for the ticker`
- `overlap_count = scan_hit_count`
- `duplicate_ticker = scan_hit_count >= duplicate_min_count`
- current `duplicate_min_count = 3`

### 4.2 What is not used

Duplicate tickers are not derived from:

- the 7 list annotations
- `list_overlap_count`
- transformed card output rows

The UI priority band is built directly from raw scan hits plus the raw watchlist rows.

---

## 5. Watchlist generation flow

1. Resolve the active symbols.
2. Load prices, profile data, and fundamentals.
3. Build indicator histories.
4. Build the latest snapshot.
5. Apply scoring: RS, Fundamental, Industry, Hybrid, VCS.
6. Apply the local universe filter.
7. Evaluate the 9 scans and 7 list annotations.
8. Keep only symbols with `scan_hit_count > 0`.
9. Mark duplicate tickers from scan overlap.
10. Sort the watchlist.
11. Build scan cards, duplicate band rows, and earnings rows for the UI.

---

## 6. Sorting

### 6.1 Active watchlist sort

Default config uses `watchlist_sort_mode: hybrid_score`.

This produces the active sort priority:

1. `hybrid_score`
2. `overlap_count`
3. `vcs`
4. `rs21`

### 6.2 Optional sort mode

If `watchlist_sort_mode` is changed to `overlap_then_hybrid`, the runner sorts by:

1. `overlap_count`
2. `hybrid_score`
3. `vcs`
4. `rs21`

### 6.3 Card-level sort

Each scan card uses `card_sections[*].sort_columns`.
The current default is:

1. `hybrid_score`
2. `overlap_count`
3. `vcs`

---

## 7. Active watchlist outputs

The display-oriented watchlist table currently exposes these fields when available:

- `name`
- `sector`
- `industry`
- `H`, `F`, `I`, `21`, `63`, `126`
- `rs5`
- `overlap_count`
- `scan_hit_count`
- `list_overlap_count`
- `duplicate_ticker`
- `hit_scans`
- `hit_lists`
- `vcs`
- `earnings`
- `pp_count_30d`
- `ema21_low_pct`
- `atr_21ema_zone`
- `atr_50sma_zone`
- `three_weeks_tight`
- `atr_pct_from_50sma`
- `price_data_source`
- `fundamental_data_source`
- `data_quality_label`
- `data_quality_score`
- `data_warning`

---

## 8. Configurable areas

The active implementation keeps these areas configurable:

- scan thresholds
- enabled scan rules
- enabled list rules
- card sections and their display names
- duplicate minimum count
- watchlist sort mode
- universe thresholds
