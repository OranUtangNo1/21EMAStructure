# Universe and Provider Decisions

## 1. Scope of this note

This note records the active decisions for:
- scan universe definition
- refresh cadence
- provider strategy
- low-cost operation with finviz + yfinance

Date: 2026-03-30

---

## 2. Universe definition

### 2.1 Default exchanges
- NASDAQ
- NYSE
- AMEX

### 2.2 Allowed security type
- common stock only where practical
- use the finviz stock screener as the coarse starting point

### 2.3 Default exclusions
- exclude Healthcare as a shared universe rule
- defer strict instrument-type cleanup to configurable filters and local validation when needed

### 2.4 Scanable universe filters
Stage 1 coarse snapshot:
- market cap > 1B
- exclude Healthcare

Stage 2 local daily filter after prices are loaded:
- avg volume 50d > 1M
- ADR percent 3.5 to 10.0

### 2.5 Price floor policy
- no explicit minimum price filter by default
- market cap > 1B is treated as the primary coarse quality floor

---

## 3. Refresh cadence

### 3.1 Weekly universe snapshot
Contents:
- symbols that pass coarse finviz filters
- sector and industry attributes
- market cap
- EPS growth, revenue growth, earnings date

Recommended cadence:
- weekly rebuild
- reuse the latest snapshot during daily runs until TTL expiry

### 3.2 Daily scan inputs
Contents:
- OHLCV
- indicators
- scores
- 9 scans
- watchlist outputs

Recommended cadence:
- daily update
- fetch recent price deltas and merge them into local cache

### 3.3 ETF data for dashboards
Contents:
- Market Dashboard ETFs
- RS Radar ETFs
- benchmark and snapshot symbols

Recommended cadence:
- daily update through the same batched price provider

---

## 4. Provider strategy

### 4.1 Active provider split
Use this split as the default architecture:
1. finviz screener for weekly universe discovery
2. finviz snapshot as the primary source for profile and fundamental fields
3. yfinance bulk download for OHLCV only
4. local cache as the persistence and stale-fallback layer

### 4.2 Why finviz is the primary universe source
- it returns the coarse stock list and key attributes in one pass
- it provides the required EPS growth, sales growth, and earnings date fields
- it avoids per-symbol profile and fundamental scraping during normal runs
- it keeps the stack free of paid dependencies such as FMP

### 4.3 Why yfinance remains in the stack
- it is sufficient for daily OHLCV updates
- it can serve prices for both stock universe members and ETF dashboards
- it works well when requests are batched instead of sent one symbol at a time

### 4.4 Batch price requirements
- batch size: 80 symbols per request
- retry: up to 3 attempts with backoff
- merge successful downloads into local per-symbol cache
- allow stale-cache fallback when live fetch fails

---

## 5. Practical recommendation

The active low-cost architecture is:
- weekly finviz snapshot for universe, attributes, and fundamentals
- daily yfinance bulk price update for stocks and ETFs
- local filtering for avg volume and ADR after price histories are available

This is the default operating mode for the current screening platform.

---

## 6. Immediate implementation tasks

1. Keep `FinvizScreenerProvider` as the default universe discovery provider.
2. Keep weekly universe snapshots persisted and reused within TTL.
3. Keep `YFinancePriceDataProvider` batched and cache-aware.
4. Preserve stale-cache fallback and fetch-status visibility in the pipeline.
5. Keep universe thresholds configurable through `config/default.yaml`.
6. Treat paid or secondary providers as optional future work, not part of the active default stack.