# 内部で利用している情報

## データ取得

主なデータ取得元:

- price history: yfinance 系 provider。
- profile: yfinance profile provider。
- fundamentals: yfinance fundamental provider。
- universe discovery: Finviz provider。

主要設定:

- price period: 3y
- benchmark: SPY
- VIX: ^VIX
- technical cache TTL: 12 hours
- profile cache TTL: 168 hours
- fundamental cache TTL: 24 hours
- price batch size: 80
- price max retries: 3
- retry backoff multiplier: 2.0
- stale cache on failure: enabled
- sample fallback: disabled

## Universe

通常は universe discovery で候補 universe を作る。
手動 symbol が指定された場合は手動 symbol を優先する。

universe discovery 設定:

- provider: finviz
- allowed exchanges: NASDAQ、NYSE、AMEX
- max symbols: 2500
- min market cap: 1,000,000,000
- snapshot TTL: 7 days

active universe filter:

- min_market_cap: 1,000,000,000
- min_avg_volume_50d: 1,000,000
- min_price: 0.0
- min_adr_percent: 3.5
- max_adr_percent: 10.0
- excluded_sectors: Healthcare

この filter は、スイング対象として流動性と値幅がある銘柄を残すためのもの。

## Indicator

主な indicator 設定:

- EMA: 21
- SMA short: 50
- SMA medium: 150
- SMA long: 200
- SMA long slope lookback: 21
- ATR: 14
- ADR: 20
- relative volume: 50
- up/down volume: 50
- RSI short: 21
- RSI long: 63
- weekly WMA: 10 / 30
- 3WT threshold: 1.5%
- pocket pivot lookback: 10
- pp count window: 20 days
- structure pivot length: 2 to 10
- resistance test lookback: 20
- resistance zone width: 0.5 ATR
- power gap threshold: 10.0%
- VCP prior uptrend lookback: 126

## Scoring

### RS

RS は SPY を benchmark として計算する。

設定:

- lookbacks: 5、21、63、126
- normalization: percentile
- strong threshold: 80
- weak threshold: 39
- new high tolerance: 1.0

### Fundamental

Fundamental score は EPS と revenue を使う。

設定:

- eps_weight: 1.0
- revenue_weight: 1.0
- normalization: percentile
- missing policy: fill_neutral

### Industry

Industry score は同業種の RS を集約する。

設定:

- aggregation: mean
- input metric: rs21
- normalization: percentile

### Hybrid

Hybrid score は RS、fundamental、industry を合成する。

設定:

- RS weights: 1.0、2.0、2.0
- fundamental weight: 2.0
- industry weight: 3.0
- missing policy: fill_neutral_50

### VCS

VCS は価格・出来高・トレンドの圧縮品質を評価する。

設定:

- candidate threshold: 60.0
- priority threshold: 80.0
- len_short: 13
- len_long: 63
- len_volume: 50
- high-low lookback: 63
- sensitivity: 2.0
- trend penalty weight: 1.0
- penalty factor: 0.75
- bonus max: 15.0

## Pipeline

内部処理順序:

1. active symbols を解決する。
2. price、benchmark、VIX、profile、fundamental を取得する。
3. 各銘柄の indicator history を作る。
4. 最新行から snapshot を作る。
5. profile と fundamental を join する。
6. fetch status と data source を付与する。
7. RS、fundamental、industry、hybrid、VCS を計算する。
8. listing age、earnings flag、data quality を付与する。
9. universe filter で eligible snapshot を作る。
10. scan runner が scan hits と raw watchlist を作る。
11. WatchlistViewModelBuilder が Watchlist、duplicate tickers、scan cards、earnings today を作る。
12. Market Dashboard と RS Radar を作る。
13. snapshot、watchlist、scan hits、market metadata、radar metadata を保存する。

## Data Quality

内部では以下の data source / quality 情報を保持する。

- price_data_source
- profile_data_source
- fundamental_data_source
- price_data_note
- profile_data_note
- fundamental_data_note
- price_data_timestamp
- profile_data_timestamp
- fundamental_data_timestamp
- data_quality_label
- data_quality_score
- data_warning
- data_health_summary
- fetch_status

この情報は、候補の質ではなく、判断材料として信頼できるデータかどうかを確認するために使う。

## EntrySignal Tracking

EntrySignal は一日限りの評価ではなく、signal pool として DB に保持される。

内部で保持する主な情報:

- signal_name
- ticker
- preset_sources
- first_detected_date
- latest_detected_date
- detection_count
- pool_status
- snapshot_at_detection
- low_since_detection
- high_since_detection
- invalidated_date
- invalidated_reason

候補は detection_window_days を過ぎると expire される。
無効化条件に該当すると invalidated になる。

## Market / Report 内部情報

Market Dashboard と market report は次の情報を使う。

- ETF universe。
- sector rotation。
- leadership ETF。
- external ETF。
- factor ETF。
- Risk-On Ratio: IWO / IWN。
- Safe Haven: SPY / TLT。
- VIX。
- market score components。
- breadth and participation。
- industry leadership。
- market document と final report。

market report の horizon:

- short: 5 days
- medium: 21 days
- long: 63 days

この 5 / 21 / 63 day horizon のうち、短中期ロングオンリー swing の主評価は 5 / 21 day を中心に置く。63 day は中期トレンド継続やリーダーシップ持続性を確認する補助 horizon として扱う。
