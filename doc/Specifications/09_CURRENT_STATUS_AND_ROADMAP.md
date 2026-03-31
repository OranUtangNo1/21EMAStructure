# Current Status and Roadmap

## 1. Purpose of This Document

This document is a status review of the project as of March 27, 2026.
It reflects the scope clarification that the system is a **screening and candidate extraction platform**,
not an entry evaluation or trade management system.

---

## 2. Scope Clarification

### What this system does

The system delivers three daily outputs:

1. **Market Dashboard** — market environment assessment
2. **RS Radar** — sector and industry strength ranking
3. **Today's Watchlist** — candidate stocks from 9 scans, displayed as a card grid sorted by Hybrid-RS

### What this system does not do

The following are performed outside the system, primarily in TradingView:

- Entry evaluation (21EMA Cockpit)
- Chart structure analysis (Structure Pivot, 21EMA Cloud visual)
- Position sizing (Position Size Calculator)
- Trade management (phase exits, trim, trail)
- Portfolio-level risk

### Archived modules

Code and design for entry, structure, risk, and exit modules have been isolated to `archived/`.
They are preserved as assets for a future entry decision system.

---

## 3. Current Progress

### Data foundation

Status: implemented

- price / profile / fundamental loading (yfinance primary)
- cache management with TTL
- data lineage and fetch status tracking (live / cache_fresh / cache_stale / sample / missing)
- data quality scoring
- run snapshot persistence under `data_runs/`

### Indicators

Status: implemented

- 21EMA High / Low / Cloud
- SMA50 / SMA200
- ATR / ADR / DCR / Relative Volume
- RS5 / RS21 / RS63 / RS126
- PP Count 30d
- 3WT
- ATR zone metrics (21EMA / 10WMA / 50SMA)
- ATR% from 50SMA
- ema21_low_pct

### Scoring

Status: initial version implemented

- Fundamental Score (placeholder research formula)
- Industry Score (placeholder research formula)
- Hybrid Score (RS 5 : F 2 : I 3 weighting)
- VCS (initial version)

### Scans

Status: implemented

- 9 scan rules implemented
- 7 lists implemented
- duplicate ticker aggregation

### Today's Watchlist

Status: needs UI revision

- Watchlist data pipeline is working
- UI currently shows a detailed table format
- **Needs revision to scan-based card grid format** matching actual usage

### Market Dashboard

Status: initial version present

- Market condition score and label
- Breadth summary
- VIX display
- **Needs revision to match actual UI** (43 ETF scoring, Market Snapshot, S5TH chart, Factors vs SP500)

### RS Radar

Status: initial version present

- Sector/industry grouping exists
- **Needs revision to match actual UI** (4-axis RS, RS change rates, MAJOR STOCKS, Top 3 RS% Change)

### Archived (scope-external) modules

Status: code exists, isolated from active scope

- StructurePivotDetector (initial version)
- EntryEvaluator (initial hypothesis)
- PositionSizingCalculator
- ExitRuleEvaluator (phase model)
- CockpitPanelBuilder
- DarvasRetestFilter (stub)
- TrendRegimeFilter (stub)

---

## 4. Current Gaps (Within Scope)

### Data

- Provider coverage depends heavily on yfinance
- FMP integration as secondary provider not yet active
- Fundamental coverage varies by symbol
- 43 ETF list for Market Conditions not defined

### Scan quality

- Scan thresholds still need research validation
- Some scan conditions may need refinement against real market data

### UI

- Today's Watchlist needs conversion from table to card grid
- Market Dashboard needs significant expansion (Market Snapshot, S5TH, Factors)
- RS Radar needs expansion (4-axis RS, RS change rates, MAJOR STOCKS)
- Earnings for today section not implemented

### Research workflow

- No run-to-run comparison UI
- No daily watchlist history
- No scan-hit history tracking

---

## 5. Roadmap

### Near-term priorities

#### A. Revise Today's Watchlist UI

Priority: high

Planned work:
- Convert from detailed table to scan-based card grid
- Each scan as an independent card showing ticker count + ticker grid
- Sort within each card by Hybrid-RS
- Add Earnings for today section

#### B. Expand Market Dashboard

Priority: high

Planned work:
- Implement 43 ETF-based Market Conditions scoring
- Add Market Snapshot (RSP, QQQE, IWM, DIA, VIX, BTC + 21EMA position labels)
- Add S5TH time-series chart
- Add Factors vs SP500 display
- Add time-axis scores (1D/1W/1M/3M ago)

#### C. Expand RS Radar

Priority: high

Planned work:
- Add 4-axis RS (overall, 1D, 1W, 1M)
- Add RS change rate columns (RS DAY%, RS WK%, RS MTH%)
- Add MAJOR STOCKS to Industry Leaders
- Add Top 3 RS% Change (Daily / Weekly)

#### D. Strengthen provider chain

Priority: medium

Planned work:
- Add FMP as optional provider
- Improve profile/fundamental coverage
- Define 43 ETF universe for Market Conditions

#### E. Add run comparison

Priority: medium

Planned work:
- Compare saved runs under `data_runs/`
- Show watchlist deltas by day
- Track data-quality changes over time

### Mid-term themes

- Richer Market Dashboard analytics
- Stronger Industry RS model
- Fundamental Score research refinement
- Daily workflow automation

### Decision principles

1. Focus on the three output screens first
2. Match UI to actual usage patterns
3. Improve trust in real data
4. Keep scoring logic configurable for research
5. Preserve entry/structure/risk research for future use

---

## 6. Summary

The project has a working data foundation, indicator pipeline, scoring engine, and scan execution layer.

The most important near-term work is not adding new features but **aligning the UI with actual usage**:
- Today's Watchlist as a scan-based card grid
- Market Dashboard with full breadth, Market Snapshot, S5TH chart, and Factors
- RS Radar with full detail (4-axis RS, RS change rates, MAJOR STOCKS)

Entry/structure/risk modules are preserved but isolated from the active screening scope.
