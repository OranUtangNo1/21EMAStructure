# System Overview

## 1. 目的

本システムは、成長株トレード手法に基づく**スクリーニング・候補抽出プラットフォーム**である。

目的は以下の3つ。

1. 市場環境・業界・個別銘柄の強さを一体で把握する
2. スキャンに基づき候補銘柄を抽出・順位付けする
3. 毎日の候補リストを安定的に生成し、レビュー効率を高める

---

## 2. スコープ

### 2.1 本システムの責務

本システムの責務は、以下の3つの出力を毎日提供することに集約される。

1. **Market Dashboard**: 今日の市場環境はどうか
2. **RS Radar**: 今日どのセクター・業界が強いか
3. **Today's Watchlist**: 今日どの銘柄が複数の好条件を満たしているか

### 2.2 本システムのスコープ外

以下は本システムのスコープ外とする。
これらは TradingView 上のツール群（21EMA Cockpit, Structure Pivot, VCS, Position Size Calculator）で行う。

- エントリー評価・最終判断
- チャート上の構造分析（Structure Pivot, 21EMA Cloud の目視確認）
- ポジションサイジング
- 売買執行・フェーズ別イグジット管理
- ポートフォリオレベルのリスク管理

### 2.3 将来の拡張

entry/structure/risk に関する設計情報は `archived/` に隔離保存しており、
将来「エントリー判断システム」を別途構築する際の資産として使う。

---

## 3. 基本方針

### 3.1 固定するもの

公開情報から確定度が高い構造は固定する。

- 日足ベース
- 21EMA 構造（High / Low / Cloud）をスキャン条件の基盤として使用
- 9スキャンの存在と基本条件
- 7リスト重複（duplicate tickers）の考え方
- Hybrid Score の大枠（RS + Fundamental + Industry）
- VCS の位置づけ（圧縮状態の数値化）
- Market Conditions の基本構造（43 ETF ベースの breadth スコア）

### 3.2 固定しないもの

非公開または未確定部分はパラメータ化する。

- Fundamental Score の詳細式
- Industry RS の詳細式
- Market Conditions の集計式の詳細
- 各スキャンの閾値
- Hybrid の重み
- キャッシュ TTL

### 3.3 システムの性質

本システムは「完全再現アプリ」ではなく「研究・運用基盤」である。

---

## 4. 全体構造

本システムは以下の3層で構成する。

### 4.1 市場環境判定層

- Market Conditions（43 ETF ベースの breadth スコア）
- Breadth & Trend Metrics（SMA10/20/50/200 の % above 等）
- Performance Overview（YTD/1W/1M/1Y）
- HIGH & VIX（S2W HIGH, VIX）
- Market Snapshot（RSP, QQQE, IWM, DIA, VIX, BTC + 21EMA位置関係）
- S5TH チャート（S&P 500 % above 200SMA の時系列）
- Factors vs SP500（Growth, Value, High Dividend, Large/Mid/Small-Cap, Momentum, IPOs）
- Sector / Industry RS Radar

### 4.2 銘柄抽出層

- 9スキャン実行
- 候補銘柄抽出
- scan hit の記録

### 4.3 候補順位付け層

- Hybrid Score でスキャン結果をソート
- 7リスト構築
- duplicate tickers 集計（3回以上出現した銘柄を優先監視）
- earnings flag 付与
- スキャン別カードグリッドとして表示

---

## 5. この手法の本質

- 強い銘柄を見つける
- 強い業界に属する銘柄を優先する
- 成長性も加味して候補を絞る
- 21EMA 構造の指標をスキャン条件に活用する
- VCS や 3WT で収縮状態を確認する
- 複数スキャンに重複して出現する銘柄に注目する
- スクリーニング通過後の最終判断は TradingView 上で行う

---

## 6. 実装上の重要方針

### 6.1 分割単位

ロジックは以下の3分割を基本とする。

- Config
- Calculator / Scorer / Evaluator
- Result

### 6.2 試行錯誤前提

非公開部分は差し替え可能にし、比較実験できる構造を優先する。

### 6.3 データ品質の可視化

データソースの状態（live / cache_fresh / cache_stale / sample / missing）を
出力に含め、データ品質を常に把握できるようにする。

---

## 7. まず作るべきもの

1. データ取得
2. 基本指標（21EMA, SMA, ATR, ADR, DCR, RelVol, RS）
3. Hybrid Score 骨格
4. 9スキャン
5. Today's Watchlist UI（スキャン別カードグリッド）
6. Market Dashboard
7. RS Radar
