# マーケットレポート生成 Skill 設計書

作成日: 2026-05-18

この文書は、`market_document.v1` を入力として、人間が読む日次マーケットレポートを生成する skill の設計書です。システム側は完成レポートを書かず、AI入力用 market document を出力します。skill はその market document だけを根拠として最終レポートを書きます。

## 1. Skill の目的

skill の目的は、market document に含まれる数値・ラベル・trajectory・significance・watchpoint_candidates を、人間が投資判断の文脈として読める日次レポートへ変換することです。

skill は以下を行います。

- market document の重要情報を優先順位づけする
- executive summary を行動文脈として書く
- significance に応じて記述量を調整する
- watchpoint_candidates から次回注視点を選ぶ
- evidence に基づく判断文だけを書く

skill は以下を行いません。

- market document にない外部要因を補完する
- ニュース、経済指標、決算、原油、金利、為替、地政学要因を推測して書く
- 個別銘柄の売買実行指示を書く
- ポジションサイズや損切り管理を書く
- watchpoint_candidates にない次回注視点を作る

## 2. 入力

入力は `data_runs/market_reports/YYYYMMDD.md` または同 JSON です。

必須条件:

- `schema_version` が `market_document.v1`
- `document_type` が `ai_market_report_input`
- `analysis_boundary` が存在する
- `report_generation_contract.final_report_owner` が `skill`

これらが欠けている場合、skill は「入力ドキュメントが不足している」と明示し、外部知識で補完しません。

## 3. 出力

出力は日本語 Markdown の日次マーケットレポートです。

推奨ファイル名:

```text
data_runs/market_reports/YYYYMMDD_final.md
```

現時点ではファイル保存の自動化は別フェーズです。skill はまず本文生成責務を持ちます。

## 4. 最終レポート構成

### 4.1 第1層: 必読

第1層は毎日必ず出力します。

```markdown
# 日次マーケットレポート

## 今日の結論

## 投資優先度
```

`今日の結論` には以下を含めます。

- 市場の一行診断
- 今日の行動文脈 2〜3文
- 注視すべき変化 最大2点

`投資優先度` には `recommendation_inputs.facts_for_ai` を使います。

記述例:

```markdown
Market Score は Positive だが、Risk-On Ratio は risk_off_warning。新規候補は通常より確認基準を厳しくし、優先候補は relative strength が維持されているセクターに絞る。
```

### 4.2 第2層: 状態変化

```markdown
## 状態変化
```

対象:

- `market_regime`
- `risk_on_ratio`
- `recent_transitions`

ルール:

- `recent_transitions` がある場合は優先して説明する
- `trajectory.pattern` を使って、単なる delta ではなく変化の経路を書く
- `significance=low` の場合は「大きな状態変化なし」と短くまとめる

### 4.3 第3層: 詳細確認

```markdown
## 詳細確認
```

対象:

- `breadth_participation`
- `volatility_safe_haven`
- `sector_rotation`
- `factor_style`

ルール:

- `significance=high`: 3〜5文
- `significance=medium`: 2〜3文
- `significance=low`: 1文以内
- 全セクションが `low` なら「主要詳細指標に大きな変化なし」とまとめてよい

### 4.4 次回注視点

```markdown
## 次回注視点
```

`watchpoint_candidates` から最大2点を選びます。候補外の注視点は禁止です。

## 5. エビデンスルール

すべての判断文は、market document 内の具体的な section、fact、metric、trajectory、transition、watchpoint に紐づけ可能でなければなりません。

禁止:

- 「原油価格の上昇を受けて」
- 「FOMCを控えて」
- 「決算期待から」
- 「金利低下を背景に」
- 「地政学リスクで」

これらは market document に明示されていない限り使用禁止です。

許可:

- `Risk-On Ratio が全MAを下回っている`
- `SMA20 breadth が50%を下回っている`
- `21EMA POS の above count が低下した`
- `REL 1W がプラスに転じた`

## 6. トークン効率ルール

skill は、全 section を同じ粒度で書いてはいけません。

| significance | 出力量 |
| --- | --- |
| `high` | 通常段落。重要変化として扱う。 |
| `medium` | 変化点だけ短く記述。 |
| `low` | 1文以内。複数 low section はまとめてよい。 |

第1層は毎日必ず書きます。第2層・第3層は significance に従って圧縮します。

## 7. 文体ルール

- 日本語で書く
- 断定しすぎず、market document の範囲で書く
- `21EMA High`、`21EMA Low`、`21EMA Cloud`、`21EMA POS` は固有名詞として維持する
- `Risk-On Ratio`、`Safe Haven`、`Profit-taking/Exit Watch` は必要ならそのまま使う
- 「助言あり」「スクリーニング文脈」などの抽象ラベルで終わらせない
- 読み手が「今日どう候補確認を変えるべきか」を理解できる文章にする

## 8. レポート生成手順

1. `schema_version` と `document_type` を確認する
2. `analysis_boundary` と `report_generation_contract` を読む
3. `executive_context` から一行診断と行動文脈を作る
4. `recommendation_inputs` を使って投資優先度を書く
5. `recent_transitions` と `trajectory` から状態変化を書く
6. `significance` に従って詳細 section を圧縮または展開する
7. `watchpoint_candidates` から最大2点を次回注視点として出す
8. 外部知識が混入していないか自己チェックする

## 9. 自己チェック

出力前に以下を確認します。

- すべての判断文が market document 内の情報に紐づく
- watchpoint_candidates 外の注視点を書いていない
- 外部イベント、ニュース、マクロ要因を補完していない
- `significance=low` の section を長く書いていない
- 個別売買、ポジションサイズ、損切り管理を書いていない

## 10. 将来の実装メモ

実際の Codex skill 化では、`SKILL.md` に本設計のルールを移し、入力 market document の読み取り、最終 Markdown 生成、保存先決定を workflow として定義する。
