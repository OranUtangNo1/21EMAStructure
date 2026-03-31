# OraTek Agent Guide

## Scope

- The active product is a screening and candidate extraction platform.
- Keep the active scope limited to Market Dashboard, RS Radar, and Today's Watchlist.
- Treat entry evaluation, position sizing, trade execution, and exit management as out of scope for the active system. Those notes belong in `archived/`.

## Source Of Truth

- Treat implementation files and `config/default.yaml` as the source of truth for behavior.
- Use `doc/Specifications/00_INDEX.md` as the navigation entry for numbered design docs.
- Keep architecture and behavior docs aligned when changing pipeline flow, scoring logic, scan rules, or UI outputs.

## Code Map

- `src/pipeline.py`: main orchestration for data loading, indicators, scoring, scans, and result packaging.
- `app/main.py`: Streamlit entrypoint for the three screening views.
- `config/default.yaml`: default symbols, universes, thresholds, weights, and dashboard/radar configuration.
- `src/data/`: providers, cache, snapshot store, and universe discovery.
- `src/indicators/`, `src/scoring/`, `src/scan/`, `src/dashboard/`: calculation and presentation modules.
- `tests/`: pytest coverage for data realization, indicators, scoring, scan behavior, radar, and market dashboard output.

## Working Rules

- Preserve the Config / Calculator / Result separation used across the codebase.
- Preserve data-quality visibility. Fetch status, source labels, stale-cache handling, and persisted run metadata are product behavior, not incidental logging.
- Do not edit generated artifacts in `data_cache/`, `data_runs/`, or `__pycache__/` unless the task explicitly targets persistence, fixtures, or cache behavior.
- Keep active screening docs separate from archived entry/risk docs.
- If numbered specs are added, moved, or repurposed, update `doc/Specifications/00_INDEX.md` in the same pass.

## Commands

- Run the full test suite with `python -m pytest -q`.
- Run a focused test file when iterating on one subsystem, for example `python -m pytest -q tests/test_scoring.py`.
- Launch the UI with `streamlit run app/main.py`.
- Use `config/default.yaml` as the default config path unless the task calls for an alternate config.

## Skills

- Use `$oratek-doc-syncing` for larger spec-sync or index-sync tasks after code or config changes.
