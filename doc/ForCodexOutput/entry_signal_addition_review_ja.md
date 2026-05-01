# Entry Signal 追加依頼の精査メモ

作成日: 2026-04-26

## 対象

- 依頼元: `doc/ForUsersOnly/改修依頼/`
- 対象ファイル:
  - `00_overview.md`
  - `01_gap_reentry_entry.md`
  - `02_rs_lead_breakout_entry.md`
  - `03_pullback_resumption_entry.md`
  - `04_recovery_breakout_entry.md`
  - `05_momentum_acceleration_entry.md`

このメモは依頼書の内容を現在の実装、`config/default/scan.yaml`、Entry Signal 実装と照合したレビューです。元ファイルは変更していません。

## 全体結論

5 本の新規 Entry Signal 案は、現在 enabled の built-in preset 群への対応としては概ね妥当です。特に、現在 disabled の `Orderly Pullback` / `Trend Pullback` ではなく、enabled preset を source にしている点は現行 runtime に合っています。

ただし、現在の実装では `config/default/entry_signals.yaml` に定義を追加するだけでは動きません。`src/signals/runner.py` の dispatch は `orderly_pullback_entry` のみ対応しており、評価ロジックも `src/signals/evaluators/orderly_pullback.py` に強く寄っています。新規 signal は最低でも evaluator 追加、runner dispatch 追加、テスト追加が必要です。

また、依頼書の YAML 例は現在の `EntrySignalConfig` スキーマと一致していません。現行スキーマでは `entry_signals.definitions.<signal_key>` 配下に `pool`、`setup_maturity`、`timing`、`risk_reward.stop/reward/scoring`、`entry_strength`、`display` を持つ必要があります。

## 実装可能性

| 項目 | 判定 | 理由 |
|---|---|---|
| signal config の追加 | 実装可能 | ただし依頼書の簡略 YAML はそのままでは読めないため、現行スキーマへ展開が必要 |
| pool source preset 連携 | 実装可能 | `EntrySignalRunner` は preset duplicate 出力を source にして pool を作る設計済み |
| 複数 preset を 1 signal に統合 | 実装可能 | `preset_sources` は複数 source を保持でき、DB に JSON 配列で保存される |
| signal ごとの scoring | 実装可能 | ただし現状は `orderly_pullback_entry` 専用 evaluator のため、新規 evaluator が必要 |
| signal ごとの R/R | 実装可能 | ただし現在の `risk_reward.py` は参照名が限定的。gap low/high、depth adaptive、break stage adaptive、rr_2x などは拡張が必要 |
| custom pool tracking | 一部不可 | DB は `low_since_detection` と `high_since_detection` のみ。`days_in_pool` は算出可能だが、`follow_through_count` などは追加実装が必要 |
| warning flag 表示 | 一部不可 | `Entry Signal` 結果列に warning 専用列はない。`Timing Detail` に入れるか UI/DB 拡張が必要 |

## Preset 適合性

| Entry Signal 案 | Source preset | 適合性 | コメント |
|---|---|---|---|
| Gap Reentry Entry | `Power Gap Pullback` | 高い | preset は `Recent Power Gap`、`Trend Base`、`Pullback Quality scan`、reentry trigger、demand confirmation を要求しており設計意図と合う |
| RS Lead Breakout Entry | `RS Breakout Setup`, `Accumulation Breakout` | 高い | `RS Breakout Setup` は直接対応。`Accumulation Breakout` は RS New High を要求しないため、RS lead なしの accumulation path として評価を分ける必要あり |
| Pullback Resumption Entry | `Pullback Trigger`, `50SMA Defense`, `Reclaim Trigger` | 高い | pullback 深度別に source を分ける設計は現行 preset とよく合う。`Reclaim Trigger` は `Pullback Quality scan` を直接要求しない点だけ注意 |
| Recovery Breakout Entry | `Screening Thesis`, `Early Cycle Recovery` | 中〜高 | `Screening Thesis` は構造 break と合う。`Early Cycle Recovery` は structure break 必須ではないため、entry signal 側で breakout timing を再評価すべき |
| Momentum Acceleration Entry | `Momentum Ignition` | 高い | preset は `Momentum 97` required、acceleration event、quality structure を要求しており直接対応 |

## 実装上の不足点

### 1. evaluator の追加が必須

現在の `EntrySignalRunner._evaluate_signal()` は `orderly_pullback_entry` 以外を `ValueError` にします。5 本を追加するなら、以下のいずれかが必要です。

- signal ごとに evaluator を追加する
- 共通 evaluator を作り、signal key ごとの custom timing / R/R resolver を registry 化する

今回の設計は signal ごとの R/R 参照が大きく違うため、最初は signal 別 evaluator の方が安全です。

### 2. gap low / gap high が現在ない

`Recent Power Gap` は `power_gap_up_pct` と `days_since_power_gap` だけを見ています。依頼書の Gap Reentry が必要とする `gap_low` / `gap_high` は現在 snapshot にありません。

改善案:

- indicator layer に `power_gap_low`, `power_gap_high`, `power_gap_open`, `power_gap_close`, `power_gap_date_index` を追加する
- `Gap Reentry Entry` の snapshot fields は `power_gap_low` / `power_gap_high` を使う
- R/R は `stop = power_gap_low - 0.25〜0.5 ATR`、target は `min(power_gap_high, rolling_20d_close_high)` を第一候補にする

### 3. preset source 名を個別 row に残す粒度が弱い

現在の pool は `preset_sources` を配列で持ちます。複数 preset に同時ヒットした場合、どの source を優先して深度や R/R を決めるかは evaluator 側で決める必要があります。

改善案:

- Pullback Resumption は source 優先順位を明示する: `50SMA Defense > Reclaim Trigger > Pullback Trigger`
- RS Lead Breakout は `RS Breakout Setup` を RS lead path、`Accumulation Breakout` を accumulation path として scoring 分岐する
- 同時ヒット時は R/R が良い source ではなく、より厳格な source を採用する

### 4. R/R resolver が不足

現在の `risk_reward.py` は主に `low_since_detection`、通常 row field、`snapshot_rolling_20d_close_high`、`measured_move` に対応しています。依頼書の以下は追加が必要です。

- `gap_low`, `gap_high`
- `contraction_low`
- `depth_adaptive`
- `break_stage_adaptive`
- `acceleration_day_low`
- `rr_2x`, `rr_3x`
- `structure_pivot_swing_high`

## R/R を良くするための改善案

### Gap Reentry Entry

設計方向は良いですが、`gap_high` を固定 target にすると、すでに gap high 近辺まで戻った候補の R/R が悪くなります。

改善案:

- Signal Detected 条件に `close <= power_gap_high` を必須化する
- `close` が `power_gap_high` の 98% 以上なら `Signal Detected` ではなく `Tracking` に落とす
- stop buffer は `0.5 ATR` 固定ではなく、`max(0.25 ATR, entry * 1.0%)` 程度に抑える
- `gap_low` からの距離だけでなく、`target_gap = power_gap_high - close` と `risk = close - stop` の実 R/R を最優先する

推奨重み:

| axis | 現案 | 改善案 |
|---|---:|---:|
| setup_maturity | 0.30 | 0.25 |
| timing | 0.40 | 0.35 |
| risk_reward | 0.30 | 0.40 |

Gap Reentry は構造 target が明確なので、R/R を 0.40 まで上げる方が設計思想に合います。

### RS Lead Breakout Entry

`RS Breakout Setup` と `Accumulation Breakout` を同じ signal に入れるのは妥当ですが、accumulation path に RS lead スコア 30 を与えるだけだと、良い accumulation breakout が不当に低くなる可能性があります。

改善案:

- `RS Breakout Setup` 経由: `rs_price_divergence_score` を重視
- `Accumulation Breakout` 経由: `pp_count_window`, `ud_volume_ratio`, `pocket_pivot`, `daily_change_pct` を重視
- stop は `low_since_detection - 0.5 ATR` でよいが、`risk_in_atr > 2.5` は R/R score を強く減点する
- target は `high_52w` が近すぎる場合、`rr_3x` を primary に切り替える

推奨ルール:

- `high_52w - close` が `1.5R` 未満なら `high_52w` を target にしない
- `dist_from_52w_high > -3%` の near-high breakout は `rr_3x` target を優先

### Pullback Resumption Entry

「深い pullback ほど R/R が良い」という洞察は有効ですが、深い pullback は失敗率も上がります。50SMA Defense を常に最高点にすると、trend damage を過小評価します。

改善案:

- 50SMA Defense は `sma50_slope_10d_pct > 0`、`close_crossed_above_sma50 = true`、`dcr_percent >= 60` が揃った場合だけ M1 最高点
- `atr_50sma_zone < 0` または `close < sma50` は即 invalidation
- target は `rolling_20d_close_high` を使い、`reward_in_atr < 1.5` なら Signal Detected 不可
- `Pullback Trigger` は浅い分、stop を `ema21_close - 0.75 ATR` にして過度に広げない

推奨 source 優先:

| source | R/R score の初期 bias | 条件 |
|---|---:|---|
| `50SMA Defense` | 高 | SMA50 上 reclaim 当日かつ trend slope positive |
| `Reclaim Trigger` | 中〜高 | low_since_detection からの距離が近い |
| `Pullback Trigger` | 中 | shallow pullback で target 余地がある |

### Recovery Breakout Entry

1st break を最重視する方針は R/R 面で正しいです。ただし `Early Cycle Recovery` は structure break を要求しないため、signal 側で 1st/2nd/CT break の有無を厳密に見ないと、ただの recovery watchlist が entry signal 化します。

改善案:

- `Signal Detected` は `structure_pivot_1st_break` または `ct_trendline_break` を必須にする
- `structure_pivot_2nd_break` は確認として扱い、R/R が 1.5 未満なら `Approaching` に落とす
- `Early Cycle Recovery` 経由で structure break がない場合は `Tracking` に固定する
- stop は 1st break なら `structure_pivot_hl_price - 0.75 ATR`
- target は `structure_pivot_swing_high`、ただし target が近すぎる場合は `rr_2x` を fallback にする

推奨表示閾値:

- Signal Detected: 45 は維持でよい
- ただし timing が 50 未満なら floor gate で 25 に cap

### Momentum Acceleration Entry

設計は preset とよく合っています。最大の課題は R/R ではなく、climax top を避けることです。

改善案:

- `daily_change_pct >= 8%` かつ `rel_volume >= 5` は Signal Detected ではなく warning 付き Approaching に落とす
- `dcr_percent < 60` は acceleration day の失敗として timing を大きく減点する
- stop は `snapshot_low - 0.25 ATR` から始め、`risk_in_atr > 2.0` なら R/R score を cap する
- target は固定 2R を primary、`entry * 1.08` は secondary にする
- `days_in_pool > 1` で follow-through がない場合は急速に score decay させる

推奨重み:

| axis | 現案 | 改善案 |
|---|---:|---:|
| setup_maturity | 0.25 | 0.20 |
| timing | 0.50 | 0.45 |
| risk_reward | 0.25 | 0.35 |

Momentum は timing が重要ですが、R/R の悪い追いかけ買いを避けるため、risk_reward を 0.35 まで上げる方が実運用向きです。

## 実装優先順位

1. `Pullback Resumption Entry`
   - 既存 `orderly_pullback_entry` の発展形で、既存 evaluator の再利用余地が最も大きい。
   - source preset がすべて enabled。

2. `Momentum Acceleration Entry`
   - 必要フィールドの多くが既存にあり、実装範囲が比較的小さい。
   - climax warning の扱いだけ追加判断が必要。

3. `RS Lead Breakout Entry`
   - preset 適合性は高いが、RS lead path と accumulation path の分岐が必要。

4. `Recovery Breakout Entry`
   - structure pivot fields は既にあるが、break stage adaptive R/R の実装がやや複雑。

5. `Gap Reentry Entry`
   - preset 適合性は高いが、肝心の `gap_low` / `gap_high` が現状ないため、indicator layer 拡張が先に必要。

## 最低限の実装タスク

- `config/default/entry_signals.yaml` に 5 signal を現行スキーマで追加
- `src/signals/evaluators/` に evaluator を追加
- `src/signals/runner.py::_evaluate_signal()` に dispatch を追加
- `src/signals/risk_reward.py` に signal-specific reference resolver を追加、または evaluator 内で R/R を個別計算
- `src/indicators/core.py` に不足フィールドを追加
- `tests/test_entry_signals.py` と `tests/test_entry_signal_scoring.py` に各 signal の代表ケースを追加
- 実装後に `doc/SystemDocs/EntrySignal/` と `doc/SystemDocs/Specifications/05_DASHBOARD_UI_SPEC.md` を同期

## 推奨方針

最初から 5 本を同時実装するより、共通基盤を少し整えたうえで `Pullback Resumption Entry` から入るのが安全です。理由は、現行の `orderly_pullback_entry` とドメインが近く、pool tracking、R/R、timing detail の既存設計を最も多く流用できるためです。

その後、`Momentum Acceleration Entry` を追加すると、短期 event 型 signal の実装パターンを固められます。`Gap Reentry Entry` は R/R の思想は最も明確ですが、gap price reference のデータ整備が先です。
