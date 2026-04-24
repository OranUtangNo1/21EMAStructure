# Growth Trading Screener - SystemDocs Index

## Scope Definition

This system is a screening and candidate extraction platform.
Its active responsibility ends at six app outputs:

1. Watchlist
2. Entry Signal
3. Market Dashboard
4. RS
5. Analysis
6. Setting

Entry Signal is an implemented downstream timing-review layer over selected candidate universes. Analysis is an implemented preset-hit performance analysis layer. Setting currently exposes tracking-store diagnostics and is the future home for app-wide settings. Full chart-based structure review, position sizing, trade execution, and trade management remain out of scope and archived.

---

## SystemDocs Scope

`doc/SystemDocs/` is the writable system-specification set for the active screener.
These documents must stay aligned with the current implementation and config.

Use this folder for:

- active numbered system specifications
- active per-scan canonical definitions
- implementation-synced behavior references

Do not use this folder for:

- Codex-to-user answer documents
- user-only working notes
- warehouse-style legacy references
- built-in preset catalog documents

Related folders:

- Codex output docs: `doc/ForCodexOutput/`
- user-managed docs: `doc/ForUsersOnly/`
- warehouse references: `doc/Archive/`
- annotation filter catalog: `doc/SystemDocs/AnnotationFilters/`
- entry signal catalog: `doc/SystemDocs/EntrySignal/`
- watchlist preset catalog: `doc/SystemDocs/WatchlistPresets/`

## Numbered Specifications

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
   - references to per-scan documents under `doc/SystemDocs/Scan/`

5. `05_DASHBOARD_UI_SPEC.md`
   - tab order: Watchlist, Entry Signal, Market Dashboard, RS, Analysis, Setting
   - Market Dashboard
   - RS
   - Watchlist
   - Entry Signal
   - active UI behavior

6. `06_MODULE_AND_INTERFACE_SPEC.md`
   - module responsibilities
   - Config / Calculator / Result split
   - active interfaces

7. `07_TRACKING_ANALYTICS_AND_DB.md`
   - SQLite tracking database
   - preset-hit detection grain
   - forward-return refresh model
   - Analysis UI contract

8. `08_PARAMETER_CATALOG.md`
   - active config parameters
   - thresholds, weights, universes, and modes

9. `10_TRADING_METHOD_PLAYBOOK.md`
    - human-readable method guide
    - screening workflow
    - active scope boundary

10. `12_UNIVERSE_PROVIDER_DECISIONS.md`
   - universe discovery strategy
   - refresh cadence
   - current provider decisions

---

## Per-Scan References

- `doc/SystemDocs/Scan/scan_00_index.md`
  - entry point for per-scan reference documents
  - one scan per document
  - exact scan-specific thresholds and formulas live there instead of in the numbered specifications

## Annotation Filter References

- `doc/SystemDocs/AnnotationFilters/00_index.md`
  - entry point for per-annotation-filter reference documents
  - one annotation filter per document
  - exact filter conditions live there instead of in the numbered specifications

## Entry Signal References

- `doc/SystemDocs/EntrySignal/00_index.md`
  - entry point for per-entry-signal reference documents
  - one entry signal per document
  - exact signal conditions live there instead of in the numbered specifications

## Preset Catalog

- `doc/SystemDocs/WatchlistPresets/00_index.md`
  - built-in watchlist preset catalog
  - one preset per document
  - exact preset scan selections, duplicate rule, and filter settings

## Suggested Reading Order

1. `01_SYSTEM_OVERVIEW.md`
2. `02_DATA_MODEL_AND_SOURCES.md`
3. `03_INDICATORS_AND_SCORING.md`
4. `04_SCAN_AND_WATCHLIST_SPEC.md`
5. `05_DASHBOARD_UI_SPEC.md`
6. `07_TRACKING_ANALYTICS_AND_DB.md`

## Agent Operations

- `AGENTS.md`
  - repository-wide operating rules
- `.agents/skills/oratek-spec-to-code-syncing/SKILL.md`
  - use when specs are authoritative and implementation must change
- `.agents/skills/oratek-code-to-spec-syncing/SKILL.md`
  - use when implementation is authoritative and specs must change

## Code Entry Points

1. `src/pipeline.py`
2. `src/data/*`
3. `src/indicators/core.py`
4. `src/scoring/*`
5. `src/scan/*`
6. `src/dashboard/*`
7. `app/main.py`

---

## Out Of Scope And Archive

- `archived/ENTRY_EXIT_AND_RISK_SPEC.md`
- `archived/ENTRY_STRUCTURE_NOTES.md`

These are preserved for a future entry-decision system and are not part of the active screener.
