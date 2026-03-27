# Parameter Catalog

## 1. 基本方針

非公開または未確定ロジックは、すべて設定可能にする。
各パラメータには
- 目的
- 初期値
- 調整候補
を持たせる。

Note: Entry, Structure Pivot, Position Sizing, optional filter のパラメータは
スコープ外のため `archived/ENTRY_EXIT_AND_RISK_SPEC.md` に移動済み。

---

## 2. EMA / Cloud 関連

### ema_period
- 初期値: 21

### ema_high_source
- 初期値: high

### ema_low_source
- 初期値: low

### ema_close_source
- 初期値: close

### show_ema21_cloud
- 初期値: true

---

## 3. Hybrid 関連

### benchmark_symbol
- 初期値: SPY

### rs_lookbacks
- 初期値: [5, 21, 63, 126]

### rs_weights
- 初期値: [1, 2, 2]

### rs_strong_threshold
- 初期値: 80

### rs_weak_threshold
- 初期値: 39

### fundamental_weight
- 初期値: 2

### industry_weight
- 初期値: 3

### hybrid_missing_value_policy
- 初期値: fill_neutral_50
- 候補:
  - renormalize_weights
  - fill_neutral_50
  - drop_symbol

---

## 4. Fundamental 関連

### fundamental_metrics
- 初期値: [eps_growth, revenue_growth]

### eps_growth_period
- 初期候補: configurable

### revenue_growth_period
- 初期候補: configurable

### use_estimates
- 初期候補: false

### eps_weight
- 初期候補: 1

### revenue_weight
- 初期候補: 1

### fundamental_normalization_method
- 初期値: percentile
- 候補:
  - percentile
  - zscore
  - clipped_rank

### missing_fundamental_policy
- 初期値: fill_neutral
- 候補:
  - fill_neutral
  - renormalize
  - drop

---

## 5. Industry 関連

### industry_classification_source
- 候補:
  - FMP
  - cached_mapping
  - custom

### industry_aggregation_method
- 初期値: mean
- 候補:
  - mean
  - median
  - market_cap_weighted_mean

### industry_rs_input_metric
- 初期値: rs21
- 候補:
  - rs21
  - rs63
  - rs126
  - weighted_rs

### industry_score_normalization_method
- 初期値: percentile
- 候補:
  - percentile
  - rank

### industry_cache_ttl_hours
- 初期値: 168

---

## 6. Cockpit Core Stats 関連

### adr_period
- 初期値: 20

### adr_formula
- 初期値: `100 * (SMA(high/low, adr_period) - 1)`

### adr_good_min
- 初期値: 3.5
- 用途: ユニバースフィルタ下限

### adr_good_max
- 初期値: 10.0
- 用途: ユニバースフィルタ上限
- 注意: 原典では "ADR% 3.5 to 10"。8.0 は Cockpit 良好ゾーン（スコープ外）

### atr_period
- 初期値: 14

### atr_21ema_good_min
- 初期値: -0.5

### atr_21ema_good_max
- 初期値: 1.0

### atr_50sma_good_max
- 初期値: 3.0

### ema21_low_pct_full_max
- 初期値: 5.0

### ema21_low_pct_reduce_max
- 初期値: 8.0

### atr_pct_from_50sma_overheat
- 初期値: 7.0

### show_overheat_dot
- 初期値: true

### enable_3wt
- 初期値: true

---

## 7. VCS 関連

### vcs_threshold_candidate
- 初期値: 60

### vcs_threshold_priority
- 初期値: 80

### len_short
- 初期候補: 13

### len_long
- 初期候補: 63

### len_volume
- 初期候補: 50

### sensitivity
- 初期候補: 2.0

### trend_penalty_weight
- 初期候補: 1.0

### bonus_max
- 初期候補: 15

---

## 8. キャッシュ関連

### technical_cache_ttl_hours
- 初期値: 12

### fundamental_cache_ttl_hours
- 初期値: 24

### earnings_cache_ttl_hours
- 初期候補: 24

---

## 9. Market Dashboard 関連

### market_condition_method
- 43 ETF のポジティブシグナル割合

### market_condition_etf_universe
- 初期候補: 43 ETF（具体リストは非公開、configurable）

### market_condition_components
- 初期候補:
  - pct_above_sma10
  - pct_above_sma20
  - pct_above_sma50
  - pct_above_sma200
  - pct_sma20_gt_sma50
  - pct_sma50_gt_sma200
  - vix
  - 52w_high_metrics
  - performance_overview
  - factor_strength

### component_weights
- 初期値: 均等加重（仮定義）

### bullish_threshold
- 初期値: 80

### positive_threshold
- 初期値: 60

### neutral_threshold
- 初期値: 40

### negative_threshold
- 初期値: 20

### market_snapshot_symbols
- 初期値: [RSP, QQQE, IWM, DIA, VIX, BTC]

### sector_etf_list
- 初期値: [QQQ, QQQE, RSP, DIA, IWM, XLV, XLE, XLF, XLRE, XLB, XLP, XLU, XLY, XLK, XLC, XLI]
- Relative Strength Table のデフォルトプリセット準拠

### factor_etfs
- 初期値（仮定義）: VUG(Growth), VTV(Value), VYM(High Dividend), MGC(Large-Cap), VO(Mid-Cap), VB(Small-Cap), MTUM(Momentum), IPO(IPOs)

### breadth_chart_source
- 初期値: ユニバースから自前計算（SMA200超え銘柄の割合）
- 将来: S5TH データの外部取得に切替可能

---

## 10. 実験管理で残すべきもの

- config version
- run timestamp
- universe size
- benchmark
- parameter snapshot
- candidate list
- hybrid breakdown
- market condition result
- scan hit counts