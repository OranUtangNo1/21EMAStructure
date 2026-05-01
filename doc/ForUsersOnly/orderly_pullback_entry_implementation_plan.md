# Orderly Pullback Entry 実装計画書

## 1. 概要

### 1.1 目的

Orderly Pullback Entry は、Entry Signal 拡張の最初の実装対象である。
上昇トレンド中の orderly pullback から 21EMA reclaim を捉え、
セットアップ成熟度・タイミング精度・リスクリワード比率の 3 軸で
エントリ強度を連続値として算出する。

### 1.2 設計原則

- Entry Signal は自己完結した判断単位であり、専用の pool を持つ
- pool は preset の duplicate 検出を起点とし、detection window の間追跡する
- 評価は boolean ではなく 0–100 の連続値スコアで行う
- 判断根拠は 3 軸に分解して追跡可能にする

### 1.3 対象セットアップ

orderly pullback とは以下の構造を持つ価格パターンである。

- 上昇トレンド中の銘柄（ema21 上昇、sma50 上昇）
- 21EMA 付近への健全な調整（drawdown 3–15%）
- 調整中の出来高縮小（売り圧力の枯渇）
- 調整後の 21EMA 奪還（買い手の復帰）

---

## 2. 前提条件と追加実装

### 2.1 indicator 層への追加

`IndicatorCalculator.calculate` に以下を追加する。

```python
rolling_5d_low  = low.rolling(5).min()
rolling_10d_low = low.rolling(10).min()
```

既存の `rolling_20d_close_high = close.rolling(20).max()` と対称の計算。
全 eligible universe 銘柄に対して算出される汎用インジケーターであり、
他の Entry Signal でも利用可能。

### 2.2 tracking DB スキーマ

#### signal_pool_entry テーブル

```sql
CREATE TABLE signal_pool_entry (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_name           TEXT    NOT NULL,
    ticker                TEXT    NOT NULL,
    preset_sources        TEXT    NOT NULL,  -- JSON array of preset names
    first_detected_date   TEXT    NOT NULL,  -- ISO date
    latest_detected_date  TEXT    NOT NULL,  -- ISO date, updated on re-detection
    detection_count       INTEGER NOT NULL DEFAULT 1,
    pool_status           TEXT    NOT NULL DEFAULT 'active',
        -- 'active' | 'invalidated' | 'expired' | 'orphaned'
    invalidated_date      TEXT,
    invalidated_reason    TEXT,
    snapshot_at_detection  TEXT    NOT NULL,  -- JSON object
    low_since_detection   REAL,    -- daily updated: min(today low, prev value)
    high_since_detection  REAL,    -- daily updated: max(today high, prev value)
    created_at            TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT    NOT NULL DEFAULT (datetime('now')),

    UNIQUE(signal_name, ticker, first_detected_date)
);

CREATE INDEX idx_pool_active
    ON signal_pool_entry(signal_name, pool_status)
    WHERE pool_status = 'active';
```

#### signal_evaluation テーブル

```sql
CREATE TABLE signal_evaluation (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_name           TEXT    NOT NULL,
    ticker                TEXT    NOT NULL,
    eval_date             TEXT    NOT NULL,  -- ISO date
    signal_version        TEXT    NOT NULL,  -- e.g. "1.0"
    pool_entry_id         INTEGER NOT NULL,

    -- 3-axis scores (0-100)
    setup_maturity_score  REAL    NOT NULL,
    timing_score          REAL    NOT NULL,
    risk_reward_score     REAL    NOT NULL,
    entry_strength        REAL    NOT NULL,

    -- sub-indicator breakdown (JSON)
    maturity_detail       TEXT,   -- JSON: each sub-indicator score
    timing_detail         TEXT,   -- JSON: each sub-indicator score

    -- R/R specifics
    stop_price            REAL,
    reward_target         REAL,
    rr_ratio              REAL,
    risk_in_atr           REAL,
    reward_in_atr         REAL,
    stop_adjusted         INTEGER DEFAULT 0,  -- 1 if min-distance safety applied

    created_at            TEXT    NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (pool_entry_id) REFERENCES signal_pool_entry(id),
    UNIQUE(signal_name, ticker, eval_date)
);

CREATE INDEX idx_eval_date
    ON signal_evaluation(eval_date, signal_name);
```

### 2.3 snapshot_at_detection フィールド

pool 登録時に JSON として保存するフィールド一覧。

```json
{
    "close": 150.25,
    "ema21_close": 148.50,
    "sma50": 142.30,
    "rs21": 78.5,
    "atr": 3.20,
    "drawdown_from_20d_high_pct": 6.2,
    "volume_ma5_to_ma20_ratio": 0.72,
    "atr_21ema_zone": -0.35,
    "atr_50sma_zone": 2.10,
    "rolling_20d_close_high": 160.10,
    "high": 151.00
}
```

---

## 3. Entry Signal 定義 (YAML)

```yaml
entry_signals:
  definitions:
    orderly_pullback_entry:
      display_name: "Orderly Pullback Entry"
      signal_version: "1.0"
      description: >
        上昇トレンド中の orderly pullback から 21EMA reclaim を捉える。
        出来高枯渇 → 支持線収束 → reclaim イベントの時系列を追跡し、
        リスクリワードの良いエントリポイントを検出する。

      # --- pool 構築 ---
      pool:
        preset_sources:
          - "Orderly Pullback"
          - "Trend Pullback"
        detection_window_days: 10

        invalidation:
          - field: close
            condition: below
            reference: sma50
          - field: drawdown_from_20d_high_pct
            condition: above
            threshold: 20.0
          - field: rs21
            condition: below
            threshold: 40.0
          - field: sma50_slope_10d_pct
            condition: at_or_below
            threshold: 0.0

        snapshot_fields:
          - close
          - ema21_close
          - sma50
          - rs21
          - atr
          - drawdown_from_20d_high_pct
          - volume_ma5_to_ma20_ratio
          - atr_21ema_zone
          - atr_50sma_zone
          - rolling_20d_close_high
          - high

        pool_tracking:
          - low_since_detection
          - high_since_detection

      # --- setup_maturity (0-100) ---
      setup_maturity:
        indicators:
          volume_exhaustion:
            weight: 0.30
            field: volume_ma5_to_ma20_ratio
            scoring_type: piecewise_linear
            breakpoints:
              - [0.60, 100]
              - [0.70,  80]
              - [0.80,  55]
              - [0.85,  35]
              - [0.95,  10]
              - [1.00,   0]

          support_convergence:
            weight: 0.25
            field: atr_21ema_zone
            scoring_type: piecewise_linear
            breakpoints:
              - [-1.25,   0]
              - [-0.75,  40]
              - [-0.50,  70]
              - [-0.25,  95]
              - [ 0.00, 100]
              - [ 0.25,  95]
              - [ 0.50,  70]
              - [ 1.00,   0]

          pullback_duration:
            weight: 0.20
            field: _days_since_first_detected
            scoring_type: piecewise_linear
            breakpoints:
              - [ 1,  20]
              - [ 2,  50]
              - [ 3,  80]
              - [ 4, 100]
              - [ 5, 100]
              - [ 6,  85]
              - [ 7,  65]
              - [ 8,  45]
              - [ 9,  25]
              - [10,  10]

          trend_integrity:
            weight: 0.15
            composite: true
            components:
              ema21_slope:
                field: ema21_slope_5d_pct
                weight: 0.60
                breakpoints:
                  - [-0.05,  0]
                  - [ 0.00, 20]
                  - [ 0.10, 50]
                  - [ 0.20, 80]
                  - [ 0.30, 100]
              sma50_slope:
                field: sma50_slope_10d_pct
                weight: 0.40
                breakpoints:
                  - [-0.02,  0]
                  - [ 0.00, 20]
                  - [ 0.05, 50]
                  - [ 0.10, 80]
                  - [ 0.15, 100]

          rs_resilience:
            weight: 0.10
            field: _rs21_delta_from_detection
            scoring_type: piecewise_linear
            breakpoints:
              - [-20,   0]
              - [-15,  25]
              - [-10,  50]
              - [ -5,  75]
              - [  0, 100]
              - [  5, 100]

      # --- timing (0-100) ---
      timing:
        indicators:
          ema_reclaim_event:
            weight: 0.30
            composite: true
            logic: |
              if close_crossed_above_ema21:
                  score = 100
              elif 0.0 <= atr_21ema_zone <= 0.5:
                  score = 70
              elif -0.3 <= atr_21ema_zone < 0.0:
                  score = 40
              elif -0.5 <= atr_21ema_zone < -0.3:
                  score = 20
              else:
                  score = 5

          volume_confirmation:
            weight: 0.25
            field: volume_ratio_20d
            scoring_type: piecewise_linear
            note: "inverted-U: too low = weak reclaim, too high = reversal risk"
            breakpoints:
              - [0.60,  5]
              - [0.80, 15]
              - [1.00, 40]
              - [1.30, 70]
              - [1.50, 90]
              - [2.00, 95]
              - [2.50, 80]
              - [3.50, 50]

          close_quality:
            weight: 0.20
            field: dcr_percent
            scoring_type: piecewise_linear
            breakpoints:
              - [20,   5]
              - [30,  10]
              - [40,  25]
              - [50,  40]
              - [60,  60]
              - [70,  80]
              - [80, 100]

          micro_structure_breakout:
            weight: 0.15
            composite: true
            logic: |
              base = 70 if (high > prev_high) else 20
              bonus = 30 if close_crossed_above_ema21 else 0
              score = min(base + bonus, 100)

          demand_footprint:
            weight: 0.10
            composite: true
            logic: |
              if pocket_pivot:
                  score = 90
              elif ud_volume_ratio >= 1.5:
                  score = 70
              elif ud_volume_ratio >= 1.0:
                  score = 40
              else:
                  score = 15

      # --- risk_reward ---
      risk_reward:
        stop:
          reference: low_since_detection
          atr_buffer: 0.25
          min_distance_atr: 0.75
          structural_penalty: 0.80
        reward:
          primary: snapshot_rolling_20d_close_high
          secondary: high_52w
          fallback: measured_move
        scoring:
          method: system_default
          breakpoints:
            - [0.5,   5]
            - [1.0,  25]
            - [1.5,  50]
            - [2.0,  70]
            - [2.5,  85]
            - [3.0,  95]

      # --- entry_strength 統合 ---
      entry_strength:
        weights:
          setup_maturity: 0.25
          timing: 0.40
          risk_reward: 0.35
        floor_gate:
          min_axis_threshold: 20
          capped_strength: 30

      # --- 表示 ---
      display:
        thresholds:
          signal_detected: 50
          approaching: 35
          tracking: 0
```

---

## 4. 実装フェーズ

### Phase 1: 基盤層（DB + インジケーター）

#### タスク 1.1: インジケーター追加

対象ファイル: `src/indicators/core.py`

追加内容:
- `rolling_5d_low = low.rolling(5).min()`
- `rolling_10d_low = low.rolling(10).min()`

既存の `rolling_20d_close_high` 算出箇所の近傍に追加する。

受け入れ基準:
- enriched snapshot に `rolling_5d_low`, `rolling_10d_low` が含まれる
- 値が正しい（手動サンプル 5 銘柄で検証）
- 既存テストが pass する

#### タスク 1.2: tracking DB スキーマ追加

対象ファイル: `src/data/tracking_schema.sql` 相当

追加内容:
- `signal_pool_entry` テーブル作成
- `signal_evaluation` テーブル作成
- インデックス作成
- マイグレーション処理

受け入れ基準:
- テーブルが作成される
- 既存テーブルに影響がない
- 空の DB からでも正常に起動する

#### タスク 1.3: pool entry CRUD

対象: 新規モジュール `src/signals/pool.py`

実装内容:
- `create_pool_entry(signal_name, ticker, preset_source, snapshot)`
- `update_pool_entry_redetection(entry_id, new_snapshot)`
- `invalidate_pool_entry(entry_id, reason)`
- `expire_pool_entries(signal_name, window_days)`
- `orphan_pool_entries(signal_name, valid_presets)`
- `update_tracking_fields(entry_id, today_low, today_high)`
- `get_active_pool(signal_name) -> List[PoolEntry]`

受け入れ基準:
- 各操作のユニットテスト pass
- pool_status 遷移が正しい（active → invalidated, active → expired, active → orphaned）
- 再検出時に latest_detected_date, detection_count, snapshot が更新される
- invalidated 後の再検出が新規行になる

依存: タスク 1.2

---

### Phase 2: 評価エンジン

#### タスク 2.1: スコアリングユーティリティ

対象: 新規モジュール `src/signals/scoring.py`

実装内容:
- `piecewise_linear_score(value, breakpoints) -> float`
  区間線形補間による汎用スコアリング関数
- `composite_score(scores_with_weights) -> float`
  重み付き加重平均

受け入れ基準:
- breakpoints 境界値での正確なスコア
- breakpoints 中間値での線形補間の正確性
- breakpoints 範囲外でのクランプ処理
- ユニットテスト: 各関数 10 ケース以上

#### タスク 2.2: setup_maturity evaluator

対象: 新規モジュール `src/signals/evaluators/orderly_pullback.py`

実装内容:
- `evaluate_setup_maturity(row, pool_entry, config) -> MaturityResult`
- 5 サブ指標の算出
- 加重平均による maturity スコア算出
- MaturityResult: score + detail dict

必要な入力:
- `row`: 当日の enriched snapshot（volume_ma5_to_ma20_ratio, atr_21ema_zone, ema21_slope_5d_pct, sma50_slope_10d_pct, rs21）
- `pool_entry`: first_detected_date, snapshot_at_detection（rs21_at_detection）
- `config`: YAML から読み込んだ breakpoints と weights

受け入れ基準:
- 各サブ指標が 0–100 の範囲に収まる
- 加重平均が weights に従って正しく算出される
- pullback_duration がベルカーブ型（day 4-5 がピーク）になる
- rs_resilience が検出時との差分で正しく算出される

依存: タスク 2.1

#### タスク 2.3: timing evaluator

対象: 同上モジュール

実装内容:
- `evaluate_timing(row, config) -> TimingResult`
- 5 サブ指標の算出
- 加重平均による timing スコア算出

必要な入力:
- `row`: close_crossed_above_ema21, atr_21ema_zone, volume_ratio_20d, dcr_percent, high, prev_high, pocket_pivot, ud_volume_ratio
- `config`: YAML breakpoints と weights

受け入れ基準:
- close_crossed_above_ema21 = True の日に ema_reclaim_event = 100
- volume_confirmation が inverted-U 型（2.0 付近でピーク、3.5+ で減衰）
- pocket_pivot 発生日に demand_footprint が高スコア

依存: タスク 2.1

#### タスク 2.4: risk_reward evaluator

対象: 新規共通モジュール `src/signals/risk_reward.py` + signal 固有設定

実装内容:
- `calculate_stop_price(pool_entry, row, config) -> StopResult`
  - low_since_detection - atr * buffer
  - min_distance 安全弁
  - stop_adjusted フラグ
- `calculate_reward_target(pool_entry, row, config) -> float`
  - primary: snapshot_rolling_20d_close_high
  - secondary: high_52w
  - fallback: measured_move
- `calculate_rr_ratio(entry_price, stop_price, reward_target) -> float`
- `score_rr(rr_ratio, stop_adjusted, config) -> float`
  - 統一カーブ × structural_penalty

受け入れ基準:
- stop_price が常に entry_price 未満
- min_distance 安全弁が正しく発動する
- T1 超えの場合に T2 へフォールバックする
- stop_adjusted 時に penalty が適用される

依存: タスク 1.3（pool_entry の low_since_detection）

#### タスク 2.5: entry_strength 統合

対象: 同上 evaluator モジュール

実装内容:
- `calculate_entry_strength(maturity, timing, rr, config) -> float`
  - 加重平均算出
  - floor gate 適用

```python
def calculate_entry_strength(maturity, timing, rr, config):
    weights = config["weights"]
    weighted_avg = (
        maturity * weights["setup_maturity"]
        + timing * weights["timing"]
        + rr * weights["risk_reward"]
    )
    min_axis = min(maturity, timing, rr)
    threshold = config["floor_gate"]["min_axis_threshold"]
    cap = config["floor_gate"]["capped_strength"]

    if min_axis < threshold:
        return min(weighted_avg, cap)
    return weighted_avg
```

受け入れ基準:
- 3 軸すべて 80 → entry_strength ≈ 80
- maturity=90, timing=10, rr=80 → entry_strength ≤ 30（floor gate 発動）
- 3 軸すべて 0 → entry_strength = 0

依存: タスク 2.2, 2.3, 2.4

---

### Phase 3: Runner 統合

#### タスク 3.1: EntrySignalRunner リファクタリング

対象: `src/signals/runner.py`

変更内容:
- 現行の共有 universe + boolean 判定フローを維持しつつ、新しい signal 定義型を並走できる構造にする
- 新 runner フロー:
  1. signal 定義をロード
  2. signal ごとに pool 更新（Phase 1 の pool CRUD 呼び出し）
  3. active pool entries に対して evaluator を実行
  4. signal_evaluation に記録
  5. 結果を統合して返却

入出力契約の変更:
- 現行出力: `List[Dict]`（ticker + hit signal names + risk reference）
- 新出力: `List[SignalResult]`（ticker + signal_name + 3 軸スコア + entry_strength + detail）

受け入れ基準:
- 既存の 5 つの boolean signal が引き続き動作する（後方互換）
- 新しい orderly_pullback_entry が pool ベースで動作する
- signal_evaluation テーブルに日次記録が書き込まれる

依存: Phase 1 全体, Phase 2 全体

#### タスク 3.2: pool 更新の日次パイプライン組み込み

対象: `app/main.py` のパイプライン実行箇所

変更内容:
- preset duplicate 判定後、Entry Signal pool 更新を呼び出す
- pool 更新は scan/watchlist 生成後、Entry Signal 評価前に実行

受け入れ基準:
- パイプライン実行で pool が正しく更新される
- 保存済み run 読み込み時の挙動が定義されている
  （pool 更新はスキップし、既存 pool のみ評価する）

依存: タスク 3.1

---

### Phase 4: UI 表示

#### タスク 4.1: Entry Signal 表の拡張

対象: Entry Signal ページの表示コンポーネント

変更内容:
- signal ごとのセクション分け
- 各行に 3 軸スコア + entry_strength を表示
- 表示閾値による 3 段階表示（Signal Detected / Approaching / Tracking）
- Tracking は折りたたみ
- preset_sources 列の追加（pool に入った経路の可視化）
- pool_status, detection 日数の表示

受け入れ基準:
- entry_strength >= 50 の行が強調表示される
- 35–49 の行が通常表示される
- 35 未満の行が折りたたみ内に表示される
- 各行から 3 軸スコアの内訳が確認できる

依存: タスク 3.1

---

### Phase 5: 検証

#### タスク 5.1: バックテスト的検証

対象: 過去の enriched snapshot データ

内容:
- 過去 30–60 日分の日次データに対して orderly_pullback_entry を遡及実行
- entry_strength と forward return（5d, 10d, 20d）の相関を分析
- 表示閾値の妥当性を検証
- 各サブ指標の弁別力を検証

受け入れ基準:
- entry_strength >= 50 のエントリが、ランダムエントリより統計的に優位
- timing スコアが高い日のエントリが、低い日より forward return が良い
- 閾値調整の推奨値を出す

#### タスク 5.2: 運用検証

内容:
- 2 週間のライブ運用で daily evaluation を蓄積
- signal_evaluation テーブルのデータ品質を確認
- UI の実用性をフィードバック

---

## 5. 実装順序と依存関係

```
Phase 1 (基盤)
  ├── 1.1 インジケーター追加
  ├── 1.2 DB スキーマ
  └── 1.3 pool CRUD ← 1.2

Phase 2 (評価エンジン)
  ├── 2.1 スコアリングユーティリティ
  ├── 2.2 maturity evaluator ← 2.1
  ├── 2.3 timing evaluator ← 2.1
  ├── 2.4 risk_reward evaluator ← 1.3
  └── 2.5 entry_strength ← 2.2, 2.3, 2.4

Phase 3 (Runner 統合) ← Phase 1, Phase 2
  ├── 3.1 Runner リファクタリング
  └── 3.2 パイプライン組み込み ← 3.1

Phase 4 (UI) ← 3.1

Phase 5 (検証) ← Phase 3, Phase 4
```

---

## 6. リスクと対策

### パフォーマンス

pool 管理で DB I/O が増加する。active pool のサイズは signal × eligible universe の
一部なので通常は数十〜数百行。日次更新のバッチ処理で対応可能。
ボトルネックが発生した場合はインメモリキャッシュで対処する。

### 後方互換

既存の 5 つの boolean Entry Signal を即座に廃止しない。
新 runner は新旧両方を実行可能な構造にし、移行期間を設ける。

### スコアリング精度

初期の breakpoints は設計時の推定値である。
Phase 5 の検証結果に基づいてチューニングする前提で、
breakpoints を YAML config 化しておくことで、コード変更なしに調整可能にする。

### preset 変更の影響

custom preset のリネーム・削除に対しては orphaned 処理で対応する。
pool entry の寿命は最大 10 日なので、影響期間は限定的。

---

## 7. signal_version 管理

初期リリースは `signal_version: "1.0"` とする。

以下の変更時にバージョンを上げる:
- breakpoints の変更
- weights の変更
- invalidation 条件の変更
- 新しいサブ指標の追加・削除

signal_evaluation テーブルに signal_version が記録されるため、
バージョン間の forward return 比較が可能になる。
