# 21EMA パターンスキャン仕様書

作成日: 2026-04-17

---

## 1. 概要

既存の scan_01 (21EMA scan) を廃止し、21EMA の高値 EMA / 安値 EMA を用いた 2 本のパターン別スキャンに置き換える。

### 1.1 設計思想

21EMA は 1 本の線ではなく、`EMA(high, 21)` / `EMA(close, 21)` / `EMA(low, 21)` の 3 本で構成されるバンドとして扱う。株価がバンドのどの位置に触れているかによって、セットアップの質とトリガー条件が異なる。

- **パターン H**: 安値が 21EMA(H) 近辺で止まる浅い押し。最も強いトレンドで出現する
- **パターン L**: 安値が 21EMA(L) を日中割り込んで終値で奪回する深い押し。トレンド継続の最終防衛線

パターン C（中央帯 `atr_21ema_zone ∈ [-0.1, 0.3]`）は本仕様では保留とし、将来の追加候補として記録する。

### 1.2 scan_01 との関係

| 項目 | scan_01 (廃止) | scan_22 Pattern H | scan_23 Pattern L |
|---|---|---|---|
| atr_21ema_zone 帯域 | [-0.5, 1.0] | [0.3, 1.0] | [-0.5, -0.1] |
| カバー外の帯域 | なし | [-0.5, 0.3) | (-0.1, 1.0] |
| トリガー条件 | なし（セットアップ存在スキャン） | 前日高値ブレイク | 21EMA(L) 割り込み奪回 + 前日高値ブレイク |
| trend_base | スキャン内に記述 | ポストスキャンに移譲済み | ポストスキャンに移譲済み |
| weekly_return | [0, 15] | なし（プリセット側で制御） | なし（プリセット側で制御） |
| dcr_percent | > 20 | なし（プリセット側で制御） | なし（プリセット側で制御） |

scan_01 の `weekly_return` / `dcr_percent` 条件は、スキャン改修依頼書に基づきスキャン固有条件として各スキャンに残す方針だが、新規 2 本では**意図的に含めない**。理由は、これらの品質フィルタはパターン H / L の足型定義に固有ではなく、プリセット側で他スキャンや将来のポストスキャンと組み合わせて制御する方が表現力が高いため。

---

## 2. 廃止: scan_01 21EMA scan

### 2.1 廃止理由

- scan_01 はトリガー条件を持たないセットアップ存在スキャンであり、「当日バーにトリガー成立を抜く」方針と整合しない
- scan_01 のゾーン帯域 [-0.5, 1.0] は scan_22 / scan_23 のゾーン帯域の和集合から中央帯 [-0.1, 0.3] を除いたものと近似する
- scan_01 に含まれていた汎用品質ゲート (`trend_base`, `weekly_return`, `dcr_percent`) は、スキャン改修依頼書に基づきポストスキャン化またはプリセット側制御に移行済み

### 2.2 廃止作業

- `src/scan/rules.py::_scan_21ema` 関数を削除
- スキャン登録箇所から該当エントリを削除
- スキャンドキュメント `doc/SystemDocs/Scan/scan_01_21ema.md` を削除
- `scan_00_index.md` の Active Scan Specs 表から該当行を削除
- `scan_00_index.md` 本文のスキャン数記述を更新
- scan_01 を指定している既存プリセットの書き換え（システム側対応）

---

## 3. 新規指標フィールド

scan_22 / scan_23 の実装に先立ち、`src/indicators/core.py::IndicatorCalculator.calculate` に以下のフィールドを追加する。

### 3.1 追加フィールド一覧

```python
# 21EMA バンド
ema21_high = high.ewm(span=21, adjust=False).mean()
ema21_low  = low.ewm(span=21, adjust=False).mean()

# ATR ゾーン（close 基準）
atr_21emaH_zone = (close - ema21_high) / atr
atr_21emaL_zone = (close - ema21_low) / atr

# ATR ゾーン（low 基準、パターン判定用）
atr_low_to_ema21_high = (low - ema21_high) / atr
atr_low_to_ema21_low  = (low - ema21_low) / atr

# 前日高値
prev_high = high.shift(1)
```

### 3.2 フィールド定義の詳細

| フィールド | 計算式 | 意味 |
|---|---|---|
| `ema21_high` | `high.ewm(span=21, adjust=False).mean()` | 高値の 21 日 EMA |
| `ema21_low` | `low.ewm(span=21, adjust=False).mean()` | 安値の 21 日 EMA |
| `atr_21emaH_zone` | `(close - ema21_high) / atr` | 終値と 21EMA(H) の ATR 正規化距離 |
| `atr_21emaL_zone` | `(close - ema21_low) / atr` | 終値と 21EMA(L) の ATR 正規化距離 |
| `atr_low_to_ema21_high` | `(low - ema21_high) / atr` | 安値と 21EMA(H) の ATR 正規化距離 |
| `atr_low_to_ema21_low` | `(low - ema21_low) / atr` | 安値と 21EMA(L) の ATR 正規化距離 |
| `prev_high` | `high.shift(1)` | 前日高値 |

### 3.3 既存フィールドとの関係

| 既存フィールド | 新フィールド | 関係 |
|---|---|---|
| `ema21_close` | `ema21_high`, `ema21_low` | 同じ EMA 計算を high / low 列に適用した兄弟 |
| `atr_21ema_zone` | `atr_21emaH_zone`, `atr_21emaL_zone` | 同じ ATR 正規化パターンを 21EMA(H) / 21EMA(L) に適用した派生 |
| なし | `atr_low_to_ema21_high`, `atr_low_to_ema21_low` | 安値基準の新系統。close ではなく low を使う点が既存と異なる |
| なし | `prev_high` | `high.shift(1)` の単純シフト |

---

## 4. scan_22: 21EMA Pattern H

### 4.1 Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `21EMA Pattern H` |
| UI display name | `21EMA PH` |
| Implementation owner | `src/scan/rules.py::_scan_21ema_pattern_h` |
| Output | `bool` |
| Direct scan config | none (v1 hard-coded thresholds) |

### 4.2 Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads only precomputed indicator fields.
- All conditions are combined with `AND`.
- Intended as a **shallow pullback trigger scan** for stocks holding near the 21EMA high band.
- This scan detects **the strongest pullback pattern** where selling pressure is minimal and the stock barely dips below its recent high-value EMA.

### 4.3 Intent / Scan Role

このスキャンは、**最も強いトレンドにおける浅い押し目からの再始動**を検出する。

マッチした銘柄は以下の全てを満たすべきである。

- 終値が 21EMA(C) より十分上にあり、押しが浅い
- 日中安値が 21EMA(H) の近辺で支えられている（高値 EMA がサポートとして機能）
- 50SMA からの乖離が健全な範囲にある
- 前日高値を上抜けたトリガーバーが出現している

このスキャンが意図的に除外するもの。

- 21EMA(C) まで深く押した銘柄（→ パターン C 保留 or 他スキャンが担当）
- 21EMA(L) まで押した銘柄（→ scan_23 Pattern L が担当）
- トリガー未成立の「待ち」状態の銘柄

### 4.4 Canonical Boolean Definition

```python
matched = bool(
    0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
    and 0.3 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
    and row.get("atr_low_to_ema21_high", float("nan")) >= -0.2
    and row.get("high", 0.0) > row.get("prev_high", float("inf"))
)
```

### 4.5 Condition Design Notes

**50SMA 距離フィルタ**

```
0.0 <= atr_50sma_zone <= 3.0
```

下限 0.0 で close >= sma50 を暗黙に要求。上限 3.0 で 50SMA から 3 ATR 超の過熱銘柄を除外。scan_01 と同一の帯域を踏襲。

**21EMA(C) ゾーン**

```
0.3 <= atr_21ema_zone <= 1.0
```

終値が 21EMA(C) の上方 0.3〜1.0 ATR にある状態。下限 0.3 によりパターン C（中央帯）との境界を明確化。上限 1.0 により過度に伸びた銘柄を除外。

**21EMA(H) サポート確認**

```
atr_low_to_ema21_high >= -0.2
```

当日安値が 21EMA(H) から 0.2 ATR 以内に収まっていること。安値が 21EMA(H) を大きく割り込んだ場合はパターン H のサポート仮説が崩れるため除外。-0.2 ATR の許容幅は、ノイズレベルの一時的な割り込みを許容しつつ、構造的な崩壊は排除する設計。

**前日高値ブレイク（トリガー）**

```
high > prev_high
```

当日バーが前日高値を上抜けたことを確認するトリガー条件。浅い押しからの再始動を「前日高値を超えた」という客観的イベントとして定義。

### 4.6 Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `atr_50sma_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.0 <= value <= 3.0` |
| `atr_21ema_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.3 <= value <= 1.0` |
| `atr_low_to_ema21_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `>= -0.2` |
| `high` | latest price row | `0.0` | `> prev_high` |
| `prev_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("inf")` | upper comparison target |

### 4.7 Direct Config Dependencies

None. `_scan_21ema_pattern_h` uses hard-coded thresholds only in v1.

### 4.8 Upstream Field Definitions

- `atr_50sma_zone = (close - sma50) / atr`
- `atr_21ema_zone = (close - ema21_close) / atr`
- `atr_low_to_ema21_high = (low - ema21_high) / atr`
- `ema21_high = high.ewm(span=21, adjust=False).mean()`
- `prev_high = high.shift(1)`

---

## 5. scan_23: 21EMA Pattern L

### 5.1 Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `21EMA Pattern L` |
| UI display name | `21EMA PL` |
| Implementation owner | `src/scan/rules.py::_scan_21ema_pattern_l` |
| Output | `bool` |
| Direct scan config | none (v1 hard-coded thresholds) |

### 5.2 Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads only precomputed indicator fields.
- All conditions are combined with `AND`.
- Intended as a **deep pullback reclaim trigger scan** for stocks that pierced the 21EMA low band intraday and recovered by close.
- This scan detects **the last-resort support pattern** where the 21EMA(L) acts as the final line of trend defense.

### 5.3 Intent / Scan Role

このスキャンは、**21EMA(L) を日中割り込んだ後、終値で奪回し、翌日に前日高値をブレイクした銘柄**を検出する。

マッチした銘柄は以下の全てを満たすべきである。

- 終値が 21EMA(C) より下方にあるが、21EMA(L) より上で引けている
- 日中安値が 21EMA(L) を一時的に割り込んでいる（下ヒゲでサポートを試した証拠）
- 50SMA からの乖離が健全な範囲にある
- 前日高値を上抜けたトリガーバーが出現している

このスキャンが意図的に除外するもの。

- 21EMA(L) を割り込まなかった浅い押し（→ scan_22 Pattern H が担当）
- 21EMA(L) を終値で割った銘柄（サポート仮説の崩壊）
- トリガー未成立の「待ち」状態の銘柄

### 5.4 Canonical Boolean Definition

```python
matched = bool(
    0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
    and -0.5 <= row.get("atr_21ema_zone", float("nan")) <= -0.1
    and row.get("atr_low_to_ema21_low", float("nan")) < 0.0
    and row.get("atr_21emaL_zone", float("nan")) > 0.0
    and row.get("high", 0.0) > row.get("prev_high", float("inf"))
)
```

### 5.5 Condition Design Notes

**50SMA 距離フィルタ**

```
0.0 <= atr_50sma_zone <= 3.0
```

scan_22 と同一。

**21EMA(C) ゾーン**

```
-0.5 <= atr_21ema_zone <= -0.1
```

終値が 21EMA(C) の下方 0.1〜0.5 ATR にある状態。上限 -0.1 によりパターン C（中央帯）との境界を明確化。下限 -0.5 により 21EMA(C) から過度に離れた弱い銘柄を除外。

**21EMA(L) 割り込み確認**

```
atr_low_to_ema21_low < 0.0
```

当日安値が 21EMA(L) を下回ったことを確認。これにより「21EMA(L) をサポートとして試しに行った」証拠を要求する。この条件がなければ、単なる 21EMA(C) 近辺のもみ合いと区別がつかない。

**21EMA(L) 奪回確認**

```
atr_21emaL_zone > 0.0
```

`atr_21emaL_zone = (close - ema21_low) / atr > 0.0` は、終値が 21EMA(L) より上で引けたことを意味する。日中に割り込んだが終値で奪回した、というパターン L の核心条件。**終値で 21EMA(L) を割った銘柄はトレンド継続仮説が崩壊するため除外**される。

**前日高値ブレイク（トリガー）**

```
high > prev_high
```

scan_22 と同一のトリガー条件。パターン L では特に重要で、**「21EMA(L) 奪回日 + 翌日の前日高値ブレイク」という 2 段階確認**として機能する。

ただし注意: 本スキャンは EOD スキャンとして「当日バーにトリガー成立を抜く」方式であるため、**奪回と前日高値ブレイクが同一バーで発生**する場合も検出対象に含まれる。「奪回翌日に前日高値ブレイク」という 2 バーまたぎのパターンは、奪回日にはトリガー未成立でスキップされ、翌日に `atr_21ema_zone` が [-0.5, -0.1] に留まっていれば検出される。翌日に `atr_21ema_zone` が -0.1 を超えている場合は中央帯に入りパターン C 保留領域となるため、本スキャンでは検出されない。

### 5.6 Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `atr_50sma_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.0 <= value <= 3.0` |
| `atr_21ema_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `-0.5 <= value <= -0.1` |
| `atr_low_to_ema21_low` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `< 0.0` |
| `atr_21emaL_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `> 0.0` |
| `high` | latest price row | `0.0` | `> prev_high` |
| `prev_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("inf")` | upper comparison target |

### 5.7 Direct Config Dependencies

None. `_scan_21ema_pattern_l` uses hard-coded thresholds only in v1.

### 5.8 Upstream Field Definitions

- `atr_50sma_zone = (close - sma50) / atr`
- `atr_21ema_zone = (close - ema21_close) / atr`
- `atr_low_to_ema21_low = (low - ema21_low) / atr`
- `atr_21emaL_zone = (close - ema21_low) / atr`
- `ema21_low = low.ewm(span=21, adjust=False).mean()`
- `prev_high = high.shift(1)`

---

## 6. scan_00_index.md 更新

### 6.1 削除行

```
| [scan_01_21ema.md](scan_01_21ema.md) | `21EMA scan` | `src/scan/rules.py::_scan_21ema` |
```

### 6.2 追加行

```
| [scan_22_21ema_pattern_h.md](scan_22_21ema_pattern_h.md) | `21EMA Pattern H` | `src/scan/rules.py::_scan_21ema_pattern_h` |
| [scan_23_21ema_pattern_l.md](scan_23_21ema_pattern_l.md) | `21EMA Pattern L` | `src/scan/rules.py::_scan_21ema_pattern_l` |
```

### 6.3 スキャン数の更新

scan_01 廃止(-1)、scan_18 廃止(-1、改修依頼書に基づく)、scan_22/23 新設(+2) で、Active Scan Specs は **21 本のまま変更なし**。ただし内訳が変わるため、一覧表の全面更新が必要。

---

## 7. プリセット対応

### 7.1 既存プリセットの書き換え

scan_01 を指定している既存プリセットは、システム側で以下のいずれかに書き換える。

- scan_22 単独に置換（浅い押し目のみ対象とする場合）
- scan_23 単独に置換（深い押し目のみ対象とする場合）
- scan_22 と scan_23 の両方を指定（旧 scan_01 の帯域に近い網羅性を維持する場合。中央帯は欠落する）

書き換え方針と等価性の検証はシステム側で対応する。

### 7.2 新規プリセットの設計例

以下は scan_22 / scan_23 を使った新規プリセットの設計例（参考）。

**21EMA 押し目戦略（保守的）**

```yaml
preset_name: 21EMA Pullback Conservative
selected_scan_names: [21EMA Pattern H, Structure Pivot, RS Acceleration]
selected_annotation_filters: [Trend Base, Fund Score > 70]
duplicate_rule:
  mode: required_plus_optional_min
  required_scans: [21EMA Pattern H, Structure Pivot]
  optional_scans: [RS Acceleration]
  optional_min_hits: 1
```

**21EMA 押し目戦略（積極的）**

```yaml
preset_name: 21EMA Pullback Aggressive
selected_scan_names: [21EMA Pattern H, 21EMA Pattern L, Structure Pivot]
selected_annotation_filters: [Trend Base]
duplicate_rule:
  mode: required_plus_optional_min
  required_scans: [Structure Pivot]
  optional_scans: [21EMA Pattern H, 21EMA Pattern L]
  optional_min_hits: 1
```

---

## 8. 未確定事項とリスク

### 8.1 パターン H の閾値チューニング

`atr_low_to_ema21_high >= -0.2` の `-0.2` は初期値であり、バックテストによる検証が必要。厳しすぎると検出数が極端に減り、緩すぎるとパターン H の「浅い押し」という特性が薄れる。バックテスト結果に基づき -0.1〜-0.3 の範囲で調整する可能性がある。

### 8.2 パターン L の 2 バーまたぎ問題

§5.5 に記載の通り、奪回日翌日に `atr_21ema_zone` が中央帯に移動するケースでは scan_23 の検出対象外となる。これがどの程度の頻度で発生するかはバックテストで確認が必要。頻度が高い場合はパターン C の早期実装を検討するか、`atr_21ema_zone` の上限を -0.1 から 0.0 に緩和する対応が候補となる。

### 8.3 scan_01 指定プリセットの移行リスク

scan_01 が中央帯を含む広い帯域をカバーしていたため、scan_22 / scan_23 への置換後に検出数が減少する可能性がある。プリセット移行後は検出数の変化を監視し、必要に応じてパターン C の早期実装を判断する。
