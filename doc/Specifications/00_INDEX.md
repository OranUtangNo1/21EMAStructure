# Growth Trading Screener - Document Index

## Scope Definition

This system is a screening and candidate extraction platform.
Its active responsibility ends at three outputs:

1. Market Dashboard
2. RS Radar
3. Today's Watchlist

Entry evaluation, chart-based structure review, position sizing, and trade management are out of scope for the active system and remain archived.

---

## Active Documents

1. `01_SYSTEM_OVERVIEW.md`
   - active product scope
   - architecture boundaries
   - screening-system positioning

2. `02_DATA_MODEL_AND_SOURCES.md`
   - live data architecture
   - provider split
   - cache and snapshot flow
   - universe discovery

3. `03_INDICATORS_AND_SCORING.md`
   - indicators
   - RS
   - Fundamental / Industry / Hybrid
   - VCS

4. `04_SCAN_AND_WATCHLIST_SPEC.md`
   - stable watchlist workflow
   - scan / annotation evaluation model
   - duplicate ticker logic
   - watchlist generation flow
   - references to per-scan documents under `doc/Scan/`

5. `05_DASHBOARD_UI_SPEC.md`
   - Market Dashboard
   - RS Radar
   - Today's Watchlist
   - active UI behavior

6. `06_MODULE_AND_INTERFACE_SPEC.md`
   - module responsibilities
   - Config / Calculator / Result split
   - active interfaces

7. `07_IMPLEMENTATION_PLAN.md`
   - implementation phases
   - active priorities

8. `08_PARAMETER_CATALOG.md`
   - active config parameters
   - thresholds, weights, universes, and modes

9. `09_CURRENT_STATUS_AND_ROADMAP.md`
   - current implementation status
   - active roadmap

10. `10_TRADING_METHOD_PLAYBOOK.md`
    - human-readable method guide
    - screening workflow
    - active scope boundary

11. `11_IMPLEMENTATION_GAP_ANALYSIS.md`
    - code-first gap analysis
    - remaining active-scope issues

12. `12_UNIVERSE_PROVIDER_DECISIONS.md`
    - universe discovery strategy
    - refresh cadence
    - current provider decisions

---

## Scan References

- `doc/Scan/scan_00_index.md`
  - entry point for per-scan reference documents
  - one scan per document
  - exact scan-specific thresholds and formulas live there instead of in the numbered specifications

## Additional User Guide

- `doc/SCREENING_FIELD_GUIDE_JA.md`
  - Japanese user guide for the meaning of displayed indicators, scan outputs, and practical screening interpretation
- `doc/WatchlistPresets/00_index.md`
  - built-in watchlist preset catalog
  - one preset per document
  - exact preset scan selections, duplicate threshold, and filter settings

---

## Archived Documents

- `archived/ENTRY_EXIT_AND_RISK_SPEC.md`
- `archived/ENTRY_STRUCTURE_NOTES.md`

These are preserved for a future entry-decision system and are not part of the active screener.

---

## Suggested Reading Order

1. `01_SYSTEM_OVERVIEW.md`
2. `02_DATA_MODEL_AND_SOURCES.md`
3. `03_INDICATORS_AND_SCORING.md`
4. `04_SCAN_AND_WATCHLIST_SPEC.md`
5. `05_DASHBOARD_UI_SPEC.md`
6. `09_CURRENT_STATUS_AND_ROADMAP.md`

## Agent Operations

- `AGENTS.md`
  - repository-wide operating rules
- `.agents/skills/oratek-spec-to-code-syncing/SKILL.md`
  - use when specs are authoritative and implementation must change
- `.agents/skills/oratek-code-to-spec-syncing/SKILL.md`
  - use when implementation is authoritative and specs must change
- `.agents/skills/oratek-doc-syncing/SKILL.md`
  - use only to route ambiguous sync-direction requests

## Code Entry Points

1. `src/pipeline.py`
2. `src/data/*`
3. `src/indicators/core.py`
4. `src/scoring/*`
5. `src/scan/*`
6. `src/dashboard/*`
7. `app/main.py`
