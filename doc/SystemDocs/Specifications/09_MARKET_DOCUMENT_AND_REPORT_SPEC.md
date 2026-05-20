# Market Document And Report Spec

## 1. Scope

This specification defines the daily market-document and final-report contract.

The system does not attempt to write the final human-facing market report directly. Instead, it writes an evidence-bearing AI-input market document. A report-writing skill consumes that market document and writes the final report.

## 2. Artifact Ownership

| Artifact | Owner | Purpose | Path |
| --- | --- | --- | --- |
| Market summary JSON | System | Persisted `MarketConditionResult` payload. | `data_runs/market_summary/YYYYMMDD.json` |
| Market document JSON | System | Canonical AI-input structured document. | `data_runs/market_documents/YYYYMMDD.json` |
| Market document Markdown | System | Skill-friendly rendering of the same market document. | `data_runs/market_documents/YYYYMMDD.md` |
| Final market report Markdown | Skill | Human-facing daily market report. | `data_runs/market_reports/YYYYMMDD.md` |

The system does not write final-report JSON metadata. The final report is a Markdown artifact only.

## 3. Daily Flow

1. The pipeline computes `MarketConditionResult`.
2. `DataSnapshotStore` persists `market_summary/YYYYMMDD.json`.
3. The market-document builder reads the current summary plus recent same-folder summaries.
4. The system writes `market_documents/YYYYMMDD.json` and `market_documents/YYYYMMDD.md`.
5. The report-writing skill reads the market document, preferably the Markdown rendering with the JSON treated as canonical data.
6. The skill writes `market_reports/YYYYMMDD.md`.

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

The Markdown market document is not the final report. It is the AI/skill input form.

## 5. Required Market Document Features

The market document must include these intermediate representations so the skill does not need to infer them:

- `trajectory`: summarized path of recent change, not only point-in-time deltas
- `significance`: section-level output-volume control, one of `high`, `medium`, `low`
- `recent_transitions`: recent state changes detected by the system
- `watchpoint_candidates`: allowed next-watch candidates; the skill must choose from these only
- `analysis_boundary`: allowed and prohibited information sources
- `facts_for_ai`: section-specific facts the skill may turn into prose

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

Sector implications must be limited to `21EMA POS`, `DAY %`, relative strength, and basket comparison fields that exist in the document.

## 7. Final Report Format

The final report is Japanese Markdown and uses this structure:

```markdown
### 日次マーケットレポート

- 対象日: YYYY-MM-DD
- 生成時刻: YYYY-MM-DDTHH:MM:SS
- 入力 Market Document: data_runs/market_documents/YYYYMMDD.md


#### 1. 今日の結論（必読）

##### 市場の一行診断

##### 今日の行動文脈

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

`状態変化` must prioritize `recent_transitions` and `trajectory`.

`詳細確認` must follow `significance`:

- `high`: normal paragraph, usually 3 to 5 sentences
- `medium`: only changed elements, usually 2 to 3 sentences
- `low`: one sentence or grouped summary

`次回注視点` must select at most two items from `watchpoint_candidates`.

The report must use compact heading levels (`###`, `####`, `#####`) and blank lines between major sections/subsections so the rendered Markdown remains readable.

Body text must start a new source line after each Japanese full stop (`。`) so sentences are easy to scan.

For sector-level prose, the final report must write sector names instead of ETF labels. For example, write `Financials`, not `XLF Financials`, and `Energy`, not `XLE Energy`.

## 9. Terminology

These terms are implementation/domain labels and should not be over-translated:

- `21EMA High`
- `21EMA Low`
- `21EMA Cloud`
- `21EMA POS`
- `Risk-On Ratio`
- `Safe Haven`
- `Profit-taking/Exit Watch`

## 10. Skill Location

The report-writing skill is located at:

```text
.agents/skills/market-report-writer/SKILL.md
```

The skill's input should be whichever form is easiest for the AI to write from. Operationally, Markdown is the primary prompt input and JSON remains the canonical persisted data.
