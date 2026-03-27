# Dashboard UI Spec

## 1. 目的

UI は以下の3つの出力を一体で提供する。

- 市場環境の把握（Market Dashboard）
- セクター・業界の強弱把握（RS Radar）
- 好条件銘柄の一覧（Today's Watchlist）

本システムの UI は「候補の発見と市場コンテキストの提供」に特化する。
個別銘柄の詳細評価（チャート構造、エントリー判断）は TradingView 上で行うため、
本システムには Main Chart / Cockpit Panel / Position Sizing Panel は含まない。

---

## 2. UI の基本方針

### 2.1 3画面構成

本システムは以下の3つの独立した画面で構成する。

1. **Market Dashboard** — 市場全体の健康状態
2. **RS Radar** — セクター・業界のリーダーシップ
3. **Today's Watchlist** — スキャン結果のカードグリッド

### 2.2 設計原則

- スキャン結果は詳細テーブルではなく、スキャン別カードグリッドで俯瞰する
- 重複出現する銘柄を目視で発見しやすい構成にする
- 各スキャン内は Hybrid-RS 順でソートする
- 詳細な指標比較は行わない（それは TradingView の役割）

---

## 3. Market Dashboard

### 3.1 Market Conditions

表示内容:

- Market Conditions スコア（0〜100）
- Market Conditions ラベル（Bearish / Negative / Neutral / Positive / Bullish）
- 時間軸別スコア（1D ago / 1W ago / 1M ago / 3M ago）
- ゲージ表示（現在スコアの視覚化）

スコアリング方式:

- 43 ETF を対象に、Breadth and Trend Metrics, Performance Overview, 52 week highs, VIX のポジティブシグナルの割合で算出

### 3.2 Breadth & Trend Metrics

表示内容:

- % above SMA10
- % above SMA20
- % above SMA50
- % above SMA200
- % SMA20 > SMA50
- % SMA50 > SMA200

各指標に Positive / Neutral / Negative のラベルを付与する。

### 3.3 Performance Overview

表示内容:

- % YTD
- % 1W
- % 1M
- % 1Y

各指標に Positive / Neutral / Negative のラベルを付与する。

### 3.4 HIGH & VIX

表示内容:

- S2W HIGH（2週間新高値の割合）
- VIX

### 3.5 Market Snapshot

表示内容:

- S&P 500 Equal Weight (RSP) — 価格、日次変化率、Volume % vs 50d Avg、21EMA位置ラベル
- NASDAQ 100 Equal Weight (QQQE) — 同上
- Russell 2000 (IWM) — 同上
- Dow Jones (DIA) — 同上
- Volatility (VIX) — 値、日次変化率、21EMA位置ラベル
- Bitcoin (BTC) — 価格、日次変化率、Volume % vs 50d Avg、21EMA位置ラベル

21EMA位置ラベル:

- `↘ 21EMA Low`: 価格が 21EMA Low を下回っている
- `↗ 21EMA High`: 価格が 21EMA High を上回っている
- `↔ 21EMA Cloud`: 価格がクラウド内

### 3.6 S5TH チャート

表示内容:

- S&P 500 Stocks > 200-Day Moving Average (S5TH) の時系列チャート
- ローソク足表示
- 参考ラインの表示

### 3.7 Factors vs SP500

表示内容:

- Growth — 相対パフォーマンスバー、変化率
- Value — 同上
- High Dividend — 同上
- Large-Cap — 同上
- Mid-Cap — 同上
- Small-Cap — 同上
- Momentum — 同上
- IPOs — 同上

---

## 4. RS Radar

### 4.1 Top 3 RS% Change

表示内容:

- Top 3 RS% Change (Daily) — RS, ティッカー、業界名、価格、日次変化率
- Top 3 RS% Change (Weekly) — RS, ティッカー、業界名、価格、週次変化率

### 4.2 Sector Leaders テーブル

カラム:

- RS（総合）
- 1D（日次RS）
- 1W（週次RS）
- 1M（月次RS）
- TICKER
- NAME
- DAY %
- WK %
- MTH %
- RS DAY%
- RS WK%
- RS MTH%
- 52W HIGH

### 4.3 Industry Leaders テーブル

カラム:

- RS（総合）
- 1D
- 1W
- 1M
- TICKER
- NAME
- DAY %
- WK %
- MTH %
- RS DAY%
- RS WK%
- RS MTH%
- 52W HIGH
- MAJOR STOCKS（上位3銘柄のティッカー）

---

## 5. Today's Watchlist

### 5.1 基本構成

- 日付表示（例: March 20, 2026）
- ソート基準表示（例: Sorted by Hybrid-RS）
- 9スキャン別のカードグリッド
- Earnings for today セクション

### 5.2 スキャンカード

各スキャンは独立したカードとして表示する。

カード内容:

- スキャン名（例: 21EMA, 4% bullish, Vol Up ...）
- ヒット数（例: 26 tickers）
- ティッカーのグリッド表示（Hybrid-RS 順ソート）

### 5.3 9スキャンカード

1. **21EMA** — 21EMA 構造に基づくセットアップ候補
2. **4% bullish** — 当日4%以上上昇 + RS + 出来高
3. **Vol Up** — 出来高増加 + 上昇
4. **Momentum 97** — 短期・中期モメンタム上位
5. **97 Club** — Hybrid RS 上位 + RS 1M 上位
6. **VCS** — ボラティリティ圧縮スコア上位
7. **Pocket Pivot** — 当日 Pocket Pivot 発生
8. **3+ Pocket Pivots (30d)** — 過去30日で PP 3回以上
9. **Weekly 20% + Gainers** — 週間20%以上上昇

### 5.4 Earnings for today (liquid)

- 当日決算発表予定の流動性のある銘柄を独立セクションで表示
- ヒット数とティッカーグリッド

### 5.5 ユーザーの使い方

1. 各スキャンカードを俯瞰する
2. **複数のカードに重複して出現する銘柄**に注目する（= duplicate tickers の実運用）
3. 注目銘柄を TradingView に持っていき、21EMA Cockpit で詳細評価する

---

## 6. ソート

- 各スキャンカード内は `hybrid_score desc` でソート
- duplicate tickers の自動集計は内部で行い、重複銘柄は特別表示可能にする

---

## 7. Market Conditions スコアリング詳細

### 7.1 基本構造

- 43 ETF を対象
- Breadth and Trend Metrics、Performance Overview、52 week highs、VIX のポジティブシグナル割合

### 7.2 非公開のためパラメータ化

- 対象 ETF リスト
- 各メトリクスの Positive / Negative 判定閾値
- component weights
- label thresholds（Bearish / Negative / Neutral / Positive / Bullish の境界値）

---

## 8. 更新情報

- 各画面に `Updated: HH:MM:SS` を表示
- データの鮮度を常に把握できるようにする
