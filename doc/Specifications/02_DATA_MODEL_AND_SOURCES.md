# Data Model and Sources

## 1. データソース

### 1.1 役割分担

| ソース | 役割 | コスト |
|---|---|---|
| finviz | 銘柄リスト、属性（MCap, sector, industry）、ファンダメンタル（EPS growth, Sales growth, earnings date） | 無料 |
| yfinance | 日次価格（OHLCV）のバルク取得 | 無料 |

### 1.2 設計原則
- finviz Screener で MCap>1B + ex Healthcare のフィルタ済みリストを一括取得（属性+ファンダメンタル込み）
- yfinance は価格データのバルクダウンロード専用
- ローカルキャッシュを最大限活用し、API コール数を最小化する
- 完全無料構成（FMP 不要）

### 1.3 ベンチマーク
- デフォルト: SPY

### 1.4 特記事項
- RS 計算は SPY ベンチマークとの比較
- RS% はパーセンタイルランク（銘柄自身の過去 ratio 時系列内での順位）
- RS Radar のセクター／業界RSはETFベースで算出
- finviz のデータは 15分遅延（NASDAQ）/ 20分遅延（NYSE, AMEX）だが、週次取得なので問題なし

---

## 2. ユニバース定義

### 2.1 スキャン用ユニバース（仮定義）

9スキャンを走らせる母集団。以下の条件で構築する。

#### 確定条件（9スキャンの共通条件から逆算）

- Market Cap > 1B（8/9スキャンで明示、Momentum 97 のみ未指定）
- Avg Vol 50d > 1M（全9スキャン共通）
- ADR% 3.5 〜 10（共通フィルタとして明記）
- Sector != Healthcare（共通フィルタ: ex Healthcare）

#### 仮定義条件（今後検証・調整する）

- 対象取引所: NYSE, NASDAQ, AMEX
- 証券種別: 普通株（Common Stock）のみ
- 除外対象: ETF, SPAC, Warrant, Unit, Preferred, Rights
- 最低株価: 明示フィルタなし（Market Cap > 1B で実質カバー）

#### 想定規模

- フィルタ前の全米普通株: 約 7,000 銘柄
- Market Cap > 1B + Avg Vol > 1M 後: 約 2,000 銘柄
- ADR% 3.5〜10 + ex Healthcare 後: 約 1,500 銘柄（= スキャン対象ユニバース）

#### データ取得量の目安

| データ種別 | 銘柄数 | 取得頻度 |
|---|---|---|
| 銘柄リスト + 属性 | ~7,000 | 週1回（キャッシュ） |
| 日次価格（スキャン対象） | ~1,500 | 毎日 |
| ファンダメンタル | ~1,500 | 24時間キャッシュ |
| ETF群（Dashboard / Radar / Factors / Snapshot） | ~100 | 毎日 |
| 合計日次取得 | ~1,600 | |

### 2.2 Market Dashboard 用ユニバース

Market Conditions スコア算出に使う 43 ETF の集合。
具体的なリストは非公開のためパラメータ化する。

参考として、Relative Strength Table のデフォルトプリセットは以下の16セクターETF:
QQQ, QQQE, RSP, DIA, IWM, XLV, XLE, XLF, XLRE, XLB, XLP, XLU, XLY, XLK, XLC, XLI

### 2.3 RS Radar 用ユニバース

- Sector Leaders: セクターETF（上記プリセット等）
- Industry Leaders: 業界ETF（カスタム設定）
- MAJOR STOCKS: 各業界内の代表銘柄（時価総額上位等）

### 2.4 Market Snapshot 用シンボル

- RSP（S&P 500 Equal Weight）
- QQQE（NASDAQ 100 Equal Weight）
- IWM（Russell 2000）
- DIA（Dow Jones）
- VIX（Volatility）
- BTC（Bitcoin）

### 2.5 Factors vs SP500 用 ETF

Growth, Value, High Dividend, Large-Cap, Mid-Cap, Small-Cap, Momentum, IPOs
の各ファクターに対応するETFを設定する。（具体的なETFはパラメータ化）

### 2.6 ユニバース調整パラメータ

以下はすべて configurable とする:
- 対象取引所リスト
- 証券種別フィルタ
- 除外セクターリスト
- Market Cap 下限
- Avg Volume 下限
- ADR% 範囲
- 最低株価（必要に応じて追加）
- Market Conditions 用 ETF リスト
- RS Radar 用セクター/業界 ETF リスト
- Market Snapshot 用シンボルリスト
- Factor ETF リスト

---

## 3. 必要データ

### 3.1 個別銘柄 — 日次価格データ
- open, high, low, close, adjusted_close, volume

### 3.2 個別銘柄 — 属性
- ticker, name, market_cap, sector, industry, ipo_date

### 3.3 個別銘柄 — ファンダメンタル
- EPS growth, revenue growth, earnings date

### 3.4 市場 / ベンチマーク
- SPY（RS計算用）
- VIX（Market Dashboard用）
- セクター / 業界 / ファクター ETF 群（RS Radar, Factors用）
- Market Snapshot 用シンボル群（RSP, QQQE, IWM, DIA, BTC）
- S5TH（S&P 500 % above 200SMA、breadthチャート用）

### 3.5 銘柄リスト
- 全米普通株リスト（ユニバース構築の起点）
- 取得元: FMP, Nasdaq API, またはキャッシュ

---

## 4. データ取得戦略

### 4.1 2段階取得による効率化

```
Stage 1: フィルタ済み銘柄リスト + 属性 + ファンダメンタル（週1回）
  finviz Screener → MCap>1B, ex Healthcare でフィルタ済み
  → ticker, sector, industry, MCap, EPS growth, Sales growth, earnings date を一括取得
  → ~2,000銘柄

Stage 2: 日次価格（毎日）
  yfinance バルクダウンロード → ~2,000銘柄 + ~100 ETF の当日OHLCV
  → ローカルキャッシュに追記
  → Avg Vol, ADR% はローカルデータから計算し、~1,500に絞る
```

### 4.2 具体的な取得フロー

| ステップ | 頻度 | ソース | 内容 | 推定負荷 |
|---|---|---|---|---|
| 銘柄リスト + 属性 + ファンダメンタル | 週1 | finviz Screener | MCap>1B, ex Healthcare, ~2,000銘柄分の全データ | ~100ページ取得（数分） |
| 日次価格（初回） | 初回のみ | yfinance | ~2,000銘柄 × 過去252日OHLCV | ~25バッチ（5-10分） |
| 日次価格（毎日） | 毎日 | yfinance | ~2,000銘柄 × 当日1日分OHLCV | ~25バッチ（約1分） |
| ETF価格（毎日） | 毎日 | yfinance | ~100 ETF × 当日1日分 | 2バッチ（数秒） |

### 4.3 finviz Screener の取得内容

finviz Screener の1回の取得で以下が全て含まれる:
- Ticker, Company, Sector, Industry, Country
- Market Cap
- EPS growth (this year / next year / past 5 years / quarter)
- Sales growth (quarter over quarter)
- P/E, Forward P/E
- Earnings date
- その他 90 以上の指標

これにより yfinance で個別に `Ticker().info` や `Ticker().financials` を叩く必要がなくなる。

### 4.4 yfinance バルクダウンロードの運用

- `yf.download(tickers, period='1d')` で複数銘柄を1リクエストにまとめる
- 1バッチあたり最大80銘柄
- ~2,000銘柄 ÷ 80 = 約25リクエスト
- リクエスト間に2秒のスリープ → 約1分で完了
- 失敗したバッチはリトライ（最大3回、間隔倍増）

### 4.5 キャッシュ戦略

| データ種別 | 保存形式 | TTL | 更新タイミング |
|---|---|---|---|
| 銘柄リスト + 属性 + ファンダメンタル | CSV/JSON | 1週間 | 週末バッチ（finviz） |
| 日次価格（OHLCV） | Parquet/CSV | 永続 + 日次追記 | 毎日市場終了後（yfinance） |
| ETF価格 | Parquet/CSV | 永続 + 日次追記 | 毎日市場終了後（yfinance） |

### 4.6 初回セットアップ vs 日次運用

**初回セットアップ（1回だけ）:**
- finviz から銘柄リスト + 属性 + ファンダメンタル取得（数分）
- yfinance から ~2,000銘柄の過去252日分の価格データ取得（5-10分）

**日次運用（毎日）:**
- yfinance から当日1日分のOHLCVのみ追加取得（約1分）

**週次運用（週1回）:**
- finviz から銘柄リスト + ファンダメンタルを更新（数分）

### 4.7 データソース状態追跡

各データに以下の状態ラベルを付与する:
- `live`: 当日取得成功
- `cache_fresh`: キャッシュ有効期間内
- `cache_stale`: TTL超過だがデータは存在
- `missing`: データなし

stale cache fallback: TTL超過時もデータを使用し、警告を表示する

---

## 5. データモデル

### 5.1 SymbolDailyBar
```
ticker
trade_date
open
high
low
close
adjusted_close
volume
```

### 5.2 SymbolProfile
```
ticker
name
market_cap
sector
industry
ipo_date
last_profile_update
```

### 5.3 FundamentalSnapshot
```
ticker
trade_date
eps_growth
revenue_growth
earnings_date
last_fundamental_update
```

### 5.4 SymbolIndicatorSnapshot
```
ticker
trade_date
sma50
sma200
ema21_high
ema21_low
ema21_close
ema21_cloud_width
wma10_weekly
atr
adr_percent
dcr_percent
weekly_return
monthly_return
quarterly_return
rel_volume
rs5
rs21
rs63
rs126
fundamental_score
industry_score
hybrid_score
vcs
pp_count_30d
three_weeks_tight
atr_21ema_zone
atr_10wma_zone
atr_50sma_zone
atr_pct_from_50sma
ema21_low_pct
earnings_in_7d
listing_age_days
```

### 5.5 ScanResult
```
trade_date
scan_name
ticker
hybrid_score
overlap_count
earnings_in_7d
pp_count_30d
```

### 5.6 MarketSnapshot
```
trade_date
market_condition_score
market_condition_label
score_1d_ago
score_1w_ago
score_1m_ago
score_3m_ago
pct_above_sma10
pct_above_sma20
pct_above_sma50
pct_above_sma200
pct_sma20_gt_sma50
pct_sma50_gt_sma200
vix_close
s2w_high
```

### 5.7 MarketSnapshotItem
```
symbol
name
price
daily_change_pct
volume_vs_50d_avg_pct
ema21_position_label
```

### 5.8 GroupStrengthSnapshot
```
trade_date
group_type (sector / industry)
group_name
ticker
rs
rs_1d
rs_1w
rs_1m
day_pct
week_pct
month_pct
rs_day_pct
rs_week_pct
rs_month_pct
high_52w
major_stocks
```

---

## 6. RS 計算の仕様

### 6.1 RS% の算出方法

1. `ratio = ticker_close / benchmark_close`（benchmark = SPY）
2. 指定 lookback 期間の ratio 時系列に対するパーセンタイルランクを算出
3. 0〜100 のスコアとして出力

### 6.2 母集団

RS のパーセンタイルランクは**他銘柄との横断比較ではない**。
各銘柄の**自身の過去 ratio 時系列**の中での順位を表す。

- RS 80 = その銘柄の対SPY比率が、過去の中で上位20%の位置にある
- RS 50 = ニュートラル
- RS 40以下 = 相対的に弱い

### 6.3 期間
- RS5: 5日
- RS21: 21日
- RS63: 63日
- RS126: 126日

### 6.4 ハイライト基準
- >= 80: 強い
- <= 39: 弱い

---

## 7. データ取得モジュール要件

### 7.1 FinvizScreenerProvider
- finviz Screener からフィルタ済み銘柄リストを一括取得
- フィルタ: MCap > 1B, Sector != Healthcare
- 取得項目: ticker, company, sector, industry, market_cap, EPS growth, sales growth, earnings date, P/E 等
- Python ライブラリ: `finviz` または `finvizfinance`
- キャッシュ TTL: 1週間

### 7.2 PriceDataProvider
- ソース: yfinance（`yf.download()` バルク取得）
- バッチサイズ: 80銘柄/リクエスト
- リトライ: 最大3回、間隔倍増
- ローカルキャッシュとの差分追記
- 対象: スキャン用ユニバース ~2,000銘柄 + ETF ~100

### 7.3 CacheLayer
- ファイルベースキャッシュ（Parquet for 価格, CSV/JSON for 属性+ファンダメンタル）
- TTL 管理（データ種別別）
- stale cache fallback（TTL超過時もデータ使用 + 警告）
- データソース状態追跡（live / cache_fresh / cache_stale / missing）

### 7.4 UniverseBuilder
- FinvizScreenerProvider からフィルタ済み銘柄リスト取得（~2,000）
- 価格データ取得後に Avg Vol > 1M + ADR% 3.5-10 で追加フィルタ（~1,500）
- スキャン対象ユニバース出力
