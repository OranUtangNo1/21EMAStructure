---
name: reportskill-1
description: Write the default action-oriented Japanese daily market report from OraTek market documents. Use when Codex needs to create a daily market report from `data_runs/market_documents/YYYYMMDD.md` or `.json`, including a change-to-action interpretation section, enumerated indicator readouts, in-report confirmation order, industry-level RS leadership, and priority candidate groups without changing EntrySignal or WatchList systems.
---

# ReportSkill-1

<!--
version: 1.2
v1.1 changes:
- Added required report section `指標の変化と投資行動への含意（必読）` (change -> interpretation -> action).
- Added Change Interpretation Rules with level/change/persistence framing and selection thresholds.
- Readability Rules now require enumeration for listable facts; sentence-per-line applies to prose paragraphs only.
- Action Guidance Rules now separate level vs change vs persistence and require flagging contradictions.
- Self-check extended for the new section.
v1.2 changes:
- Added `swing_market_posture` consumption for current swing-investing market recognition.
- Section 1 must explicitly write long-exposure, new-entry, profit-taking/watch, risk-management, and EntrySignal interpretation posture when the market document provides it.
The skill name is kept as `reportskill-1` so existing reports' "使用スキル: ReportSkill-1" line stays stable.
-->

## Overview

Convert an OraTek AI-input market document into a human-facing Japanese daily market report focused on swing-investing action context.
This is the default OraTek daily market-report writing skill.
It preserves the market-document-only evidence boundary, then adds in-report guidance for indicator-change interpretation, confirmation order, industry-level RS leadership, and high-priority candidate groups.

The report's core value is to translate **current market recognition and meaningful market changes** into **how swing-investing review behavior should change**, not merely to restate current levels.

Use `references/final_report_template.md` for the required section structure and self-check.

## Scope

Keep all improvements inside the Markdown report.
Do not change, read from, write to, or directly integrate with EntrySignal, WatchList, Today's Watchlist, RS Radar, or dashboard logic.
Use terms such as EntrySignal and WatchList only as interpretation context inside the report.

If the market document does not include actual candidate symbols, write priority candidate groups, industry groups, or conditions rather than inventing tickers.
If the market document includes candidate-level fields in the future, use only those fields and still avoid changing system behavior.

## Required Report Sections (fixed order)

Write these sections in this order. Headings must match `references/final_report_template.md` exactly.

1. `今日の投資・行動方針`（一行診断、`今日の行動モード`、`現在の市場認識`）
2. `指標の変化と投資行動への含意（必読）`  ← v1.1 で新設。`今日の行動モード` の直後に置く。
3. `今日の確認順序`
4. `本日の重点確認候補`（High / Medium / Low・Watch）
5. `EntrySignal 確認時の見方`
6. `市場状態の詳細`（水準の列挙）
7. `次回注視点`

Sections 1 と 5 は文脈を述べる散文。
それ以外の事実列(数値・候補・業種群・style pair)は散文にせず箇条書きで列挙する(Readability Rules 参照)。

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
   - If `executive_context.market_action_mode` is present, use it as the primary `今日の行動モード`; do not replace it with a looser prose-only regime label.
   - If `executive_context.swing_market_posture` is present, use it as the primary source for `現在の市場認識`.
   - `現在の市場認識` must include long-exposure posture, new-entry posture, profit-taking/watch posture, risk-management strictness, and EntrySignal interpretation posture.
   - Treat `swing_market_posture` as report-level market context only. Do not turn it into order, sizing, stop-loss placement, or exit-management instructions.
   - If `executive_context.confirmation_order` is present, use it as the base for `今日の確認順序`, editing only for readability.
   - Use `recommendation_inputs` for investment priority, lower-priority areas, `Profit-taking/Exit Watch`, and style tilt.
   - When `recommendation_inputs.facts_for_ai` includes `priority_candidate_high`, `priority_candidate_medium`, or `priority_candidate_low_watch`, use those fields directly for `本日の重点確認候補`.
   - Use `industry_leadership` when present for industry-level priority groups, 52W HIGH groups, accelerating groups, sustained-leadership groups, and weak groups.
   - **Extract threshold-crossing changes for the change-interpretation section.** Read `metric_deltas` (1D/1W/1M), the Market Score history (`score_1d/1w/1m/3m_ago` and each `label_*`), sector/industry `RANK DELTA`, style-pair `ABOVE MA COUNT`, `recent_transitions`, and each section's `trajectory`/`significance`. Keep only changes that cross the thresholds in **Change Interpretation Rules**.
   - Use `recent_transitions` and each section's `trajectory` for state changes.
   - Use each section's `significance` to decide how much detail to write.
   - Use only `watchpoint_candidates` for next watchpoints.
4. Write the report in Japanese Markdown.
   - Follow `references/final_report_template.md` and the fixed section order above.
   - Explain what the market state means for screening, candidate review, and EntrySignal interpretation.
   - **Write `指標の変化と投資行動への含意（必読）`** as 3 to 6 enumerated change blocks, each in the change -> interpretation -> action format (see Change Interpretation Rules).
   - Include `今日の確認順序` as a practical review sequence based only on the document.
   - Include `本日の重点確認候補` as enumerated High / Medium / Low-or-Watch candidate groups or conditions (one item per line).
   - **Enumerate listable facts.** Breadth/participation numbers, volatility/Safe Haven numbers, industry-leadership groups, and factor/style pairs must be bullet lists, not prose sentences.
   - Use the exact readable Japanese headings from `references/final_report_template.md`; do not reuse mojibake headings from older reports or corrupted source documents.
   - Prioritize industry-level groups over broad sector prose when `industry_leadership` is available.
   - Convert sector ETF labels into sector-name prose. For example, write `Financials`, not `XLF Financials`, and `Energy`, not `XLE Energy`.
   - Keep implementation/domain labels as-is when translation would distort meaning: `21EMA High`, `21EMA Low`, `21EMA Cloud`, `21EMA POS`, `Risk-On Ratio`, `Safe Haven`, `Profit-taking/Exit Watch`, `EntrySignal`, `WatchList`.
5. Save the output.
   - Derive the filename from `trade_date` as `data_runs/market_reports/YYYYMMDD.md`.
   - Create `data_runs/market_reports/` if it does not exist.
   - Do not create final-report JSON metadata.
6. Reopen and self-check the saved Markdown.
   - Confirm every required heading is present and in the fixed order.
   - Confirm `指標の変化と投資行動への含意（必読）` exists, contains 3 to 6 items, and every item has the three lines 変化 / 解釈 / 行動.
   - Confirm every change item cites a number or a state transition that actually appears in the market document, and clears a selection threshold.
   - Confirm listable sections (breadth, volatility, industry groups, factor/style, candidates) are bullet lists, not prose.
   - Confirm `次回注視点` contains at most two items and both come from `watchpoint_candidates`.
   - Confirm report headings and metadata labels are readable Japanese, not mojibake.
   - Confirm no prohibited external causes or events were added.
   - Confirm no suspicious replacement text such as repeated `?` remains.
   - Confirm there is no claim that EntrySignal or WatchList logic was changed.

## Analysis Boundary

Use only information present in the market document:

- values, labels, trajectories, and significance flags
- `metric_deltas` and score/label history
- `facts_for_ai`
- `recent_transitions`
- `watchpoint_candidates`
- `analysis_boundary` instructions

Do not add outside explanations, including economic releases, company earnings/news, rates, FX, oil, credit, geopolitical events, or unlisted watchpoints.
Sector and industry implications must stay within fields present in the document such as `21EMA POS`, `DAY %`, relative strength, `52W HIGH`, `RANK DELTA`, and basket comparisons.
In the change section, every cited delta or transition must come from the document; never estimate or interpolate a change that is not stated.

## Change Interpretation Rules（変化 → 解釈 → 行動）

This is the engine for the `指標の変化と投資行動への含意（必読）` section.

### Read every indicator on three axes

Always distinguish, and never conflate, these three:

- **水準 (level)**: where the value sits now (e.g. Risk-On Ratio above all MAs = 3/3).
- **変化 (delta / trajectory)**: did it improve or worsen recently (sign and size of 1W / 1M deltas).
- **持続性 (persistence)**: one-off or established (consecutive days, `ABOVE MA COUNT`, `recent_transitions`).

State which axis a conclusion rests on. A high level with a negative delta, and a sharply improving delta with a still-weak level, are different situations and must read differently.

### Selection thresholds (only report changes that cross these)

Include a change in the section only if it meets at least one threshold. Everything else stays in `市場状態の詳細` as a level, not in the change section. This keeps the section reproducible and prevents noise.

- Market Score `label` changed, or score moved 1W ±3 or 1M ±5.
- breadth / participation `metric_deltas` moved 1W ±10pt.
- `pct_2w_high` moved 1W ±20pt (breakout-environment shift).
- Risk-On Ratio `state` transitioned, or `ABOVE MA COUNT` crossed 0 <-> 3.
- VIX moved ±2, or `vix_score` / `safe_haven_score` moved 1M ±15.
- Sector or industry `RANK DELTA` (1W or 1M) is ±3 or more.
- style-pair `ABOVE MA COUNT` crossed 0 <-> 3 (regime flag).

Pick the 3 to 6 most decision-relevant crossings. Prefer changes that affect which preset family or which industry group to review first.

### Output format (enumerate, do not narrate)

Each item is one bullet block with exactly three lines:

```
- 変化: <指標名> <現値>（1W <±x>、1M <±x>、state遷移があれば明記）
  - 解釈: この変化が示す市場の方向（水準・変化・持続性のどれに基づくか）
  - 行動: スクリーニング / 候補確認 / EntrySignal解釈をどう変えるか
```

The 行動 line must stay at report-workflow level (how aggressively to review, which group first, how to interpret a signal). Never write order types, sizing, stop placement, take-profit, or chart commands.

## Action Guidance Rules

Write actionable advice only for report-level workflow:

- how aggressively to review candidates
- whether long exposure should be treated as broadly acceptable, selective, wait-and-confirm, or defensive
- whether new-entry review should be normal, selective, or restrained
- whether profit-taking/watch candidates should be reviewed before new candidates
- whether risk-management rules should be treated as normal, stricter, or never loosened
- which sector/style groups to inspect first
- which industry groups to inspect first when `industry_leadership` is present
- which groups to downgrade or watch
- how to interpret EntrySignal under the current market environment
- what confirmation would increase or decrease swing-trade expectancy

Do not write trade execution instructions, order types, position sizing, stop-loss placement, take-profit management, or discretionary chart-review commands.

### Level vs change separation

- Describe each indicator with its 水準 / 変化 / 持続性 distinguished.
- An area whose level is still weak but whose rank or change is improving sharply (e.g. large `RANK DELTA` while `REL 1M` is still negative) is `改善中・確認待ち`. Place it at Medium or below; never merge it into Low.
- When change and level disagree, state the contradiction in one line before giving the action.

For `今日の確認順序`, write 3 to 5 ordered steps.
Prefer `executive_context.confirmation_order` when the market document supplies it.
Start with the highest-evidence area from `industry_leadership` when present, then use `priority_sectors`, style tilts, breadth, sector rotation, and risk-on context.

For `本日の重点確認候補`, use:

- `優先度 High`: prefer `priority_candidate_high`; otherwise use industry groups in `new_high_industries`, `sustained_leadership_industries`, or `accelerating_industries`.
- `優先度 Medium`: prefer `priority_candidate_medium`; otherwise use top or secondary industry/sector groups with partial confirmation, or `改善中・確認待ち` groups.
- `優先度 Low / Watch`: prefer `priority_candidate_low_watch`; otherwise use `weak_industries`, lower-priority new entries, or Profit-taking/Exit Watch.

Each candidate or group is one bullet line. When per-group metrics exist (RS, 1W, 1M, RS MTH%, 52W HIGH, tag), put them on the same line as compact fields rather than in a sentence.

For `EntrySignal 確認時の見方`, explain whether signals should be treated as easier to promote, require stricter confirmation, or be downgraded by market context.
When `industry_leadership` exists, explicitly explain that EntrySignal candidates from stronger industry groups may be reviewed first and candidates from `weak_industries` should be downgraded inside the report interpretation.
Keep this as interpretation only; never imply the EntrySignal score or rule changed.

## Readability Rules

Enumerate listable facts; reserve prose for context.

- **Listable facts must be Markdown bullet lists**: multiple indicator values, candidate groups, industry groups, style pairs, and every change block. Do not turn an enumerable set into a chain of `〜です。` sentences.
- The "one Japanese sentence per source line" rule applies **only to prose paragraphs** — the one-line diagnosis, `今日の行動モード`, the 解釈/行動 lines, and `EntrySignal 確認時の見方`. In those paragraphs, when a sentence ends with `。`, the next sentence starts on the next line.
- Use compact heading levels exactly as shown in the template.
- Leave a blank line between major sections and between subsections.

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
If `metric_deltas` or the score/label history is missing, write the change section with whatever transitions are available and state that quantified deltas were unavailable; do not fabricate delta numbers.

Do not quote the full market document back to the user.
Transform it into a concise final report.

The report's role is to help the user translate market changes into higher-expectancy swing-investing review behavior, while staying inside screening, candidate review, and entry-evaluation interpretation.
