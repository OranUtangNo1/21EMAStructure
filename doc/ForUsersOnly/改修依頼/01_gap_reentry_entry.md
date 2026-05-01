# Gap Reentry Entry — 設計書（Step 1〜4）

---

## Step 1: セットアップ定義

### 1.1 セットアップの構造記述

**対象フェーズ**: catalyst gap → pullback → gap support zone reentry

**なぜこのセットアップが最も良い機械的 R/R を持つか**:

Power gap（決算・ガイダンス・大型提携等）で大きく窓を開けた銘柄には、**ギャップの下限**（gap low）と**ギャップの上限**（gap high / ギャップ日の高値）という 2 つの自然な構造的参照点がある。gap low を割ると catalyst の需要が否定されたことを意味し、gap high は利確が最後に集中した水準。

この 2 点が存在するおかげで、SL と TP が**トレーダーの裁量ではなくセットアップの構造から自動的に導かれる**。これが「機械的エントリで R/R が良い」の核心。

**価格パターン**:

1. **Gap 発生日**: 出来高を伴った陽線の窓開け。`Recent Power Gap` annotation filter が成立
2. **Pullback 期**: gap 後に 21EMA / 50SMA 方向に調整。Pullback Quality scan がこの品質を確認
3. **Reentry trigger**: 21EMA pattern または Reclaim scan が発火し、gap 方向への反転が始まる
4. **Demand confirmation**: Volume Accumulation または Pocket Pivot が需要を確認

**セットアップ成立条件**:

- `Recent Power Gap` annotation が true
- Pullback Quality scan が成立（orderly pullback の証拠）
- Reentry trigger（21EMA Pattern H/L or Reclaim scan）が発火
- Demand confirmation（Volume Accumulation or PP）が成立
- `trend_base = true`

**セットアップ崩壊条件**:

- close が gap low を下回った場合 → catalyst 否定
- gap 発生から 20 営業日以上経過（gap の記憶が薄れ、構造の意味が弱まる）

**理想的なエントリポイント**: gap 後の pullback から reentry trigger が出た初日。gap low からの距離が近いほど SL がタイトで R/R が良い。

### 1.2 preset 対応

| preset_source | Status | 整合性 |
|---|---|---|
| `Power Gap Pullback` | enabled | 直接対応。PB Quality required + Reentry Trigger + Demand Confirmation + annotation: Recent Power Gap, Trend Base |

### 1.3 時間的特性

- **ラグ型**。gap 発生 → pullback 形成 → reentry trigger まで 5〜15 日
- **detection_window: 10 日**。gap 後の pullback は通常 1〜2 週間で完了。10 日を超えると gap 構造の鮮度が低下

---

## Step 2: プール構築設計

### preset_sources

```yaml
preset_sources: [Power Gap Pullback]
```

### detection_window_days: 10

### 無効化条件

| # | 条件 | 根拠 |
|---|---|---|
| 1 | `close < gap_low` | catalyst 否定。構造の根幹が崩壊 |
| 2 | `days_in_pool > 15` | gap 構造の鮮度切れ |
| 3 | `close > gap_high * 1.05` | 既に gap high を 5% 超えて上昇。reentry の文脈ではなくなった |

### snapshot_at_detection

| フィールド | 理由 |
|---|---|
| `close` | 基準線 |
| `gap_low` | **SL 参照（最重要）**。gap の下限 |
| `gap_high` | **TP 参照（最重要）**。gap の上限 |
| `atr` | バッファ計算 |
| `rs21` | RS 変化追跡 |
| `sma50` | support level 補助参照 |

### pool_tracking

| フィールド | 更新ロジック | 用途 |
|---|---|---|
| `low_since_detection` | `min(low, prev)` | pullback の深さ追跡。gap low との距離 |
| `high_since_detection` | `max(high, prev)` | reentry 進行度 |
| `days_in_pool` | `+1` | detection window 管理 |

---

## Step 3: 評価軸設計

### setup_maturity（重み 0.30）

| # | 指標 | フィールド | 重み | 根拠 |
|---|---|---|---|---|
| M1 | Gap low からの距離 | `close` vs `snapshot_gap_low` | 0.40 | gap low に近いほど SL がタイト → R/R が良い |
| M2 | Pullback の秩序性 | `dcr_percent` の 5 日平均 | 0.30 | pullback 中の引け位置が安定しているほど、panic selling ではなく orderly correction |
| M3 | RS 維持度 | `rs21` | 0.30 | gap 後も RS が維持されていれば、機関投資家の conviction は継続 |

**M1 スコアリング（gap low proximity）**:
- `gap_low と close の距離 <= 3%`: 100（gap support zone のど真ん中。理想）
- `3〜5%`: 80
- `5〜8%`: 60
- `8〜12%`: 40
- `> 12%`: 20（gap low から遠すぎ。SL が広い）

### timing（重み 0.40）

| # | 指標 | フィールド | 重み | 根拠 |
|---|---|---|---|---|
| T1 | 21EMA Pattern trigger | `21ema_pattern_h` or `21ema_pattern_l` | 0.35 | gap 後の pullback からの反転の最初のシグナル |
| T2 | Reclaim scan | `reclaim_scan` | 0.25 | 21EMA reclaim イベント |
| T3 | 出来高確認 | `rel_volume` | 0.25 | reentry 日の出来高 |
| T4 | 引け位置 | `dcr_percent` | 0.15 | 当日の close 品質 |

**timing 特殊ロジック**: T1 と T2 はいずれかが true であれば trigger 成立。両方 true なら bonus。

### risk_reward（重み 0.30）

**SL 参照: `snapshot_gap_low - 0.5 * atr`**

gap low が構造的 SL。0.5 ATR のバッファは gap low をわずかに下回るノイズを許容。

**TP 参照: `snapshot_gap_high`**

gap high は利確が最後に集中した水準。一次目標としてこれを使う。

| # | 指標 | 重み |
|---|---|---|
| R1 | R/R ratio = (gap_high - entry) / (entry - SL) | 0.60 |
| R2 | SL 距離 % | 0.40 |

**R/R の構造的優位性**: gap の値幅が大きいほど、pullback 後の reentry は R/R が自動的に良くなる。gap low に近い位置で reentry trigger が出ると、R/R 3:1 以上が構造的に達成されやすい。

---

## Step 4: 統合設計

### 重み配分

| 軸 | 重み | 根拠 |
|---|---|---|
| setup_maturity | 0.30 | gap 構造があることは preset 通過で保証済み。maturity は補助的 |
| timing | 0.40 | **reentry trigger が出た日がエントリ日**。機械的エントリの核心 |
| risk_reward | 0.30 | **このセットアップの最大の強み**。gap 構造由来の R/R を重視。通常の pullback entry（0.20）より高い |

### floor gate

- `min_axis_threshold: 15`
- `capped_strength: 30`

### 表示閾値

- Signal Detected: >= 50
- Approaching: >= 35
- Tracking: < 35

### config

```yaml
entry_signals:
  gap_reentry_entry:
    pool:
      preset_sources: [Power Gap Pullback]
      detection_window_days: 10
    weights:
      setup_maturity: 0.30
      timing: 0.40
      risk_reward: 0.30
    floor_gate:
      min_axis_threshold: 15
      capped_strength: 30
    display_thresholds:
      signal_detected: 50
      approaching: 35
    risk_reward:
      sl_reference: gap_low
      atr_buffer_multiplier: 0.50
      tp_reference: gap_high
```

### 典型的 R/R シナリオ

gap が 8% の銘柄が gap low から 3% 上で reentry trigger → SL 距離 3.5%（gap low + buffer）、TP 距離 5%（gap high）→ **R/R ≈ 1.4:1**。gap low のすぐ上で trigger なら **R/R ≈ 2.0:1 以上**。
