# Final Report Template

Use this exact heading structure for ReportSkill-1 Japanese Markdown reports.

```markdown
### 日次マーケットレポート
- 対象日: YYYY-MM-DD
- 生成時刻: YYYY-MM-DDTHH:MM:SS
- 入力 Market Document: data_runs/market_documents/YYYYMMDD.md
- 使用スキル: ReportSkill-1


#### 1. 今日の投資・行動方針（必読）
##### 市場の一行診断

##### 今日の行動モード
##### 注視すべき変化


#### 2. 今日の確認順序（必読）

#### 3. 本日の重点確認候補
##### 優先度 High

##### 優先度 Medium

##### 優先度 Low / Watch


#### 4. EntrySignal 確認時の見方


#### 5. 市場状態の詳細

##### Breadth と参加率
##### ボラティリティと Safe Haven

##### セクターと 21EMA POS

##### 業種リーダーシップ

##### ファクターとスタイル

##### Risk-On Ratio


#### 6. 次回注視点
```

## Writing Checklist

- Use compact heading levels exactly as shown (`###`, `####`, `#####`) so rendered reports do not look oversized.
- Leave a blank line between major sections and between subsections for human readability.
- Start a new source line after every Japanese full stop (`。`); do not place multiple Japanese sentences on one line.
- `今日の投資・行動方針（必読）` explains how market changes affect screening and candidate review.
- `今日の確認順序（必読）` gives 3 to 5 ordered review steps and stays inside report guidance.
- `本日の重点確認候補` writes industry/sector candidate groups or conditions, not invented symbols.
- `EntrySignal 確認時の見方` explains interpretation only and must not claim system logic changed.
- If `industry_leadership` is present, prioritize industry groups before broad sector-only prose.
- `業種リーダーシップ` summarizes top, 52W HIGH, accelerating, sustained-leadership, and weak industry groups from the market document.
- `市場状態の詳細` respects each section's `significance`.
- `次回注視点` uses at most two items and both are copied from `watchpoint_candidates`.
- Do not add external causes, events, or market facts outside the input document.
- Do not add execution, position sizing, stop-loss, take-profit, or exit-management instructions.
- Before finishing, reopen the saved report as UTF-8 and confirm all headings and metadata labels are readable Japanese, not mojibake.
