# Data Model and Sources

## 1. Active data-source architecture

### 1.1 Source split

| Source | Current role | Status |
| --- | --- | --- |
| finviz | Weekly universe discovery plus snapshot fields for name, sector, industry, market cap, EPS growth, revenue growth, and earnings date | Active default |
| yfinance | Daily OHLCV for stocks, benchmark, VIX, radar ETFs, and market ETFs | Active default |
| yfinance profile provider | Fallback profile source when a symbol is missing from the weekly snapshot | Active fallback |
| yfinance fundamental provider | Fallback fundamental source when a symbol is missing from the weekly snapshot | Active fallback |
| local cache | Persistence, TTL handling, stale fallback, and fetch-status lineage | Active |

### 1.2 Current design principles

- Use a weekly coarse universe snapshot instead of rebuilding the full universe every run.
- Use finviz as the default source for the weekly discovery snapshot.
- Use yfinance bulk downloads for price histories.
- Reuse cached price, profile, and fundamental data whenever possible.
- Preserve fetch status and data-quality visibility as first-class outputs.

### 1.3 Benchmark and market symbols

- Benchmark: `SPY`
- Volatility: `^VIX`
- Market Dashboard ETFs, RS Radar ETFs, and factor ETFs come from `config/default.yaml`.

---

## 2. Active universe flow

### 2.1 Symbol resolution order

`ResearchPlatform.run()` resolves the active symbol set in this order:

1. manual symbols passed from the app
2. fresh weekly universe snapshot
3. live universe discovery
4. stale weekly universe snapshot
5. `app.default_symbols`

### 2.2 Weekly universe discovery

Current implementation uses `FinvizScreenerProvider` with these coarse rules from `config/default.yaml`:

- allowed exchanges: `NASDAQ`, `NYSE`, `AMEX`
- excluded sectors: `Healthcare`
- minimum market cap: `1B`
- maximum snapshot size: `2500`

The finviz snapshot currently carries:

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
- `discovered_at`

### 2.3 Local screenable-universe filter

After price histories and indicators are available, `UniverseBuilder.filter()` applies the active local filter:

- `market_cap >= 1B`
- `avg_volume_50d >= 1M`
- `close >= min_price` where the current default is `0.0`
- `adr_percent >= 3.5`
- `adr_percent <= 10.0`
- `sector != Healthcare`

This filtered set is the actual input to the 9 scans.

---

## 3. Data loading flow

### 3.1 Prices

`YFinancePriceDataProvider` currently fetches:

- scan-universe stocks
- benchmark (`SPY`)
- VIX (`^VIX`)
- RS Radar ETFs
- Market Dashboard ETFs
- factor ETFs
- Market Snapshot symbols

Key active behavior:

- batch size: `80`
- max retries: `3`
- request sleep: `2.0s`
- retry backoff multiplier: `2.0`
- incremental refresh period: `5d`
- stale-cache fallback allowed

### 3.2 Profiles and fundamentals

Profile and fundamental loading is split into two stages:

1. Build profile/fundamental batches from the weekly universe snapshot.
2. For symbols still missing, fall back to the yfinance profile and fundamental providers.

This means the active implementation does not fetch per-symbol profile/fundamental payloads when the weekly snapshot already provides those fields.

---

## 4. Cache and lineage

### 4.1 Active cache layers

- price cache under `data_cache/`
- profile cache under `data_cache/`
- fundamental cache under `data_cache/`
- weekly universe snapshots under `data_runs/universe_snapshots/`
- run snapshots under `data_runs/`

### 4.2 Current TTLs

- technical cache: `12h`
- profile cache: `168h`
- fundamental cache: `24h`
- universe snapshot TTL: `7d`

### 4.3 Fetch-status states

The implementation tracks fetch status using these states:

- `live`
- `cache_fresh`
- `cache_stale`
- `sample`
- `missing`

The current default config has sample fallback disabled, so normal operation is expected to be `live`, `cache_fresh`, `cache_stale`, or `missing`.

---

## 5. Core data models in active use

### 5.1 SymbolDailyBar history

Price-history columns normalized by the active price provider:

- `open`
- `high`
- `low`
- `close`
- `adjusted_close`
- `volume`

### 5.2 Snapshot fields used by the screener

The active latest-row snapshot is built from indicator histories and then extended with:

- profile fields such as `name`, `market_cap`, `sector`, `industry`, `ipo_date`
- fundamental fields such as `eps_growth`, `revenue_growth`, `earnings_date`
- fetch-status source labels and timestamps
- data-quality fields
- indicator, scoring, and scan-context columns

### 5.3 Scan outputs

The active scan pipeline produces:

- `scan_hits` with `ticker`, `kind`, and `name`
- watchlist candidate rows with `hit_scans`, `hit_lists`, `scan_hit_count`, `list_overlap_count`, `overlap_count`, and `duplicate_ticker`
- scan-card view models for the UI
- duplicate-ticker rows for the watchlist priority band

---

## 6. Active provider modules

- `src/data/finviz_provider.py`
  - weekly universe discovery
  - snapshot-based profile/fundamental extraction
- `src/data/providers.py`
  - yfinance price, profile, and fundamental providers
  - optional Yahoo screener provider
- `src/data/universe.py`
  - local post-price universe filter
- `src/data/cache.py`
  - cache load/save and stale fallback
- `src/data/store.py`
  - weekly universe snapshots and per-run snapshot persistence

---

## 7. Notes on current limitations

The live code does not yet implement:

- FMP as an active provider
- a strict common-stock security-master model
- a Nasdaq-backed symbol-list provider

Those remain future enhancements, not part of the active default implementation.
