---
name: market-report-writer
description: Write the final Japanese daily market report Markdown from OraTek AI-input market documents. Use when Codex needs to consume `data_runs/market_documents/YYYYMMDD.md` or `.json`, validate the `market_document.v1` / `ai_market_report_input` contract, obey the document's `analysis_boundary`, and write `data_runs/market_reports/YYYYMMDD.md`.
---

# Market Report Writer

## Overview

Convert an OraTek AI-input market document into the human-facing Japanese daily market report. Treat the market document as the only evidence source and write the final report to `data_runs/market_reports/YYYYMMDD.md`.

Use `references/final_report_template.md` for the required section structure and self-check.

## Workflow

1. Select the input market document.
   - If the user gives a path, use it.
   - Otherwise use the newest `data_runs/market_documents/YYYYMMDD.md`.
   - If both `.md` and `.json` exist for the date, prefer the Markdown for writing and use JSON only to resolve ambiguity.
2. Validate the input contract before writing.
   - Require `schema_version: market_document.v1`.
   - Require `document_type: ai_market_report_input`.
   - Confirm `trade_date`, `generated_at`, `analysis_boundary`, `sections`, and `watchpoint_candidates` are present.
   - Stop and report the missing fields if the document cannot support a faithful report.
3. Extract the writing inputs.
   - Use `executive_context` for the headline conclusion and daily action context.
   - Use `recommendation_inputs` for investment priority, lower-priority areas, `Profit-taking/Exit Watch`, and style tilt.
   - Use `recent_transitions` and each section's `trajectory` for state changes.
   - Use each section's `significance` to decide how much detail to write.
   - Use only `watchpoint_candidates` for next watchpoints.
4. Write the report in Japanese Markdown.
   - Follow `references/final_report_template.md`.
   - Use the compact heading levels in the template so titles and headings do not render oversized.
   - Leave a blank line between major sections and between subsections.
   - In body text, start a new source line after every Japanese full stop (`。`). Do not put multiple Japanese sentences on the same line.
   - Convert sector ETF labels into sector-name prose. For example, write `Financials`, not `XLF Financials`, and `Energy`, not `XLE Energy`.
   - Keep implementation/domain labels as-is when translation would distort meaning: `21EMA High`, `21EMA Low`, `21EMA Cloud`, `21EMA POS`, `Risk-On Ratio`, `Safe Haven`, `Profit-taking/Exit Watch`.
   - Explain how the market document should affect screening and candidate confirmation. Do not write a neutral recap of every field.
5. Save the output.
   - Derive the filename from `trade_date` as `data_runs/market_reports/YYYYMMDD.md`.
   - Create `data_runs/market_reports/` if it does not exist.
   - Do not create final-report JSON metadata.
6. Reopen and self-check the saved Markdown.
   - Confirm every required heading is present.
   - Confirm `次回注視点` contains at most two items and both come from `watchpoint_candidates`.
   - Confirm no prohibited external causes or events were added.
   - Confirm no suspicious replacement text such as repeated `?` remains.

## Analysis Boundary

Use only information present in the market document:

- values, labels, trajectories, and significance flags
- `facts_for_ai`
- `recent_transitions`
- `watchpoint_candidates`
- `analysis_boundary` instructions

Do not add outside explanations, including economic releases, company earnings/news, rates, FX, oil, credit, geopolitical events, or unlisted watchpoints. Sector implications must stay within fields present in the document such as `21EMA POS`, `DAY %`, relative strength, and basket comparisons.

## Detail Rules

Write Layer 1 every day:

- `今日の結論`
- `投資優先度`

Use state-change fields before point-in-time summaries:

- Prioritize `recent_transitions`.
- Use `trajectory` when explaining whether the current label is improving, deteriorating, recovering, or volatile.

Control length by `significance`:

- `high`: normal paragraph, usually 3 to 5 sentences.
- `medium`: changed elements only, usually 2 to 3 sentences.
- `low`: one sentence or a grouped summary.

## Readability Rules

Write one Japanese sentence per source line. When a sentence ends with `。`, the next sentence must start on the next line.

Use ETF tickers only when the ticker itself is the important artifact. For sector-level prose, remove the ETF ticker and write the sector name:

- `XLB Materials` -> `Materials`
- `XLC Communication Services` -> `Communication Services`
- `XLE Energy` -> `Energy`
- `XLF Financials` -> `Financials`
- `XLI Industrials` -> `Industrials`
- `XLK Technology` -> `Technology`
- `XLP Consumer Staples` -> `Consumer Staples`
- `XLRE Real Estate` -> `Real Estate`
- `XLU Utilities` -> `Utilities`
- `XLV Health Care` -> `Health Care`
- `XLY Consumer Discretionary` -> `Consumer Discretionary`

If Japanese wording helps readability, use the English sector name first and add a short Japanese gloss only when it clarifies the sentence.

## Output Discipline

Do not invent precision. If a required input is missing, say that the report is constrained by the missing field rather than filling the gap.

Do not quote the full market document back to the user. Transform it into a concise final report.

Do not add trading execution, position sizing, exit management, or discretionary chart-review instructions. The active system scope is screening, candidate extraction, watchlist context, and entry evaluation.
