# Market Conditions 算出式メモ

このメモは、現行実装を正として `Market Conditions` の算出方法を整理したものです。

対象コード:

- `src/dashboard/market.py`
- `config/default/market.yaml`

## 1. 結論

現在の `Market Conditions score` は、複数の市場内部指標の raw 値を集計し、その一部に score 用の変換を適用したうえで重み付き合計したものです。

基本式:

```text
score = Σ(component_value × component_weight)
```

実装上の対応箇所:

- `MarketConditionScorer._score_from_components()`

## 2. 現在の重み

現行設定は `config/default/market.yaml` にあります。

```text
pct_above_sma20      0.12
pct_above_sma50      0.14
pct_above_sma200     0.14
pct_sma50_gt_sma200  0.08
pct_positive_1m      0.09
pct_positive_3m      0.08
pct_2w_high          0.05
safe_haven_score     0.15
vix_score            0.15
```

重み合計は `1.00` です。

## 3. 各コンポーネントの意味

各コンポーネントは、対象ユニバース内で条件を満たした銘柄または ETF の割合を `%` で表したものです。

### 3.1 Breadth / Trend 系

```text
pct_above_sma20      = 100 × mean(close >= sma20)
pct_above_sma50      = 100 × mean(close >= sma50)
pct_above_sma200     = 100 × mean(close >= sma200)
pct_sma50_gt_sma200  = 100 × mean(sma50 >= sma200)
```

### 3.2 Return 系

`ret_1m` と `ret_3m` が正である比率を使います。

```text
pct_positive_1m   = 100 × mean(ret_1m > 0)
pct_positive_3m   = 100 × mean(ret_3m > 0)
```

補足:

- `ret_1m` は 21 営業日変化率
- `ret_3m` は 63 営業日変化率

### 3.3 2-week high 系

```text
pct_2w_high = 100 × mean(current_close >= rolling_10day_high)
```

実装では `2 weeks` を営業日ベースの 10 本ローリング高値として扱っています。

### 3.4 Score 用の比率変換

比率系コンポーネントは score 計算時に raw 値をそのまま使わず、上側を圧縮した変換を通します。

```text
if value <= 50:
    score = value
else:
    score = 50 + ((value - 50) / 50) × 30
```

### 3.5 Safe Haven スコア

Safe Haven は、risk-on ETF と risk-off ETF の一定期間リターン差を使います。

現行デフォルト:

- risk-on: `SPY`
- risk-off: `TLT`
- window: 20 営業日

```text
safe_haven_spread = return(SPY, 20d) - return(TLT, 20d)
safe_haven_score = clamp(50 + safe_haven_spread × 4, 0, 100)
```

### 3.6 VIX スコア

VIX は比率ではなく、現在値から 0-100 のスコアへ変換します。

```text
vix_score = clamp(50 - (VIX - 17) × 5, 0, 100)
```

意味:

- `VIX = 17` を中立の基準とする
- VIX が 1 上がるごとにスコアを `5` ずつ減点
- VIX が 1 下がるごとにスコアを `5` ずつ加点
- 上限と下限は `0-100`

VIX が取得できないときは `50` を返します。

## 4. score の具体式

現行デフォルト設定では次の式です。

```text
score =
  pct_above_sma20      × 0.12 +
  pct_above_sma50      × 0.14 +
  pct_above_sma200     × 0.14 +
  pct_sma50_gt_sma200  × 0.08 +
  pct_positive_1m      × 0.09 +
  pct_positive_3m      × 0.08 +
  pct_2w_high          × 0.05 +
  safe_haven_score     × 0.15 +
  vix_score            × 0.15
```

各項目が 0-100 のため、最終 `score` も概ね `0-100` に収まります。

## 5. ラベル判定

最終 score は次の閾値でラベル化されます。

```text
score >= 80  -> Bullish
score >= 60  -> Positive
score >= 40  -> Neutral
score >= 20  -> Negative
else         -> Bearish
```

閾値は `config/default/market.yaml` の以下を使用します。

- `bullish_threshold`
- `positive_threshold`
- `neutral_threshold`
- `negative_threshold`

## 6. どのユニバースで計算するか

計算対象は `market.calculation_mode` で変わります。

### 6.1 `etf`

`market_condition_etf_universe` の ETF 群だけでコンポーネントを作ります。

現行デフォルトはこのモードです。

### 6.2 `active_symbols`

watchlist 候補抽出のためにロードされたアクティブ銘柄群でコンポーネントを作ります。

### 6.3 `blended`

ETF 側コンポーネントと active_symbols 側コンポーネントをブレンドします。

基本式:

```text
blended_component =
  (etf_component × etf_weight + active_component × active_symbols_weight)
  / (etf_weight + active_symbols_weight)
```

現行デフォルト重み:

- `etf_weight = 0.5`
- `active_symbols_weight = 0.5`

## 7. 画面表示との関係

`Market Dashboard` の表示項目すべてが score に入るわけではありません。

- `Core` は `calculation_mode = etf` のとき score に使う
- `Leadership` は表示用
- `External` は表示用
- `Safe Haven` は score に直接入る
- `Factors vs SP500` は表示用
- `Performance Overview` は score には直接入らず、補助表示

補足:

`score` の計算で使う return 系は `pct_positive_1m` と `pct_positive_3m` であり、画面の `Performance Overview` に出る `% 1W`, `% 1M`, `% 1Y`, `% YTD` とは別物です。

## 8. 時点別 score

`1D Ago`, `1W Ago`, `1M Ago`, `3M Ago` は、同じロジックをそれぞれ以下のオフセットで再計算したものです。

- `1D Ago` -> 1
- `1W Ago` -> 5
- `1M Ago` -> 21
- `3M Ago` -> 63

## 9. 実装上の注意点

- `sma10` と `sma20` はその場で rolling mean を計算
- `sma50` と `sma200` は履歴列があれば使用し、なければ `close` から再計算
- ヒストリ不足の銘柄や ETF は集計対象から外れる
- VIX が欠損のときだけ `vix_score = 50`
- score の source of truth は文書ではなく実装

## 10. 実装参照

- `src/dashboard/market.py`
  - `MarketConditionScorer.score()`
  - `MarketConditionScorer._raw_component_values_at_offset()`
  - `MarketConditionScorer._raw_component_values_for_histories()`
  - `MarketConditionScorer._score_components()`
  - `MarketConditionScorer._safe_haven_score()`
  - `MarketConditionScorer._vix_score()`
  - `MarketConditionScorer._score_from_components()`
  - `MarketConditionScorer._label()`

- `config/default/market.yaml`
