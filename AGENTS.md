# OraTek Agent Guide

## Project Summary

- The active product is a screening, candidate extraction, and entry evaluation platform.
- The active product is short- to medium-term, long-only, and Stage 2 oriented by default.
- The active scope includes Market Dashboard, RS Radar, Today's Watchlist, and Entry Signal evaluation.
- Bottom-fishing, recovery, 52-week-low, and short-side setups are not default actionable workflows.
- Final discretionary chart review, position sizing, trade execution, and exit management are out of scope for the active system.
- Those out-of-scope notes belong in `archived/`.
- The top priority is to keep the screening and entry-evaluation workflow reliable, inspectable, and easy to change.
- The top priority is not adding trade management features.
- The top priority is preserving correct scan behavior, data lineage, entry-signal outputs, and dashboard outputs.

## Source Of Truth

- Treat implementation files and `config/default.yaml` as the source of truth for behavior.
- Use `doc/SystemDocs/Specifications/00_INDEX.md` as the navigation entry for numbered design docs.
- Use `doc/SystemDocs/Scan/` as the source of truth for per-scan definitions.
- Use `doc/SystemDocs/Modularization/00_INDEX.md` when modularization reference material is needed.

## Architecture Rules

### Layer Structure

- `src/data/` handles providers, cache, snapshot store, and universe discovery.
- `src/indicators/` computes raw technical fields from time series.
- `src/scoring/` computes RS, VCS, industry, hybrid, and other scores.
- `src/scan/` applies scan rules, post-scan annotations, and watchlist assembly.
- `src/dashboard/` shapes results for Market Dashboard, RS Radar, and Today's Watchlist.
- `src/services/` contains independently executable service orchestration.
- `src/cli/oratek.py` is the active user entrypoint; the system has no GUI.

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

- `archived/` contains out-of-scope code and notes that are intentionally not active.
- `config/` contains default and alternate configuration files.
- `doc/SystemDocs/` contains writable system specifications and references.
- `doc/SystemDocs/Modularization/` contains modularization reference specifications, shared-data contracts, DB pause decisions, and the optional work plan.
- `doc/Archive/` contains read-only warehouse-style reference material such as original dashboard notes and legacy logic references.
- `doc/ForCodexOutput/` contains user-requested answer documents and Codex-generated project notes intended for user review.
- `doc/ForUsersOnly/` contains project documents reserved for user-managed reading and writing unless a task explicitly directs Codex to use them.
- `doc/SystemDocs/WatchlistPresets/` contains the built-in preset catalog documents for the current watchlist preset set.
- `src/` contains active implementation modules.
- `tests/` contains active automated tests.
- `data_cache/` stores local cache artifacts.
- `data_runs/` stores persisted run outputs and universe snapshots.

### Where To Save New Files

- New implementation modules go under the appropriate `src/` subdirectory.
- New orchestration code belongs in the relevant `src/services/` module or `src/cli/oratek.py`.
- Do not add a GUI entrypoint; presentation builders that produce documents or tables belong in `src/dashboard/`.
- New configuration files belong in `config/`.
- When explicitly requested, new numbered design documents belong in `doc/SystemDocs/Specifications/` and must be linked from `doc/SystemDocs/Specifications/00_INDEX.md`.
- When explicitly requested, modularization specifications and work-plan updates belong in `doc/SystemDocs/Modularization/` and should be linked from `doc/SystemDocs/Modularization/00_INDEX.md`.
- New per-scan documents belong in `doc/SystemDocs/Scan/` and should follow the strict scan spec format.
- New answer-style documents requested by the user should be saved in `doc/ForCodexOutput/`.
- User-only working documents should be kept in `doc/ForUsersOnly/`; do not read or edit them unless the task explicitly requires it.
- New warehouse-style reference material that does not need code-sync belongs in `doc/Archive/`.
- Watchlist preset documentation should be saved in `doc/SystemDocs/WatchlistPresets/`.
- New tests belong in `tests/` and should sit next to the subsystem they validate.
- New out-of-scope material belongs in `archived/`.
- Do not save generated cache data, run exports, or temporary investigation notes as new tracked source files unless the task explicitly requires fixtures or durable artifacts.

## Working Rules

- Preserve the Config / Calculator / Result separation used across the codebase.
- Preserve data-quality visibility. Fetch status, source labels, stale-cache handling, and persisted run metadata are product behavior, not incidental logging.
- Do not edit generated artifacts in `data_cache/`, `data_runs/`, or `__pycache__/` unless the task explicitly targets persistence, fixtures, or cache behavior.
- Treat `doc/ForCodexOutput/` as the default destination for user-requested explanatory documents that Codex creates during a task.
- Treat `doc/ForUsersOnly/` as user-controlled documentation space. Do not read from it, write to it, or use it as source material unless the user explicitly asks.
- Treat `doc/Archive/` as read-only warehouse material unless the user explicitly requests archive maintenance.
- Keep active screening docs separate from archived entry/risk docs.
- If numbered specs are added, moved, or repurposed, update `doc/SystemDocs/Specifications/00_INDEX.md` in the same pass.
- When documenting modularization contracts, place shared-data schema, service-boundary, DB-pause, and `as_of_date` material in `doc/SystemDocs/Modularization/`.
- Prefer ASCII-safe file edits by default. Only use non-ASCII text when it is explicitly needed and the write path has been verified to preserve UTF-8 without lossy replacement.
- Keep Japanese CLI copy centralized in `src/cli/messages_ja.py`; avoid adding user-facing Japanese literals directly to `src/cli/oratek.py`.
- After editing Japanese text or CLI copy, run the mojibake guard test in `tests/test_text_encoding.py`.
- In this Windows Codex environment, if `rg` fails with `Access is denied`, switch immediately to `Get-ChildItem ... | Select-String`.
- Preserve existing line endings when editing files; after edits, run `git diff --stat` and `git diff --check` to catch line-ending-only churn and trailing whitespace.

## Planning And Documentation Policy

- Treat implementation files and `config/default.yaml` as the behavior source of truth unless the user explicitly makes a specification authoritative.
- Do not create or update a plan, work-plan document, or specification as a routine prerequisite for implementation.
- For a well-scoped implementation request, inspect only the relevant code and proceed directly to implementation and validation.
- Do not perform documentation drift checks or SystemDocs synchronization by default.
- Update specifications only when the user explicitly requests documentation work, explicitly makes a specification authoritative, or the implementation cannot proceed safely without resolving a material contract ambiguity.
- If a material code-versus-spec contradiction is encountered during scoped work, report it concisely; do not broaden the task into automatic documentation maintenance.
- When documentation is explicitly changed, keep its own links and indexes valid.

## Edit Rules

- Keep this file between 60 and 300 lines.
- Include the existing guidance in this file when restructuring it.
- Structure the content with stable section headers and short, direct bullets.
- Prefer adding guidance to an existing section before creating a new top-level section.
- Keep the active product scope explicit.
- Keep source-of-truth rules explicit.
- Keep directory ownership explicit so new files are saved in the right place.
- Do not create a plan or update SystemDocs merely because behavior changed.
- Do not add long narrative explanations here.

## Python Environment
- Always use `.venv`
- Do not use system Python

## Commands

- Run the full test suite with `python -m pytest -q`.
- Run a focused test file when iterating on one subsystem, for example `python -m pytest -q tests/test_scoring.py`.
- Launch the CLI with `python -m src.cli.oratek`.
- Use `config/default.yaml` as the default config path unless the task calls for an alternate config.

## Skills

- Use `$oratek-spec-to-code-syncing` only when the user explicitly makes specifications authoritative and implementation must change. Do not edit specs in that flow.
- Use `$oratek-code-to-spec-syncing` only when the user explicitly requests specification synchronization from the current implementation. Do not edit implementation in that flow.
- Use `$handoff-save` before compaction, session end, or interruption when session state should be preserved in `tmp/handoffs/`.
- Use `$handoff-resume` when resuming prior work from a saved handoff in `tmp/handoffs/`.
