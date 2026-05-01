# 現行システムにおける取得可能情報・算出指標・取得困難項目

## 前提

この整理は、**現在のコードベースで実際に使っている provider / API** を基準にしている。

- Universe discovery の現行設定: `finviz`
- 価格履歴 / プロファイル / 基本財務の現行取得元: `yfinance`
- 時間軸の中心: **日足**

したがって、ここでいう「根本的に取得可能」は、現在のシステムが直接 fetch している raw 情報、または同じ取得経路の延長で安定的に扱える情報を指す。

## 1. 根本的に取得可能な情報

## 1-1. 銘柄ユニバース発見時に取得している情報

### 現行アクティブ経路: Finviz

| 区分 | 現在取得している raw 情報 |
|---|---|
| 銘柄識別 | ticker, company name |
| 企業属性 | sector, industry, country, exchange |
| 規模 | market cap |
| 成長系スナップショット | EPS Q/Q, Sales Q/Q |
| イベント | earnings date |

### 実装済みの代替経路: Yahoo Screener

| 区分 | 現在取得している raw 情報 |
|---|---|
| 銘柄識別 | ticker, long/display name |
| 規模・流動性 | market cap, averageDailyVolume3Month |
| 価格 | regularMarketPrice |
| 市場属性 | exchange, currency, quoteType |

## 1-2. 価格履歴として取得している情報

### yfinance 日足履歴

| 区分 | 現在取得している raw 情報 |
|---|---|
| OHLCV | open, high, low, close, adjusted_close, volume |
| 対象 | 個別株、benchmark、VIX、sector/industry/factor ETF |
| 時間軸 | 主に日足 |

補足:

- 現行システムの主要計算は日足ベース
- ETF や `^VIX` も同じ価格取得基盤で扱っている

## 1-3. 企業プロファイルとして取得している情報

### yfinance profile

| 区分 | 現在取得している raw 情報 |
|---|---|
| 銘柄識別 | ticker, company name |
| 規模 | market cap |
| 属性 | sector, industry |
| 上場時点 | ipo_date |

## 1-4. 基本財務スナップショットとして取得している情報

### yfinance fundamentals

| 区分 | 現在取得している raw 情報 |
|---|---|
| 成長 | eps_growth, revenue_growth |
| イベント | earnings_date |

## 2. それを前提に現在算出している指標

## 2-1. テクニカル指標・価格派生

現在のシステムは日足 OHLCV から、少なくとも次を算出している。

- EMA 系: `ema21_high`, `ema21_low`, `ema21_close`, `ema21_cloud_width`
- SMA 系: `sma50`, `sma200`
- 年初来・高安系: `high_52w`, `low_52w`, `dist_from_52w_high`, `dist_from_52w_low`
- 出来高系: `avg_volume_50d`, `rel_volume`, `volume_ma5`, `volume_ma20`, `volume_ma5_to_ma20_ratio`, `volume_ratio_20d`, `ud_volume_ratio`
- ボラティリティ系: `atr`, `adr_percent`
- ローソク足・位置系: `dcr_percent`, `from_open_pct`, `daily_change_pct`
- リターン系: `weekly_return`, `monthly_return`, `quarterly_return`
- ドローダウン系: `rolling_20d_close_high`, `drawdown_from_20d_high_pct`
- レジスタンス系: `resistance_level_lookback`, `resistance_test_count`, `breakout_body_ratio`
- ゾーン系: `atr_21ema_zone`, `atr_21emaH_zone`, `atr_21emaL_zone`, `atr_low_to_ema21_high`, `atr_low_to_ema21_low`, `atr_10wma_zone`, `atr_50sma_zone`
- クロス・傾き系: `close_crossed_above_ema21`, `close_crossed_above_sma50`, `ema21_slope_5d_pct`, `sma50_slope_10d_pct`
- ギャップ・過熱系: `days_since_power_gap`, `power_gap_up_pct`, `ema21_low_pct`, `atr_pct_from_50sma`, `overheat`
- 補助ラベル系: `atr_21ema_label`, `atr_50sma_label`, `ema21_low_size_bucket`

## 2-2. パターン・構造認識

- `three_weeks_tight`
- `pocket_pivot`
- `pp_count_window`
- `trend_base`
- structure pivot 系一式
  - `structure_pivot_long_active`
  - `structure_pivot_long_breakout_first_day`
  - `structure_pivot_long_hl_price`
  - `structure_pivot_1st_break`
  - `structure_pivot_2nd_break`
  - `ct_trendline_break`
  - その他関連フィールド

## 2-3. RS / スコア系

- RS 系
  - `raw_rs5`, `raw_rs21`, `raw_rs63`, `raw_rs126`
  - `rs5`, `rs21`, `rs63`, `rs126`
  - `rs_ratio`
  - `rs_ratio_52w_high`
  - `rs_ratio_at_52w_high`
- 財務系
  - `eps_growth_score`
  - `revenue_growth_score`
  - `fundamental_score`
- 業種系
  - `industry_score`
- 総合系
  - `hybrid_score`
- VCP / contraction 系
  - `vcs`

## 2-4. Scan / Annotation / Watchlist 集計

- scan hit の有無
- `hit_scans`
- `scan_hit_count`
- `annotation_hits`
- `annotation_hit_count`
- `overlap_count`
- `duplicate_ticker`
- preset duplicate 判定
- Entry Signal 用の `signal_pool_entry`, `signal_evaluation`

## 2-5. Market Dashboard / Radar 系

同じ日足 OHLCV を前提に、次も算出している。

- 市場 breadth 系
  - `% above SMA20`
  - `% above SMA50`
  - `% above SMA200`
  - `% SMA50 > SMA200`
  - `% positive 1M / 3M`
  - `% 2W high`
- 市場スコア系
  - `vix_score`
  - `safe_haven_score`
  - 総合 `market score`
- Radar 系
  - `RS DAY%`
  - `RS WK%`
  - `RS MTH%`
  - `1D`, `1W`, `1M`, `RS`

## 3. 今は算出していないが、現在の raw 情報から算出可能な指標の例

以下は、**今ある日足 OHLCV + profile/fundamental snapshot** だけでも追加実装しやすい。

## 3-1. 日足 OHLCV だけで比較的容易に出せるもの

- MACD, signal, histogram
- Bollinger Bands, BandWidth, %B
- Donchian Channel
- Keltner Channel
- Stochastic %K / %D
- Williams %R
- CCI
- ROC
- OBV
- Accumulation / Distribution
- Chaikin Money Flow
- MFI
- 標準偏差ベースの realized volatility
- downside volatility
- beta / alpha の簡易推定
- 20日, 60日, 120日の回帰傾き
- 高値更新頻度 / 安値更新頻度
- ギャップ統計
  - gap up/down 発生率
  - gap fill 率
  - earnings gap 後リターン

## 3-2. benchmark / ETF 比較があるので出せるもの

- 相対パフォーマンスの追加 horizon
  - 10日
  - 6か月
  - YTD
- relative volatility
- benchmark 比での downside capture / upside capture の簡易版
- industry / sector に対する相対強度
- correlation 行列
- regime 別パフォーマンス集計

## 3-3. 現在の profile / fundamental snapshot でも可能なもの

- earnings までの日数
- earnings 直前 / 直後フラグ
- IPO からの経過日数
- market cap bucket
- growth acceleration proxy
  - `eps_growth - revenue_growth`
  - growth z-score
- sector / industry 別ランキング

## 4. 現在のシステム構成や API では取得が困難な項目

ここでいう「困難」は、単に未実装ではなく、**現行の provider 構成・データ粒度では弱い / 不安定 / そもそも不足** という意味。

## 4-1. intraday 系

- 1分足, 5分足などの安定した intraday OHLCV
- opening range
- 当日 intraday VWAP
- true intraday relative volume curve
- 板情報, bid/ask, spread
- Level 2 / order book
- 約定フロー, tape, aggressor side

理由:

- 現行計算基盤は日足中心
- 現在の provider 実装は intraday execution analysis 用に組まれていない

## 4-2. デリバティブ・需給マイクロ構造系

- 安定した options chain 時系列
- implied volatility surface
- skew / term structure
- gamma exposure
- dealer positioning
- borrow fee / stock loan utilization
- detailed short interest time series

理由:

- 現行 provider では直接の安定取得経路がない
- 取得できても研究用途として継続運用しにくい

## 4-3. テキスト / イベント深掘り系

- 決算ガイダンス本文
- earnings call transcript
- 8-K / 10-Q / 10-K の本文解析結果
- news sentiment
- insider transaction の安定時系列
- analyst revision history

理由:

- 現行システムは構造化数値データ中心
- テキストソースやイベント全文の ingest パイプラインを持っていない

## 4-4. より深い財務諸表系

今のシステムは `eps_growth`, `revenue_growth`, `earnings_date` という**薄い snapshot** しか使っていないため、次は現状では弱い。

- 売上総利益率
- 営業利益率
- FCF
- debt / equity
- 現金残高
- share count の精密時系列
- segment / geography 別売上
- ROE / ROIC / ROA の安定算出

理由:

- 現在の fundamental provider が薄い snapshot 設計
- 履歴・明細・statement 正規化レイヤーがない

## 5. 実務上の読み方

現行システムの前提は、かなり明確に **「日足 OHLCV + 最小限の profile/fundamental snapshot」** である。

したがって、新しい設計を考えるときはまず次の3層に分けるのがよい。

1. 今の raw 情報だけで十分作れるもの
2. provider を少し拡張すれば作れるもの
3. intraday / options / text ingestion など、別アーキテクチャが必要なもの

今の構成で最も強いのは、

- 日足 price action
- volume / contraction / relative strength
- sector / industry / ETF relative comparison

であり、最も弱いのは、

- intraday execution quality
- options / short borrow / microstructure
- 深い財務 statement とテキストイベント解析

である。
