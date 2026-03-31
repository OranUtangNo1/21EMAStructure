# [ARCHIVED] Entry Structure and Cockpit Notes

## Archive Notice

This document preserves design notes for Structure Pivot detection,
21EMA Cockpit entry process, and related TradingView-based evaluation flows.
These are outside the current screening system scope.

---

## 1. Structure Pivot Detection

### Bullish structure
1. LL (Lowest Low)
2. HL (Higher Low)
3. Pivot Line = highest High between LL and HL

### Multiple length scanning
Scans across all specified lengths simultaneously.
Priority modes: tightest, longest, shortest.

### Implementation notes (from existing code)
- StructurePivotConfig: length ranges, priority mode
- StructurePivotDetector: LL-HL detection, pivot selection
- StructurePivotResult: pivot price, structure type, breakout trigger

---

## 2. 21EMA Cockpit Entry Process

The Cockpit is a TradingView indicator with three components:

1. **Core Stats** — entry timing (ADR%, ATR zones, ema21_low_pct, 3WT, IPO timer)
2. **21EMA Cloud** — trend confirmation (EMA21 High / Low band on main chart)
3. **Growth Table** — fundamentals (EPS growth, revenue growth)

### Cockpit v2 layout
- Cockpit panel on the right side
- 21EMA Cloud on the main chart
- Not a single-page dashboard; a chart-assist panel

---

## 3. TradingView Tools Referenced

- 21EMA Cockpit v2 (unified version)
- 21EMA Cloud (standalone cloud indicator)
- 21EMA Scan for Pine Screener
- Structure Pivot (LL-HL / HH-LH)
- Volatility Contraction Score (VCS)
- Darvas Lines/Box
- 5ma + O'Neil & Minervini Buy Condition
- Position Size Calculator
- Relative Strength Table

---

## 4. Module References (from existing codebase)

These modules exist in the codebase but are outside the screening system scope:

- `archived/src/structure/pivot.py` — StructurePivotDetector
- `archived/src/entry/evaluator.py` — EntryEvaluator
- `archived/src/risk/position_sizing.py` — PositionSizingCalculator
- `archived/src/risk/exits.py` — ExitRuleEvaluator
- `archived/src/dashboard/cockpit.py` — CockpitPanelBuilder

---

## 5. Future Entry Decision System

When building a separate entry decision system, these modules could serve as the starting point.
The entry system would:

1. Take screening output (Today's Watchlist candidates) as input
2. Apply Structure Pivot analysis
3. Evaluate against my_entry_criteria hypothesis
4. Calculate position sizing
5. Provide structured entry/exit recommendations

This would bridge the gap between automated screening and the currently manual TradingView evaluation.
