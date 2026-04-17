# スキャン・アノテーションフィルタ改修依頼書

作成日: 2026-04-16

---

## 1. 改修の背景と思想

### 1.1 現状の問題認識

既存の 21 本のスキャン定義を横断して精査した結果、**複数のスキャンで同一条件が重複して記述されている**状態が確認された。

特に顕著なのは以下の 2 条件。

**`trend_base` 条件** (`(close > sma50) AND (wma10_weekly > wma30_weekly)`)

全 21 本中、11 本で登場している。内訳は、10 本で必須条件として記述(scan_01, 04, 05, 08, 10, 11, 12, 16, 17, 19)、1 本で config フラグ付きで任意化(scan_13)。全スキャンの過半数で同じ条件がコピペされている状態。

**`raw_rs21` 下限閾値**

8 本のスキャンで登場する。このうち 60 前後の下限値(scan_02 の `> 60`、scan_06 の `> 60`、scan_18 の `>= 60`)は、個別戦略の定義ではなく「RS が市場平均を上回る」という汎用品質ゲートの意味で使われている。

### 1.2 設計思想の整合

本システムは既に以下の 2 つのオーケストレーション機構を持っている。

- 必須スキャン + 任意スキャン(閾値付き)によるプリセット合成
- アノテーションフィルタ(ポストスキャン)による属性ベース絞り込み

この機構が存在する以上、**「汎用品質ゲートはアノテーションフィルタに、戦略固有条件のみスキャンに」という分離が設計哲学として自然**である。しかし現状は汎用品質ゲートがスキャン本体に残存しており、この分離が徹底されていない。

既にアノテーションフィルタとして `High Est. EPS Growth` / `PP Count` / `RS 21 >= 63` の 3 件が運用されており、これらは全て「snapshot 属性による汎用品質ゲート」の性格を持つ。新設する 2 件(Trend Base、Fund Score > 70)も同じ性格であり、既存運用との一貫性がある。

### 1.3 改修で達成すること

**スキャン本体を「そのスキャンに固有の戦略条件」のみに純化する。**

重複する汎用品質ゲートはアノテーションフィルタに切り出し、プリセットが必要に応じて任意に組み合わせる構造に移行する。効果は以下。

- スキャン本体の記述量が減り、各スキャンのアイデンティティ(何を抽出するスキャンか)が明快になる
- 品質ゲートの変更が 1 箇所で完結する(現状は 11 スキャン全部を触る必要がある)
- プリセット側の表現力が拡大する

### 1.4 改修のスコープ

本改修のスコープは以下に限定する。

- アノテーションフィルタの新設 2 件: `Trend Base`、`Fund Score > 70`
- 既存アノテーションフィルタの流用 1 件: `RS 21 >= 63`
- スキャンの削除 1 件: scan_18 Fundamental Demand
- スキャンの条件除去: 該当 12 本(trend_base / raw_rs21 / config フラグ)

スコープ外とする事項は §8 に明記。

---

## 2. 新設するアノテーションフィルタ

### 2.1 Trend Base

#### 目的

中長期の上昇トレンド健全性を判定する汎用品質ゲート。既存のスキャン本体における `trend_base` 条件と**完全に同じ意味論**を、アノテーションフィルタ層に移譲する。

#### 仕様

| 項目 | 値 |
|---|---|
| アノテーションフィルタ名(canonical) | `Trend Base` |
| 実装配置 | `src/scan/rules.py::ANNOTATION_FILTER_REGISTRY` |
| 出力 | `bool` |
| 新規指標計算 | 不要(既存の `trend_base` フィールドを読むのみ) |

#### 判定ロジック

```python
matched = bool(row.get("trend_base", False))
```

#### 参照フィールド

| フィールド | 既存プロデューサ | 欠損時の扱い |
|---|---|---|
| `trend_base` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` |

#### 上流フィールド定義(参考)

```
trend_base = (close > sma50) & (wma10_weekly > wma30_weekly)
```

---

### 2.2 Fund Score > 70

#### 目的

EPS 成長と売上成長の複合スコアによる、総合的なファンダメンタル品質の下限ゲート。既存 scan_18 Fundamental Demand の `fundamental_score >= 70.0` 条件を、アノテーションフィルタ層に切り出す。

#### 既存アノテーションフィルタとの関係

既存の `High Est. EPS Growth` とは**別物**。両者は独立して AND 指定可能。

| フィルタ | 参照値 | 判定 | 意味 |
|---|---|---|---|
| `High Est. EPS Growth`(既存) | `eps_growth_rank` | `>= 90.0` | EPS Growth **単体**の上位 10% 判定(相対) |
| `Fund Score > 70`(新設) | `fundamental_score` | `>= 70.0` | EPS + Revenue の**複合**スコアの絶対閾値 |

具体例として以下のケースで判定が分岐する。

- EPS Growth が極めて高いが Revenue Growth が低い銘柄 → `High Est. EPS Growth` = true だが `Fund Score > 70` は満たさない可能性
- EPS Growth は上位 10% ではないが EPS と Revenue の複合で良好な銘柄 → `High Est. EPS Growth` = false だが `Fund Score > 70` = true の可能性

#### 仕様

| 項目 | 値 |
|---|---|
| アノテーションフィルタ名(canonical) | `Fund Score > 70` |
| 実装配置 | `src/scan/rules.py::ANNOTATION_FILTER_REGISTRY` |
| 出力 | `bool` |
| 新規指標計算 | 不要(既存の `fundamental_score` フィールドを読むのみ) |
| 閾値 | 固定 70.0(プリセット側でパラメータ化しない) |

#### 判定ロジック

```python
matched = bool(row.get("fundamental_score", 0.0) >= 70.0)
```

#### 参照フィールド

| フィールド | 既存プロデューサ | 欠損時の扱い |
|---|---|---|
| `fundamental_score` | `src/scoring/fundamental.py::FundamentalScorer.score` | `0.0` |

#### 上流フィールド定義(参考)

`fundamental_score` は `eps_growth_score` と `revenue_growth_score` の重み付き平均。デフォルトでは両者 1:1(`eps_weight=1.0`, `revenue_weight=1.0`)。

---

## 3. 流用する既存アノテーションフィルタ

### 3.1 RS 21 >= 63

既存の `RS 21 >= 63` アノテーションフィルタを、scan_02 と scan_06 の RS21 下限条件の代替として流用する。

アノテーションフィルタ自体の仕様変更はない。

#### 挙動上の注意(重要)

scan_02 と scan_06 の現行閾値は `raw_rs21 > 60.0` であり、`RS 21 >= 63` で代替すると**閾値がわずかに厳しくなる**(raw_rs21 が 60.01〜62.99 の帯域が新たに除外される)。

この挙動変化を許容することが本改修の前提。許容しない場合は §10(c) を参照。

---

## 4. 削除するスキャン

### 4.1 scan_18 Fundamental Demand

#### 削除理由

本スキャンの 5 条件は以下のように分解でき、全条件がスキャン本体外で表現可能である。

| 現行条件 | 移譲先 |
|---|---|
| `fundamental_score >= 70.0` | 新設アノテーションフィルタ `Fund Score > 70` |
| `raw_rs21 >= 60.0` | 既存アノテーションフィルタ `RS 21 >= 63` |
| `trend_base` | 新設アノテーションフィルタ `Trend Base` |
| `rel_volume >= 1.0` | プリセット側で既存スキャン等と組み合わせ(本ドキュメントのスコープ外) |
| `daily_change_pct > 0.0` | 同上 |

つまり scan_18 は「4 つの独立した汎用条件の合成」になっており、プリセット合成機構の存在意義と重複している。「各スキャンは単一の戦略概念に責任を持つ」という設計思想と照らして、合成はプリセット層に寄せる方が筋。

#### 削除作業

- `src/scan/rules.py::_scan_fundamental_demand` 関数を削除
- スキャン登録箇所から該当エントリを削除
- `config/default.yaml` から以下 3 キーを削除
  - `scan.fund_demand_fundamental_min`
  - `scan.fund_demand_rs21_min`
  - `scan.fund_demand_rel_vol_min`
- スキャンドキュメント `doc/SystemDocs/Scan/scan_18_fundamental_demand.md` を削除
- `scan_00_index.md` の Active Scan Specs 表から該当行を削除
- `scan_00_index.md` 本文の「21 scan families」記述を「20 scan families」に更新

#### プリセット再構成

既存プリセットで scan_18 を指定しているものはシステム側で書き換える(本ドキュメントでは指定しない)。等価性検証はシステム側で実施する。

---

## 5. 変更するスキャン(`trend_base` 条件の除去)

以下 10 本のスキャンから、canonical boolean definition の `row.get("trend_base", False)` 行を除去する。作業内容は 10 本すべてで同構造(1 行除去)。

scan_13 については config フラグと併せて §7 で記述。

#### 5.1 scan_01 21EMA

```python
# 変更前
weekly_return = row.get("weekly_return", float("nan"))
matched = bool(
    weekly_return >= 0.0
    and weekly_return <= 15.0
    and row.get("dcr_percent", 0.0) > 20.0
    and -0.5 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
    and 0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
    and row.get("trend_base", False)  # ← 削除
)

# 変更後
weekly_return = row.get("weekly_return", float("nan"))
matched = bool(
    weekly_return >= 0.0
    and weekly_return <= 15.0
    and row.get("dcr_percent", 0.0) > 20.0
    and -0.5 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
    and 0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
)
```

#### 5.2 〜 5.10 共通の変更内容

scan_04 / scan_05 / scan_08 / scan_10 / scan_11 / scan_12 / scan_16 / scan_17 / scan_19 について、各 canonical boolean definition から `row.get("trend_base", False)`(または `and row.get("trend_base", False)`)の 1 行を削除する。他の条件は変更しない。

該当スキャンの現行 canonical definition は以下の通り(参照用)。

**scan_04 Momentum 97**: `weekly_return_rank`, `quarterly_return_rank`, `trend_base` ← 除去
**scan_05 97 Club**: `hybrid_score`, `raw_rs21`, `trend_base` ← 除去
**scan_08 PP Count**: `pp_count_window`, `trend_base` ← 除去
**scan_10 Near 52W High**: `high_52w` 存在チェック, `close` 距離チェック, `hybrid_score`, `trend_base` ← 除去
**scan_11 Three Weeks Tight**: `three_weeks_tight`, `trend_base` ← 除去, `vcs`
**scan_12 RS Acceleration**: `rs21 > rs63`, `rs21 >= threshold`, `trend_base` ← 除去
**scan_16 Pullback Quality**: 9 条件のうち `trend_base` ← 除去、他 8 条件は維持
**scan_17 Reclaim**: 11 条件のうち `trend_base` ← 除去、他 10 条件は維持
**scan_19 Sustained Leadership**: `rs21`, `rs63`, `rs126`, `trend_base` ← 除去

#### 5.11 対応するドキュメント更新

各スキャンの `scan_XX_*.md` について、以下を更新。

- Canonical Boolean Definition のコードブロックから該当行を除去
- Required Inputs 表から `trend_base` 行を除去
- Upstream Field Definitions から `trend_base` の定義行を除去(他スキャンで参照されるため完全削除はせず、§2.1 で仕様化したものを引用する形に留める選択肢もあり)

---

## 6. 変更するスキャン(`raw_rs21` 下限条件の除去)

### 6.1 scan_02 4% bullish

```python
# 変更前
raw_rs21 = _raw_rs(row, 21)
matched = bool(
    row.get("rel_volume", 0.0) >= config.relative_volume_bullish_threshold
    and row.get("daily_change_pct", 0.0) >= config.daily_gain_bullish_threshold
    and row.get("from_open_pct", 0.0) > 0.0
    and raw_rs21 > 60.0  # ← 削除
)

# 変更後
matched = bool(
    row.get("rel_volume", 0.0) >= config.relative_volume_bullish_threshold
    and row.get("daily_change_pct", 0.0) >= config.daily_gain_bullish_threshold
    and row.get("from_open_pct", 0.0) > 0.0
)
```

削除に伴い、関数先頭の `raw_rs21 = _raw_rs(row, 21)` の行も不要になるため併せて削除。

**役割変化**: scan_02 は「当日の出来高増 + 寄りから上抜け + 指定%以上の上昇バー」という純粋な当日バーパターンスキャンとなる。RS21 による絞り込みが必要な既存プリセットは、`RS 21 >= 63` アノテーションフィルタを必須指定することで代替(プリセット対応はシステム側)。

#### ドキュメント更新

`scan_02_4pct_bullish.md` について以下を更新。

- Canonical Boolean Definition の `raw_rs21 > 60.0` 行を除去
- Required Inputs 表から `raw_rs21` と `rs21` の行を除去
- Direct Config Dependencies の「Hard-coded threshold in code」セクションから `raw_rs21 > 60.0` を除去
- Upstream Field Definitions から `raw_rs21` の定義を除去

### 6.2 scan_06 VCS

```python
# 変更前
raw_rs21 = _raw_rs(row, 21)
matched = bool(
    row.get("vcs", 0.0) >= config.vcs_min_threshold
    and raw_rs21 > 60.0  # ← 削除
)

# 変更後
matched = bool(
    row.get("vcs", 0.0) >= config.vcs_min_threshold
)
```

関数先頭の `raw_rs21 = _raw_rs(row, 21)` の行も併せて削除。

**役割変化**: scan_06 は「VCS スコア下限」という単一条件スキャンとなる。代替方針は scan_02 と同じ。

#### ドキュメント更新

scan_02 と同構造で `scan_06_vcs.md` を更新。

---

## 7. 変更するスキャン(config フラグと `trend_base` の除去)

### 7.1 scan_13 VCS 52 High

```python
# 変更前
matched = bool(
    row.get("vcs", 0.0) >= config.vcs_52_high_vcs_min
    and _raw_rs(row, 21) > config.vcs_52_high_rs21_min
    and row.get("dist_from_52w_high", float("nan")) >= config.vcs_52_high_dist_max
    and (not config.vcs_52_high_require_trend_base or row.get("trend_base", False))  # ← 削除
)

# 変更後
matched = bool(
    row.get("vcs", 0.0) >= config.vcs_52_high_vcs_min
    and _raw_rs(row, 21) > config.vcs_52_high_rs21_min
    and row.get("dist_from_52w_high", float("nan")) >= config.vcs_52_high_dist_max
)
```

#### Config 変更

`config/default.yaml` から以下のキーを完全削除(deprecate ではなく削除)。

- `scan.vcs_52_high_require_trend_base`

#### ドキュメント更新

`scan_13_vcs_52_high.md` について以下を更新。

- Canonical Boolean Definition から trend_base 条件行を除去
- Required Inputs 表から `trend_base` 行を除去
- Direct Config Dependencies 表から `scan.vcs_52_high_require_trend_base` 行を除去
- Upstream Field Definitions から `trend_base` の定義行を除去

**挙動変化について**: 現行のデフォルト値は `vcs_52_high_require_trend_base = true` であるため、`Trend Base` アノテーションフィルタを必須指定する既存プリセットは挙動等価を維持できる。必須指定しないプリセットでは、従来より広い結果集合となる(trend_base 条件が外れるため)。

---

## 8. スコープ外(今回は変更しない)

### 8.1 戦略固有の閾値として残す条件

以下は「複数スキャンで同一概念が登場する」形には見えるが、各スキャン固有の戦略意味を持つため本改修では触らない。

| フィールド | 該当スキャン(閾値) | 残す理由 |
|---|---|---|
| `weekly_return` 範囲 | scan_01 `[0, 15]`, scan_16 `[-8, 3]`, scan_17 `[-3, 10]` | 押し目の深さ・タイミングという戦略設計そのもの |
| `dcr_percent` 下限 | scan_01 `> 20`, scan_16 `>= 50`, scan_17 `>= 60` | 戦略ごとに要求される引けの質が異なる |
| `atr_50sma_zone` 上限 | scan_01 `<= 3.0`, scan_16 `<= 3.5`, scan_17 `<= 4.0` | 押し目/奪回で許容される過熱度が異なる |
| `raw_rs21` 高閾値 | scan_05 `>= 97`, scan_14 `> 80`, scan_19 `>= 80` | 戦略の定義そのもの(例: 97 Club の「97」は戦略名) |
| `raw_rs21` 低閾値 | scan_13 `> 25`, scan_20 `>= 50` | `RS 21 >= 63` より低く、63 への統一は戦略挙動を変える |

### 8.2 将来検討事項(メモ)

本改修のスコープからは外すが、将来的に検討すべき拡張。

- **ATR 変化系指標の新設**
  - ゾーンのスロープ系(`atr_50sma_zone_change_Nd`, `atr_21ema_zone_change_Nd` 等): 過熱度の変化を捉える。絶対値フィルタでは区別できない「過熱加速」「過熱冷却」「定常過熱」の 3 ケースを識別可能にする。
  - ATR レジーム変化系(`atr_ratio_short_long` 等): ボラティリティ収縮/拡大を純粋に捉える。既存の VCS との役割分担設計が必要。
- **`atr_50sma_zone` 上限の汎用過熱ガードとしてのアノテーションフィルタ化**(現状は閾値バリエーション 3.0/3.5/4.0 があり統一が困難)
- **`fundamental_score` 閾値のパラメータ化**(現在は固定 70.0。将来的にプリセット側で閾値指定したいユースケースが生じた場合)

---

## 9. 実装時のチェック項目

### 9.1 アノテーションフィルタの実装詳細

- `ANNOTATION_FILTER_REGISTRY` への新規登録: `Trend Base` / `Fund Score > 70`
- UI 表示名の決定(本ドキュメントでは canonical 名をそのまま採用する前提)
- アノテーションフィルタのドキュメント配置先の決定(既存 annotation filter のドキュメント配置に従う)

### 9.2 削除に伴う波及範囲

- `_scan_fundamental_demand` を参照するテストコードの更新・削除
- `fund_demand_*` config キーを参照するテストコード・サンプル config の更新
- `vcs_52_high_require_trend_base` config キーを参照するテストコード・サンプル config の更新
- `scan_00_index.md` の Active Scan Specs 表と「21 scan families」記述の更新

### 9.3 プリセット移行(システム側対応)

以下を参照する既存プリセットは、等価性を保つようシステム側で書き換える。等価性の検証方針はシステム側で決定する(本ドキュメントのスコープ外)。

- scan_18 を指定しているプリセット → 新設 3 アノテーションフィルタ等で再構成
- trend_base を明示/暗黙に前提としているプリセット → `Trend Base` アノテーションフィルタを必須指定
- scan_02 / scan_06 の raw_rs21 条件を前提としているプリセット → `RS 21 >= 63` アノテーションフィルタを必須指定
- scan_13 の `vcs_52_high_require_trend_base = true` 前提のプリセット → `Trend Base` アノテーションフィルタを必須指定

---

## 10. 本ドキュメントで厳密化されていない可能性のある点

改修実装着手前に、ユーザ確認が必要と想定される論点。

**(a) アノテーションフィルタ名の最終決定**

本ドキュメントでは canonical 名として `Trend Base` と `Fund Score > 70` を採用しているが、既存 annotation filter(`High Est. EPS Growth` / `PP Count` / `RS 21 >= 63`)との命名スタイル統一の観点で要レビュー。

**(b) scan_02 / scan_06 の RS21 閾値差挙動変化の許容範囲**

`raw_rs21 > 60.0` → `RS 21 >= 63.0` で代替するため、raw_rs21 が 60.01〜62.99 の銘柄が新たに除外される。この挙動変化が許容範囲か、厳密等価を求めるかの確認。厳密等価を求める場合は、アノテーションフィルタ側に閾値 60 の別エントリを追加するなどの追加対応が必要。

**(c) scan_18 削除時の rel_volume + daily_change_pct 条件の再構成**

scan_18 の `rel_volume >= 1.0 AND daily_change_pct > 0.0` を既存プリセットでどう再構成するかの方針。scan_03 Vol Up(`rel_volume >= 1.5`)を流用すると閾値差が生じる。完全等価を求める場合は、閾値 1.0 の Vol Up 亜種を新設するか、scan_18 を完全廃止ではなく縮小版として残す選択肢もある(本ドキュメントでは廃止で確定しているが、プリセット再構成の困難さが顕在化した場合の再検討余地として記載)。

**(d) `Fund Score > 70` の閾値 70.0 の妥当性**

`fundamental_score` のスコア体系(想定されるスコア分布、正規化方法)に対して、絶対閾値 70.0 が意味のある分水嶺になっているかの確認。現行 scan_18 の `fund_demand_fundamental_min = 70.0` をそのまま踏襲しているが、この値自体の妥当性レビューは行っていない。
