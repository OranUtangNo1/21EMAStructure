# Scan and Watchlist Spec

## 1. 既知の 9 スキャン

### 1.1 21EMA scan
- Market Cap > 1B
- Avg Vol 50d > 1M
- Weekly % = 0 to 15%
- DCR% > 20%
- 21EMA at ATR -0.5R to +1R
- 50SMA at ATR 0R to 3R
- PP Count 30d > 1
- Trend Base

### 1.2 4% bullish
- Market Cap > 1B
- Avg Vol 50d > 1M
- Rel Vol > 1x
- Daily % > 4%
- From Open % > 0%
- RS 1M > 60

### 1.3 Vol Up
- Market Cap > 1B
- Avg Vol 50d > 1M
- Rel Vol > 1.5x
- Daily % > 0%

### 1.4 Momentum 97
- Avg Vol 50d > 1M
- 1W % change top 3% percentile ≥ 0.97（ユニバース横断パーセンタイル）
- 3M % change top 15% percentile ≥ 0.85（ユニバース横断パーセンタイル）
- Trend Base

### 1.5 97 Club
- Market Cap > 1B
- Avg Vol 50d > 1M
- Hybrid RS > 90（※ Hybrid RS を使用する唯一のスキャン条件）
- RS 1M > 97（旧RS）
- Trend Base

### 1.6 VCS
- Market Cap > 1B
- Avg Vol 50d > 1M
- VCS 60 to 100
- RS 1M > 60（旧RS）

### 1.7 Pocket Pivot
- Market Cap > 1B
- Avg Vol 50d > 1M
- Price > 50SMA
- green candle
- volume > highest volume in past 10 days

### 1.8 PP Count
- Market Cap > 1B
- Avg Vol 50d > 1M
- PP Count 30d > 3
- Trend Base

### 1.9 Weekly 20% plus gainers
- Market Cap > 1B
- Avg Vol 50d > 1M
- Weekly % > 20%

---

## 2. 共通要因

- ADR% フィルタ
- ex Healthcare

### 2.1 Trend Base
- Price > 50SMA
- 10WMA > 30WMA

### 2.2 Cockpit 由来の追加解釈
21EMA scan は、単なる screener 条件ではなく、
21EMA Cockpit Core Stats のうち以下と強く対応している。

- ADR%
- ATR 21EMA
- ATR 50SMA
- 21EMA Low %
- Trend Base

---

## 3. 21EMA Scan for Pine Screener の扱い

### 3.1 位置づけ
- Pine Screener 専用 indicator
- 標準の built-in screener では難しい条件を再現するためのもの

### 3.2 設計上の扱い
本システムでは TradingView 依存にはせず、同等条件をローカルで再現する。

### 3.3 実装上の示唆
- 全市場を直接スキャンするのではなく、まず対象ユニバース / 独自 watchlist を作る思想を持つ
- その上で detailed scan を走らせる

---

## 4. 実運用の 7 リスト

7リストはUIに直接表示しない。
裏側で集計し、duplicate tickers（3回以上出現した銘柄）を自動抽出するために使う。

### 4.1 リスト一覧と生成条件（仮定義）

| # | リスト名 | 生成条件 |
|---|---|---|
| 1 | Momentum 97 | Momentum 97 スキャン結果を流用 |
| 2 | Volatility Contraction Score | VCS スキャン結果を流用 |
| 3 | 21EMA Watch | 21EMA スキャン結果を流用 |
| 4 | 4% Gainers | 4% bullish スキャン結果を流用 |
| 5 | Relative Strength 21 > 63 | ユニバース内で RS21 > RS63 の銘柄（RS加速中）|
| 6 | Vol Up Gainers | Vol Up スキャン結果を流用 |
| 7 | High Est. EPS Growth | ユニバース内で EPS growth 上位銘柄 |

### 4.2 注意事項
- リスト 1〜4, 6 は9スキャン結果の流用
- リスト 5, 7 は独立した条件で生成
- 7リストの生成条件は仮定義であり、正確な条件が判明した時点で差し替える
- すべて configurable とする

---

## 5. duplicate tickers

### 5.1 定義
- **7リスト**中、3回以上出現した銘柄

### 5.2 扱い
- 優先監視対象
- Today's Watchlist 上で強調表示可能にする
- 7リスト自体はUIに表示しない（裏側集計のみ）

### 5.3 RS の二層構造との関係
- 9スキャンの条件内では旧RS（Raw RS）を使用
- スキャン結果のソートと7リストの生成にはHybrid RSを使用
- duplicate tickers は7リスト（Hybrid RS基準）に基づいて集計する

---

## 6. Watchlist 生成フロー

1. データ更新
2. 指標計算
3. 9スキャンまたは 7 リスト判定
4. scan hit 記録
5. duplicate tickers 集計
6. Hybrid Score でソート
7. earnings / PP Count / VCS / Cockpit Core Stats など補助情報を付与
8. watchlist candidate として表示

---

## 7. 順位付けルール

### 7.1 確定
- Hybrid Score でソートしている運用が確認されている

### 7.2 初期案
- primary: `overlap_count desc`
- secondary: `hybrid_score desc`
- tertiary: `vcs desc`
- quaternary: `cockpit_quality_score desc`
- quinary: `earnings proximity asc` または penalty

---

## 8. watchlist に表示すべき補助情報

- hit した scan 名一覧
- `overlap_count`
- `hybrid_score`
- `vcs`
- `earnings_in_7d`
- `pp_count_30d`
- `ema21_low_pct`
- `atr_21ema_zone`
- `atr_50sma_zone`
- `three_weeks_tight`
- `atr_pct_from_50sma`

---

## 9. 非公開部分の扱い

以下はパラメータ化する。
- 各 scan の閾値細部
- 7 リストと 9 スキャンの完全対応関係
- duplicate tickers の最終順位付け
- earnings 近接の扱い
- cockpit_quality_score の合成方法