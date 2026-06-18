# Market Document And Report Spec

## 1. Scope

This specification defines the daily market-document and final-report contract.

The system does not attempt to write the final human-facing market report directly. Instead, it writes an evidence-bearing AI-input market document. A report-writing skill consumes that market document and writes the final report.

## 2. Artifact Ownership

| Artifact | Owner | Purpose | Path |
| --- | --- | --- | --- |
| Market summary JSON | System | Persisted `MarketConditionResult` payload. | `data_runs/market_summary/YYYYMMDD.json` |
| Market document JSON | System | Canonical AI-input structured document. | `data_runs/market_documents/latest.json` by default; `YYYYMMDD.json` when `market_report.output.mode=daily_history` |
| Market document Markdown | System | Skill-friendly rendering of the same market document. | `data_runs/market_documents/latest.md` by default; `YYYYMMDD.md` when `market_report.output.mode=daily_history` |
| Market context JSON | System | Fixed-schema compact market and RS context artifact. | `data_runs/market_context/latest.json` by default; `YYYYMMDD.json` when `market_context.output.mode=daily_history` |
| Market context Markdown | System | Fixed-schema compact Markdown rendering of the same context. | `data_runs/market_context/latest.md` by default; `YYYYMMDD.md` when `market_context.output.mode=daily_history` |
| Final market report Markdown | Skill | Human-facing daily market report. | `data_runs/market_reports/YYYYMMDD.md` |

The system does not write final-report JSON metadata. The final report is a Markdown artifact only.

## 3. Daily Flow

1. The pipeline computes `MarketConditionResult` and `RadarResult`.
2. `DataSnapshotStore` persists `market_summary/YYYYMMDD.json`.
3. The market-document builder reads the current summary, RS Radar industry leadership rows, and recent same-folder summaries.
4. The market-context builder reads the current summary and recent same-folder summaries.
5. The system writes market document and market context artifacts according to each `output.mode`. The default is `latest_only`, which writes `latest.json` and `latest.md`.
6. The report-writing skill reads the market document, preferably the Markdown rendering with the JSON treated as canonical data.
7. The skill writes `market_reports/YYYYMMDD.md`.

`market_context` is a separate compact AI-input artifact. It uses the same market and RS data family as the market document, but it has its own fixed `MARKET_CONTEXT` v1.0.1 schema and does not replace the market document or final report.

`market_context` renders `INDUSTRY_RS` rows as `tactRS|structRS63|dRank1W|majors`. `tactRS` is RS Radar tactical `RS`, `structRS63` is RS Radar structural `STRUCT RS`, and `dRank1W` is the prior comparable structural-rank position minus the current structural-rank position across the full configured industry ETF universe. Positive `dRank1W` means the ETF moved up in structural rank. When no previous summary exists, the row delta is `NA` and `NEW_IN_TOP8` / `OUT` are `NA(no_history)`. When previous industry rows exist but lack `STRUCT RS`, the row delta is `NA` and `NEW_IN_TOP8` / `OUT` are `NA(no_struct_history)`.

## 4. Market Document Contract

The market document JSON uses:

- `schema_version`: `market_document.v1`
- `document_type`: `ai_market_report_input`

Top-level fields:

- `trade_date`
- `generated_at`
- `source_summary_path`
- `executive_context`
- `sections`
- `recent_transitions`
- `watchpoint_candidates`
- `analysis_boundary`
- `missing_inputs`
- `data_appendix`
- `report_generation_contract`

`executive_context` includes the system-derived `market_action_mode`, `market_action_mode_key`, `market_action_mode_reason`, `swing_market_posture`, and `confirmation_order` when the required market inputs are available.
These fields are report-level guidance for current swing-investing market recognition and candidate review intensity; they do not change EntrySignal, WatchList, scan logic, position sizing, execution, or exit management.

The Markdown market document is not the final report. It is the AI/skill input form.

## 5. Required Market Document Features

The market document must include these intermediate representations so the skill does not need to infer them:

- `swing_market_posture`: current market-recognition guidance for long-exposure posture, new-entry posture, profit-taking/watch posture, risk-management strictness, and EntrySignal interpretation posture
- `trajectory`: summarized path of recent change, not only point-in-time deltas
- `significance`: section-level output-volume control, one of `high`, `medium`, `low`
- `recent_transitions`: recent state changes detected by the system
- `watchpoint_candidates`: allowed next-watch candidates; the skill must choose from these only
- `analysis_boundary`: allowed and prohibited information sources
- `facts_for_ai`: section-specific facts the skill may turn into prose

The system includes an `industry_leadership` section when RS Radar `industry_leaders` rows are available. This section supplies industry-level RS leadership context, 52W HIGH industry groups, accelerating industry groups, sustained-leadership industry groups, and weak industry groups for report-level candidate-priority guidance.

The system includes a `term_credit_diagnostics` section when auxiliary market symbols are available. It uses `volatility_term_structure` (`VIX9D/VIX`, `VIX/VIX3M`, front inversion, and full backwardation flags) and `credit_risk_proxy` (`HYG/LQD`, `HYG/IEF`, high-yield OAS, and delta OAS) as report-level context only; these diagnostics do not change Market Score, scans, Watchlist output, or EntrySignal evaluation. The `volatility_safe_haven` section also includes `high_vix_summary` VIX diagnostics (`VIX 252D PCTL`, `VIX PEAK DAYS`, and `VIX PEAK RATIO %`) when available.

The system includes an `index_state_diagnostics` section when index-state symbols are available. It uses `index_state_summary` for SPY/QQQ rally-attempt day, FTD flag, FTD age, FTD quality metrics, distribution-day count, and under-pressure flag. FTD quality metrics are FTD-day gain, FTD-day volume ratio, active-universe advance ratio on the FTD date, and a bounded quality score. These are report-level context only and do not change Market Score, scans, Watchlist output, or EntrySignal evaluation.

The saved market summary also includes `breadth_momentum_summary` for A20 momentum, `breadth_internal_summary` for active-universe breadth internals, and `drawdown_summary` for configured index drawdown state (`DD 252D %`, `T_DD`, and rolling high). These are report inputs only until report-generation logic is explicitly upgraded.

The `recommendation_inputs` section may also include `priority_candidate_high`, `priority_candidate_medium`, and `priority_candidate_low_watch` facts.
These are generated from the existing sector/style/industry inputs and are intended to make the final report's candidate-review order explicit.

## 6. Analysis Boundary

The skill may use:

- values and labels in the market document
- trajectories and significance flags in the market document
- `facts_for_ai`
- `watchpoint_candidates`

The skill must not use:

- economic release schedules
- company earnings or news
- oil, rates, FX, credit, or other external market causes unless present in the document
- geopolitical events
- watchpoints not listed in `watchpoint_candidates`

Sector and industry implications must be limited to `21EMA POS`, `DAY %`, relative strength, 52W HIGH, and basket comparison fields that exist in the document.

## 7. Final Report Format

The final report is Japanese Markdown and uses this structure:

```markdown
### 日次マーケットレポート

- 対象日: YYYY-MM-DD
- 生成時刻: YYYY-MM-DDTHH:MM:SS
- 入力 Market Document: data_runs/market_documents/latest.md


#### 1. 今日の結論（必読）

##### 市場の一行診断

##### 今日の行動文脈

##### 現在の市場認識

- ロング保有の許容度:
- 新規エントリー確認の積極度:
- 利確・警戒確認の優先度:
- リスク管理ルールの厳格度:
- EntrySignal 確認時の厳格度:

##### 注視すべき変化


#### 2. 投資優先度（必読）

##### 優先して確認する領域

##### 新規候補の優先度を下げる領域

##### Profit-taking/Exit Watch

##### スタイル傾向


#### 3. 状態変化


#### 4. 詳細確認

##### ブレッドスと参加率

##### ボラティリティと Safe Haven

##### セクターと 21EMA POS

##### ファクターとスタイル


#### 5. 次回注視点
```

## 8. Final Report Writing Rules

The first layer is mandatory every day:

- `今日の結論`
- `投資優先度`

`今日の結論` must focus on action context, not a neutral description of every section. It should explain how today's market document should change screening and candidate-confirmation behavior.

When `executive_context.swing_market_posture` exists, the final report must use it in `現在の市場認識` and keep the content at report-level guidance: long-exposure posture, new-entry review intensity, profit-taking/watch review priority, risk-management strictness, and EntrySignal interpretation posture.
It must not turn these fields into execution instructions, position sizing, stop-loss placement, or exit-management commands.

`状態変化` must prioritize `recent_transitions` and `trajectory`.

`詳細確認` must follow `significance`:

- `high`: normal paragraph, usually 3 to 5 sentences
- `medium`: only changed elements, usually 2 to 3 sentences
- `low`: one sentence or grouped summary

`次回注視点` must select at most two items from `watchpoint_candidates`.

The report must use compact heading levels (`###`, `####`, `#####`) and blank lines between major sections/subsections so the rendered Markdown remains readable.

Body text must start a new source line after each Japanese full stop (`。`) so sentences are easy to scan.

For sector-level prose, the final report must write sector names instead of ETF labels. For example, write `Financials`, not `XLF Financials`, and `Energy`, not `XLE Energy`.

When the market document includes `industry_leadership`, action-oriented report skills may use it to write industry-level priority groups, 52W HIGH groups, accelerating groups, sustained-leadership groups, and weak groups. This must remain report-level guidance only; the report must not claim that EntrySignal, WatchList, RS Radar, or dashboard logic changed.

## 9. Terminology

These terms are implementation/domain labels and should not be over-translated:

- `21EMA High`
- `21EMA Low`
- `21EMA Cloud`
- `21EMA POS`
- `Risk-On Ratio`
- `Safe Haven`
- `Profit-taking/Exit Watch`
- `EntrySignal`
- `WatchList`

## 10. Skill Location

The standard report-writing skill is ReportSkill-1 and is located at:

```text
.agents/skills/reportskill-1/SKILL.md
```

ReportSkill-1 keeps the market-document-only evidence boundary, then adds in-report confirmation order, industry-level priority groups, and EntrySignal interpretation.
It does not directly integrate with or modify EntrySignal or WatchList systems.

The skill's input should be whichever form is easiest for the AI to write from. Operationally, Markdown is the primary prompt input and JSON remains the canonical persisted data.
