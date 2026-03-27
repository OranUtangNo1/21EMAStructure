# Implementation Plan

## 1. 実装方針

本システムのスコープは「候補抽出・順位付け・市場環境の可視化」に限定する。

エントリー評価、Structure Pivot、Position Sizing、売買管理は
TradingView 上で行うため、本システムには含まない。

---

## 2. フェーズ分割

### Phase 1: データ基盤 + 基本指標

目的:
- データ取得パイプラインの構築
- 全スキャンに必要な基本指標の計算

実装対象:
- price / profile / fundamental 取得（yfinance + FMP）
- EMA21 High / Low / Cloud
- SMA50 / SMA200
- ATR, ADR, DCR, Relative Volume
- RS5 / RS21 / RS63 / RS126
- Fundamental / Industry の仮スコア
- Hybrid Score
- キャッシュ基盤
- データソース状態追跡（live / cache_fresh / cache_stale / sample / missing）

成果物:
- 全指標が計算可能な状態
- データ品質レポート

---

### Phase 2: 9スキャン + Today's Watchlist

目的:
- 9スキャンの実装
- スキャン別カードグリッド UI の構築

実装対象:
- 9スキャンルール実装
- VCS 計算
- PP Count 計算
- 3WT 計算
- Trend Base 条件
- スキャン結果の Hybrid-RS 順ソート
- Today's Watchlist カードグリッド UI
- Earnings for today セクション

成果物:
- 9スキャン別のカードグリッド表示
- 各スキャン内は Hybrid-RS 順ソート
- 当日決算銘柄の表示

---

### Phase 3: 7リスト + duplicate tickers

目的:
- 7リスト構築
- 重複銘柄の自動集計

実装対象:
- 7リスト生成ロジック
- duplicate tickers 集計（3回以上出現）
- 重複銘柄の強調表示

成果物:
- 7リスト
- duplicate tickers の自動抽出
- 重複銘柄が目視で発見しやすい UI

---

### Phase 4: Market Dashboard

目的:
- 市場環境の可視化

実装対象:
- Market Conditions スコア（43 ETF ベース）
- Breadth & Trend Metrics
- Performance Overview
- HIGH & VIX
- Market Snapshot（RSP, QQQE, IWM, DIA, VIX, BTC + 21EMA位置ラベル）
- S5TH チャート
- Factors vs SP500
- 時間軸別スコア（1D/1W/1M/3M ago）

成果物:
- Market Dashboard 画面

---

### Phase 5: RS Radar

目的:
- セクター・業界の強弱可視化

実装対象:
- Sector Leaders テーブル（RS 4軸 + パフォーマンス + RS変化率 + 52W HIGH）
- Industry Leaders テーブル（同上 + MAJOR STOCKS）
- Top 3 RS% Change（Daily / Weekly）

成果物:
- RS Radar 画面

---

### Phase 6: 研究強化

目的:
- 日次比較
- パラメータ調整
- 品質改善

実装対象:
- run 保存と比較
- watchlist 日次差分表示
- scan-hit 履歴
- データ品質の時系列追跡
- config バージョン管理

成果物:
- 試行錯誤しやすい研究環境

---

## 3. MVP で外してよいもの

最初はなくてよい:
- 完全な Market Conditions の精密再現
- Industry RS の精密実装
- Fundamental Score の精密実装
- run 比較 UI
- 日次履歴追跡

---

## 4. 先に決めるべきこと

- 実装言語 / フレームワーク
- UI 方式（Streamlit 等）
- データ保存方式
- config 形式
- chart 描画方法（S5TH チャート等）

---

## 5. 推奨実装順

1. データ取得
2. データモデル定義
3. 21EMA High / Low / Cloud
4. 基本指標（ATR, ADR, DCR, RelVol, RS）
5. VCS / PP Count / 3WT
6. Hybrid Score 骨格
7. 9スキャン
8. Today's Watchlist カードグリッド UI
9. 7リスト + duplicate tickers
10. Market Dashboard
11. RS Radar

---

## 6. 検証の最初の問い

- Hybrid で並べると候補の質は上がるか
- duplicate tickers は有効か
- 9スキャンのカバレッジは十分か
- Market Conditions スコアは環境判断に使えるか
- RS Radar はセクターローテーションの把握に役立つか
- VCS は候補の質の向上に寄与するか
