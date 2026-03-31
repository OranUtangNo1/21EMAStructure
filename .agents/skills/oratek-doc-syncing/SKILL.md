---
name: oratek-doc-syncing
description: This skill should be used when the user asks to update OraTek documentation, sync numbered specs with code or config changes, refresh the document index, revise screening-system docs, or keep implementation notes aligned after changes to pipeline, scoring, scans, radar, dashboard, or universe logic. Do not use it for unrelated code-only edits or for generic writing outside the OraTek repository.
---

# OraTek Doc Syncing

## Overview

Update OraTek's design docs from the current implementation state. Keep the active screening docs aligned with code and config changes without pulling archived entry or risk material back into the active scope.

## Workflow

1. Read `doc/Specifications/00_INDEX.md` to identify the active document set and current reading order.
2. Treat the changed code, changed tests, and `config/default.yaml` as the source of truth.
3. Read `references/doc-map.md` and choose the smallest correct set of docs to update.
4. Edit only the docs implied by the change area. If a numbered spec was added, moved, or removed, update `doc/Specifications/00_INDEX.md` in the same pass.
5. Reopen every edited Markdown file with explicit UTF-8 and verify that filenames, section names, and links still match the repository.

## Scope Guardrails

- Keep the active product scope limited to Market Dashboard, RS Radar, and Today's Watchlist.
- Treat entry evaluation, structure analysis, position sizing, and exit logic as archived material unless the user explicitly asks to change archived docs.
- Do not use generated files in `data_cache/`, `data_runs/`, or `__pycache__/` as documentation sources.
- Do not rewrite large sections of the doc set when a narrow correction is enough.

## Output Requirements

- Report which docs were updated and why those docs were in scope.
- Call out any code-versus-doc mismatch that could not be resolved from source files.
- If the implementation and docs disagree, prefer the code and config, then state the mismatch plainly.

## Reference

- Read `references/doc-map.md` whenever the affected docs are not obvious from the user request.