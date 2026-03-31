---
name: oratek-spec-to-code-syncing
description: Use when the OraTek specifications are the source of truth and Codex must update implementation to match them. Trigger this skill when the user asks to implement behavior described in doc/Specifications, close a code-versus-spec gap by changing code, config, tests, or UI, or align the product with the written specification. Do not use it when the request is to update documentation from the current code.
---

# OraTek Spec to Code Syncing

## Critical Rule

- Do not edit the specifications.
- If the specs appear wrong, incomplete, or inconsistent, stop and report the mismatch instead of rewriting the docs.

## Restriction Scope

- The specification-edit restriction applies only while executing the current task under this skill.
- Once the current task is complete, the restriction does not carry forward unless this skill is invoked again.

## Workflow

1. Read `doc/Specifications/00_INDEX.md` to identify the active spec set.
2. Read the exact numbered specs in scope for the requested behavior.
3. Read `references/doc-map.md` to choose the smallest correct implementation surface.
4. Treat the selected specifications as the source of truth.
5. Update only the required implementation files, config, and tests.
6. Validate the affected behavior with targeted compile/test runs.
7. Report changed implementation files and any unresolved spec ambiguity.

## Scope Guardrails

- Keep the active product scope limited to Market Dashboard, RS Radar, and Today's Watchlist.
- Treat entry evaluation, structure analysis, position sizing, and exit logic as archived unless the task explicitly changes archived scope.
- Do not use generated files in `data_cache/`, `data_runs/`, or `__pycache__/` as design authority.
- Do not repair doc-versus-code mismatches by editing docs. This skill exists to change implementation only.

## Output Requirements

- Report which implementation files were changed and why they were in scope.
- Call out any spec ambiguity that blocked or constrained the implementation.
- State which tests or validations were run.

## Reference

- Read `references/doc-map.md` whenever the code touchpoints are not obvious from the user request.
