# Final Report Template

Use this exact heading structure for ReportSkill-1 Japanese Markdown reports.
This template matches ReportSkill-1 v1.2 (swing market posture, change -> interpretation -> action section, enumerated readouts).

```markdown
### 日次マーケットレポート
- 対象日: YYYY-MM-DD
- 生成時刻: YYYY-MM-DDTHH:MM:SS
- 入力 Market Document: data_runs/market_documents/YYYYMMDD.md
- 使用スキル: ReportSkill-1


#### 1. 今日の投資・行動方針（必読）
##### 市場の一行診断

##### 今日の行動モード

##### 現在の市場認識

- ロング保有の許容度:
- 新規エントリー確認の積極度:
- 利確・警戒確認の優先度:
- リスク管理ルールの厳格度:
- EntrySignal 確認時の厳格度:


#### 2. 指標の変化と投資行動への含意（必読）

<!--
ここは「水準の再掲」ではなく「変化の解釈」を書く本体セクション。
選別閾値を超えた変化だけを 3〜6 件、次の3行ブロックで列挙する。
散文で繋がず、必ず箇条書きにする。

- 変化: <指標名> <現値>（1W <±x>、1M <±x>、state遷移があれば明記）
  - 解釈: この変化が示す市場の方向（水準・変化・持続性のどれに基づくか）
  - 行動: スクリーニング / 候補確認 / EntrySignal解釈をどう変えるか（執行指示は書かない）
-->


#### 3. 今日の確認順序（必読）


#### 4. 本日の重点確認候補
##### 優先度 High

##### 優先度 Medium

##### 優先度 Low / Watch


#### 5. EntrySignal 確認時の見方


#### 6. 市場状態の詳細

##### Breadth と参加率
##### ボラティリティと Safe Haven

##### セクターと 21EMA POS

##### 業種リーダーシップ

##### ファクターとスタイル

##### Risk-On Ratio


#### 7. 次回注視点
```

## Section Roles

- 散文で書くのは `1. 市場の一行診断` `1. 今日の行動モード` `2. の各 解釈/行動 行` `5. EntrySignal 確認時の見方` のみ。
- それ以外（`2. の変化見出し` `4. 候補群` `6. の各数値ブロック`）は箇条書きで列挙する。
- `1. 現在の市場認識` は `executive_context.swing_market_posture` がある場合に必ず使い、ロング保有・新規確認・利確警戒・リスク管理・EntrySignal解釈を箇条書きで書く。
- `2. 指標の変化と投資行動への含意` がレポートの中核。水準の再掲は `6. 市場状態の詳細` に置き、`2.` には閾値を超えた「変化」だけを載せて重複させない。

## Writing Checklist

- Use compact heading levels exactly as shown (`###`, `####`, `#####`) so rendered reports do not look oversized.
- Leave a blank line between major sections and between subsections for human readability.
- **Enumerate listable facts.** Breadth/participation numbers, volatility/Safe Haven numbers, industry-leadership groups, factor/style pairs, and candidate groups are bullet lists, not chains of `〜です。` sentences.
- **Start a new source line after every Japanese full stop (`。`) only inside prose paragraphs** (一行診断・今日の行動モード・各 解釈/行動 行・EntrySignal 確認時の見方). Do not apply this rule to bullet-list items.
- `今日の投資・行動方針（必読）` explains how market changes affect screening and candidate review, and gives the daily action mode.
- `現在の市場認識` must translate `swing_market_posture` into report-level recognition only. Do not write trade execution, position sizing, stop-loss placement, or exit-management instructions.
- `指標の変化と投資行動への含意（必読）` lists 3 to 6 change blocks, each with the three lines 変化 / 解釈 / 行動.
  - Only include a change that crosses a selection threshold: Market Score label change or score 1W ±3 / 1M ±5; breadth・participation 1W ±10pt; `pct_2w_high` 1W ±20pt; Risk-On Ratio state transition or ABOVE MA COUNT 0<->3; VIX ±2 or vix_score / safe_haven_score 1M ±15; sector/industry RANK DELTA 1W/1M ±3; style-pair ABOVE MA COUNT 0<->3.
  - Read each indicator on 水準 (level) / 変化 (delta) / 持続性 (persistence) and state which axis a conclusion rests on.
  - When change and level disagree (e.g. RANK DELTA up but REL 1M still negative), state the contradiction in one line before the action, and treat the area as `改善中・確認待ち`.
  - Every cited delta or transition must actually appear in the market document; never fabricate a delta.
- `今日の確認順序（必読）` gives 3 to 5 ordered review steps and stays inside report guidance.
- `本日の重点確認候補` writes industry/sector candidate groups or conditions as one bullet per line, not invented symbols. When per-group metrics exist (RS, 1W, 1M, RS MTH%, 52W HIGH, tag), keep them as compact fields on the same line.
- `EntrySignal 確認時の見方` explains interpretation only and must not claim system logic changed.
- If `industry_leadership` is present, prioritize industry groups before broad sector-only prose.
- `業種リーダーシップ` summarizes top, 52W HIGH, accelerating, sustained-leadership, and weak industry groups from the market document, with one group per line.
- `市場状態の詳細` respects each section's `significance` and presents levels as bullet lists.
- `次回注視点` uses at most two items and both are copied from `watchpoint_candidates`.
- Do not add external causes, events, or market facts outside the input document.
- Do not add execution, position sizing, stop-loss, take-profit, or exit-management instructions.
- Before finishing, reopen the saved report as UTF-8 and confirm all headings and metadata labels are readable Japanese, not mojibake, and that section 2 exists with the 変化 / 解釈 / 行動 structure.
