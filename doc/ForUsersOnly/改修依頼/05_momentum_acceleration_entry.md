# Momentum Acceleration Entry — 設計書（Step 1〜4）

---

## Step 1: セットアップ定義

### 1.1 セットアップの構造記述

**対象フェーズ**: established momentum → acceleration event → continuation

**核心的洞察 — 「モメンタムの二階微分」でエントリする**:

Momentum Ignition は、Momentum 97（weekly rank 97 + quarterly rank 85 以上 = 既に上位 3% の momentum 銘柄）が、さらに acceleration event（4% bullish day / PP Count >= 3）を見せている状態を検出する。

これは momentum の「一階微分」（方向 = 上昇中）ではなく「二階微分」（加速度 = 上昇が加速中）に賭ける trade。新しい catalyst や機関投資家の新規大量参入を示唆する。

**なぜ R/R が良いか**: top momentum 銘柄が加速する日は、その翌日以降に continuation が出やすい。SL は acceleration event の低値に置けるため、タイト。一方、既に強い momentum のさらなる加速であるため、短期間に大きな値幅が出やすい。

**ただし、この signal の最大のリスク**は「既に走った銘柄にさらに乗る」ことであり、climax top のリスクが常にある。そのためセットアップの品質フィルタ（VCS / Volume Accumulation）が不可欠。

**価格パターン**:

1. **確立済み momentum**: Momentum 97 が成立。weekly rank 97, quarterly rank 85 以上
2. **Acceleration event**: 4% bullish day（出来高を伴った 4% 以上の上昇）または PP Count >= 3（直近 20 日で PP が 3 回以上）
3. **Quality structure**: VCS 52 High（tight base near highs）または Volume Accumulation（U/D ratio 確認）
4. **Continuation**: acceleration event 後に follow-through があるかどうかで signal の価値が決まる

**セットアップ成立条件**:

- Momentum 97 が成立
- Acceleration event（4% bullish or PP Count）が成立
- Quality structure（VCS 52 High or Volume Accumulation）が成立

**セットアップ崩壊条件**:

- 当日に大陰線（daily_change_pct < -4%）→ climax reversal の兆候
- SMA50 を下回った → momentum 崩壊
- 翌日以降に gap down → follow-through 失敗

### 1.2 preset 対応

| preset_source | Status | 整合性 |
|---|---|---|
| `Momentum Ignition` | enabled | Momentum 97 required + Acceleration Event（4% bullish, PP Count）+ Quality Structure（VCS 52 High, Volume Accumulation）。直接対応 |

### 1.3 時間的特性

- **同日型**。Momentum 97 は rolling state だが、acceleration event（4% bullish）は当日限りのイベント
- **detection_window: 3 日**。momentum play の shelf life は非常に短い。3 日以内に follow-through がなければ、acceleration は false signal だった可能性が高い

---

## Step 2: プール構築設計

### preset_sources

```yaml
preset_sources: [Momentum Ignition]
```

### detection_window_days: 3

### 無効化条件

| # | 条件 | 根拠 |
|---|---|---|
| 1 | `daily_change_pct < -4%` | 大陰線 = climax reversal リスク。即座に pool から除外 |
| 2 | `close < sma50` | momentum 崩壊 |
| 3 | `weekly_return_rank < 80` | top momentum から脱落 |

### snapshot_at_detection

| フィールド | 理由 |
|---|---|
| `close` | 基準線 |
| `high` | acceleration day の高値（TP 参照） |
| `low` | acceleration day の安値（**SL 参照。acceleration event の下限**） |
| `atr` | バッファ幅 |
| `rs21` | RS 確認 |
| `vcs` | base 品質 |
| `weekly_return_rank` | momentum rank 追跡 |
| `rel_volume` | acceleration day の出来高（品質確認） |

### pool_tracking

| フィールド | 更新ロジック | 用途 |
|---|---|---|
| `low_since_detection` | `min(low, prev)` | SL 参照 |
| `high_since_detection` | `max(high, prev)` | continuation 進行度 |
| `days_in_pool` | `+1` | 3 日 window 管理 |
| `follow_through_count` | `+1 if daily_change_pct > 0 else 0` | follow-through の連続日数 |

---

## Step 3: 評価軸設計

### setup_maturity（重み 0.25）

| # | 指標 | フィールド | 重み | 根拠 |
|---|---|---|---|---|
| M1 | VCS 品質 | `vcs` | 0.40 | VCS が高い = base からの acceleration は構造的。VCS が低い = random spike のリスク |
| M2 | PP Count 密度 | `pp_count_window` | 0.30 | PP Count が多いほど、acceleration が一過性ではなく機関需要の継続的な表明 |
| M3 | Momentum rank | `weekly_return_rank` | 0.30 | rank が高いほど momentum が強い |

### timing（重み 0.50）

| # | 指標 | フィールド | 重み | 根拠 |
|---|---|---|---|---|
| T1 | 4% bullish | `daily_change_pct >= 4% and rel_volume >= 1.0` | 0.35 | **acceleration event の中心**。当日の爆発的値動き |
| T2 | 出来高倍率 | `rel_volume` | 0.30 | acceleration day の出来高が高いほど、event の信頼度が高い |
| T3 | 引け位置 | `dcr_percent` | 0.20 | 高値引けの acceleration は follow-through 確率が高い |
| T4 | Follow-through | `follow_through_count` | 0.15 | pool 登録翌日以降に陽線が続いているか（2 日目以降のみ有効） |

**timing 重み 0.50 の根拠**: momentum play はタイミングが全て。maturity や R/R よりも、**acceleration event が本物かどうか**がこの signal の成否を決める。

### risk_reward（重み 0.25）

**SL 参照: `snapshot_low - 0.5 * atr`**

acceleration day の安値。この日の安値を割ると、acceleration は否定された。momentum 銘柄は ATR が大きいことが多いが、acceleration day の安値は参加者の最低買い付け水準であり、構造的に意味がある。

**TP 参照**:
- 一次: `entry + (entry - SL) * 2.0`（R/R 2:1。momentum play は R/R 2:1 で十分）
- 二次: `entry * 1.08`（8% 上昇。momentum 銘柄の 3〜5 日の典型的 continuation 幅）
- **Trailing stop 推奨**: momentum play は TP を固定するより、follow-through がある限りポジションを維持する戦略が優位。entry signal としては初期 TP を示すが、trailing stop の使用を推奨する

| # | 指標 | 重み |
|---|---|---|
| R1 | R/R ratio | 0.50 |
| R2 | SL 距離 % | 0.50 |

**R2 の重みが高い理由**: momentum 銘柄は ATR が大きく、SL 距離が大きくなりやすい。SL 距離 % がポジションサイジングに直結するため、R/R ratio と同等に重視。

---

## Step 4: 統合設計

### 重み配分

| 軸 | 重み | 根拠 |
|---|---|---|
| setup_maturity | 0.25 | momentum play は maturity（base 品質）より timing（acceleration event の品質）が支配的 |
| timing | 0.50 | **最大重み**。acceleration event が本物かどうかが全て。VCS + 4% bullish + high volume + 高値引け = 最強の timing |
| risk_reward | 0.25 | SL 距離がポジションサイジングに直結するため確保 |

### floor gate

- `min_axis_threshold: 20`（momentum play は timing が低ければ意味がない。threshold を高めに）
- `capped_strength: 30`

### 表示閾値

- Signal Detected: >= 55
- Approaching: >= 40
- Tracking: < 40

**閾値を他 signal より高くした理由**: momentum play は false signal のコストが高い（climax top からの急落）。Signal Detected の基準を厳しくすることで、低品質な acceleration event をフィルタする。

### config

```yaml
entry_signals:
  momentum_acceleration_entry:
    pool:
      preset_sources: [Momentum Ignition]
      detection_window_days: 3
    weights:
      setup_maturity: 0.25
      timing: 0.50
      risk_reward: 0.25
    floor_gate:
      min_axis_threshold: 20
      capped_strength: 30
    display_thresholds:
      signal_detected: 55
      approaching: 40
    risk_reward:
      sl_reference: acceleration_day_low
      atr_buffer_multiplier: 0.50
      tp_reference: rr_2x
      trailing_stop_recommended: true
```

### Climax 対策

この signal 固有のリスクは climax top。以下のケースで warning flag を付与する（signal は出すが注意喚起）：

- `rel_volume >= 5.0`（異常な出来高。climax の可能性）
- `dist_from_52w_high >= -1%` かつ `daily_change_pct >= 6%`（新高値圏での大幅上昇。exhaustion risk）
- `days_in_pool = 0` かつ `dcr_percent < 50`（acceleration day に安値圏引け。intraday reversal の兆候）
