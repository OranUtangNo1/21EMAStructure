# Pullback Resumption Entry — 設計書（Step 1〜4）

---

## Step 1: セットアップ定義

### 1.1 セットアップの構造記述

**対象フェーズ**: uptrend → orderly pullback → support defense → trend resumption

**核心的洞察 — 「支持線の階層構造」を R/R に変換する**:

3 つの pullback 系 preset は、pullback の深さごとに異なる support level で反転を検出する。

- **Pullback Trigger**: 21EMA 近辺での浅い pullback → 21EMA pattern trigger
- **Reclaim Trigger**: 21EMA を一度割ってからの reclaim → より深い pullback からの回復
- **50SMA Defense**: 50SMA まで調整後の reclaim → 最も深い pullback

この階層構造が R/R を自動的に定義する。**pullback が深いほど SL がタイトになり（support level のすぐ下）、TP が遠くなる（直近高値への距離が大きい）ため、R/R は pullback の深さに比例して改善する**。

これは既存の orderly_pullback_entry（disabled）を発展させ、3 preset を統合し、**pullback 深度を maturity の中心指標として組み込む**設計。

**価格パターン**:

1. **Uptrend 確認**: trend_base = true（SMA50 > SMA200）。Pullback Trigger と 50SMA Defense は Trend Base annotation を持つ
2. **Orderly pullback**: Pullback Quality scan が品質を保証。出来高減少 + 適切な drawdown + 秩序ある引け位置
3. **Support test**: 21EMA / 50SMA 付近でのサポートテスト
4. **Resumption trigger**: 21EMA Pattern H/L、Reclaim scan、50SMA Reclaim、または Pocket Pivot が反転を確認
5. **Demand confirmation**: Volume Accumulation または PP

**セットアップ成立条件**:

- Pullback Quality scan が成立（orderly pullback の証拠）
- support level（21EMA or 50SMA）への接近が確認済み
- resumption trigger（21EMA Pattern / Reclaim / 50SMA Reclaim / PP）が発火

**セットアップ崩壊条件**:

- close が SMA50 を明確に下回った場合（trend 根幹の崩壊）
- pullback が 20% を超えた場合（orderly ではなく distribution の可能性）
- RS21 が 40 未満に低下（RS 崩壊）

### 1.2 preset 対応

| preset_source | Status | 整合性 |
|---|---|---|
| `Pullback Trigger` | enabled | PB Quality required + 21EMA Pattern Trigger + Demand Confirmation。浅い pullback の検出 |
| `50SMA Defense` | enabled | 50SMA Reclaim required + PB Quality + Demand Confirmation。深い pullback の検出 |
| `Reclaim Trigger` | enabled | Reclaim scan required + PP + annotation: Trend Base。中間深度の pullback の検出 |

### 1.3 時間的特性

- **ラグ型**。pullback 開始から trigger まで 3〜10 日
- **detection_window: 7 日**。pullback は通常 1〜2 週間で解決。7 日以内に trigger が出なければ次の run で再検出

---

## Step 2: プール構築設計

### preset_sources

```yaml
preset_sources: [Pullback Trigger, 50SMA Defense, Reclaim Trigger]
```

### detection_window_days: 7

### 無効化条件

| # | 条件 | 根拠 |
|---|---|---|
| 1 | `close < sma50 * 0.97` | SMA50 を 3% 以上下回ると、pullback ではなく breakdown の可能性 |
| 2 | `drawdown_from_20d_high_pct > 20%` | orderly pullback の範囲を逸脱 |
| 3 | `rs21 < 40` | RS 崩壊。pullback ではなく trend 転換 |

### snapshot_at_detection

| フィールド | 理由 |
|---|---|
| `close` | 基準線 |
| `atr_21ema_zone` | 21EMA との距離（ATR 単位）。pullback 深度の指標 |
| `atr_50sma_zone` | 50SMA との距離（ATR 単位）。pullback 深度の指標 |
| `rs21` | RS 変化追跡 |
| `atr` | バッファ幅 |
| `sma50` | SL 参照 |
| `ema21_close` | support level 参照 |
| `high_20d` | 直近高値（TP 参照） |
| `preset_source_name` | どの preset 経由で pool に入ったか（pullback 深度の判定に使用） |

### pool_tracking

| フィールド | 更新ロジック | 用途 |
|---|---|---|
| `low_since_detection` | `min(low, prev)` | pullback の最安値。SL 参照 |
| `high_since_detection` | `max(high, prev)` | resumption 進行度 |
| `days_in_pool` | `+1` | 管理 |
| `pullback_depth_category` | preset_source_name から判定 | 浅い(PT) / 中間(RT) / 深い(50D) の 3 段階 |

---

## Step 3: 評価軸設計

### setup_maturity（重み 0.35）

| # | 指標 | フィールド | 重み | 根拠 |
|---|---|---|---|---|
| M1 | Pullback 深度 R/R 品質 | `atr_50sma_zone`, `atr_21ema_zone`, `preset_source_name` | 0.35 | **深い pullback ほど R/R が良い**。50SMA Defense 経由が最高スコア |
| M2 | 出来高乾燥度 | `volume_ma5_to_ma20_ratio` | 0.25 | pullback 中の出来高乾燥は、売り圧力の枯渇を示す |
| M3 | RS 維持度 | `rs21` | 0.20 | pullback 中に RS が維持されていれば、機関投資家は手放していない |
| M4 | Trend health | `sma50_slope_10d_pct` | 0.20 | SMA50 の傾きが正であれば、trend は健全。pullback は一時的 |

**M1 の創造的スコアリング — Pullback 深度 R/R マッピング**:

pullback が深いほど（ただし orderly なら）R/R が構造的に改善する。この非直感的な関係をスコアに反映する。

- `50SMA Defense` 経由（atr_50sma_zone 0〜1）: score = 100（**最も深い orderly pullback。SL タイト + TP 遠い = 最高 R/R**）
- `Reclaim Trigger` 経由（21EMA reclaim）: score = 75（中間深度）
- `Pullback Trigger` 経由（21EMA pattern near）: score = 55（浅い pullback。R/R は moderate）
- ATR zone が不明の場合: score = 50（フォールバック）

### timing（重み 0.40）

| # | 指標 | フィールド | 重み | 根拠 |
|---|---|---|---|---|
| T1 | 21EMA Pattern trigger | `21ema_pattern_h` or `21ema_pattern_l` | 0.30 | 21EMA 近辺での反転パターン |
| T2 | Reclaim / 50SMA Reclaim | `reclaim_scan` or `close_crossed_above_sma50` | 0.25 | MA reclaim イベント |
| T3 | 出来高確認 | `rel_volume` | 0.25 | resumption 日の出来高 |
| T4 | Pocket Pivot | `pocket_pivot` | 0.20 | 機関需要の確認 |

### risk_reward（重み 0.25）

**SL 参照 — pullback 深度に応じた階層的 SL**:

| 深度カテゴリ | SL 参照 | 根拠 |
|---|---|---|
| 50SMA Defense | `sma50 - 0.5 * atr` | 50SMA 割れは trend 否定 |
| Reclaim Trigger | `low_since_detection - 0.5 * atr` | pullback の最安値割れは continuation failure |
| Pullback Trigger | `ema21_close - 1.0 * atr` | 21EMA の 1 ATR 下。浅い pullback は buffer を広めに |

**TP 参照: `snapshot_high_20d`**（直近 20 日高値 = pullback 前の高値）

| # | 指標 | 重み |
|---|---|---|
| R1 | R/R ratio | 0.55 |
| R2 | SL 距離 % | 0.45 |

---

## Step 4: 統合設計

### 重み配分

| 軸 | 重み | 根拠 |
|---|---|---|
| setup_maturity | 0.35 | pullback 深度が R/R を構造的に決定するため、maturity = R/R の先行指標 |
| timing | 0.40 | resumption trigger が出た日がエントリ日。pullback play は trigger のタイミングが全て |
| risk_reward | 0.25 | R/R は maturity（深度）と timing から間接的に決まるが、explicit R/R チェックも必要 |

### floor gate

- `min_axis_threshold: 15`
- `capped_strength: 30`

### 表示閾値

- Signal Detected: >= 48
- Approaching: >= 32
- Tracking: < 32

### config

```yaml
entry_signals:
  pullback_resumption_entry:
    pool:
      preset_sources: [Pullback Trigger, 50SMA Defense, Reclaim Trigger]
      detection_window_days: 7
    weights:
      setup_maturity: 0.35
      timing: 0.40
      risk_reward: 0.25
    floor_gate:
      min_axis_threshold: 15
      capped_strength: 30
    display_thresholds:
      signal_detected: 48
      approaching: 32
    risk_reward:
      sl_reference: depth_adaptive
      tp_reference: high_20d
```

### 差別化ポイント

3 preset を 1 つの entry signal に統合しつつ、**pullback_depth_category で R/R の構造的優位性を自動評価**する。50SMA Defense 経由の候補は maturity M1 で最高スコアを取り、かつ R/R ratio も構造的に高くなるため、entry_strength が自然に最上位になる。浅い pullback（Pullback Trigger 経由）は R/R が moderate だが、trigger の頻度が高いためスクリーニング候補の幅を確保する。
