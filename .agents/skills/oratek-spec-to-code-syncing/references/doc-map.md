# OraTek Documentation Map

Use this file to decide which numbered docs should move together when implementation changes.

## Change Map

| Change area | Read and update | Primary code and config touchpoints | Validation hints |
| --- | --- | --- | --- |
| Product scope, architecture, or screen boundaries | `doc/SystemDocs/Specifications/00_INDEX.md`, `doc/SystemDocs/Specifications/01_SYSTEM_OVERVIEW.md`, `doc/SystemDocs/Specifications/06_MODULE_AND_INTERFACE_SPEC.md` | `src/pipeline.py`, `app/main.py`, `doc/SystemDocs/Specifications/*` | Re-check that the active scope still ends at screening outputs |
| Data sources, cache behavior, fetch status, snapshot persistence, or universe discovery | `doc/SystemDocs/Specifications/02_DATA_MODEL_AND_SOURCES.md`, `doc/SystemDocs/Specifications/08_PARAMETER_CATALOG.md`, `doc/SystemDocs/Specifications/12_UNIVERSE_PROVIDER_DECISIONS.md` | `src/data/*`, `src/configuration.py`, `src/pipeline.py`, `config/default.yaml` | Run or review `tests/test_data_realization.py` and `tests/test_universe_discovery.py` |
| Indicators, RS, fundamental/industry/hybrid scoring, VCS, or ranking thresholds | `doc/SystemDocs/Specifications/03_INDICATORS_AND_SCORING.md`, `doc/SystemDocs/Specifications/08_PARAMETER_CATALOG.md` | `src/indicators/*`, `src/scoring/*`, `config/default.yaml` | Run or review `tests/test_indicators.py`, `tests/test_scoring.py`, and `tests/test_radar.py` when relevant |
| Scan rules, watchlist composition, duplicate logic, or earnings flags | `doc/SystemDocs/Specifications/04_SCAN_AND_WATCHLIST_SPEC.md`, `doc/SystemDocs/Specifications/05_DASHBOARD_UI_SPEC.md`, `doc/SystemDocs/Specifications/08_PARAMETER_CATALOG.md`, `doc/SystemDocs/Scan/*`, `doc/SystemDocs/WatchlistPresets/*` | `src/scan/*`, `src/dashboard/watchlist.py`, `src/pipeline.py`, `config/default.yaml` | Run or review `tests/test_scan.py` |
| Market Dashboard behavior or metrics | `doc/SystemDocs/Specifications/05_DASHBOARD_UI_SPEC.md`, `doc/SystemDocs/Specifications/08_PARAMETER_CATALOG.md` | `src/dashboard/market.py`, `src/pipeline.py`, `app/main.py`, `config/default.yaml` | Run or review `tests/test_market_dashboard.py` |
| RS Radar behavior, ETF universes, or major stocks lists | `doc/SystemDocs/Specifications/05_DASHBOARD_UI_SPEC.md`, `doc/SystemDocs/Specifications/08_PARAMETER_CATALOG.md`, `doc/SystemDocs/Specifications/12_UNIVERSE_PROVIDER_DECISIONS.md` | `src/dashboard/radar.py`, `src/scoring/rs.py`, `src/pipeline.py`, `config/default.yaml` | Run or review `tests/test_radar.py` |
| Numbered spec additions, removals, or moves | `doc/SystemDocs/Specifications/00_INDEX.md` | `doc/SystemDocs/Specifications/*` | Confirm filenames and reading order stay accurate |
| Entry, structure, risk, or execution behavior | `archived/ENTRY_EXIT_AND_RISK_SPEC.md`, `archived/ENTRY_STRUCTURE_NOTES.md` | Archived notes and any future entry-system code | Do not pull these details back into active screening docs unless the task explicitly changes scope |

## Operating Rules

- Read the changed code and `config/default.yaml` before editing specs.
- Update the smallest correct document set; avoid broad rewrites when one area changed.
- If behavior is ambiguous in code, state the ambiguity instead of inventing rules.
- Treat `data_cache/`, `data_runs/`, and `__pycache__/` as generated outputs, not documentation sources.
