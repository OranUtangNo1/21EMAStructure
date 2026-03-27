# Data Model and Sources

## 1. データソース

### 1.1 主データソース
- yfinance（価格、プロファイル、ファンダメンタル）
- FMP — starter plan（プロファイル、ファンダメンタル、earnings、銘柄リスト）

### 1.2 補助ソース
- Nasdaq API（バックアップ用銘柄リスト）

### 1.3 ベンチマーク
- デフォルト: SPY

### 1.4 特記事項
- RS 計算は SPY ベンチマークとの比較
- RS% はパーセンタイルランク（銘柄自身の過去 ratio 時系列内での順位）
- industry / market cap / fundamentals はキャッシュ前提
- RS Radar のセクター／業界RSはETFベースで算出

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

- フィルタ前の全米普通株: 約 7,000〜8,000 銘柄
- Market Cap + Volume フィルタ後: 約 1,500〜2,500 銘柄
- ADR% + ex Healthcare 後: 約 1,000〜2,000 銘柄（= スキャン対象ユニバース）

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

## 4. キャッシュ戦略

### 4.1 初期デフォルト
- 銘柄リスト / market cap / industry classification: 1週間
- technical price-related data: 12時間
- fundamentals: 24時間
- earnings: 24時間

### 4.2 目的
- 大規模ユニバースを現実的な時間内で処理する
- API 負荷を抑える
- stale cache fallback で可用性を確保する

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

### 7.1 PriceDataProvider
- 日次価格の取得（個別銘柄 + ベンチマーク + ETF群）
- 欠損処理

### 7.2 ProfileDataProvider
- market cap, sector, industry, name, ipo_date
- 証券種別（普通株判定用）

### 7.3 FundamentalDataProvider
- EPS growth, revenue growth, earnings date

### 7.4 SymbolListProvider
- 全米普通株リストの取得
- 取引所、証券種別によるフィルタリング

### 7.5 CacheLayer
- TTL 管理
- データ種別別キャッシュ
- stale cache fallback

### 7.6 UniverseBuilder
- SymbolListProvider から全銘柄取得
- ユニバース条件でフィルタ（Market Cap, Volume, ADR%, Sector除外）
- スキャン対象ユニバースを構築
