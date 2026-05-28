---
name: reportskill-1
description: Write an action-oriented Japanese daily market report from OraTek market documents. Use when the user explicitly asks to use ReportSkill-1 / reportskill-1 for market report creation, or asks for a report that adds in-report confirmation order, industry-level RS leadership, and priority candidate groups without changing EntrySignal or WatchList systems.
---

# ReportSkill-1

## Overview

Convert an OraTek AI-input market document into a human-facing Japanese daily market report focused on swing-investing action context.
This skill is a report-only variant of `market-report-writer`: it preserves the same input contract and analysis boundary, then adds in-report guidance for confirmation order, industry-level RS leadership, and high-priority candidate groups.

Use `references/final_report_template.md` for the required section structure and self-check.

## Scope

Keep all improvements inside the Markdown report.
Do not change, read from, write to, or directly integrate with EntrySignal, WatchList, Today's Watchlist, RS Radar, or dashboard logic.
Use terms such as EntrySignal and WatchList only as interpretation context inside the report.

If the market document does not include actual candidate symbols, write priority candidate groups, industry groups, or conditions rather than inventing tickers.
If the market document includes candidate-level fields in the future, use only those fields and still avoid changing system behavior.

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
   - Use `industry_leadership` when present for industry-level priority groups, 52W HIGH groups, accelerating groups, sustained-leadership groups, and weak groups.
   - Use `recent_transitions` and each section's `trajectory` for state changes.
   - Use each section's `significance` to decide how much detail to write.
   - Use only `watchpoint_candidates` for next watchpoints.
4. Write the report in Japanese Markdown.
   - Follow `references/final_report_template.md`.
   - Explain what the market state means for screening, candidate review, and EntrySignal interpretation.
   - Include `今日の確認順序（必読）` as a practical review sequence based only on the document.
   - Include `本日の重点確認候補` as High / Medium / Low-or-Watch candidate groups or conditions.
   - Use the exact readable Japanese headings from `references/final_report_template.md`; do not reuse mojibake headings from older reports or corrupted source documents.
   - Prioritize industry-level groups over broad sector prose when `industry_leadership` is available.
   - Convert sector ETF labels into sector-name prose. For example, write `Financials`, not `XLF Financials`, and `Energy`, not `XLE Energy`.
   - Keep implementation/domain labels as-is when translation would distort meaning: `21EMA High`, `21EMA Low`, `21EMA Cloud`, `21EMA POS`, `Risk-On Ratio`, `Safe Haven`, `Profit-taking/Exit Watch`, `EntrySignal`, `WatchList`.
5. Save the output.
   - Derive the filename from `trade_date` as `data_runs/market_reports/YYYYMMDD.md`.
   - Create `data_runs/market_reports/` if it does not exist.
   - Do not create final-report JSON metadata.
6. Reopen and self-check the saved Markdown.
   - Confirm every required heading is present.
   - Confirm `次回注視点` contains at most two items and both come from `watchpoint_candidates`.
   - Confirm report headings and metadata labels are readable Japanese, not mojibake.
   - Confirm no prohibited external causes or events were added.
   - Confirm no suspicious replacement text such as repeated `?` remains.
   - Confirm there is no claim that EntrySignal or WatchList logic was changed.

## Analysis Boundary

Use only information present in the market document:

- values, labels, trajectories, and significance flags
- `facts_for_ai`
- `recent_transitions`
- `watchpoint_candidates`
- `analysis_boundary` instructions

Do not add outside explanations, including economic releases, company earnings/news, rates, FX, oil, credit, geopolitical events, or unlisted watchpoints.
Sector and industry implications must stay within fields present in the document such as `21EMA POS`, `DAY %`, relative strength, `52W HIGH`, and basket comparisons.

## Action Guidance Rules

Write actionable advice only for report-level workflow:

- how aggressively to review candidates
- which sector/style groups to inspect first
- which industry groups to inspect first when `industry_leadership` is present
- which groups to downgrade or watch
- how to interpret EntrySignal under the current market environment
- what confirmation would increase or decrease swing-trade expectancy

Do not write trade execution instructions, order types, position sizing, stop-loss placement, take-profit management, or discretionary chart-review commands.

For `今日の確認順序（必読）`, write 3 to 5 ordered steps.
Start with the highest-evidence area from `industry_leadership` when present, then use `priority_sectors`, style tilts, breadth, sector rotation, and risk-on context.

For `本日の重点確認候補`, use:

- `優先度 High`: industry groups in `new_high_industries`, `sustained_leadership_industries`, or `accelerating_industries` that also align with priority sectors/styles or broad market confirmation.
- `優先度 Medium`: top or secondary industry/sector groups with partial confirmation, positive RS but less complete confirmation, or secondary relative strength.
- `優先度 Low / Watch`: `weak_industries`, lower-priority new entries, Profit-taking/Exit Watch, or groups penalized by risk-on/breadth context.

For `EntrySignal 確認時の見方`, explain whether signals should be treated as easier to promote, require stricter confirmation, or be downgraded by market context.
When `industry_leadership` exists, explicitly explain that EntrySignal candidates from stronger industry groups may be reviewed first and candidates from `weak_industries` should be downgraded inside the report interpretation.
Keep this as interpretation only; never imply the EntrySignal score or rule changed.

## Readability Rules

Write one Japanese sentence per source line.
When a sentence ends with `。`, the next sentence must start on the next line.
Use compact heading levels exactly as shown in the template.
Leave a blank line between major sections and between subsections.

Use ETF tickers only when the ticker itself is the important artifact.
For sector-level and industry-level prose, remove the ETF ticker when the name is enough; write `Cybersecurity`, not `CIBR Cybersecurity`, unless the ticker helps identify an ETF artifact.
For sector-level prose, remove the ETF ticker and write the sector name:

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

## Output Discipline

Do not invent precision.
If a required input is missing, say that the report is constrained by the missing field rather than filling the gap.

Do not quote the full market document back to the user.
Transform it into a concise final report.

The report's role is to help the user translate market changes into higher-expectancy swing-investing review behavior, while staying inside screening, candidate review, and entry-evaluation interpretation.
