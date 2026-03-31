---
name: oratek-doc-syncing
description: Use only when an OraTek request is ambiguous about sync direction and Codex must choose between syncing implementation to the specifications or syncing the specifications to the implementation. Route to $oratek-spec-to-code-syncing when the specs are authoritative. Route to $oratek-code-to-spec-syncing when the implementation is authoritative.
---

# OraTek Doc Syncing

This skill is now a direction selector.

- Use `$oratek-spec-to-code-syncing` when the specifications are the source of truth.
- Use `$oratek-code-to-spec-syncing` when the implementation is the source of truth.
- Do not perform the sync work inside this skill if the direction is already clear.
