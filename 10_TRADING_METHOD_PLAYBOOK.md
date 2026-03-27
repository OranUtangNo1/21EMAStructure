# Trading Method Playbook

## 1. Why This Document Exists

This document is a human-readable guide to the trading method and how it relates to this system.
It clarifies which parts of the method are covered by this screening system
and which parts are handled externally in TradingView.

Status reflects the codebase as of March 27, 2026.

---

## 2. Method at a Glance

The full trading method is a layered workflow.
This system covers the first three steps; the remaining steps happen in TradingView.

### Steps covered by this system

1. **Assess market environment** (Market Dashboard)
   - Check Market Conditions score and label
   - Review breadth, performance, VIX, and factor relative strength
   - Check index ETFs against 21EMA position

2. **Identify strong sectors and industries** (RS Radar)
   - Review Sector Leaders and Industry Leaders tables
   - Note which groups have rising RS across daily, weekly, and monthly timeframes
   - Identify major stocks within leading industries

3. **Extract candidate stocks** (Today's Watchlist)
   - Run 9 scans to find stocks meeting various quality criteria
   - Note stocks appearing across multiple scans (duplicate tickers)
   - Review Earnings for today to flag near-term risk

### Steps handled in TradingView (outside this system)

4. **Review chart structure**
   - Use 21EMA Cloud to judge whether the stock is acting well
   - Use Structure Pivot to identify breakout trigger levels
   - Use VCS to confirm compression maturity

5. **Evaluate entry quality**
   - Use 21EMA Cockpit Core Stats (ADR%, ATR zones, ema21_low_pct)
   - Check RS, growth, and industry context in the Cockpit panel
   - Confirm volume

6. **Size the position**
   - Use Position Size Calculator
   - Based on entry price, stop (21EMA Low), and risk percentage

7. **Manage the trade**
   - Phase 1: Before 1R, exit on close below 21EMA Low
   - Phase 2: After 1R, exit on close below entry
   - Trim 33% at 3R
   - Final: After 3R, exit remainder on close below 21EMA Low

---

## 3. Screening Flow (This System)

### 3.1 What screening is trying to do

The screening layer answers a practical question:
which stocks are strong enough, active enough, and orderly enough to deserve detailed review today.

Screening is a first-pass filter, not a buy signal.

### 3.2 Current screening flow

| Step | What the system does | Current status |
| --- | --- | --- |
| Universe filter | Apply minimum market cap, average volume, minimum price, ADR range, and sector exclusions | Implemented |
| Trend-base check | Use conditions such as price above 50SMA and 10WMA above 30WMA | Implemented |
| 9 scans | Run scan rules (21EMA, 4% bullish, Vol Up, Momentum 97, 97 Club, VCS, Pocket Pivot, PP Count, Weekly 20%+) | Implemented |
| 7 lists | Build operational lists (Momentum 97, VCS, 21EMA Watch, 4% Gainers, RS21>RS63, Vol Up Gainers, High Est. EPS Growth) | Implemented |
| Duplicate tickers | Count stocks appearing 3+ times across the 7 lists | Implemented |
| Hybrid ranking | Sort candidates within each scan by Hybrid Score | Initial hypothesis implemented |
| Earnings flag | Flag stocks with earnings within 7 days | Implemented |
| Market condition overlay | Provide market-level context before review | Initial hypothesis implemented |

### 3.3 How to interpret screening output

A stock passing multiple scans does not mean "buy now."
It means:
- the name is worth reviewing in TradingView
- the stock has enough strength or compression to enter the detailed review queue
- the next step moves to TradingView for chart, cockpit, and structure evaluation

---

## 4. Indicator Guide

| Indicator | What it measures | Why it is useful in screening | Status |
| --- | --- | --- | --- |
| EMA21 Low | Practical support line | Anchors the 21EMA scan zone condition | Implemented |
| EMA21 High | Upper edge of support band | Defines cloud boundary for trend assessment | Implemented |
| 21EMA Cloud | Short-term support zone | Helps identify stocks in healthy pullback zones | Implemented |
| SMA50 | Intermediate trend | Used in Trend Base condition (price > 50SMA) | Implemented |
| SMA200 | Long-term trend | Used for breadth metrics | Implemented |
| ATR | Daily movement scale | Makes distance metrics comparable across stocks | Implemented |
| ADR% | Movement quality | Filters out stocks that are too quiet or too volatile | Implemented |
| DCR% | Close strength | Filters for stocks closing strong within their range | Implemented |
| Relative Volume | Participation level | Identifies unusual volume activity | Implemented |
| RS5/21/63/126 | Relative strength vs SPY | Core ranking input for Hybrid Score | Implemented |
| Fundamental Score | Growth quality | Adds growth context to pure price strength | Initial hypothesis |
| Industry Score | Group strength | Prioritizes stocks in strong industry groups | Initial hypothesis |
| Hybrid Score | Combined ranking quality | Primary sort key for scan results | Initial hypothesis |
| VCS | Compression maturity | Identifies tight setups ready for expansion | Initial hypothesis |
| 3WT | Weekly tightness | Spotting orderly setups | Implemented |
| PP Count 30d | Accumulation evidence | Counts institutional-style volume events | Implemented |
| ATR% from 50SMA | Extension level | Helps avoid late-stage extended stocks | Implemented |
| ema21_low_pct | Risk distance | Used in 21EMA scan zone condition | Implemented |

---

## 5. Scope Boundary

### What this system is good at

- Data loading and indicator calculation
- Running 9 scans with configurable thresholds
- Building the daily watchlist with Hybrid-RS ranking
- Identifying duplicate tickers across 7 lists
- Providing market environment context
- Showing sector and industry leadership

### What this system does not do

- Final entry decisions (handled by 21EMA Cockpit in TradingView)
- Chart structure evaluation (handled by Structure Pivot indicator)
- Position sizing (handled by Position Size Calculator)
- Trade management (handled by manual tracking + sell rules)

This separation is intentional. The system focuses on what can be automated (scanning and ranking),
while judgment-heavy decisions remain with the trader using visual tools.

---

## 6. Archived Research

Design and research for the following areas are preserved in `archived/` for future use:

- Entry hypothesis (my_entry_criteria)
- Structure Pivot detection logic
- Phase-based exit rules
- Position sizing formulas
- 21EMA Cockpit panel design
- Darvas Retest Filter concept
- O'Neil / Minervini Trend Regime Filter concept

These may form the basis of a future "entry decision system" that takes screening output
as input and provides structured entry/exit recommendations.
