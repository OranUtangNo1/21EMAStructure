---
name: handoff-save
description: Save the current session state into a compact handoff document before compaction, session end, or interruption. Use when the user asks to save a handoff, preserve work state, prepare for `/compact`, continue later, or checkpoint the current progress.
---

# Session Handoff Save

Write a compact Markdown handoff that lets the next session continue work without re-discovery.

## Workflow

1. Reconstruct the current session state from the conversation and the repository.
2. Capture only high-signal items:
   - goal
   - completed work
   - work in progress
   - decisions and reasons
   - failed approaches worth avoiding
   - concrete next steps
   - relevant file paths and validation commands
3. Check repo state when it materially helps the handoff:
   - `git status --short`
   - `git diff --stat HEAD`
4. Save the handoff under `tmp/handoffs/` unless the user specifies a different path.
5. Use filename format `YYYY-MM-DD-HHmm-handoff.md`.
6. Keep the document concise but sufficient for accurate resumption.

## Required Sections

- `Goal`
- `Completed`
- `In Progress`
- `File Status`
- `Decisions Made`
- `Failed Approaches (Do NOT Retry)` when applicable
- `Learnings & Gotchas` when applicable
- `Blocking Issues` when applicable
- `Next Steps (Prioritized)`
- `Environment & Commands` when relevant

## Quality Bar

- Make the handoff actionable without re-reading the whole prior session.
- Prefer concrete file paths, functions, commands, and current states.
- Preserve rationale, not just outcomes, when decisions matter.
- Do not pad the document with generic background.

## Reporting

- Tell the user where the handoff was saved.
- State the first recommended action for the next session.
