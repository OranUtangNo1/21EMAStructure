# Universe and Provider Decisions

## 1. Scope of this note

This note records the current decisions for:
- scan universe definition
- refresh cadence
- provider strategy
- yfinance-only feasibility

Date: 2026-03-27

---

## 2. Universe definition

### 2.1 Default exchanges
- NASDAQ
- NYSE

### 2.2 AMEX policy
- Exclude AMEX by default
- Keep it configurable for later re-enable

Rationale:
- most target growth names are on NASDAQ or NYSE
- AMEX increases noise for this workflow
- common-stock filtering is easier when the default universe is narrower

### 2.3 Allowed security type
- common stock only

### 2.4 Default exclusions
- ETF
- fund
- bond
- preferred
- warrant
- rights
- unit
- SPAC
- ADR
- ETN
- crypto-linked products

### 2.5 Scanable universe filters
- market cap > 1B
- avg volume 50d > 1M
- ADR percent 3.5 to 10.0
- exclude Healthcare

---

## 3. Refresh cadence

### 3.1 Security master
Contents:
- ticker list
- exchange
- security type
- instrument exclusion flags

Recommended cadence:
- monthly full refresh
- weekly delta refresh

### 3.2 Screenable universe snapshot
Contents:
- symbols that pass common-stock and broad universe filters

Recommended cadence:
- weekly rebuild

### 3.3 Daily scan inputs
Contents:
- OHLCV
- indicators
- scores
- 9 scans
- watchlist outputs

Recommended cadence:
- daily update

### 3.4 ETF data for dashboards
Contents:
- Market Dashboard ETFs
- RS Radar ETFs

Recommended cadence:
- daily update

---

## 4. Provider strategy

### 4.1 Phase A: yfinance first
Goal:
- make the screening workflow work at low cost

Approach:
1. use Yahoo screener as a coarse symbol discovery step
2. store a weekly universe snapshot
3. fetch daily OHLCV only for that stored snapshot
4. compute all 9-scan indicators locally

### 4.2 Phase B: FMP later
Goal:
- improve universe accuracy and stability

Approach:
1. use FMP as SymbolListProvider source of truth
2. stabilize common-stock filtering
3. keep yfinance as fallback or secondary source

---

## 5. Can yfinance-only work?

Yes, for Phase A.

It is good enough for:
- MVP
- research workflow
- small to medium weekly universe snapshots
- daily scan runs on an already filtered universe

It is not ideal for:
- a precise full US common-stock security master
- strict instrument-type classification
- fully reliable market-wide universe construction

### 5.1 Why it can work
- yfinance provides OHLCV history
- yfinance exposes Yahoo screener query tools
- the 9 scans still depend on local indicator calculation anyway

### 5.2 Main limitations
- Yahoo screener result limits require segmentation or paging
- common-stock-only classification is weaker than a dedicated symbol master source
- provider stability is lower than a dedicated low-cost market-data API

### 5.3 Practical recommendation
- start with yfinance-only
- use weekly universe snapshots, not daily full rebuilds
- migrate to FMP when the workflow is proven and the universe pipeline becomes the bottleneck

---

## 6. Immediate implementation tasks

1. Add a YahooScreenerProvider for coarse ticker discovery
2. Persist weekly universe snapshots
3. Run daily scans only against the latest approved snapshot
4. Keep AMEX disabled by default
5. Add config for exchange list, exclusion types, and refresh cadence
6. Add FMP-backed SymbolListProvider later without changing scan logic
