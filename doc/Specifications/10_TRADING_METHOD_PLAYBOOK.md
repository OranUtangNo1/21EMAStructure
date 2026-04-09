# 10. Trading Method Playbook

## 1. Purpose

This document explains the current workflow supported by the active OraTek application. It is written from the implementation as it exists today.

The active product is a screening and candidate extraction platform. It supports:

1. market environment review
2. sector and industry RS review
3. watchlist candidate extraction

The product does not perform final chart-based trade execution decisions.

## 2. End-To-End Workflow

### 2.1 Universe Preparation

The application prepares a reusable weekly universe snapshot and then applies daily calculations on top of that universe.

Current flow:

1. reuse a fresh weekly universe snapshot when available
2. otherwise discover a new weekly universe live
3. load daily price history from Yahoo Finance
4. source profile and fundamental data from the snapshot first, then fill missing rows from Yahoo fallback providers
5. apply the local eligible-universe filter
6. calculate indicators and scores
7. run the enabled scan rules
8. create the raw watchlist as the union of scan hits
9. mark duplicate tickers when a ticker appears in `duplicate_min_count` or more scan hits

### 2.2 Market Review

Before looking at individual names, the user reviews the Market Dashboard.

This is intended to answer:

- is the market supportive or hostile?
- how broad is trend participation?
- how are factors behaving versus SPY?
- how is VIX interacting with the rest of the market state?

In the current implementation, the dashboard can score from ETF breadth, active-symbol breadth, or a blend of the two, depending on `market.calculation_mode`.

### 2.3 RS Review

The user then reviews the RS Radar tab.

This is intended to answer:

- which sectors are leading?
- which industry ETFs are leading?
- which groups are accelerating daily or weekly?
- which groups are near highs?

### 2.4 Candidate Extraction

The user then reviews Today's Watchlist.

This is intended to answer:

- which names pass one or more active scan rules?
- which names survive the currently selected post-scan filters?
- which names appear repeatedly across the currently selected scan cards?
- which names have same-day earnings inside the current eligible universe?

## 3. Active Scan Workflow

### 3.1 Stable scan workflow and current scan family

The watchlist workflow is stable even if the scan family changes over time.

Stable rule:

- a ticker becomes a raw watchlist candidate if it passes at least one enabled scan
- annotation filters do not create watchlist candidates by themselves

The exact active scan family is documented under `doc/Scan/scan_00_index.md`.
The default config currently enables 15 scan families.

### 3.2 Duplicate Tickers

Duplicate tickers are not derived from annotation filters.

Backend rule:

- count how many scan hits include the ticker
- if the ticker appears in `duplicate_min_count` or more scan hits, mark it as a duplicate ticker

UI rule:

- recompute duplicate counting from the currently selected scan cards
- apply the current duplicate threshold
- optionally apply duplicate-only subfilters such as `Top3 HybridRS`

### 3.3 Annotation Filters

The system also computes annotation-style filters for additional context.

Available default definitions:

- `RS 21 >= 63`
- `High Est. EPS Growth`

These rules do not determine raw watchlist eligibility. They narrow the displayed watchlist only when the user selects them in the sidebar.

## 4. Indicator Guide

### 4.1 21EMA Structure Indicators

Implemented indicators:

- `ema21_high`
- `ema21_low`
- `ema21_close`
- `ema21_low_pct`

Use in workflow:

- identifies whether price is operating near the 21EMA structure
- supports pullback-style screening
- helps discriminate between orderly movement and extended movement

### 4.2 ATR, ADR, And DCR

Implemented indicators:

- `atr`
- `adr_percent`
- `dcr_percent`
- `atr_21ema_zone`
- `atr_50sma_zone`
- `atr_pct_from_50sma`

Use in workflow:

- estimates volatility regime
- separates orderly movers from unstable movers
- highlights overheated names relative to moving-average context

### 4.3 52-Week And Accumulation Indicators

Implemented indicators:

- `high_52w`
- `low_52w`
- `dist_from_52w_high`
- `dist_from_52w_low`
- `rel_volume`
- `ud_volume_ratio`

Use in workflow:

- `dist_from_52w_high` supports continuation-style scans near yearly highs
- `dist_from_52w_low` supports VCS-style contraction setups close to yearly lows
- `ud_volume_ratio` separates sustained accumulation from one-day volume spikes

### 4.4 Relative Strength And RSI

Implemented indicators:

- raw RS: `raw_rs5`, `raw_rs21`, `raw_rs63`, `raw_rs126`
- normalized RS: `rs5`, `rs21`, `rs63`, `rs126`
- RSI: `rsi21`, `rsi63`

Use in workflow:

- raw RS is used by the scan layer to compare stock performance versus SPY across horizons
- the default RS score is the trailing-window percent-rank of each symbol's own `close / SPY` ratio history
- normalized RS currently matches raw RS in the implementation
- RSI is a separate momentum oscillator and is not the same thing as SPY-relative RS

### 4.5 Fundamental, Industry, Hybrid, And VCS

Implemented scores:

- `fundamental_score`
- `industry_score`
- `hybrid_score`
- `vcs`

Use in workflow:

- fundamental score summarizes earnings and revenue growth inputs
- industry score reflects relative strength of grouped peers
- hybrid score combines RS, fundamental, and industry components
- VCS estimates contraction quality and maturity using the published Pine-style workflow

## 5. What The User Should Treat As Research Output

The following outputs are useful, but still research-oriented:

- hybrid ranking
- industry ranking
- VCS values
- market condition composite score
- annotation flags based on internal heuristics

The current implementation exposes them as configurable calculations, not immutable truth.

## 6. What Happens Outside The App

The application stops at candidate extraction.

The following remain outside the active product workflow:

- discretionary chart review
- external charting tools
- final entry confirmation
- position sizing
- stop management
- trade exits

Those topics are not part of the active screening workflow and are not product behavior.
