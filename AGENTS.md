# OraTek Agent Guide

## Project Summary

- The active product is a screening and candidate extraction platform.
- The active scope is limited to Market Dashboard, RS Radar, and Today's Watchlist.
- Entry evaluation, position sizing, trade execution, and exit management are out of scope for the active system.
- Those out-of-scope notes belong in `archived/`.
- The top priority is to keep the screening workflow reliable, inspectable, and easy to change.
- The top priority is not adding trade management features.
- The top priority is preserving correct scan behavior, data lineage, and dashboard outputs.

## Source Of Truth

- Treat implementation files and `config/default.yaml` as the source of truth for behavior.
- Use `doc/Specifications/00_INDEX.md` as the navigation entry for numbered design docs.
- Use `doc/Scan/` as the source of truth for per-scan definitions.
- Keep architecture and behavior docs aligned when changing pipeline flow, scoring logic, scan rules, or UI outputs.

## Architecture Rules

### Layer Structure

- `src/data/` handles providers, cache, snapshot store, and universe discovery.
- `src/indicators/` computes raw technical fields from time series.
- `src/scoring/` computes RS, VCS, industry, hybrid, and other scores.
- `src/scan/` applies scan rules, post-scan annotations, and watchlist assembly.
- `src/dashboard/` shapes results for Market Dashboard, RS Radar, and Today's Watchlist.
- `src/pipeline.py` orchestrates the end-to-end flow.
- `app/main.py` is the Streamlit entrypoint for the active UI.

### Responsibilities Of Each Layer

- Data layer: fetch data, manage cache freshness, record source labels, and persist run metadata.
- Indicator layer: calculate reusable fields without watchlist-specific presentation concerns.
- Scoring layer: calculate reusable scores and breakdowns from prepared indicator fields.
- Scan layer: define candidate rules, annotation filters, duplicate logic, and hit aggregation.
- Dashboard layer: format active outputs for display without owning raw calculations.
- App layer: collect user inputs and render the three active tabs.

### Role Of The Main Directory

- The repository root is the coordination layer for code, config, documentation, tests, and generated run folders.
- The root should stay clean and contain only top-level project assets and stable entry points.
- Do not place new business logic modules directly in the root.
- Do not place ad hoc scratch files in the root.

## Directory Guide

### The Role Of The Main Directory

- `app/` contains the active Streamlit application entrypoint.
- `archived/` contains out-of-scope code and notes that are intentionally not active.
- `config/` contains default and alternate configuration files.
- `doc/Specifications/` contains numbered system specifications.
- `doc/Scan/` contains one-file-per-scan canonical scan definitions.
- `doc/ForCodexOutput/` contains user-requested answer documents and Codex-generated project notes intended for user review.
- `doc/ForUsersOnly/` contains project documents reserved for user-managed reading and writing unless a task explicitly directs Codex to use them.
- `src/` contains active implementation modules.
- `tests/` contains active automated tests.
- `data_cache/` stores local cache artifacts.
- `data_runs/` stores persisted run outputs and universe snapshots.

### Where To Save New Files

- New implementation modules go under the appropriate `src/` subdirectory.
- New pipeline orchestration code belongs in `src/pipeline.py` or a nearby active `src/` module.
- New UI files belong in `app/` or `src/dashboard/` depending on whether they are entrypoints or presentation helpers.
- New configuration files belong in `config/`.
- New numbered design documents belong in `doc/Specifications/` and must be linked from `doc/Specifications/00_INDEX.md`.
- New per-scan documents belong in `doc/Scan/` and should follow the strict scan spec format.
- New answer-style documents requested by the user should be saved in `doc/ForCodexOutput/`.
- User-only working documents should be kept in `doc/ForUsersOnly/`; do not read or edit them unless the task explicitly requires it.
- New tests belong in `tests/` and should sit next to the subsystem they validate.
- New out-of-scope material belongs in `archived/`.
- Do not save generated cache data, run exports, or temporary investigation notes as new tracked source files unless the task explicitly requires fixtures or durable artifacts.

## Working Rules

- Preserve the Config / Calculator / Result separation used across the codebase.
- Preserve data-quality visibility. Fetch status, source labels, stale-cache handling, and persisted run metadata are product behavior, not incidental logging.
- Do not edit generated artifacts in `data_cache/`, `data_runs/`, or `__pycache__/` unless the task explicitly targets persistence, fixtures, or cache behavior.
- Treat `doc/ForCodexOutput/` as the default destination for user-requested explanatory documents that Codex creates during a task.
- Treat `doc/ForUsersOnly/` as user-controlled documentation space. Do not read from it, write to it, or use it as source material unless the user explicitly asks.
- Keep active screening docs separate from archived entry/risk docs.
- If numbered specs are added, moved, or repurposed, update `doc/Specifications/00_INDEX.md` in the same pass.
- Prefer ASCII-safe file edits by default. Only use non-ASCII text when it is explicitly needed and the write path has been verified to preserve UTF-8 without lossy replacement.

## Edit Rules

- Keep this file between 60 and 300 lines.
- Include the existing guidance in this file when restructuring it.
- Structure the content with stable section headers and short, direct bullets.
- Prefer adding guidance to an existing section before creating a new top-level section.
- Keep the active product scope explicit.
- Keep source-of-truth rules explicit.
- Keep directory ownership explicit so new files are saved in the right place.
- When behavior changes, update the matching docs in the same pass unless the current task explicitly forbids doc edits.
- When a scan definition changes, keep `doc/Scan/` aligned with implementation or call out the mismatch immediately.
- Do not add long narrative explanations here.

## Python Environment
- Always use `.venv`
- Do not use system Python

## Commands

- Run the full test suite with `python -m pytest -q`.
- Run a focused test file when iterating on one subsystem, for example `python -m pytest -q tests/test_scoring.py`.
- Launch the UI with `streamlit run app/main.py`.
- Use `config/default.yaml` as the default config path unless the task calls for an alternate config.

## Skills

- Use `$oratek-spec-to-code-syncing` when the specifications are authoritative and implementation must change. Do not edit specs in that flow.
- Use `$oratek-code-to-spec-syncing` when the implementation is authoritative and specifications must change. Do not edit implementation in that flow.
- Use `$oratek-doc-syncing` only when the request is ambiguous and you need to choose the sync direction first.
