# RS Lead Breakout Entry — 設計書（Step 1〜4）

---

## Step 1: セットアップ定義

### 1.1 セットアップの構造記述

**対象フェーズ**: volatility contraction near 52W high → RS-confirmed breakout

**核心的洞察 — RS が価格に先行する「非対称情報」**:

RS Breakout Setup は `RS New High`（RS ratio が 52 週高値）+ `VCS 52 High`（価格が 52W high 近辺で contraction 中）を required とする。これは**価格がまだ新高値を取っていないのに、RS ratio が先に新高値を取った**状態を検出する。

この RS-price divergence は、機関投資家がベンチマーク対比で当該銘柄をオーバーウェイトし始めた構造的証拠。RS が先行し、価格が追随するパターンは、breakout の中で最も follow-through 率が高い類型の一つ。

Accumulation Breakout は VCS 52 High + PP Count / Volume Accumulation で accumulation の痕跡を検出する。RS lead と accumulation は同じコインの裏表であり、共通の trade thesis を持つ。

**価格パターン**:

1. **Contraction 期**: 52W high 近辺で VCS が高水準（base 形成中）
2. **RS 先行シグナル**: RS ratio が 52W high に到達。価格は -5% 〜 -30% の位置にまだいる
3. **Breakout trigger**: PP / 4% bullish / PP Count が出来高面で breakout を確認
4. **価格の追随**: RS が既に示した方向に、出来高を伴って価格が動き出す

**セットアップ成立条件**:

- `rs_ratio_at_52w_high = true`（RS 先行）または `pp_count >= 3`（accumulation 痕跡）
- `VCS 52 High` scan が成立（tight base near highs）
- breakout trigger（PP / 4% bullish）が発火可能な状態

**セットアップ崩壊条件**:

- `rs_ratio_at_52w_high` が false に戻った（RS が新高値から後退）
- VCS が 40 未満に低下（base 崩壊）
- `dist_from_52w_high < -30%`（RS New High scan の下限を超えて下落）

### 1.2 preset 対応

| preset_source | Status | 整合性 |
|---|---|---|
| `RS Breakout Setup` | enabled | RS New High + VCS 52 High required + Breakout Event optional。RS lead breakout の核心 |
| `Accumulation Breakout` | enabled | VCS 52 High required + Accumulation Evidence + Breakout Trigger。accumulation 視点の breakout。RS lead と相補的 |

### 1.3 時間的特性

- **同日〜数日ラグ型**。RS lead は数日〜数週間持続するが、breakout trigger は特定日に発火
- **detection_window: 7 日**。VCS 52 High + RS New High が同時成立する期間は限定的

---

## Step 2: プール構築設計

### preset_sources

```yaml
preset_sources: [RS Breakout Setup, Accumulation Breakout]
```

### detection_window_days: 7

### 無効化条件

| # | 条件 | 根拠 |
|---|---|---|
| 1 | `close < sma50` | trend base 崩壊 |
| 2 | `vcs < 40` | base quality 劣化 |
| 3 | `dist_from_52w_high < -30%` | RS New High の有効レンジ外に下落 |

### snapshot_at_detection

| フィールド | 理由 |
|---|---|
| `close` | 基準線 |
| `vcs` | contraction 品質の基準 |
| `rs21` | RS 変化追跡 |
| `dist_from_52w_high` | 52W high との距離。breakout 余地の計算 |
| `high_52w` | TP 参照。新高値到達の基準 |
| `atr` | バッファ幅 |
| `sma50` | SL 補助参照 |
| `rs_ratio_at_52w_high` | RS lead の有無（検出時） |

### pool_tracking

| フィールド | 更新ロジック | 用途 |
|---|---|---|
| `low_since_detection` | `min(low, prev)` | SL 候補（contraction low） |
| `high_since_detection` | `max(high, prev)` | breakout 進行度 |
| `days_in_pool` | `+1` | 管理 |
| `rs_lead_sustained` | `current rs_ratio_at_52w_high` | RS lead が持続しているかの追跡 |

---

## Step 3: 評価軸設計

### setup_maturity（重み 0.35）

| # | 指標 | フィールド | 重み | 根拠 |
|---|---|---|---|---|
| M1 | VCS レベル | `vcs` | 0.30 | 高いほど base が tight で breakout の成功率が高い |
| M2 | RS lead 強度 | `dist_from_52w_high` + `rs_ratio_at_52w_high` | 0.35 | **RS が新高値 + 価格がまだ離れている = 乖離が大きいほど潜在エネルギーが大きい** |
| M3 | 52W high 近接度 | `dist_from_52w_high` | 0.20 | 近いほど breakout までの距離が短い |
| M4 | Accumulation 証拠 | `pp_count_window` | 0.15 | PP Count が多いほど機関需要の蓄積が厚い |

**M2 の創造的スコアリング — RS-Price 乖離スコア**:

RS が新高値なのに価格が 52W high から離れている = 「バネが圧縮されている」状態。

- `rs_ratio_at_52w_high = true` かつ `dist >= -10%`: score = 70（RS lead あるが price も近い。乖離小）
- `rs_ratio_at_52w_high = true` かつ `-10% > dist >= -20%`: score = 100（**最大スコア。RS lead + 十分な乖離。最もエネルギーが溜まっている**）
- `rs_ratio_at_52w_high = true` かつ `dist < -20%`: score = 80（乖離大だが recovery 余地も大きい。やや不確実）
- `rs_ratio_at_52w_high = false`: score = 30（Accumulation Breakout 経由。RS lead なし）

### timing（重み 0.40）

| # | 指標 | フィールド | 重み | 根拠 |
|---|---|---|---|---|
| T1 | Pocket Pivot | `pocket_pivot` | 0.30 | 機関需要の痕跡 |
| T2 | 4% bullish | `4pct_bullish` | 0.25 | 当日の爆発的な値動き + 出来高 |
| T3 | 出来高確認 | `rel_volume` | 0.25 | breakout の出来高品質 |
| T4 | 引け位置 | `dcr_percent` | 0.20 | breakout 日の close 品質 |

### risk_reward（重み 0.25）

**SL 参照: `low_since_detection - 0.5 * atr`**

contraction 期間中の最安値。VCS が高い銘柄は ATR が小さいため、SL がタイトになりやすい = 構造的に R/R が良くなる傾向。

**TP 参照**:
- 一次: `high_52w`（新高値到達）
- 二次: `entry + (entry - SL) * 3.0`（R/R 3:1）
- フォールバック: `entry * 1.10`

| # | 指標 | 重み |
|---|---|---|
| R1 | R/R ratio | 0.60 |
| R2 | SL 距離 % | 0.40 |

---

## Step 4: 統合設計

### 重み配分

| 軸 | 重み | 根拠 |
|---|---|---|
| setup_maturity | 0.35 | RS lead の強度と VCS の品質が breakout 成功率を決定する。Accumulation Breakout は RS lead がないため maturity で差がつく |
| timing | 0.40 | breakout trigger が出た日がエントリ日。RS lead が蓄積エネルギーを示し、timing が trigger を確認する |
| risk_reward | 0.25 | VCS near highs は構造的に SL がタイトになりやすい。R/R は自然に良好 |

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
  rs_lead_breakout_entry:
    pool:
      preset_sources: [RS Breakout Setup, Accumulation Breakout]
      detection_window_days: 7
    weights:
      setup_maturity: 0.35
      timing: 0.40
      risk_reward: 0.25
    floor_gate:
      min_axis_threshold: 15
      capped_strength: 30
    display_thresholds:
      signal_detected: 50
      approaching: 35
    risk_reward:
      sl_reference: contraction_low
      atr_buffer_multiplier: 0.50
      tp_reference: high_52w
```

### 差別化ポイント

RS lead 銘柄（RS Breakout Setup 経由）と accumulation 銘柄（Accumulation Breakout 経由）が同じ pool に入るが、**M2 の RS-Price 乖離スコアで RS lead 銘柄が maturity で大きくアドバンテージを持つ**。これにより、RS lead + breakout trigger の組み合わせが自然に最高スコアを取る設計。
