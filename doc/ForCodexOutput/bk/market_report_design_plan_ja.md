# Market Report Design Plan

## 1. 最重要目的

日次の Market Condition 出力をもとに、投資判断の助けとなる市場情報を提示する。

この機能が答えるべき問いは次の通り。

- 現在の市場は risk-on / risk-off のどちらに傾いているか
- セクター/業種の資金移動はどこへ向かっているか
- growth / value、large / small、momentum / defensive のどちらが優勢か
- 市場状態は改善、悪化、継続、反転兆候のどれか
- Watchlist と Entry Signal をどの市場文脈で読むべきか

この機能は売買執行、ポジションサイズ、既存ポジション管理、利確/損切り判断を直接指示しない。OraTek の active scope に合わせ、screening と entry evaluation を補助する市場文脈レポートとして実装する。

## 2. 基本方針

Report v0 は、判断ロジックをルールベースで実装する。LLM を使う場合でも、LLM は文章化だけを担当し、market regime、risk posture、sector/style rotation、contradiction detection は構造化データから決定する。

理由:

- 同じ入力から同じ判定を再生成できるようにする
- evidence は JSON に保持し、Markdown には原則出さない
- hallucination による投資判断ノイズを避ける
- テストで回帰検証できるようにする

必須原則:

- 入力 JSON に存在するフィールドのみを分析対象にする
- 存在しない値を推測しない
- すべての主要判定に具体的な数値根拠を持たせる
- 根拠は内部データとして保持するが、ユーザー向け Markdown は助言と判断に集中する
- 水準と変化方向を両方見る
- 矛盾するシグナルは統合して消さず、contradiction として明示する
- `component_scores` と raw summary values を区別する
- active scope 外の trade management 提案を出さない

## 3. 現在の入力

主な入力:

- `data_runs/market_summary/YYYYMMDD.json`
- `MarketConditionResult`
- `config/default/market.yaml`

既存 `market_summary` で利用できる情報:

- `score`, `label`
- `score_1d_ago`, `score_1w_ago`, `score_1m_ago`, `score_3m_ago`
- `label_1d_ago`, `label_1w_ago`, `label_1m_ago`, `label_3m_ago`
- `component_scores`
- `breadth_summary`
- `participation_summary`
- `metric_deltas`
- `performance_overview`
- `high_vix_summary`
- `risk_on_ratio_summary`
- `vix_close`
- `market_snapshot`
- `leadership_snapshot`
- `external_snapshot`
- `factors_vs_sp500`

実装上の参照先:

- `src/dashboard/market.py`
- `src/pipeline.py`
- `src/data/store.py`
- `config/default/market.yaml`
- `doc/SystemDocs/Specifications/05_DASHBOARD_UI_SPEC.md`
- `doc/SystemDocs/Specifications/06_MODULE_AND_INTERFACE_SPEC.md`

## 4. 出力成果物

### 4.1 構造化 JSON

保存先候補:

- `data_runs/market_reports/YYYYMMDD.json`

目的:

- UI 表示
- 回帰テスト
- 後続の AI 文章化
- evidence の永続化

JSON は少なくとも次を含む。

```json
{
  "trade_date": "YYYY-MM-DD",
  "generated_at": "ISO-8601",
  "source_summary_path": "data_runs/market_summary/YYYYMMDD.json",
  "overall": {
    "label": "Positive",
    "direction": "improving",
    "confidence": "Medium",
    "summary_points": []
  },
  "sections": [],
  "contradictions": [],
  "missing_inputs": [],
  "data_appendix": []
}
```

### 4.2 Markdown レポート

保存先候補:

- `data_runs/market_reports/YYYYMMDD.md`

目的:

- 人間が読む日次レポート
- Market Dashboard への埋め込み
- 過去レポートの確認

Markdown は 10 セクション固定を必須にしない。UI では topic cards と summary に分解できるよう、JSON を主、Markdown を派生出力として扱う。

Markdown はユーザーが読む投資判断支援レポートであり、根拠データの一覧や source field は表示しない。根拠は JSON の `sections[].evidence`, `contradictions[].evidence`, `data_appendix` に保持する。

## 5. Report v0 のセクション

### 5.1 Executive Summary

出力:

- 今日の市場状態を 3-5 文で要約
- 重要な変化を最大 3 点に絞る
- Watchlist / Entry Signal を読むときの市場文脈を示す

推定方法:

- Market Score の現在値と 1D/1W/1M/3M 差分
- breadth、participation、VIX、safe haven、risk-on ratio の一致度
- 主要 ETF snapshot の 21EMA position 分布
- contradictions の有無

### 5.2 Market Regime

出力:

- regime label
- direction: improving / deteriorating / stable / rebound_watch / exhaustion_watch
- confidence
- evidence

推定方法:

- `label` は現行 config の threshold に従う
- prompt 案の固定閾値は採用しない
- score delta の 1D/1W/1M を方向判定に使う
- label history で regime transition を検出する
- breadth と participation が同方向なら confidence を上げる
- VIX / safe haven / risk-on ratio が逆方向なら confidence を下げる

必要パラメータ:

- `score_improving_1w`
- `score_deteriorating_1w`
- `score_improving_1m`
- `score_deteriorating_1m`
- confidence scoring weights

### 5.3 Breadth And Participation

出力:

- breadth state
- participation state
- broadening / narrowing
- narrow leadership warning
- raw breadth と transformed score の差

推定方法:

- `breadth_summary` を raw participation として使う
- `component_scores` は Market Score に反映される transformed score として別扱いにする
- SMA10 / SMA20 は短期参加
- SMA50 / SMA200 は中長期参加
- `pct_sma20_gt_sma50` と `pct_sma50_gt_sma200` は trend structure
- `participation_summary` の `pct_positive_*` は期間別 momentum
- `metric_deltas` の 1D/1W/1M で改善/悪化を判定する
- `S2W HIGH %` は新高値の広がりとして扱う

条件付きパラメータ:

- breadth 70% / 50% 区分は仮値として検証する
- S2W High 30% / 15% 区分は仮値として検証する

### 5.4 Volatility And Safe Haven

出力:

- volatility state
- VIX direction
- safe-haven state
- VIX と safe haven の整合性

推定方法:

- `vix_close`
- `component_scores.vix_score`
- `high_vix_summary.SAFE HAVEN %`
- `component_scores.safe_haven_score`
- `metric_deltas.VIX`
- `metric_deltas.safe_haven_score`

条件付きパラメータ:

- VIX 12 / 17 / 25 / 30 の区分は仮値として検証する
- 固定値だけでなく、将来は percentile threshold も検討する

### 5.5 Risk-On Ratio

出力:

- risk-on ratio state
- short-term / medium-term / long-term relative momentum
- high distance warning
- MA confirmation

推定方法:

- `risk_on_ratio_summary.RATIO`
- `REL 1W %`, `REL 1M %`, `REL 3M %`
- `HIGH DIST %`
- `ABOVE MA COUNT / MA COUNT`
- `metric_deltas.risk_on:*`

判定方針:

- REL 1W / 1M / 3M が揃ってプラスなら risk-on confirmation
- HIGH DIST が大きくマイナスなら構造的な弱さ
- ABOVE MA COUNT が MA COUNT に近いほど構造的 risk-on
- Market Score と矛盾する場合は contradiction として出す

### 5.6 Sector And Leadership Landscape

出力:

- Core ETF の 21EMA position 分布
- Leadership ETF の 21EMA position 分布
- External ETF の 21EMA position 分布
- 当日の leader / laggard
- leadership quality comment
- external risk comment

推定方法:

- `market_snapshot`
- `leadership_snapshot`
- `external_snapshot`
- `21EMA POS` の count
- `DAY %` の ranking
- `VOL vs 50D %` の確認

採用条件:

- `DAY %` ranking は当日確認に使う
- sector rotation の主判定には使わない
- `VOL vs 50D %` は確認材料として使う
- 出来高だけで機関投資家参加を断定しない

不足:

- セクター別 1W/1M/3M relative return
- セクター順位の履歴差分
- defensive / cyclical / growth sector basket

### 5.7 Sector Rotation

出力:

- leading sectors
- improving sectors
- weakening sectors
- defensive leadership warning
- rotation narrative

v0 方針:

- 既存 summary だけでは本格判定は弱い
- v0 では snapshot-based observation として出す
- Phase 3 で enriched sector metrics を追加して本格判定に昇格する

必要追加データ:

- sector relative return vs SPY: 1W / 1M / 3M
- sector rank delta: 1D / 1W / 1M
- sector trend state
- sector volume confirmation
- defensive/cyclical basket spread

### 5.8 Factor And Style Rotation

出力:

- factor leadership
- factor momentum classification
- growth/value tilt
- momentum/defensive tilt
- style implication for screening

推定方法:

- `factors_vs_sp500`
- `REL 1W %` と `REL 1M %` の符号分類

分類:

- 1W+ / 1M+: accelerating
- 1W+ / 1M-: rebound_watch
- 1W- / 1M+: decelerating
- 1W- / 1M-: lagging

Phase 3 追加候補:

- VUG/VTV ratio
- MTUM/SPY ratio
- VB/MGC ratio
- VO/MGC ratio
- VYM/SPY ratio
- ratio MA state

### 5.9 Cross-Section Diagnosis

出力:

- contradictions
- risk flags
- confidence adjustment

検出する矛盾:

- Market Score は強いが breadth が狭い
- VIX は低いが safe haven が risk-off
- participation 1W は強いが S2W High が弱い
- risk-on ratio が弱いのに Market Score が強い
- factor momentum が強いのに leadership ETF が弱い
- core は強いが leadership / external が弱い

実装方針:

- 矛盾は Markdown 文章だけでなく JSON の `contradictions` に保存する
- 各 contradiction は evidence を持つ

### 5.10 Actionable Implications

出力:

- Watchlist posture
- Entry Signal posture
- 優先して確認する候補タイプ
- 慎重に扱う候補タイプ
- 次回注視する指標

制約:

- 新規エントリーすべき/停止すべきと断定しない
- ポジションサイズを指定しない
- トレーリングストップや既存ポジション管理を提案しない
- Market Dashboard と Entry Signal の判定を上書きしない

許容する表現:

- 「breakout 系候補は confirmation を強めに確認する」
- 「risk-on ratio が弱いため、小型 growth 候補は追加根拠を要求する」
- 「defensive leadership が強い場合、攻撃的 setup の優先度は下げる」
- 「次回は SMA20 breadth と VIX delta を注視する」

ユーザーが最終的に必要としているのは、直接的な期待値の高い投資を実現するための助言である。そのため、`Recommendation Layer` を追加し、セクター/テーマ/ファクター単位の優先・回避・利確/exit 検討候補を出す。これは個別銘柄の売買執行やポジションサイズ指定ではなく、screening / entry evaluation の優先順位付けとして扱う。

### 5.12 Recommendation Layer

出力:

- overweight candidates: 優先して投資候補を探すセクター/テーマ/ファクター
- underweight / avoid candidates: 新規候補の優先度を下げるセクター/テーマ/ファクター
- profit-taking watch: 利確または exit 検討に回すべきセクター/テーマ/ファクター
- entry-quality filter: どの setup に追加確認を要求するか
- risk budget posture: 攻撃的/通常/慎重の運用姿勢

実装条件:

- sector relative return 1W/1M/3M と rank delta がある
- style pair ratios がある
- defensive/cyclical basket spread がある
- sector leadership が単日 `DAY %` ではなく複数期間で確認できる
- recommendation ごとに内部 evidence を保持する
- Markdown には根拠一覧ではなく、助言と理由を短く出す

注意:

- 個別銘柄の売買執行やポジションサイズ指定とは分離する
- exit / profit-taking はまずセクター/テーマ単位の watch として実装し、個別ポジション管理へは直結させない

### 5.11 Data Appendix

出力:

- 本文で引用した主要数値
- source field
- raw value
- transformed score value
- delta

目的:

- レポートの根拠を再確認できるようにする
- Markdown 内の数値引用漏れを防ぐ
- 後からテストで検証できるようにする

## 6. 構造化モデル案

### 6.1 MarketReportResult

```python
@dataclass(slots=True)
class MarketReportResult:
    trade_date: pd.Timestamp | None
    generated_at: str
    source_summary_path: str | None
    overall_label: str
    overall_direction: str
    confidence: str
    sections: list[MarketReportSection]
    contradictions: list[MarketReportContradiction]
    missing_inputs: list[MarketReportMissingInput]
    data_appendix: list[MarketReportEvidence]
```

### 6.2 MarketReportSection

```python
@dataclass(slots=True)
class MarketReportSection:
    key: str
    title: str
    label: str
    direction: str | None
    confidence: str
    summary: str
    evidence: list[MarketReportEvidence]
    warnings: list[str]
```

### 6.3 MarketReportEvidence

```python
@dataclass(slots=True)
class MarketReportEvidence:
    metric: str
    source_field: str
    value: float | str | None
    raw_value: float | None
    score_value: float | None
    delta_1d: float | None
    delta_1w: float | None
    delta_1m: float | None
    note: str | None
```

### 6.4 MarketReportContradiction

```python
@dataclass(slots=True)
class MarketReportContradiction:
    key: str
    severity: str
    summary: str
    evidence: list[MarketReportEvidence]
```

## 7. パラメータ案

追加先候補:

- `config/default/market.yaml` の `market_report:` section

初期案:

```yaml
market_report:
  output:
    write_json: true
    write_markdown: true
  horizons:
    short_days: 5
    medium_days: 21
    long_days: 63
  regime:
    score_improving_1w: 3.0
    score_deteriorating_1w: -3.0
    score_improving_1m: 5.0
    score_deteriorating_1m: -5.0
  breadth:
    strong_level: 70.0
    weak_level: 50.0
    s2w_high_active_level: 30.0
    s2w_high_weak_level: 15.0
  volatility:
    vix_low_level: 12.0
    vix_neutral_level: 17.0
    vix_elevated_level: 25.0
    vix_stress_level: 30.0
  risk:
    safe_haven_positive_threshold: 2.0
    safe_haven_negative_threshold: -2.0
    high_distance_warning_pct: -5.0
  confidence:
    minimum_required_metric_coverage: 0.8
    disagreement_penalty: 0.2
```

これらは仮値であり、過去データで再生成してから調整する。

## 8. 不足データ

v0 で明示的に missing input として扱う候補:

- sector relative returns: 1W / 1M / 3M
- sector rank deltas: 1D / 1W / 1M
- defensive/cyclical basket spread
- growth/value ratio state
- small/large ratio state
- momentum/market ratio state
- credit proxy: HYG/IEF or JNK/IEF
- rates proxy: TLT/IEF/SHY relationship
- report-level data coverage score

追加判断:

- credit proxy は v0 には入れない
- Phase 3 で追加検討する
- 入力シンボルを増やす場合は data reliability と fetch status の影響を先に確認する

## 9. エビデンス調査計画

### 9.1 Factor / Style

初期参照:

- Kenneth French Data Library: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
- Fama/French factor descriptions: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/details_main.html

確認すること:

- ETF proxy と academic factor の違い
- short-term style rotation と long-term factor premium を混同しない注意書き
- VUG/VTV、VB/MGC、MTUM/SPY を proxy とする妥当性

### 9.2 VIX

初期参照:

- Cboe VIX Methodology: https://cdn.cboe.com/api/global/us_indices/governance/VIX_Methodology.pdf
- Cboe VIX Products: https://www.cboe.com/tradable_products/vix/

確認すること:

- VIX level と VIX change の使い分け
- VIX 単独判定の限界
- 固定 threshold と percentile threshold の比較

### 9.3 Sector

初期参照:

- S&P U.S. Indices Methodology: https://www.spglobal.com/spdji/en/methodology/article/sp-us-indices-methodology/
- S&P DJI methodology library: https://www.spglobal.com/spdji/en/governance/methodologies/

確認すること:

- GICS sector grouping の公式性
- ETF proxy の限界
- defensive / cyclical / growth sector basket の定義

### 9.4 Risk-On / Risk-Off

初期参照:

- Risk-On Risk-Off: A Multifaceted Approach to Measuring Global Investor Risk Aversion: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4637262

確認すること:

- VIX、equity/bond spread、credit spread を組み合わせる理由
- v0 で使う proxy と Phase 3 に送る proxy の線引き

## 10. 実装フェーズ

### Phase 1: Existing Summary Only Report

目的:

- 既存 `market_summary` だけで deterministic report を生成する

実装:

- 新規 module: `src/dashboard/market_report.py` または `src/reporting/market_report.py`
- dataclass 定義
- JSON serializer
- Markdown renderer
- existing summary loader
- evidence builder
- contradiction detector

出力:

- `data_runs/market_reports/YYYYMMDD.json`
- `data_runs/market_reports/YYYYMMDD.md`

テスト:

- sample summary から section が生成される
- evidence に `source_field` が入る
- missing field は missing_inputs に入る
- unknown field は自動推測しない
- trade management 文言を出さない

### Phase 2: Pipeline Integration

目的:

- 日次 run artifact として market report を保存する

実装:

- `src/data/store.py` に保存先を追加
- `src/pipeline.py` の run artifact 保存時に report を生成
- same-day saved-run restore で既存 report を読めるようにする

テスト:

- report JSON/Markdown が date key で保存される
- saved run restore で report path が復元される
- data health warning が report に反映される

### Phase 3: Enriched Metrics

目的:

- sector rotation と style rotation を本格判定に昇格する

実装:

- sector relative return vs SPY
- sector rank delta
- snapshot position counts
- style pair ratios
- factor momentum classification
- SPY/RSP and QQQ/QQQE breadth proxy
- defensive/cyclical basket summary

テスト:

- sector leadership が 1D noise だけで決まらない
- style pair ratio が missing の場合は missing_inputs になる
- factor momentum classification が符号で正しく分類される

### Phase 4: UI Integration

目的:

- Market Dashboard で日次レポートを読めるようにする

実装:

- Market Dashboard に `Daily Report` section を追加
- summary cards
- contradictions panel
- evidence appendix expander
- missing inputs warning

UI 方針:

- 10 セクションの長文をそのまま表示しない
- summary, risk flags, implications, appendix に分ける
- source fields を確認できるようにする

### Phase 5: Validation And Calibration

目的:

- 仮閾値を過去データで確認し、過敏/鈍感な判定を修正する

作業:

- `data_runs/market_summary/*.json` で過去 report を再生成
- Market Regime, Risk Posture, Contradictions の日次推移を確認
- VIX / breadth / S2W High の閾値を調整
- 過去のレポートを比較して narrative が過度に変化しないか確認

### Phase 6: Documentation Sync

目的:

- 実装後に SystemDocs を最小範囲で同期する

更新候補:

- `doc/SystemDocs/Specifications/02_DATA_MODEL_AND_SOURCES.md`
- `doc/SystemDocs/Specifications/05_DASHBOARD_UI_SPEC.md`
- `doc/SystemDocs/Specifications/06_MODULE_AND_INTERFACE_SPEC.md`
- `doc/SystemDocs/Specifications/08_PARAMETER_CATALOG.md`

## 11. 採用しない prompt 要素

`doc/ForUsersOnly/market_report_prompt.md` から、次は採用しない。

- 「ヘッジファンドのリスク委員会」向けという role
- 既存ポジション管理、ポジションサイズ、トレーリングストップ、利確判断
- prompt 内の固定 Market Regime threshold
- 未知フィールドをフィールド名から推測して自動分析する契約
- 入力が増えた場合に自動でセクションを増やす挙動
- Market Score から直接的な売買判断へつなげる表現

理由:

- 現行 config の threshold と一致しない
- active scope から外れる
- 再現性と evidence-first 方針を弱める
- UI とテストの安定性を損なう

## 12. 受け入れ条件

Report v0 は次を満たすこと。

- 最重要目的に直接答えている
- すべての主要判断に evidence がある
- evidence に `source_field` がある
- raw value と transformed score を混同しない
- missing input が隠れない
- contradiction が明示される
- 同じ入力から同じ JSON が再生成できる
- Markdown は JSON から派生生成される
- active scope 外の trade management 提案を出さない
- Market Dashboard と Entry Signal の判定を上書きしない
