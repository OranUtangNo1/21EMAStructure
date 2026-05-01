# Recovery Breakout Entry — 設計書（Step 1〜4）

---

## Step 1: セットアップ定義

### 1.1 セットアップの構造記述

**対象フェーズ**: dead cross 環境 → structural reversal → breakout confirmation

**核心的洞察 — 「構造転換の多段ロケット」**:

Screening Thesis と Early Cycle Recovery は、dead cross（SMA50 <= SMA200）環境下で recovery の最初期兆候を検出する preset。通常の uptrend play が使えない環境での唯一のエントリ機会。

**多段 breakout の考え方**: LL-HL 構造には 3 段階の breakout がある。

- **1st pivot break**（0.618 リトレースメント）: **R/R が最良。SL を HL に置ける。まだ swing high に到達していないため TP の余地が大きい**
- **2nd pivot break**（swing high）: 構造転換の完全確認。ただし SL（HL）からの距離が遠い
- **CT trendline break**: 下降トレンドラインを上抜く。独立シグナル

entry signal は **1st pivot break を最も高く評価する**。なぜなら 1st break は最も R/R が良いエントリポイントであり、2nd break は「確認」であって「最良のエントリ」ではないから。

**セットアップ成立条件**:

- `Trend Reversal Setup` が成立（SMA50 <= SMA200, SMA50 上向き, close > SMA50, PP あり）
- structure break（LL-HL 1st / 2nd / CT break）のいずれかが発火、または PP + demand confirmation が発火
- Screening Thesis 経由: Trend Reversal Setup + Structure Break + Demand
- Early Cycle Recovery 経由: Trend Reversal Setup + PP + VCS 52 Low / Volume Accumulation

**セットアップ崩壊条件**:

- SMA50 の上向き傾斜が止まった（sma50_slope_10d_pct <= 0）
- close が SMA50 を下回った
- RS21 が検出時から 15pt 以上低下（recovery 失敗）

### 1.2 preset 対応

| preset_source | Status | 整合性 |
|---|---|---|
| `Screening Thesis` | enabled | Trend Reversal Setup required + Structure Break（LL-HL 1st/2nd/CT）+ Demand Confirmation。構造転換 + breakout の検出 |
| `Early Cycle Recovery` | enabled | Trend Reversal Setup + PP required + VCS 52 Low / Volume Accumulation optional。PP ベースの早期 recovery 検出 |

### 1.3 時間的特性

- **ラグ型**。Trend Reversal Setup 成立から structure break まで 5〜20 日
- **detection_window: 14 日**。recovery play は構造形成に時間がかかるため長め

---

## Step 2: プール構築設計

### preset_sources

```yaml
preset_sources: [Screening Thesis, Early Cycle Recovery]
```

### detection_window_days: 14

### 無効化条件

| # | 条件 | 根拠 |
|---|---|---|
| 1 | `close < sma50` | SMA50 下回り = Trend Reversal Setup の前提崩壊 |
| 2 | `sma50_slope_10d_pct <= 0` | SMA50 が下向きに転じた = reversal 失敗 |
| 3 | `rs21 < snapshot_rs21 - 15` | RS の大幅悪化。recovery 失速 |

### snapshot_at_detection

| フィールド | 理由 |
|---|---|
| `close` | 基準線 |
| `rs21`, `rs63` | RS 回復追跡 |
| `structure_pivot_long_hl_price` | **SL 参照（structure break 経由の場合）** |
| `sma50` | SL 補助参照 |
| `atr` | バッファ幅 |
| `dist_from_52w_high`, `dist_from_52w_low` | recovery 進行度 |
| `sma50_slope_10d_pct` | trend reversal の勢い |

### pool_tracking

| フィールド | 更新ロジック | 用途 |
|---|---|---|
| `low_since_detection` | `min(low, prev)` | SL 参照 |
| `high_since_detection` | `max(high, prev)` | breakout 進行度 |
| `days_in_pool` | `+1` | 管理 |
| `rs21_delta` | `current rs21 - snapshot_rs21` | RS 回復の追跡 |

---

## Step 3: 評価軸設計

### setup_maturity（重み 0.40）

| # | 指標 | フィールド | 重み | 根拠 |
|---|---|---|---|---|
| M1 | SMA50 勢い | `sma50_slope_10d_pct` | 0.30 | 傾きが急であるほど reversal の conviction が高い |
| M2 | RS 回復度 | `rs21_delta` | 0.30 | pool 登録時からの RS 改善幅。recovery の進行証拠 |
| M3 | 出来高蓄積 | `ud_volume_ratio` | 0.20 | U/D ratio > 1 は institutional accumulation |
| M4 | SMA50 距離 | `atr_50sma_zone` | 0.20 | SMA50 上にしっかり乗っているほど安全 |

### timing（重み 0.35）

| # | 指標 | フィールド | 重み | 根拠 |
|---|---|---|---|---|
| T1 | 1st Pivot Break | `structure_pivot_1st_break` | 0.35 | **最高 R/R のエントリポイント** |
| T2 | 2nd Pivot Break | `structure_pivot_2nd_break` | 0.20 | 構造転換の完全確認 |
| T3 | CT Break | `ct_trendline_break` | 0.15 | 下降トレンドライン breakout |
| T4 | 出来高確認 | `rel_volume` | 0.30 | breakout の出来高品質 |

**1st break を最重視する理由**: 1st break 時点では SL（HL price）が近く、TP（swing high）が遠い。2nd break では既に swing high 付近にいるため TP が見えにくく、SL（HL）が遠い。**機械的 R/R は 1st break が圧倒的に優位**。

### risk_reward（重み 0.25）

**SL 参照 — breakout 段階に応じた適応的 SL**:

| break 段階 | SL 参照 | 根拠 |
|---|---|---|
| 1st break | `structure_pivot_long_hl_price - 0.75 * atr` | HL が構造的 SL。recovery は ATR が大きいため 0.75 ATR buffer |
| 2nd break | `structure_pivot_1st_pivot_level - 0.75 * atr` | 1st pivot level まで戻ったら構造崩壊 |
| CT break | `low_since_detection - 0.75 * atr` | pool 期間中の最安値 |
| PP only（Early Cycle Recovery 経由） | `sma50 - 1.0 * atr` | SMA50 割れは reversal 否定 |

**TP 参照**:
- 1st break 時: `structure_pivot_swing_high`（swing high への到達）
- 2nd break 時: `swing_high * 1.10`
- フォールバック: `entry * 1.15`

| # | 指標 | 重み |
|---|---|---|
| R1 | R/R ratio | 0.50 |
| R2 | SL 距離 % | 0.30 |
| R3 | TP 到達可能性 | 0.20 |

---

## Step 4: 統合設計

### 重み配分

| 軸 | 重み | 根拠 |
|---|---|---|
| setup_maturity | 0.40 | **recovery play は構造の信頼度が最重要**。SMA50 の勢い + RS 回復が false recovery の排除に直結 |
| timing | 0.35 | structure break は数日有効な構造イベント。1st break を最重視するが、当日限りのイベント性は低い |
| risk_reward | 0.25 | recovery は SL が遠くなりやすい。R/R の弁別力が高いため weight を確保 |

### floor gate

- `min_axis_threshold: 10`（recovery play は寛容に）
- `capped_strength: 25`

### 表示閾値

- Signal Detected: >= 45
- Approaching: >= 30
- Tracking: < 30

### config

```yaml
entry_signals:
  recovery_breakout_entry:
    pool:
      preset_sources: [Screening Thesis, Early Cycle Recovery]
      detection_window_days: 14
    weights:
      setup_maturity: 0.40
      timing: 0.35
      risk_reward: 0.25
    floor_gate:
      min_axis_threshold: 10
      capped_strength: 25
    display_thresholds:
      signal_detected: 45
      approaching: 30
    risk_reward:
      sl_reference: break_stage_adaptive
      atr_buffer_multiplier: 0.75
      tp_reference: swing_high
```
