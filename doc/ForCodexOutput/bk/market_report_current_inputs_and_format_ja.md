# マーケットレポート改良検討用 現行仕様メモ

作成日: 2026-05-18

この文書は、現在の実装を前提に、マーケットレポートの改良検討で参照するための整理資料です。参照元は主に `src/dashboard/market.py`、`src/dashboard/market_report.py`、`src/data/store.py`、`config/default/market.yaml` です。

注意: この文書は、完成Markdownレポートをシステムが直接出力していた段階の検討メモを含みます。2026-05-18 の仕様変更後は、正規の出力仕様は [market_document_schema_ja.md](/C:/reository/21EMAStructure/doc/ForCodexOutput/market_document_schema_ja.md) と [market_report_skill_design_ja.md](/C:/reository/21EMAStructure/doc/ForCodexOutput/market_report_skill_design_ja.md) を優先します。

## 1. MarketCondition から取得可能な値一覧

レポート生成時の直接入力は、`MarketConditionResult` を `DataSnapshotStore._save_market_result()` が保存した `data_runs/market_summary/YYYYMMDD.json` です。以下はその保存形に含まれる主な値です。

### 1.1 レジーム・スコア

| 値 | 定義 |
| --- | --- |
| `trade_date` | ベンチマーク履歴の最新日。 |
| `score` | `component_weights` に従って計算した総合 Market Score。デフォルトでは ETF universe ベース。 |
| `label` | `score` から決まる市場ラベル。`Bullish >= 80`、`Positive >= 60`、`Neutral >= 40`、`Negative >= 20`、それ未満は `Bearish`。 |
| `score_1d_ago` / `score_1w_ago` / `score_1m_ago` / `score_3m_ago` | 1営業日前、5営業日前、21営業日前、63営業日前の Market Score。 |
| `label_1d_ago` / `label_1w_ago` / `label_1m_ago` / `label_3m_ago` | 過去スコアに対応する市場ラベル。 |
| `update_time` | MarketConditionResult の生成時刻。 |

`score` の計算対象は `market.calculation_mode` で切り替わります。

| mode | 定義 |
| --- | --- |
| `etf` | `market_condition_etf_universe` の ETF 群だけで Market Score を計算。現行デフォルト。 |
| `active_symbols` | アクティブ銘柄 universe だけで Market Score を計算。 |
| `blended` | ETF 群とアクティブ銘柄 universe を `etf_weight` / `active_symbols_weight` で加重平均。 |

### 1.2 `component_scores`

`component_scores` は、Market Score に投入するための変換後スコアです。raw breadth とは値が一致しない場合があります。50を超える raw 比率は `50 + ((raw - 50) / 50) * 30` で圧縮され、最大100に丸められます。

| 値 | 定義 | デフォルト重み |
| --- | --- | --- |
| `pct_above_sma20` | 対象 universe のうち、終値が SMA20 以上の比率をスコア化。 | 0.12 |
| `pct_above_sma50` | 終値が SMA50 以上の比率をスコア化。 | 0.14 |
| `pct_above_sma200` | 終値が SMA200 以上の比率をスコア化。 | 0.14 |
| `pct_sma50_gt_sma200` | SMA50 が SMA200 以上の比率をスコア化。 | 0.08 |
| `pct_positive_1m` | 21営業日リターンがプラスの比率をスコア化。 | 0.09 |
| `pct_positive_3m` | 63営業日リターンがプラスの比率をスコア化。 | 0.08 |
| `pct_2w_high` | 終値が過去10営業日の高値以上の比率をスコア化。 | 0.05 |
| `safe_haven_score` | `safe_haven_score = clamp(50 + SAFE HAVEN % * safe_haven_score_scale, 0, 100)`。 | 0.15 |
| `vix_score` | `vix_score = clamp(50 - (VIX - vix_neutral_level) * vix_score_slope, 0, 100)`。 | 0.15 |

### 1.3 `breadth_summary`

`breadth_summary` は raw 比率です。Market Score 用に変換される前の値です。

| 値 | 定義 |
| --- | --- |
| `pct_above_sma10` | 対象 universe のうち、終値が SMA10 以上の比率。 |
| `pct_above_sma20` | 終値が SMA20 以上の比率。 |
| `pct_above_sma50` | 終値が SMA50 以上の比率。 |
| `pct_above_sma200` | 終値が SMA200 以上の比率。 |
| `pct_sma20_gt_sma50` | SMA20 が SMA50 以上の比率。 |
| `pct_sma50_gt_sma200` | SMA50 が SMA200 以上の比率。 |

### 1.4 `participation_summary`

| 値 | 定義 |
| --- | --- |
| `pct_positive_1w` | 5営業日リターンがプラスの比率。 |
| `pct_positive_1m` | 21営業日リターンがプラスの比率。 |
| `pct_positive_3m` | 63営業日リターンがプラスの比率。 |
| `pct_positive_1y` | 252営業日リターンがプラスの比率。 |
| `pct_positive_ytd` | 年初来リターンがプラスの比率。 |

### 1.5 `metric_deltas`

`metric_deltas` は、主要 metric の現在値と過去値の差分です。キーは metric 名、内側のキーは `1D` / `1W` / `1M` です。

含まれ得る metric は以下です。

| 値 | 定義 |
| --- | --- |
| breadth / participation 系 | `pct_above_sma*`、`pct_positive_*`、`pct_2w_high` などの raw 値差分。 |
| `VIX` | VIX 終値の差分。 |
| `SAFE HAVEN %` | Safe Haven Spread の差分。 |
| `vix_score` | VIX 由来スコアの差分。 |
| `safe_haven_score` | Safe Haven 由来スコアの差分。 |
| `risk_on:*` | Risk-On Ratio 関連値の差分。例: `risk_on:REL 1M %`。 |

### 1.6 `performance_overview`

ベンチマーク履歴、通常は `SPY`、のリターンです。

| 値 | 定義 |
| --- | --- |
| `% YTD` | 年初来リターン。 |
| `% 1W` | 5営業日リターン。 |
| `% 1M` | 21営業日リターン。 |
| `% 1Y` | 252営業日リターン。 |

### 1.7 `high_vix_summary`

| 値 | 定義 |
| --- | --- |
| `S2W HIGH %` | 対象 universe のうち、終値が過去10営業日の高値以上の比率。 |
| `VIX` | `^VIX` の最新終値。 |
| `SAFE HAVEN %` | `safe_haven_risk_on_symbol` の20営業日リターンから `safe_haven_risk_off_symbol` の20営業日リターンを引いた値。デフォルトは `SPY - TLT`。 |

### 1.8 `risk_on_ratio_summary`

デフォルトでは `IWO/IWN`、つまり Russell 2000 Growth / Russell 2000 Value の比率です。

| 値 | 定義 |
| --- | --- |
| `RATIO` | 最新の numerator / denominator 比率。 |
| `REL 1W %` | 比率の5営業日変化率。 |
| `REL 1M %` | 比率の21営業日変化率。 |
| `REL 3M %` | 比率の63営業日変化率。 |
| `HIGH DIST %` | `risk_on_ratio_high_window` 内の最高値から見た現在比率の距離。デフォルト lookback は756営業日。 |
| `HIGH LOOKBACK DAYS` | 実際に使った高値 lookback 日数。 |
| `ABOVE MA COUNT` | 比率が設定移動平均を上回っている本数。 |
| `MA COUNT` | 判定可能だった移動平均本数。デフォルトは20/50/200日。 |

### 1.9 スナップショット系 DataFrame

`market_snapshot`、`leadership_snapshot`、`external_snapshot` は同じ列構造です。

| 列 | 定義 |
| --- | --- |
| `TICKER` | ETF ticker。 |
| `NAME` | 表示名。 |
| `PRICE` | 最新終値。 |
| `DAY %` | 最新日の騰落率。 |
| `VOL vs 50D %` | `rel_volume` から計算した50日平均出来高比。`(rel_volume - 1) * 100`。 |
| `21EMA POS` | 終値と `ema21_low` / `ema21_high` の位置関係。`above 21EMA High`、`below 21EMA Low`、`inside 21EMA Cloud`、`unknown` のいずれか。 |

対象 universe は以下です。

| 値 | 定義 |
| --- | --- |
| `market_snapshot` | Core market ETF。S&P 500、Nasdaq、Russell、Sector SPDR など。 |
| `leadership_snapshot` | Semiconductors、Software、Biotech、Regional Banks などのリーダー候補 ETF。 |
| `external_snapshot` | Emerging Markets、China Large Cap、China Internet など外部環境 ETF。 |

### 1.10 `factors_vs_sp500`

factor ETF の SPY 相対リターンです。

| 列 | 定義 |
| --- | --- |
| `TICKER` | Factor ETF ticker。 |
| `NAME` | Factor ETF 名。 |
| `REL 1W %` | ETF 5営業日リターン - SPY 5営業日リターン。 |
| `REL 1M %` | ETF 21営業日リターン - SPY 21営業日リターン。 |
| `REL 1Y %` | ETF 252営業日リターン - SPY 252営業日リターン。 |

デフォルト factor ETF は `VUG`、`VTV`、`VYM`、`MGC`、`VO`、`VB`、`MTUM` です。

### 1.11 `sector_relative_strength`

セクターローテーション用の SPY 相対リターンです。対象は `XLB`、`XLC`、`XLE`、`XLF`、`XLI`、`XLK`、`XLP`、`XLRE`、`XLU`、`XLV`、`XLY` です。

| 列 | 定義 |
| --- | --- |
| `TICKER` / `NAME` | セクターETFの ticker と表示名。 |
| `REL 1W %` | セクターETF 5営業日リターン - SPY 5営業日リターン。 |
| `REL 1M %` | セクターETF 21営業日リターン - SPY 21営業日リターン。 |
| `REL 3M %` | セクターETF 63営業日リターン - SPY 63営業日リターン。 |
| `REL 1M 1W AGO %` | 5営業日前時点の21営業日相対リターン。 |
| `REL 1M 1M AGO %` | 21営業日前時点の21営業日相対リターン。 |
| `RANK 1M` | 現在の `REL 1M %` による順位。1が最上位。 |
| `RANK DELTA 1W` | 5営業日前の順位 - 現在順位。正なら順位上昇、負なら順位低下。 |
| `RANK DELTA 1M` | 21営業日前の順位 - 現在順位。正なら順位上昇、負なら順位低下。 |

### 1.12 `style_pair_summary`

スタイル比率のローテーション確認用です。

| 列 | 定義 |
| --- | --- |
| `PAIR` | numerator / denominator。 |
| `NAME` | 比率の説明。 |
| `REL 1W %` / `REL 1M %` / `REL 3M %` | 比率の5/21/63営業日変化率。 |
| `ABOVE MA COUNT` | 比率が設定移動平均を上回っている本数。 |
| `MA COUNT` | 判定可能だった移動平均本数。 |

現在の pair は `VUG/VTV`、`MTUM/SPY`、`VB/MGC`、`VO/MGC`、`VYM/SPY` です。

### 1.13 `defensive_cyclical_summary`

Defensive セクターと Cyclical/Growth セクターのバスケット差です。

| 値 | 定義 |
| --- | --- |
| `REL 1W %` | Cyclical/Growth バスケットの5営業日平均リターン - Defensive バスケットの5営業日平均リターン。 |
| `REL 1M %` | 同21営業日。 |
| `REL 3M %` | 同63営業日。 |

Defensive は `XLP`、`XLU`、`XLV`。Cyclical/Growth は `XLC`、`XLE`、`XLF`、`XLI`、`XLK`、`XLY` です。

### 1.14 その他

| 値 | 定義 |
| --- | --- |
| `s5th_series` | アクティブ銘柄 universe における SMA200 以上比率の時系列。現在のレポートには直接出力されません。 |
| `vix_close` | `^VIX` の最新終値。 |

## 2. レポートに出力している内容と判断基準

レポートは `MarketReportBuilder.build()` で構造化 JSON を作り、`MarketReportMarkdownRenderer.render()` で日本語 Markdown に変換します。Markdown には raw evidence 行や `source_field` は出しません。内部 JSON には根拠が残ります。

### 2.1 エグゼクティブサマリー

| 出力 | 判断基準 |
| --- | --- |
| Market Score / ラベル / 方向性 | `score`、`label`、`score_1w_ago`、`score_1m_ago` から生成。 |
| ブレッドス状態 | `breadth_participation` セクションの判定を要約。 |
| Risk-On Ratio 姿勢 | `risk_on_ratio` セクションの判定を要約。 |
| 横断的な矛盾 | `contradictions` の件数を表示。 |

方向性の判断基準:

| 判定 | 条件 |
| --- | --- |
| 改善 | 1Wスコア差分 `>= 3.0` または 1Mスコア差分 `>= 5.0`。 |
| 悪化 | 1Wスコア差分 `<= -3.0` または 1Mスコア差分 `<= -5.0`。 |
| 横ばい | 上記以外。 |

### 2.2 市場レジーム

| 出力 | 判断基準 |
| --- | --- |
| 判定 | `label` をそのまま表示。 |
| 方向性 | `score` と過去スコアの差分で改善 / 悪化 / 横ばいを判定。 |
| 確信度 | `score` があれば高、なければ低。 |
| 注記 | 過去ラベルが現在ラベルと異なる場合に表示。 |

### 2.3 ブレッドスと参加率

| 出力 | 判断基準 |
| --- | --- |
| 強い | `pct_above_sma20` と `pct_above_sma50` がどちらも `>= 70`。 |
| 弱い | `pct_above_sma20` または `pct_above_sma50` が `< 50`。 |
| まちまち | 上記以外。 |
| 方向性 | `pct_above_sma20`、`pct_above_sma50`、`pct_positive_1w` の1W差分から判定。 |
| 注記 | `S2W HIGH % < 15` の場合、新高値参加が限定的と注記。 |
| 注記 | raw `breadth_summary.pct_above_sma10` と変換後 `component_scores.pct_above_sma10` の差が5以上なら注記。 |

### 2.4 ボラティリティと Safe Haven

VIX 判定:

| 判定 | 条件 |
| --- | --- |
| Low Volatility | `vix_close < 12` |
| Normal Volatility | `12 <= vix_close < 17` |
| Elevated Volatility | `17 <= vix_close < 25` |
| High Volatility | `25 <= vix_close < 30` |
| Stress Volatility | `30 <= vix_close` |

Safe Haven 判定:

| 判定 | 条件 |
| --- | --- |
| Risk-On | `SAFE HAVEN % >= 2` |
| Risk-Off | `SAFE HAVEN % <= -2` |
| Neutral | 上記以外 |

補足: `SAFE HAVEN %` はデフォルトで `SPY` の20営業日リターンから `TLT` の20営業日リターンを引いた値です。VIX が落ち着いているのに Safe Haven が Risk-Off の場合は矛盾として扱われます。

### 2.5 Risk-On Ratio

| 出力 | 判断基準 |
| --- | --- |
| リスクオン | `REL 1W %`、`REL 1M %`、`REL 3M %` のうち2つ以上がプラス。 |
| リスクオフ警戒 | 3期間すべてがプラスでない、または `HIGH DIST % <= -5`。 |
| まちまち | 上記以外。 |
| 注記 | `ABOVE MA COUNT < MA COUNT` の場合、全移動平均を上回っていないと注記。 |

現在のデフォルト ratio は `IWO/IWN` です。

### 2.6 セクターとリーダーシップ

| 出力 | 判断基準 |
| --- | --- |
| Constructive | Core market ETF の `above 21EMA High` 件数が `below 21EMA Low` 件数より多い。 |
| Weakening | `below 21EMA Low` 件数が `above 21EMA High` 件数より多い。 |
| Mixed | 上記以外。 |
| 注記 | Core market ETF の日次上位/下位を表示。 |

このセクションでは `21EMA POS` を使います。`21EMA High`、`21EMA Low`、`21EMA Cloud` は実装上の固有概念としてそのまま扱います。

### 2.7 ファクターとスタイルローテーション

| 出力 | 判断基準 |
| --- | --- |
| Factor Leadership | `factors_vs_sp500` において、`REL 1W % > 0` かつ `REL 1M % > 0` の factor が1つ以上ある。 |
| No Clear Factor Leadership | factor データはあるが、上記を満たす factor がない。 |
| No Data | factor データがない。 |

factor 個別分類:

| 分類 | 条件 |
| --- | --- |
| `accelerating` | `REL 1W % > 0` かつ `REL 1M % > 0`。 |
| `rebound_watch` | `REL 1W % > 0` かつ `REL 1M % <= 0`。 |
| `decelerating` | `REL 1W % <= 0` かつ `REL 1M % > 0`。 |
| `lagging` | `REL 1W % <= 0` かつ `REL 1M % <= 0`。 |

### 2.8 投資優先度

このセクションは、直接的な投資判断支援を意識した現行レイヤーです。ただし、個別銘柄の売買指示、ポジションサイズ、損切り管理は出力しません。

| 出力 | 判断基準 |
| --- | --- |
| 優先候補 | セクターの `REL 1W % > 0`、`REL 1M % > 1.0`、`RANK 1M <= 3`。最大3件。 |
| 新規候補の優先度を下げる | セクターの `REL 1M % < -1.0` かつ `REL 3M % < 0`。最大3件。 |
| Profit-taking/Exit Watch | `REL 1M % > 1.0` かつ `REL 1W % < 0`、または `RANK DELTA 1W <= -3`。最大3件。 |
| スタイル傾向 | style pair の `REL 1W %` と `REL 1M %` がともにプラス、かつ全MA上なら「優位」。両方マイナスなら「劣後」。 |
| Cyclical/Growth vs Defensive | `defensive_cyclical_summary.REL 1M %` がプラスなら Cyclical/Growth 優位、マイナスなら Defensive 優位。 |

### 2.9 投資判断への示唆

| 出力 | 判断基準 |
| --- | --- |
| Screening Context | Market Score の `label` を、Watchlist / Entry Signal の上書きではなく確認優先度の文脈として使う。 |
| 追加確認の注記 | 横断的な矛盾がある場合に表示。 |
| Small Growth 注意 | `risk_on_ratio_summary.HIGH DIST % <= -5` の場合に表示。 |

### 2.10 横断診断

| 矛盾 | 条件 |
| --- | --- |
| `strong_score_narrow_breadth` | `score >= 60` かつ `breadth_summary.pct_above_sma20 < 50`。 |
| `benign_vix_negative_safe_haven` | `vix_close <= 17` かつ `SAFE HAVEN % < -2`。 |
| `participation_without_new_highs` | `pct_positive_1w >= 70` かつ `S2W HIGH % < 15`。 |
| `constructive_score_weak_risk_on_ratio` | `score >= 60` かつ `risk_on_ratio.REL 1M % < 0` または `HIGH DIST % <= -5`。 |

### 2.11 不足している入力

必須入力が空の場合は `v0` の不足として出力します。対象は `score`、`label`、`breadth_summary`、`participation_summary`、`metric_deltas`、`high_vix_summary`、`risk_on_ratio_summary`、`market_snapshot`、`factors_vs_sp500` です。

詳細ローテーション分析向けの入力として、`sector_relative_strength`、`style_pair_summary`、`defensive_cyclical_summary`、`credit_proxy` も確認します。`credit_proxy` は現時点で未実装です。

## 3. レポートフォーマットの概要

### 3.1 出力ファイル

| ファイル | 役割 |
| --- | --- |
| `data_runs/market_reports/YYYYMMDD.json` | 構造化レポート。各セクション、根拠、source field、contradiction、missing input、data appendix を保持。 |
| `data_runs/market_reports/YYYYMMDD.md` | ユーザー確認用 Markdown。根拠の内部行や source field は表示しない。 |

現在、Market Dashboard の UI にはこの Markdown レポートを表示していません。

### 3.2 JSON の構造

`MarketReportResult` の主な構造は以下です。

| フィールド | 内容 |
| --- | --- |
| `trade_date` | 対象日。 |
| `generated_at` | レポート生成時刻。 |
| `source_summary_path` | 元になった `market_summary` のパス。 |
| `overall_label` | 総合市場ラベル。 |
| `overall_direction` | 改善 / 悪化 / 横ばい。 |
| `confidence` | レポート全体の確信度。 |
| `summary_points` | 内部用の要約ポイント。 |
| `sections` | 各レポートセクション。 |
| `contradictions` | 横断的な矛盾。 |
| `missing_inputs` | 不足入力。 |
| `data_appendix` | 重複排除された根拠一覧。 |

各 section は `key`、`title`、`label`、`direction`、`confidence`、`summary`、`evidence`、`warnings` を持ちます。

各 evidence は `metric`、`source_field`、`value`、`raw_value`、`score_value`、`delta_1d`、`delta_1w`、`delta_1m`、`note` を持ちます。Markdown では evidence 行は表示しません。

### 3.3 Markdown の章構成

現行 Markdown は以下の順序です。

1. `# マーケットレポート`
2. 対象日、生成時刻、総合判定
3. エグゼクティブサマリー
4. 市場レジーム
5. ブレッドスと参加率
6. ボラティリティと Safe Haven
7. Risk-On Ratio
8. セクターとリーダーシップ
9. ファクターとスタイルローテーション
10. 投資優先度
11. 投資判断への示唆
12. 横断診断
13. 不足している入力

### 3.4 表示方針

- 日本語 Markdown として出力する。
- `21EMA High`、`21EMA Low`、`21EMA Cloud`、`21EMA POS` は実体に紐づく固有名詞として扱う。
- `Safe Haven`、`Risk-On Ratio`、`Profit-taking/Exit Watch` など、説明すると長くなる用語は固有表現として残す。
- ユーザー向け Markdown には内部 evidence / source field / data appendix を出さない。
- 内部 JSON には根拠を保持する。
- 現行レポートは市場文脈と優先度提示を担う。個別売買の実行指示、ポジションサイズ、損切り管理は出力しない。

## 4. 改良検討時の確認ポイント

- `Market Score` と `Risk-On Ratio` の矛盾をどう扱うか。
- `sector_relative_strength` の優先候補 / exit watch しきい値が妥当か。
- `Safe Haven %` が `SPY - TLT` だけで十分か。
- `credit_proxy`、金利、ドル、ハイイールドスプレッドなどを追加するか。
- `factors_vs_sp500` と `style_pair_summary` の役割が重複していないか。
- `data_cache` 差し替え後の `Recompute from cache` 運用で、PCごとの `data_runs` が期待通り再生成されるか。
