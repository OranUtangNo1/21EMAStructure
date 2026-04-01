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

The application prepares a weekly universe snapshot and then applies daily calculations on top of that universe.

Current flow:

1. discover the weekly universe with Finviz
2. store the universe snapshot locally
3. load daily price history from Yahoo Finance
4. apply the local eligible-universe filter
5. calculate indicators and scores
6. run the enabled scan rules
7. create the watchlist as the union of scan hits
8. mark duplicate tickers when a ticker appears in `duplicate_min_count` or more enabled scans

### 2.2 Market Review

Before looking at individual names, the user reviews the Market Dashboard.

This is intended to answer:

- is the market supportive or hostile?
- how broad is trend participation?
- how strong are factor groups versus SPY?
- where is VIX relative to the rest of the market state?

### 2.3 RS Review

The user then reviews the RS Radar tab.

This is intended to answer:

- which sectors are leading?
- which industry ETFs are leading?
- which groups are accelerating daily or weekly?
- which industry groups are near highs?

### 2.4 Candidate Extraction

The user then reviews Today's Watchlist.

This is intended to answer:

- which names pass one or more active scan rules?
- which names appear repeatedly across scan conditions?
- which names also carry useful research annotations such as EPS strength or RSI alignment?

## 3. Active Scan Workflow

### 3.1 Stable scan workflow and current scan family

The watchlist workflow is stable even if the scan family changes over time.

Stable rule:

- a ticker becomes a watchlist candidate if it passes at least one enabled scan
- annotation rules do not create watchlist candidates by themselves

The exact active scan family is documented under `doc/Scan/scan_00_index.md`.

### 3.2 Duplicate Tickers

Duplicate Tickers are not derived from annotation rules.

Current implemented rule:

- count how many enabled scans include the ticker
- if the ticker appears in `duplicate_min_count` or more enabled scans, mark it as a duplicate ticker

This is the overlap rule used in the application.

### 3.3 Annotation Rules

The system also computes annotation-style lists for additional context.

The current annotation family is documented in `doc/Scan/scan_00_index.md`.

These rules do not determine watchlist eligibility. They act as secondary tags on already scanned names.

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

### 4.3 Relative Strength And RSI

Implemented indicators:

- raw RS: `raw_rs5`, `raw_rs21`, `raw_rs63`, `raw_rs126`
- normalized RS: `rs5`, `rs21`, `rs63`, `rs126`
- RSI: `rsi21`, `rsi63`

Use in workflow:

- raw RS is used by the scan layer to compare stock performance versus SPY across horizons
- the default RS score is the trailing-window percentrank of each symbol's own `close / SPY` ratio history
- normalized RS is used in ranking and dashboard summaries
- RSI is used as a separate momentum-style oscillator and is not the same thing as the SPY-relative RS calculation

### 4.4 Fundamental, Industry, Hybrid, And VCS

Implemented scores:

- `fundamental_score`
- `industry_score`
- `hybrid_score`
- `vcs`

Use in workflow:

- fundamental score summarizes earnings and revenue growth inputs
- industry score reflects the relative strength of grouped peers
- hybrid score combines RS, fundamental, and industry components
- VCS estimates contraction quality and maturity using the published Pine workflow: true-range contraction, close stdev contraction, short-vs-long volume contraction, efficiency-based trend penalty, structural higher-low validation, EMA smoothing, and a consistency bonus

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
