# Market Dashboard 使い方

## 目的

Market Dashboard は、個別銘柄を見る前に市場環境を確認するための画面です。
売買判断を自動化するものではなく、Watchlist と Entry Signal をどの程度積極的に見るかを調整する材料として使います。

## 最初に見るもの

### Market Conditions

市場環境の総合スコアです。

- `Bullish` / `Positive`: 候補レビューを積極的に進めやすい地合い
- `Neutral`: 個別銘柄の質と Entry Signal を重視する地合い
- `Negative` / `Bearish`: 候補が出ても慎重に扱う地合い

1D / 1W / 1M / 3M ago は、地合いが改善中か悪化中かを見るために使います。
現在値だけでなく、スコアの方向を確認します。

## 代表指標の読み方

| セクション | 表示 | 読み方 |
|---|---|---|
| Breadth & Trend Metrics | `SMA 10/20/50/200` | Core ETF 群のうち、各移動平均より上にいる割合。高いほど参加範囲が広い |
| Breadth & Trend Metrics | `20 > 50`, `50 > 200` | 中期・長期トレンド構造が上向きのETF比率 |
| Participation Momentum | `Pos 1W/1M/3M/1Y/YTD` | 各期間リターンがプラスのCore ETF比率。一定期間で実際に上昇しているETFの広がりを見る |
| Performance Overview | `% YTD`, `% 1W`, `% 1M`, `% 1Y` | ベンチマークの期間リターン。現在の指数方向を確認する |
| High, VIX & Safe Haven | `S2W High` | 2週間高値を更新しているCore ETF比率。短期の広がりを見る |
| High, VIX & Safe Haven | `VIX` | ボラティリティ。高いほど地合いは不安定になりやすい |
| High, VIX & Safe Haven | `Safe Haven` | `SPY` と `TLT` の20営業日リターン差。株式が債券より強いかを見る |
| Risk-On Ratio IWO/IWN | `1M`, `3M` | 小型グロースが小型バリューに勝っているかを見る |
| Risk-On Ratio IWO/IWN | `High Delta`, `MA` | Risk-on ratio が高値圏か、主要移動平均の上にいるかを見る |
| Core | ETFカード | Market Score に使う主要指数・セクターETF群 |
| Leadership | ETFカード | 半導体、ソフトウェア、バイオ等のリーダー候補群。スコアには直接入らない |
| External | ETFカード | 新興国・中国関連。外部リスク確認用 |
| Factors vs SP500 | factor cards | Growth, Value, Momentum などが `SPY` に勝っているかを見る |

各カードの `Δ 1D / 1W / 1M` は、現在値がそれぞれ1営業日前、5営業日前、21営業日前からどれだけ変化したかを示します。
これは既に取得済みの価格履歴から再計算しており、追加のデータ取得や取得期間延長は行いません。

## 詳細定義と算出方法

この章は、現在の実装と `config/default/market.yaml` に基づく厳密な定義です。
現在の `market.calculation_mode` は `etf` なので、Breadth、Trend、短期高値、内部の陽線比率系コンポーネントは Core ETF 群を対象に計算されます。

対象 Core ETF は、`SPY`, `QQQ`, `DIA`, `IWM`, `RSP`, `QQQE`, `MDY`, `IJR`, `XLB`, `XLC`, `XLE`, `XLF`, `XLI`, `XLK`, `XLP`, `XLRE`, `XLU`, `XLV`, `XLY` です。
VIX、Safe Haven、Risk-On Ratio、Factors はそれぞれ専用のシンボルを追加で使います。

### Breadth & Trend Metrics

対象ユニバース内で有効な `close` 行を持つETF数を `N` とします。
各ETFについて、最新日の `close`、`sma10`、`sma20`、`sma50`、`sma200` を使います。
`sma10` と `sma20` は終値の10本・20本単純移動平均、`sma50` と `sma200` は指標計算済み列があればそれを使い、なければ終値の50本・200本単純移動平均で補います。

表示値の定義は次の通りです。

| 表示 | 厳密な定義 |
|---|---|
| `SMA 10` | `100 * count(close >= sma10) / N` |
| `SMA 20` | `100 * count(close >= sma20) / N` |
| `SMA 50` | `100 * count(close >= sma50) / N` |
| `SMA 200` | `100 * count(close >= sma200) / N` |
| `20 > 50` | `100 * count(sma20 >= sma50) / N` |
| `50 > 200` | `100 * count(sma50 >= sma200) / N` |

移動平均がまだ計算できないETFは比較結果が False 扱いになります。
つまり、長期データが不足しているETFは `SMA 200` や `50 > 200` の比率を押し下げます。

`Participation Momentum` では、同じ処理内で作られる次の値を表示します。

| 内部値 | 定義 |
|---|---|
| `pct_positive_1w` | `100 * count(5営業日リターン > 0) / N` |
| `pct_positive_1m` | `100 * count(21営業日リターン > 0) / N` |
| `pct_positive_3m` | `100 * count(63営業日リターン > 0) / N` |
| `pct_positive_1y` | `100 * count(252営業日リターン > 0) / N` |
| `pct_positive_ytd` | `100 * count(年初来リターン > 0) / N` |
| `pct_2w_high` | `100 * count(close >= 10営業日ローリング高値) / N` |

Market Conditions の総合スコアには、現在設定では `SMA 20`, `SMA 50`, `SMA 200`, `50 > 200`, `pct_positive_1m`, `pct_positive_3m`, `pct_2w_high` が使われます。
`SMA 10` と `20 > 50` は現在の表示項目ですが、総合スコアの重みには入っていません。

比率系コンポーネントは、スコア化時に次の変換を受けます。

```text
raw <= 50 の場合: score_component = raw
raw > 50 の場合 : score_component = min(80, 50 + ((raw - 50) / 50) * 30)
```

### High, VIX & Safe Haven

`S2W High` は Breadth と同じ Core ETF 群を対象にします。
各ETFの最新終値が10営業日ローリング高値以上なら `1`、それ以外は `0` とし、比率を表示します。

```text
S2W High = 100 * count(close >= rolling_high_10) / N
```

`VIX` は `^VIX` の最新終値そのものです。
表示される数値は未変換のVIX水準ですが、Market Conditions に入るスコアは次の式で作られます。

```text
vix_score = clamp(50 - ((VIX - 17.0) * 5.0), 0, 100)
```

VIXが17なら50点、17より低ければプラス、高ければマイナスです。
表示ラベルはこの `vix_score` に対して、60以上が Positive、40以下が Negative、それ以外が Neutral です。

`Safe Haven` は `SPY` と `TLT` の20営業日リターン差です。
株式リスク資産が債券系の逃避資産に対して強いかを見ます。

```text
spy_return_20d = (SPY_latest / SPY_20営業日前 - 1) * 100
tlt_return_20d = (TLT_latest / TLT_20営業日前 - 1) * 100
Safe Haven = spy_return_20d - tlt_return_20d
safe_haven_score = clamp(50 + Safe Haven * 4.0, 0, 100)
```

表示値は `Safe Haven` のリターン差です。
Market Conditions に入るのは `safe_haven_score` です。
表示ラベルは `safe_haven_score` に対して、60以上が Positive、40以下が Negative、それ以外が Neutral です。

このセクションで使うデータは、Core ETF 群の終値、`^VIX` の終値、`SPY` の終値、`TLT` の終値です。

### Risk-On Ratio IWO/IWN

Risk-On Ratio は、小型グロースETF `IWO` を小型バリューETF `IWN` で割った相対比率です。
日付を内部結合でそろえ、`IWN` が0または欠損の日は除外します。

```text
ratio_t = IWO_close_t / IWN_close_t
```

表示値の定義は次の通りです。

| 表示 | 厳密な定義 |
|---|---|
| `1M` | `(ratio_latest / ratio_21営業日前 - 1) * 100` |
| `3M` | `(ratio_latest / ratio_63営業日前 - 1) * 100` |
| `High Delta` | `(ratio_latest / max(ratio over lookback) - 1) * 100` |
| `MA` | `ratio_latest >= SMA(20/50/200)` を満たす本数 / 計算可能なMA本数 |

`High Delta` の lookback は設定上 `756` 営業日です。
実際に取得済みの比率系列が756本未満なら、存在する本数だけを使います。

表示されていませんが、同じ処理で次の値も作られます。

| 内部値 | 定義 |
|---|---|
| `RATIO` | 最新の `IWO / IWN` 比率 |
| `REL 1W %` | `(ratio_latest / ratio_5営業日前 - 1) * 100` |
| `HIGH LOOKBACK DAYS` | `min(756, ratio系列の本数)` |
| `ABOVE MA COUNT` | `ratio_latest` が上回っている移動平均の数 |
| `MA COUNT` | 計算可能だった移動平均の数 |

Risk-On Ratio は現在の実装では表示専用です。
Market Conditions の総合スコアには直接入りません。
表示ラベルは、`1M` と `3M` はプラスなら Positive、マイナスなら Negative、0なら Neutral です。
`High Delta` は `-1%` 以上なら Positive、`-5%` 以下なら Negative、それ以外は Neutral です。
`MA` は全MAの上なら Positive、全MAの下なら Negative、それ以外は Neutral です。

### Factors vs SP500

Factors vs SP500 は、各ファクターETFの期間リターンからベンチマーク `SPY` の期間リターンを引いた相対リターンです。
現在の対象ファクターETFは、`VUG` Growth、`VTV` Value、`VYM` High Dividend、`MGC` Large Cap、`VO` Mid Cap、`VB` Small Cap、`MTUM` Momentum です。

各ETFと `SPY` の終値を日付で内部結合し、欠損を除外してから計算します。

```text
asset_return_p = (asset_latest / asset_p営業日前 - 1) * 100
spy_return_p   = (SPY_latest / SPY_p営業日前 - 1) * 100
REL p %        = asset_return_p - spy_return_p
```

期間 `p` は次の通りです。

| 内部列 | 期間 |
|---|---|
| `REL 1W %` | 5営業日 |
| `REL 1M %` | 21営業日 |
| `REL 1Y %` | 252営業日 |

画面上は `REL 1W %`、`REL 1M %`、`REL 1Y %` を表示します。
並び順は `REL 1M %` の降順、同点時は `REL 1W %` の降順です。

Factors vs SP500 も現在の実装では表示専用です。
Market Conditions の総合スコアには直接入りません。

## 候補レビューへの使い方

### 1. Market Conditions が強い場合

`Positive` 以上で、Breadth も広く、VIX と Safe Haven も悪くない場合は、Watchlist の duplicate candidates と Entry Ready を通常どおり確認します。
Momentum 系、Breakout 系、Pullback 系の候補を広めに見てもよい環境です。

### 2. Market Conditions は強いが Breadth が狭い場合

指数は強くても、SMA 50/200 や `20 > 50`, `50 > 200` が弱い場合は、相場が一部の大型株や一部テーマに偏っている可能性があります。
この場合は、Leadership と Factors vs SP500 を確認し、強いテーマに属する候補を優先します。

### 3. VIX や Safe Haven が悪い場合

Market Score が中立以上でも、VIX が悪化している、または Safe Haven が弱い場合は、候補をそのまま強気に扱わない方がよいです。
Entry Signal では `Entry Ready` でも、決算・ギャップ・出来高の質を追加確認します。

### 4. Risk-On Ratio が弱い場合

`IWO/IWN` が弱い場合、小型グロースや高ベータの候補は伸びにくい可能性があります。
この時は、Momentum Surge や Early Cycle 系よりも、流動性が高く、Core/Leadership と整合する候補を優先します。

### 5. Factors vs SP500 の使い方

Growth や Momentum が `SPY` に勝っているなら、Momentum / Breakout 系の候補を見やすい環境です。
Value や Dividend が強い時は、防御的・低ボラ寄りの相場になっている可能性があるため、高ベータの Entry Ready は慎重に扱います。

## 注意

Market Dashboard は候補の優先度を調整するための環境確認です。
最終的なチャート確認、リスク許容、ポジションサイズ、売買執行はこのシステムの対象外です。
