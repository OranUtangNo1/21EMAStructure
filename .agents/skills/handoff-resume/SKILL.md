---
name: handoff-resume
description: Resume work from a saved handoff document by reconstructing the current task state, validating repository drift, and briefing the user on the next step. Use when the user asks to resume prior work, continue from a handoff, read a handoff, or pick up the previous session.
---

# Session Handoff Resume

Read a saved handoff and rebuild enough context to continue the work safely.

## Workflow

1. If the user gives a handoff path, use it.
2. Otherwise look in `tmp/handoffs/` for the newest `*-handoff.md` file.
3. Read the handoff and extract:
   - overall goal
   - completed work
   - current in-progress task
   - blockers
   - decisions to preserve
   - failed approaches to avoid
   - immediate next step
4. Validate drift against the current repo when relevant:
   - confirm referenced files still exist
   - inspect `git status --short`
   - inspect recent commits when needed
5. Brief the user concisely before continuing:
   - what was being done
   - what is already decided
   - what the next action should be
   - any drift or blockers
6. If the user explicitly asked to resume, continue from the first prioritized next step after the briefing unless a blocker requires clarification.

## Drift Rules

- Prefer the current repository state over stale handoff notes.
- If the handoff conflicts with the repo, call out the difference clearly.
- Do not silently assume the handoff is still correct when files or behavior differ.

## Reporting

- Keep the initial briefing short and action-oriented.
- Cite the handoff file used.
- State the exact next step you intend to take.
