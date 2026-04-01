# スキャン結果不一致の原因分析

## 概要

原典（TradingView Pine Script）のスキャン結果と、現在のPythonアプリケーション（OraTek）のスキャン結果が一致しない原因を、原典コードとアプリ仕様の逐条比較に基づき分析しました。

不一致の原因は以下の6カテゴリに分類されます。

---

## 1. Relative Strength（RS）の計算方式が根本的に異なる

**影響を受けるスキャン: 4% Bullish, 97 Club, VCS scan**

これが最大の不一致要因です。

### 原典の方式（3種類が存在）

**A. RS Percentile Histogram（スキャンの「RS 1M」で使用）**
- `price_ratio = close / benchClose`（SPY）
- そのprice_ratioの**時系列に対するpercentrank**を計算
- lookback = 26日（1Mモード）
- `ta.percentrank(close, 26)` を spread symbol `TICKER / SPY` に対して実行
- 出力: 0〜100のパーセンタイル（**その銘柄自身の過去26日間内での相対位置**）

**B. IBD Style RS Rating（Fred6725方式）**
- 4四半期のパフォーマンス比率を計算（63/126/189/252日）
- 重み付け: `0.4 * Q1 + 0.2 * Q2 + 0.2 * Q3 + 0.2 * Q4`
- 銘柄のスコアをSPXのスコアで割る
- 得られた `totalRsScore` を、**全米約6,600銘柄の分布曲線**に基づいて1〜99のパーセンタイルに変換
- 変換カーブは `request.seed()` で外部データから毎日更新される7つの閾値で定義

**C. Relative Strength Table（21EMA Scanで使用）**
- spread symbol `TICKER / SPY` を構成
- `ta.percentrank(close, 21)` をそのspreadに対して計算
- これも**その銘柄自身の過去N日間における相対位置**

### 現在のアプリの方式

- `price_ratio = stock_close / benchmark_close`
- lookback windowの末端値を取得し、`percentile` 正規化
- `rs*` = `raw_rs*`（正規化前後で同一値）
- **パーセンタイルの母集団が不明確**

### 不一致の核心

| 観点 | 原典 | アプリ |
|------|------|--------|
| RS 1M (21日) | `ta.percentrank(spread, 21)` = その銘柄の過去21日間内での順位 | price_ratioのlookback windowの末端値をcross-sectional percentileに変換？ |
| パーセンタイルの母集団 | 時系列（その銘柄自身の過去N日間） | 横断面（同日の全銘柄）かもしれないが仕様上不明確 |
| IBD RS Rating | 全米6,600銘柄の分布カーブで変換 | 未実装 |
| seed更新 | 毎日自動更新される閾値 | 静的な計算のみ |

**結論**: 原典の `RS 1M > 60` は「その銘柄のprice ratioが過去21日間の60パーセンタイル以上」を意味しますが、アプリの `raw_rs21 > 60` は異なる計算に基づいている可能性が高く、同じ銘柄が閾値を超えるか否かが変わります。

---

## 2. VCS（Volatility Contraction Score）の計算ロジックの差異

**影響を受けるスキャン: VCS scan**

### 原典のVCS計算

```
A. Price Compression: trShort/trLong（True Rangeベース）
B. Price Stability: stdShort/stdLong（標準偏差ベース）
C. Volume Contraction: volShort(5日)/volAvg
D. Efficiency Filter: |netChange| / totalTravel → trendFactor
E. Structure Check: Higher Low判定（lowRecent >= lowBase）

rawScore = (s_atr * 0.4) + (s_std * 0.4) + (s_vol * 0.2)
filteredScore = rawScore * trendFactor
physicsScore = min(100, filteredScore * 100)
smoothPhysics = EMA(physicsScore, 3)  ← EMA平滑化あり

consistencyBonus = min(bonusMax, daysTight)  ← 70以上が連続する日数
finalScore = smoothPhysics * (85/100) + consistencyBonus
→ Higher Low失敗時: finalScore * 0.75（penaltyFactor）
```

### アプリのVCS計算

```
- close-to-closeリターンからshort/long volatilityを計算
- (high-low)/closeからshort/long average rangeを計算
- short/long average volumeを計算
- contractionを報酬
- volume bonus（短期 < 長期のとき）
- trend penalty（close < sma50のとき）
- clip [0, 100]
```

### 不一致ポイント

| 要素 | 原典 | アプリ |
|------|------|--------|
| Price Compression入力 | True Range (`ta.tr(true)`) | close-to-closeリターン |
| Price Stability入力 | `ta.stdev(close, N)` | 仕様に記載なし（rangeベース？） |
| 平滑化 | `EMA(physicsScore, 3)` | 記載なし |
| Efficiency Filter | `|netChange| / totalTravel` でトレンドペナルティ | `close < sma50` でトレンドペナルティ |
| Structure Check | Higher Low: `lowRecent >= lowBase` → 失敗時 `* 0.75` | 記載なし |
| Consistency Bonus | `min(15, daysTight)`（70超え日数） | 記載なし |
| スコア配分 | `s_atr*0.4 + s_std*0.4 + s_vol*0.2` | 不明 |

**結論**: VCSの構成要素、入力データ、ペナルティロジック、ボーナスロジックがすべて異なるため、同じ銘柄でもスコアが大幅に乖離します。特にEMA平滑化、Higher Low構造チェック、Consistency Bonusの有無は大きな差異を生みます。

---

## 3. Momentum 97 スキャンのパーセンタイル母集団の差異

**影響を受けるスキャン: Momentum 97**

### 原典の定義

```
1W % change: top 3% percentile ≥ 0.97
3M % change: top 15% percentile ≥ 0.85
```

### アプリの実装

```
weekly_return_rank >= 97.0
quarterly_return_rank >= 85.0
（enrich_with_scan_context() による cross-sectional percentile rank）
```

### 不一致ポイント

- 原典の「top 3% percentile」は、Pine Screenerの全銘柄（数千銘柄）に対するパーセンタイル
- アプリの `weekly_return_rank` は、ローカルユニバース（Finvizで取得した銘柄群、pre-filter済み）内でのcross-sectional rank
- **母集団が異なる**: 原典は全市場、アプリはフィルタ後のユニバース（時価総額1B以上、出来高1M以上、ADR 3.5-10%、Healthcare除外済み）
- pre-filter済みユニバースでの97パーセンタイルは、全市場での97パーセンタイルとは異なる銘柄を拾う

---

## 4. スキャン条件の微妙な差異（個別ルール）

### 4.1 21EMA スキャン

| 条件 | 原典 | アプリ | 差異 |
|------|------|--------|------|
| Weekly % | 0 to 15% | `weekly_return >= 0.0 AND <= 15.0` | 一致 |
| DCR% | >20% | `dcr_percent > 20.0` | 一致 |
| 21EMA ATR zone | -0.5R to +1R | `-0.5 <= atr_21ema_zone <= 1.0` | 一致 |
| 50SMA ATR zone | 0R to 3R | `0.0 <= atr_50sma_zone <= 3.0` | 一致 |
| PP Count 30d | >1 | `pp_count_30d > 1` | 一致 |
| Trend Base | Price>50SMA, 10WMA>30WMA | `trend_base == True` | **要確認**: WMAの計算方法 |

### 4.2 4% Bullish

| 条件 | 原典 | アプリ | 差異 |
|------|------|--------|------|
| Rel Vol | >1x | `rel_volume >= 1.0` | 一致 |
| Daily % | >4% | `daily_change_pct >= 4.0` | 一致 |
| From Open % | >0% | `from_open_pct > 0.0` | 一致 |
| RS 1M | >60 | `raw_rs21 > 60.0` | **不一致**: RS計算方式が異なる（セクション1参照） |

### 4.3 VCS スキャン

| 条件 | 原典 | アプリ | 差異 |
|------|------|--------|------|
| VCS | 60 to 100 | `vcs >= 60.0` | **不一致**: 上限100チェックなし + VCS計算自体が異なる（セクション2参照） |
| RS 1M | >60 | `raw_rs21 > 60.0` | **不一致**: RS計算方式が異なる |

### 4.4 97 Club

| 条件 | 原典 | アプリ | 差異 |
|------|------|--------|------|
| Hybrid RS | >90 | `hybrid_score >= 90.0` | **要検証**: Hybrid構成が原典と合致しているか |
| RS 1M | >97 | `raw_rs21 >= 97.0` | **不一致**: RS計算方式が異なる |
| Trend Base | 同上 | `trend_base == True` | 要確認 |

### 4.5 Momentum 97

原典には `Market Cap >1B` 条件がない（`Avg Vol 50d >1M` のみ）が、アプリではpre-scan filterで `market_cap >= 1B` が適用されている。原典ではMomentum 97だけは時価総額フィルタなしで広い母集団から拾っている可能性がある。

---

## 5. データソースとユニバースの差異

### 5.1 ユニバースの構成

| 観点 | 原典 | アプリ |
|------|------|--------|
| スキャン対象 | TradingView Pine Screener（全米上場銘柄） | Finviz weekly snapshot → local filter |
| 銘柄数 | 約6,600+ | Finviz取得数に依存 |
| フィルタ順序 | Pine Screener内で各スキャン条件を直接適用 | pre-scan universe filter → scan rules |

- Finvizのスナップショットが全銘柄を網羅していない場合、そもそもスキャン対象に含まれない銘柄が存在する
- 週次更新のため、IPOや新規上場銘柄が漏れる

### 5.2 価格データの差異

| 観点 | 原典 | アプリ |
|------|------|--------|
| データソース | TradingView（リアルタイム） | Yahoo Finance（遅延あり） |
| 配当調整 | TradingViewの設定依存 | yfinanceのadj close依存 |
| 分割調整 | 自動 | yfinanceの品質依存 |
| 出来高 | 取引所データ | yfinanceデータ |

配当調整や分割調整の差異は、長期lookback（126日、252日）のRS計算で特に影響が大きくなります。

### 5.3 ファンダメンタルデータ

| 観点 | 原典 | アプリ |
|------|------|--------|
| EPS/Revenue | FMP (starter plan) + TradingView financials | Yahoo Finance fallback、FMP未実装 |
| Missing値 | スクリーナーでN/A除外 | `fill_neutral` = 50で補完 |

ファンダメンタルデータの欠損を50で補完するアプリの方式は、Hybrid ScoreとFundamental Scoreに影響し、97 Clubの `hybrid_score >= 90` 判定に直接影響します。

---

## 6. Hybrid Score の構成差異

**影響を受けるスキャン: 97 Club**

### 原典の定義

```
Hybrid RS = RS (3 timeframes) + Fundamental RS + Industry RS
重み: 5 (1:2:2) : 2 : 3
```

つまり: `(rs21*1 + rs63*2 + rs126*2 + fundamental*2 + industry*3) / 10`

### アプリの実装

```
Hybrid = (rs21*1 + rs63*2 + rs126*2 + fundamental_score*2 + industry_score*3) / 10
```

**構造は一致**していますが、各構成要素の計算方式が異なるため、結果が異なります。

| 構成要素 | 影響 |
|----------|------|
| rs21/63/126 | RS計算方式の差異（セクション1） |
| fundamental_score | データソースと欠損補完方式の差異（セクション5.3） |
| industry_score | industry_aggregation_methodの差異 + RSの差異が伝播 |

---

## 影響度サマリー

| 不一致原因 | 影響度 | 影響スキャン数 |
|------------|--------|---------------|
| RS計算方式の根本差異 | **最大** | 4 (4%Bullish, 97Club, VCS, Momentum97間接) |
| VCS計算ロジックの差異 | **大** | 1 (VCS scan) |
| パーセンタイル母集団の差異 | **大** | 1 (Momentum 97) |
| ユニバース構成の差異 | **中** | 全9スキャン |
| データソース品質差異 | **中** | 全9スキャン |
| Hybrid Score構成要素の連鎖差異 | **中** | 1 (97 Club) |
| ファンダメンタル欠損補完 | **小〜中** | 1 (97 Club) |

---

## 推奨対応の優先順位

### P0: RS計算の整合

1. 原典の `ta.percentrank(spread, 21)` の挙動を正確に再現する
2. これは**時系列パーセンタイル**（その銘柄の過去21日間のprice ratioの中で、今日がどの位置にあるか）
3. アプリの `raw_rs21` が同じロジックで計算されているか検証し、異なる場合は修正

### P1: VCS計算の整合

1. True Rangeベースの圧縮計算に切り替え
2. EMA(3)平滑化を追加
3. Efficiency Filter（`|netChange|/totalTravel`）を実装
4. Higher Low構造チェックとpenaltyFactorを実装
5. Consistency Bonus（70超え連続日数）を実装

### P2: Momentum 97のパーセンタイル母集団

1. `weekly_return_rank` と `quarterly_return_rank` の計算を、pre-filter前の全ユニバースで行うか、原典と同じ母集団で行うかを決定

### P3: ユニバースカバレッジ

1. FMPプロバイダーの実装で銘柄カバレッジを拡大
2. 週次スナップショットの更新頻度を検討
