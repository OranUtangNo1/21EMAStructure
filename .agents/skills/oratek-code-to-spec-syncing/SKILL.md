---
name: oratek-code-to-spec-syncing
description: Use when the current OraTek implementation is the source of truth and Codex must update the numbered specifications to match it. Trigger this skill when the user asks to document current behavior from code, refresh doc/Specifications after code or config changes, sync design docs to the implementation, or update the specification index and related specs from the live codebase. Do not use it when the request is to change implementation to satisfy an existing spec.
---

# OraTek Code to Spec Syncing

## Critical Rule

- Do not edit the implementation.
- If the implementation appears wrong, incomplete, or inconsistent, document the mismatch instead of changing the code.

## Restriction Scope

- The implementation-edit restriction applies only while executing the current task under this skill.
- Once the current task is complete, the restriction does not carry forward unless this skill is invoked again.

## Workflow

1. Read `doc/Specifications/00_INDEX.md` to identify the active document set.
2. Treat implementation files, tests, and `config/default.yaml` as the source of truth.
3. Read `references/doc-map.md` to choose the smallest correct document set.
4. Update only the affected specifications and `00_INDEX.md` when filenames or scope change.
5. Reopen every edited Markdown file with explicit UTF-8 and verify that links, filenames, and section names still match the repository.
6. Report which docs were updated and any implementation-versus-doc mismatch that could not be resolved from source files.

## Scope Guardrails

- Keep the active product scope limited to Market Dashboard, RS Radar, and Today's Watchlist.
- Treat entry evaluation, structure analysis, position sizing, and exit logic as archived unless the task explicitly changes archived scope.
- Do not use generated files in `data_cache/`, `data_runs/`, or `__pycache__/` as documentation sources.
- Do not repair code-versus-doc mismatches by editing implementation. This skill exists to change docs only.

## Output Requirements

- Report which docs were updated and why those docs were in scope.
- Call out any code-versus-doc mismatch that could not be resolved from source files.
- Prefer the code and config when the docs disagree, then state the mismatch plainly.

## Reference

- Read `references/doc-map.md` whenever the affected docs are not obvious from the user request.
