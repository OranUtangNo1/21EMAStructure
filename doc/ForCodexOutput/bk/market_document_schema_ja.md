# AI入力用マーケットドキュメント Schema

作成日: 2026-05-18

この文書は、日次マーケットレポートをAI/skillで生成するために、システムが出力する中間ドキュメントの schema を定義します。システムは完成レポートを書かず、根拠付きの market document を出力します。完成レポートは skill がこの market document を入力として生成します。

## 1. 目的

market document の目的は、AI が外部知識を補完せずに、人間が読める品質のマーケットレポートを書けるだけの情報を提供することです。

そのため、market document には以下を含めます。

- 当日の市場状態
- 直近変化の経路を要約した trajectory
- 状態遷移を示す recent_transitions
- 記述量を制御する significance
- 次回注視点を限定する watchpoint_candidates
- AI が言及してよい範囲を制限する analysis_boundary
- 最終レポート作成ルールを示す report_generation_contract

## 2. 出力ファイル

| ファイル | 役割 |
| --- | --- |
| `data_runs/market_reports/YYYYMMDD.json` | 正規の構造化 market document。 |
| `data_runs/market_reports/YYYYMMDD.md` | 同じ内容の Markdown 版。AI/skill に渡す入力用であり、完成レポートではない。 |

## 3. Top-level Schema

```yaml
schema_version: "market_document.v1"
document_type: "ai_market_report_input"
trade_date: "YYYY-MM-DD"
generated_at: "ISO datetime"
source_summary_path: "data_runs/market_summary/YYYYMMDD.json"
executive_context: {}
sections: []
recent_transitions: []
watchpoint_candidates: []
analysis_boundary: {}
missing_inputs: []
data_appendix: []
report_generation_contract: {}
```

## 4. executive_context

`executive_context` は、skill が冒頭の行動文脈を書くための最小要約です。

```yaml
executive_context:
  market_label: "Positive"
  market_score: 66.04
  market_direction: "stable"
  confidence: "Medium"
  one_line_diagnosis: "Market Score 66.04 (Positive, stable)"
  action_context_facts:
    - "Market Score 66.04 is Positive and direction is stable."
    - "Risk-On Ratio posture is risk_off_warning."
    - "Breadth posture is mixed."
  notable_changes:
    - "Risk-On Ratio state changed from mixed to risk_off_warning."
  required_missing_inputs: []
```

## 5. section schema

各 section は、skill が本文を作るための根拠単位です。

```yaml
section:
  key: "risk_on_ratio"
  title: "Risk-On Ratio"
  label: "risk_off_warning"
  direction: "deteriorating"
  significance:
    level: "high"
    reason: "Risk-On Ratio MA confirmation changed materially."
  summary: "Small-growth risk appetite input..."
  trajectory: {}
  facts_for_ai:
    - "REL 1W=-0.8"
    - "ABOVE MA COUNT=0 / 3"
  warnings:
    - "Risk-On Ratio is not above every configured moving average."
  metrics: []
```

### 5.1 section.key

現在の section は以下です。

| key | 役割 |
| --- | --- |
| `market_regime` | Market Score、label、score trajectory。 |
| `recommendation_inputs` | セクター/スタイル優先度、慎重、Profit-taking/Exit Watch の入力。 |
| `risk_on_ratio` | IWO/IWN 等の Risk-On Ratio 状態。 |
| `breadth_participation` | SMA breadth、positive return、S2W High。 |
| `volatility_safe_haven` | VIX と Safe Haven Spread。 |
| `sector_rotation` | セクター relative strength と 21EMA POS 分布。 |
| `factor_style` | factor ETF と style pair。 |

### 5.2 significance

`significance` は、skill が記述量を調整するためのフラグです。

| level | 意味 | skill の扱い |
| --- | --- | --- |
| `high` | ラベル変更、大きな数値変化、重要な状態遷移あり。 | 通常の段落として記述。 |
| `medium` | 数値変化はあるがラベル変更なし。 | 変化した点だけ短く記述。 |
| `low` | 前日から大きな変化なし。 | 1文以内に圧縮、またはまとめて省略可。 |

### 5.3 trajectory

`trajectory` は、delta の量だけでは分からない変化の経路を要約します。

```yaml
trajectory:
  category: "regime"
  pattern: "sustained_decline"
  sample_count: 5
  streak: -4
  delta_1d: -1.2
  delta_1w: -4.8
  delta_1m: -7.1
  delta_3m: 2.3
  best_day_in_window: 0.4
  worst_day_in_window: -2.1
  explanation: "sustained_decline; path deltas=-0.8, -1.1, -0.6, -2.1"
```

`pattern` の代表値:

- `limited_history`
- `sustained_decline`
- `sustained_improvement`
- `reversal_attempt`
- `volatile_decline`
- `volatile_improvement`
- `flat`

## 6. metric schema

```yaml
metric:
  metric: "Risk-On REL 1M"
  source_field: "risk_on_ratio_summary.REL 1M %"
  value: -2.4
  raw_value: -2.4
  score_value: null
  delta_1d: -0.2
  delta_1w: -1.1
  delta_1m: 0.4
  note: "MA COUNT=3"
```

metric は最終レポートにそのまま全件出すためのものではありません。skill が判断文を根拠に紐づけるための内部証跡です。

## 7. recent_transitions

```yaml
recent_transitions:
  - date: "2026-05-18"
    category: "risk_on"
    event: "Risk-On Ratio state changed from mixed to risk_off_warning."
    significance: "high"
    source_fields:
      - "risk_on_ratio_summary.REL 1M %"
      - "risk_on_ratio_summary.HIGH DIST %"
```

skill は、変化の説明にこの配列を優先して使います。配列が空の場合、変化が不明または大きな状態遷移なしとして扱います。

## 8. watchpoint_candidates

```yaml
watchpoint_candidates:
  - metric: "risk_on_ratio_summary.REL 1W %"
    threshold: 0.0
    direction: "above"
    narrative: "Risk-On Ratio のREL 1Wが正に転じるか"
    reason: "current=-0.8"
    source_field: "risk_on_ratio_summary.REL 1W %"
```

skill は「次回注視点」をこの候補からのみ選びます。FOMC、雇用統計、決算、原油価格など、market document にない外部イベントを注視点として追加してはいけません。

## 9. analysis_boundary

```yaml
analysis_boundary:
  allowed_sources:
    - "本ドキュメント内の数値、ラベル、trajectory、significance"
    - "本ドキュメント内の facts_for_ai"
    - "本ドキュメント内の watchpoint_candidates"
  prohibited_sources:
    - "経済指標の発表スケジュール"
    - "個別企業の決算やニュース"
    - "原油価格、金利、為替など本ドキュメントに存在しない外部市場要因"
    - "地政学的イベント"
  sector_inference_limit: "セクターの含意は 21EMA POS、DAY%、relative strength、basket comparison の範囲に限定する。"
```

## 10. report_generation_contract

```yaml
report_generation_contract:
  final_report_owner: "skill"
  system_output_role: "AIが品質を満たす日次マーケットレポートを書くための根拠付き入力を生成する。"
  must_not_do:
    - "外部イベントやニュースを補完しない"
    - "個別銘柄の売買実行指示を書かない"
    - "ポジションサイズや損切り管理を書かない"
    - "watchpoint_candidates にない次回注視点を作らない"
  token_efficiency_rule: "significance=low の section は最終レポートで1文以内に圧縮してよい。"
```

## 11. 用語方針

- `21EMA High`、`21EMA Low`、`21EMA Cloud`、`21EMA POS` は固有概念としてそのまま使う。
- `Risk-On Ratio`、`Safe Haven`、`Profit-taking/Exit Watch` は必要に応じてそのまま使う。
- market document は日本語・英語が混在してよい。最終的な自然文の整形は skill が担当する。
