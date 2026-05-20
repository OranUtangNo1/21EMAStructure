# Final Report Template

Use this exact heading structure for the final Japanese Markdown report.

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

## Writing Checklist

- Use compact heading levels exactly as shown (`###`, `####`, `#####`) so rendered reports do not look oversized.
- Leave a blank line between major sections and between subsections for human readability.
- Start a new source line after every Japanese full stop (`。`); do not place multiple Japanese sentences on one line.
- For sector-level prose, write sector names instead of ETF labels: `Financials`, not `XLF Financials`; `Energy`, not `XLE Energy`.
- `今日の結論` explains the screening and candidate-confirmation context, not a neutral field recap.
- `投資優先度` uses the document's recommendation inputs and does not become position sizing or trade execution advice.
- `状態変化` uses `recent_transitions` and `trajectory` before point-in-time labels.
- `詳細確認` respects each section's `significance`.
- `次回注視点` uses at most two items and both are copied from `watchpoint_candidates`.
- The report does not add external causes, events, or market facts outside the input document.
