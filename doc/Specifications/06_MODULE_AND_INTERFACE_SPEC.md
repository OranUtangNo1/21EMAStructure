# Module and Interface Spec

## 1. 基本方針

各機能は以下の3分割を基本とする。

- Config
- Calculator / Scorer / Evaluator
- Result

これにより、
- 設定の外出し
- 差し替え
- 比較実験
を容易にする。

---

## 2. モジュール一覧（スクリーニングスコープ）

### 2.1 data
- PriceDataProvider
- ProfileDataProvider
- FundamentalDataProvider
- CacheLayer
- UniverseBuilder

### 2.2 indicators
- EMAHighLowCalculator
- EMACloudCalculator
- ATRIndicatorCalculator
- ADRCalculator
- DCRCalculator
- RelativeVolumeCalculator
- ThreeWeeksTightCalculator
- ATRFrom50SMACalculator
- ATRZoneCalculator（21EMA / 10WMA / 50SMA）

### 2.3 scoring
- RSScorer
- FundamentalScorer
- IndustryScorer
- HybridScoreCalculator
- VCSCalculator

### 2.4 scan
- ScanConfig
- ScanRunner
- ScanResultAggregator
- DuplicateTickerAggregator

### 2.5 dashboard
- MarketConditionConfig
- MarketConditionScorer
- MarketSnapshotBuilder
- GroupStrengthAggregator（Sector / Industry RS Radar）
- FactorRelativeStrengthCalculator
- WatchlistCardGridBuilder
- DashboardViewModelBuilder

### 2.6 隔離済み（スコープ外）

以下のモジュールは `archived/` に隔離保存されている。
将来のエントリー判断システム構築時に利用する。

- StructurePivotConfig / StructurePivotDetector / StructurePivotResult
- EntryCriteriaConfig / EntryEvaluator / EntryEvaluationResult
- RiskModelConfig / RiskEvaluator / ExitRuleEvaluator
- PositionSizingConfig / PositionSizingCalculator / PositionSizingResult
- CockpitPanelBuilder / CockpitCoreStatsCalculator
- DarvasRetestFilter / TrendRegimeFilter

---

## 3. インターフェース

### 3.1 IPriceDataProvider
責務:
- 指定 ticker 群の価格取得
- benchmark 取得
- 日付範囲指定取得

### 3.2 IFundamentalScorer
責務:
- EPS growth と revenue growth を受けてスコア返却

### 3.3 IIndustryScorer
責務:
- industry group データを受けて industry score を返却

### 3.4 IHybridScoreCalculator
責務:
- RS21 / RS63 / RS126 / F / I から H を計算
- breakdown 返却

### 3.5 IScanRule
責務:
- 単一 scan 条件の判定
- scan 名返却

### 3.6 IMarketConditionScorer
責務:
- 43 ETF のシグナル集計
- 総合スコアとラベルの返却

### 3.7 IGroupStrengthAggregator
責務:
- セクター / 業界のRS集計
- リーダーテーブルの構築
- MAJOR STOCKS の抽出

---

## 4. Result オブジェクト

### 4.1 HybridScoreBreakdown
```
ticker
trade_date
hybrid_score
fundamental_score
industry_score
rs21
rs63
rs126
```

### 4.2 ScanCardResult
```
scan_name
ticker_count
tickers (sorted by hybrid_score desc)
```

### 4.3 MarketConditionResult
```
trade_date
score
label
score_1d_ago
score_1w_ago
score_1m_ago
score_3m_ago
component_scores
```

### 4.4 MarketSnapshotItem
```
symbol
name
price
daily_change_pct
volume_vs_50d_avg_pct
ema21_position_label
```

### 4.5 SectorLeaderRow
```
rs
rs_1d
rs_1w
rs_1m
ticker
name
day_pct
week_pct
month_pct
rs_day_pct
rs_week_pct
rs_month_pct
high_52w
```

### 4.6 IndustryLeaderRow
```
rs
rs_1d
rs_1w
rs_1m
ticker
name
day_pct
week_pct
month_pct
rs_day_pct
rs_week_pct
rs_month_pct
high_52w
major_stocks (top 3 tickers)
```

---

## 5. 実装上の注意

- 非公開部分は interface 差し替え可能にする
- config と algorithm を分離する
- result には説明可能性のため breakdown を残す
- test しやすい pure function を優先する
- スコープ外モジュールのコードは削除せず隔離する
