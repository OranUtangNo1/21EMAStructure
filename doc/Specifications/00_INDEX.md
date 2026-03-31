# Growth Trading Screener — Document Index

## Scope Definition

This system is a **screening and candidate extraction platform**.
Its responsibility ends at delivering three daily outputs:

1. Market environment assessment (Market Dashboard)
2. Sector and industry strength ranking (RS Radar)
3. Candidate stocks passing multiple quality scans (Today's Watchlist)

Entry evaluation, chart-based structure analysis, position sizing, and trade management
are performed outside this system (primarily in TradingView using 21EMA Cockpit, Structure Pivot, VCS, and Position Size Calculator).

Information related to entry, structure, risk, and exit has been preserved in the `archived/` directory
for future use when building a separate entry decision system.

---

## Active Documents (Screening System)

1. `01_SYSTEM_OVERVIEW.md`
   - purpose and scope
   - fixed structure vs configurable logic
   - three-layer architecture
   - research-platform positioning

2. `02_DATA_MODEL_AND_SOURCES.md`
   - data models
   - provider abstraction
   - cache strategy
   - storage formats and flow

3. `03_INDICATORS_AND_SCORING.md`
   - 21EMA family
   - RS
   - Fundamental Score
   - Industry Score
   - Hybrid Score
   - VCS
   - supporting indicators

4. `04_SCAN_AND_WATCHLIST_SPEC.md`
   - 9 scans
   - 7 lists
   - duplicate tickers
   - watchlist output model

5. `05_DASHBOARD_UI_SPEC.md`
   - Market Dashboard
   - RS Radar
   - Today's Watchlist (scan-based card grid)
   - Earnings for today

6. `06_MODULE_AND_INTERFACE_SPEC.md`
   - module responsibilities (screening scope only)
   - Config / Calculator / Result split
   - interface definitions

7. `07_IMPLEMENTATION_PLAN.md`
   - implementation phases (screening scope)
   - priorities
   - MVP scope

8. `08_PARAMETER_CATALOG.md`
   - parameter catalog
   - thresholds
   - weights and modes

9. `09_CURRENT_STATUS_AND_ROADMAP.md`
   - current status snapshot
   - scope clarification
   - next-step roadmap

10. `10_TRADING_METHOD_PLAYBOOK.md`
    - human-readable method guide
    - screening flow
    - indicator explanations
    - scope boundary with entry/exit

11. `11_IMPLEMENTATION_GAP_ANALYSIS.md`
    - docs vs code comparison
    - active-scope gaps
    - priority work order

---

## Archived Documents (Future Entry Decision System)

These documents preserve research and design work for entry evaluation,
structure analysis, risk management, and trade execution.
They are not part of the current screening system scope.

- `archived/ENTRY_EXIT_AND_RISK_SPEC.md`
  - entry hypothesis, sell rules, phase logic, position sizing
- `archived/ENTRY_STRUCTURE_NOTES.md`
  - Structure Pivot, 21EMA Cockpit entry process, open-gap filters

---

## Suggested Reading Order

1. `01_SYSTEM_OVERVIEW.md` — what this system does and does not do
2. `03_INDICATORS_AND_SCORING.md` — metrics used for scanning and ranking
3. `04_SCAN_AND_WATCHLIST_SPEC.md` — how candidates are extracted
4. `05_DASHBOARD_UI_SPEC.md` — the three output screens
5. `09_CURRENT_STATUS_AND_ROADMAP.md` — where we are now
6. `10_TRADING_METHOD_PLAYBOOK.md` — how screening fits into the full trading method

## Agent Operations

- `AGENTS.md`
  - always-on repository guidance for scope, code map, and default commands
- `.agents/skills/oratek-doc-syncing/SKILL.md`
  - task-specific guidance for syncing numbered docs after code or config changes

## Code Entry Points

1. `src/pipeline.py`
2. `src/data/providers.py`
3. `src/indicators/core.py`
4. `src/scoring/*`
5. `src/scan/*`
6. `app/main.py`
- [12_UNIVERSE_PROVIDER_DECISIONS.md](12_UNIVERSE_PROVIDER_DECISIONS.md) - current decisions for universe definition, refresh cadence, and yfinance-first provider strategy
