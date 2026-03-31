# Indicators and Scoring

## 1. 主要指標一覧

- EMA21 High
- EMA21 Low
- EMA21 Close
- 21EMA Cloud
- SMA50
- SMA200
- ATR
- ADR%
- DCR%
- Relative Volume
- RS5
- RS21
- RS63
- RS126
- Fundamental Score
- Industry RS
- Hybrid Score
- VCS
- PP Count 30d
- 3WT
- ATR% from 50SMA
- 21EMA Low %

---

## 2. EMA21 High / Low / Close

### 2.1 定義
- `EMA21 High = EMA(high, 21)`
- `EMA21 Low = EMA(low, 21)`
- `EMA21 Close = EMA(close, 21)`

### 2.2 役割
- `EMA21 Low` は stop / trail の中心
- `EMA21 High` と `EMA21 Low` は 21EMA Cloud を構成
- `EMA21 Close` は補助的トレンド確認に使える

### 2.3 重要仕様
本手法でいう `21EMA Low` は、単なる終値EMAではなく、**安値ベースの 21EMA** として扱う。

### 2.4 パラメータ
- `ema_period`
- `ema_high_source`
- `ema_low_source`
- `ema_close_source`

---

## 3. 21EMA Cloud

### 3.1 定義
- `21EMA Cloud = band(EMA21 High, EMA21 Low)`

### 3.2 用途
- トレンド環境確認
- 価格がクラウド内 / 上にあるかを確認
- support 帯の可視化
- Main Chart 側で表示

### 3.3 パラメータ
- `show_ema21_cloud`
- `ema_cloud_fill_style`

---

## 4. ATR

### 4.1 用途
- 21EMA からの距離判定
- 10WMA からの距離判定
- 50SMA からの距離判定
- ボラ把握
- リスク評価

### 4.2 パラメータ
- `atr_period = 14`
- `atr_source`

---

## 5. ADR%

### 5.1 位置づけ
- 適度なボラ銘柄を抽出するユニバース共通フィルタ

### 5.2 初期デフォルト
- average daily range % を使用
- `ADR% = 100 * (SMA(high/low, adr_period) - 1)`

### 5.3 ユニバースフィルタ基準
- 3.5% 〜 10.0%（原典: "ADR% 3.5 to 10"）

### 5.4 パラメータ
- `adr_period = 20`（VCS ソースコード / Pine Screener コード準拠）
- `adr_formula`
- `adr_filter_min = 3.5`
- `adr_filter_max = 10.0`

---

## 6. DCR%

### 6.1 位置づけ
- 日中レンジに対する終値位置の強さを見る

### 6.2 仮置きデフォルト
- `(close - low) / (high - low) * 100`

### 6.3 パラメータ
- `dcr_formula`

---

## 7. Relative Volume

### 7.1 仮置きデフォルト
- `today_volume / average_volume_50d`

### 7.2 パラメータ
- `relvol_period`

---

## 8. ATR-based Zone Metrics

### 8.1 ATR 21EMA
現在価格と `EMA21 Close`（close ベースの 21EMA）との距離を ATR 基準で評価する。
計算式: `dist_21_atr = (close - ema21) / atr`

#### 良好ゾーン
- `-0.5 ATR 〜 +1.0 ATR`
- 基本的にここが緑の時にエントリーを検討する

### 8.2 ATR 10WMA
週足 10WMA との距離を ATR 基準で評価する。
計算式: `dist_10w_atr = (close - wma10w) / atr`

#### 良好ゾーン（21EMA Cockpit ソースコード準拠）
- `-0.5 ATR 〜 +1.0 ATR`（ATR 21EMA と同じゾーン設定を共有）

#### 位置づけ
- 21EMA を一時的に割っても、10WMA で支えられている（ここが緑）なら、より深い押し目買いのチャンスとなる可能性がある

### 8.3 ATR 50SMA
現在価格と 50SMA の距離を ATR 基準で評価する。
計算式: `dist_50_atr = (close - sma50) / atr`

#### 良好ゾーン
- `0 〜 +3.0 ATR`
- 50SMA から ATR 3R 以上離れるとエントリーは遅い可能性があり、リスクが高くなる

### 8.4 パラメータ
- `atr_zone_min = -0.5`（21EMA と 10WMA で共有）
- `atr_zone_max = 1.0`（21EMA と 10WMA で共有）
- `atr_50sma_good_max = 3.0`

---

## 9. 21EMA Low %

### 9.1 定義
- price >= ema21_low の場合:
  `ema21_low_pct = (close - ema21_low) / ema21_low * 100`
- price < ema21_low の場合:
  `ema21_low_pct = (close - ema21_low) / close * 100`
- （21EMA Cockpit ソースコード準拠）

### 9.2 用途
- 初期リスクの見える化
- position sizing の判断
- フルサイズ / 縮小 / 見送り の区分

### 9.3 初期運用基準
- `<= 5%`: フルエントリー候補
- `> 5% and <= 8%`: サイズ調整候補
- `> 8%`: 見送り候補

### 9.4 パラメータ
- `ema21_low_pct_full_max = 5.0`
- `ema21_low_pct_reduce_max = 8.0`

---

## 10. RS5 / RS21 / RS63 / RS126

### 10.1 RS の二層構造

本システムでは RS を2つのレイヤーで扱う。

- **旧RS（Raw RS）**: price ratio の percentile rank。9スキャンの条件（RS 1M > 60 等）で使用
- **Hybrid RS**: 旧RS + Fundamental Score + Industry Score の加重合成。ソート順 + 97 Club 条件 + 7リストで使用

### 10.2 旧RS の定義
- benchmark は `SPY`
- `price_ratio = stock_close / benchmark_close`
- 各 lookback 期間で、**その銘柄自身の過去 ratio 時系列**に対する percentile rank を算出
- 0〜100 スコアとする
- RS 80 = 対SPY比率が過去の中で上位20%の位置

### 10.2 期間
- 5日
- 21日
- 63日
- 126日

### 10.3 運用上の役割
- Hybrid は `21 / 63 / 126` を採用
- `RS5` は補助列として短期相対強度の確認に使える

### 10.4 初期ハイライト基準
- `>= 80`: 強い
- `<= 39` または `<= 40`: 弱い

### 10.5 パラメータ
- `benchmark_symbol`
- `rs_lookbacks = [5, 21, 63, 126]`
- `rs_normalization_method`
- `rs_strong_threshold = 80`
- `rs_weak_threshold = 39`

### 10.6 IBD Style RS Rating（参考情報）

Pine Screener のコード内に、Fred6725 ロジックによる IBD Style RS Rating の計算が存在する。
重み付けは `0.4*63日 + 0.2*126日 + 0.2*189日 + 0.2*252日` の相対パフォーマンス。
RS Radar の Sector/Industry Leaders テーブルの「RS」列がこれに該当する可能性がある。

現時点では本システムのスキャン条件には使用しない（旧RS + Hybrid RS で運用）。
RS Radar の実装時に、この RS Rating の採用を検討する。

---

## 11. Fundamental Score

### 11.1 確定していること
- `EPS growth`
- `revenue growth`
に基づくスコア

### 11.2 非公開のため固定しないこと
- 具体的な期間
- 正規化方法
- EPS と売上の重み
- estimate 利用有無

### 11.3 初期デフォルト（仮定義）
- EPS growth と revenue growth を均等加重
- 各指標をユニバース内パーセンタイルランクに変換（0〜100）
- `FundamentalScore = (eps_percentile + revenue_percentile) / 2`
- データ欠損時は neutral(50) で fill

### 11.4 パラメータ
- `fundamental_metrics`
- `eps_growth_period`
- `revenue_growth_period`
- `use_estimates`
- `eps_weight`
- `revenue_weight`
- `fundamental_normalization_method`
- `missing_fundamental_policy`

---

## 12. Industry RS

### 12.1 確定していること
- industry 単位の相対力スコア
- 大規模ユニバース集計を前提とする
- industry 粒度優先

### 12.2 非公開のため固定しないこと
- 集約方式
- 加重方法
- 入力指標
- 正規化方式

### 12.3 初期デフォルト（仮定義）
- 同一 industry に属する銘柄の RS21 平均を算出
- industry 間でパーセンタイルランクに変換（0〜100）
- `IndustryScore = percentile_rank(industry_avg_rs21)`

### 12.4 パラメータ
- `industry_classification_source`
- `industry_aggregation_method`
- `industry_rs_input_metric`
- `industry_score_normalization_method`

---

## 13. Hybrid Score

### 13.1 目的
- 候補銘柄の優先順位付け
- ソート
- 内訳比較

### 13.2 構成要素
- `RS21`
- `RS63`
- `RS126`
- `Fundamental Score`
- `Industry RS`

### 13.3 重み
- `RS(3期間) : Fundamental : Industry = 5 : 2 : 3`
- RS 内部 = `1 : 2 : 2`

### 13.4 初期合成式

```text
HybridScore =
(
  RS21 * 1 +
  RS63 * 2 +
  RS126 * 2 +
  FundamentalScore * 2 +
  IndustryScore * 3
) / 10
13.5 表示内訳
H = Hybrid
F = Fundamental
I = Industry
21 = RS21
63 = RS63
126 = RS126
13.6 パラメータ
rs_weights
fundamental_weight
industry_weight
hybrid_rounding_policy
hybrid_missing_value_policy
14. VCS
14.1 位置づけ
圧縮状態の成熟度を数値化する補助指標
単独エントリーシグナルではない
14.2 用途
候補抽出
優先度加点
breakout 候補の圧縮度確認
14.3 仮置き運用
60以上で候補
80以上で強い圧縮状態
14.4 パラメータ
vcs_threshold_candidate
vcs_threshold_priority
len_short
len_long
len_volume
sensitivity
trend_penalty_weight
bonus_max
15. PP Count 30d
15.1 定義
過去 30 営業日内の Pocket Pivot 発生回数
15.2 用途
scan 条件
補助情報表示
15.3 パラメータ
pp_count_window_days
pocket_pivot_definition_variant
16. 3-Weeks Tight
16.1 位置づけ
O’Neil 系の収縮確認
Cockpit Core Stats の補助判定
16.2 用途
VCP 的な締まり具合の可視化
setup の質の補強
16.3 判定ロジック（21EMA Cockpit ソースコード準拠）
直近3週の週足終値 w_c0, w_c1, w_c2 について:
- abs(w_c0 - w_c1) / w_c1 * 100 <= threshold
- abs(w_c1 - w_c2) / w_c2 * 100 <= threshold
両方を満たせば true
16.4 パラメータ
enable_3wt
three_weeks_tight_pct_threshold = 1.5
17. ATR% from 50SMA
17.1 位置づけ
過熱判定
部分利確の補助
17.2 計算式（21EMA Cockpit ソースコード準拠）
gain_from_ma_pct = (close / sma50) - 1.0
atr_pct_daily = atr / close
atrx_from_sma50 = gain_from_ma_pct / atr_pct_daily

ATR 50SMA（ATR何個分離れているか）との違い:
ATR% from 50SMA は、株価が上昇して50SMAより高くなればなるほど、
単純な距離よりもさらに数値が大きくなる計算式である。
17.3 初期基準
>= 7 で過熱の補助シグナル
段階的な色分け: 7 / 8 / 9 / 10 / 11
17.4 パラメータ
atr_pct_from_50sma_overheat = 7.0
show_overheat_dot = true