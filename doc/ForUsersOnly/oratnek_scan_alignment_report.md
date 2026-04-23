# oratnek公開情報に基づくスキャン定義アライメントレポート

作成日: 2026-04-22
ステータス: レビュー待ち

---

## 目次

1. [エグゼクティブサマリー](#1-エグゼクティブサマリー)
2. [既存スキャン定義の修正仕様](#2-既存スキャン定義の修正仕様)
3. [新規スキャン実装依頼書](#3-新規スキャン実装依頼書)
4. [ユニバースフィルタ改修仕様](#4-ユニバースフィルタ改修仕様)
5. [その他システム改修項目](#5-その他システム改修項目)
6. [対応優先度マトリクス](#6-対応優先度マトリクス)

---

## 1. エグゼクティブサマリー

oratnekが公開した12プリセットと現システムの22スキャンを突き合わせた結果、以下の対応が必要。

| カテゴリ | 件数 | 概要 |
|---|---|---|
| 定義ずれの修正 | 7件 | 閾値変更、条件追加・削除、ロジック再実装 |
| 新規スキャン実装 | 3件 | LL-HL 1st Pivot / 2nd Pivot / Trend Line Break |
| ユニバースフィルタ改修 | 4件 | ADR上限、Real Estate除外、スキャン別MC、ADR下限 |
| その他改修 | 3件 | Pocket Pivot再定義、インジケーター拡張、ドキュメント整備 |

---

## 2. 既存スキャン定義の修正仕様

### 2.1 scan_15 Volume Accumulation — 再実装

**重要度: 最高（ロジックが根本的に異なる）**

現在の実装:
```python
matched = bool(
    row.get("ud_volume_ratio", 0.0) >= 1.5
    and row.get("rel_volume", 0.0) >= 1.0
    and row.get("daily_change_pct", 0.0) > 0.0
)
```

oratnek定義:
```
2+ consecutive up-days with Rel Vol ≥ 1.2
```

修正後の実装方針:
```python
matched = bool(
    row.get("consecutive_up_days_with_rel_vol", 0) >= 2
)
```

必要な上流フィールド追加:
```python
# src/indicators/core.py に追加
# 各日について: daily_change_pct > 0 AND rel_volume >= 1.2 を判定
is_qualified_up_day = (daily_change_pct > 0.0) & (rel_volume >= 1.2)

# 連続カウント: is_qualified_up_day が False になるたびにリセット
# 最新日時点での連続数を consecutive_up_days_with_rel_vol として出力
consecutive_up_days_with_rel_vol = consecutive_true_count(is_qualified_up_day)
```

変更対象ファイル:
- `src/indicators/core.py` — `consecutive_up_days_with_rel_vol` フィールド追加
- `src/scan/rules.py::_scan_volume_accumulation` — ロジック全面差し替え
- `config/default/scan.yaml` — 既存config keys (`vol_accum_ud_ratio_min`, `vol_accum_rel_vol_min`) を廃止、新パラメータへ移行

廃止フィールド（段階的削除）:
- `ud_volume_ratio` — このスキャンでは不要になる。他で使用していなければ計算自体を廃止可能

config移行:
```yaml
# 旧（廃止）
scan.vol_accum_ud_ratio_min: 1.5
scan.vol_accum_rel_vol_min: 1.0

# 新
scan.vol_accum_consecutive_min: 2
scan.vol_accum_rel_vol_threshold: 1.2
```

---

### 2.2 scan_14 VCS 52W Low — 閾値大幅修正 + 条件変更

**重要度: 高（閾値が全面的にずれている）**

差分一覧:

| 条件 | oratnek | 現実装 | 修正内容 |
|---|---|---|---|
| VCS | ≥ 55 | ≥ 60 | **60 → 55 に変更** |
| RS(1M) | > 60 | > 80 | **80 → 60 に変更** |
| dist_from_52w_low | 20% 〜 200% | ≤ 25% | **上限25% → 200%に拡大、下限20%を追加** |
| dist_from_52w_high | なし | ≤ -65% | **この条件を削除** |
| Rel Vol 1.2〜10x | あり | なし | **条件を追加** |

修正後のcanonical定義:
```python
matched = bool(
    row.get("vcs", 0.0) >= config.vcs_52_low_vcs_min          # 55.0
    and _raw_rs(row, 21) > config.vcs_52_low_rs21_min          # 60.0
    and config.vcs_52_low_dist_min
        <= row.get("dist_from_52w_low", float("nan"))
        <= config.vcs_52_low_dist_max                          # 20.0 <= x <= 200.0
    and config.vcs_52_low_rel_vol_min
        <= row.get("rel_volume", 0.0)
        <= config.vcs_52_low_rel_vol_max                       # 1.2 <= x <= 10.0
)
```

config変更:
```yaml
# 旧
scan.vcs_52_low_vcs_min: 60.0
scan.vcs_52_low_rs21_min: 80.0
scan.vcs_52_low_dist_max: 25.0
scan.vcs_52_low_dist_from_52w_high_max: -65.0

# 新
scan.vcs_52_low_vcs_min: 55.0
scan.vcs_52_low_rs21_min: 60.0
scan.vcs_52_low_dist_min: 20.0
scan.vcs_52_low_dist_max: 200.0
scan.vcs_52_low_rel_vol_min: 1.2
scan.vcs_52_low_rel_vol_max: 10.0
# dist_from_52w_high_max: 削除
```

---

### 2.3 scan_01 21EMA scan — 条件追加（再有効化の判断含む）

**重要度: 中高**

現scan_01はdisabledだが、oratnekの④は依然としてこの形で運用中。scan_22/23への置き換えは独自判断であり、oratnekの運用とは異なる。

追加が必要な条件:

| 追加条件 | oratnekの定義 | 実装方針 |
|---|---|---|
| RS(1M) 60+ | `_raw_rs(row, 21) >= 60.0` | scan本体に追加 |
| 1+ PP in 20D | `pp_count_window >= 1` | scan本体に追加 |
| Trend Base | `trend_base == True` | scan本体に追加（annotation依存ではなく） |

修正後のcanonical定義:
```python
weekly_return = row.get("weekly_return", float("nan"))
matched = bool(
    weekly_return >= 0.0
    and weekly_return <= 15.0
    and row.get("dcr_percent", 0.0) > 20.0
    and -0.5 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
    and 0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
    and _raw_rs(row, 21) >= config.ema21_rs21_min              # 60.0
    and row.get("pp_count_window", 0) >= config.ema21_pp_min   # 1
    and row.get("trend_base", False)                            # True
)
```

判断事項: scan_01を再有効化してscan_22/23と共存させるか、scan_01をoratnek④定義に修正して主スキャンに戻すか。

推奨: scan_01をoratnek④定義に修正して**再有効化**する。scan_22/23は独自追加スキャンとして残す。理由は、oratnekが④を現役で使用しており、22/23は④の部分的代替として設計されたが、④自体のRS+PP条件は22/23にはない。

---

### 2.4 scan_02 4% Bullish — 条件追加

**重要度: 中**

追加が必要な条件:

| 追加条件 | oratnekの定義 | 実装方針 |
|---|---|---|
| RS(1M) 60+ | `_raw_rs(row, 21) >= 60.0` | scan本体に追加 |
| Daily % 上限 50% | `daily_change_pct <= 50.0` | scan本体に追加 |
| Trend Base | `trend_base == True` | scan本体に追加 |

修正後:
```python
matched = bool(
    row.get("rel_volume", 0.0) >= config.relative_volume_bullish_threshold  # 1.0
    and config.daily_gain_bullish_threshold                                  # 4.0
        <= row.get("daily_change_pct", 0.0)
        <= config.daily_gain_bullish_max                                     # 50.0
    and row.get("from_open_pct", 0.0) > 0.0
    and _raw_rs(row, 21) >= config.bullish_4pct_rs21_min                    # 60.0
    and row.get("trend_base", False)                                         # True
)
```

新規config:
```yaml
scan.daily_gain_bullish_max: 50.0
scan.bullish_4pct_rs21_min: 60.0
```

備考: ADR上限がoratnekでは30%。これはユニバースフィルタ側の問題（後述セクション4参照）。

---

### 2.5 scan_08 PP Count — 条件追加

**重要度: 中**

追加が必要な条件:

| 追加条件 | oratnekの定義 | 実装方針 |
|---|---|---|
| RS(1M) 60+ | `_raw_rs(row, 21) >= 60.0` | scan本体に追加 |
| Trend Base | `trend_base == True` | scan本体に追加 |

修正後:
```python
matched = bool(
    row.get("pp_count_window", 0) >= config.pp_count_scan_min    # 3
    and _raw_rs(row, 21) >= config.pp_count_rs21_min              # 60.0
    and row.get("trend_base", False)                               # True
)
```

---

### 2.6 scan_13 VCS 52W High — RS条件の扱い確認

**重要度: 低**

oratnekの⑩にはRS条件がない。現scan_13には `raw_rs21 > 25.0` がある。

閾値が25と非常に低いため、実運用上はほぼフィルタとして機能していない可能性が高い。ただし厳密にはoratnekの定義にない条件。

推奨対応:
- `vcs_52_high_rs21_min` を config で 0.0 に設定してRS条件を実質無効化する
- または scan本体からRS条件を削除する

Trend Base条件の追加:
```python
matched = bool(
    row.get("vcs", 0.0) >= config.vcs_52_high_vcs_min           # 55.0
    and row.get("dist_from_52w_high", float("nan")) >= config.vcs_52_high_dist_max  # -20.0
    and pd.notna(row.get("high_52w", float("nan")))
    and row.get("high_52w", 0.0) > 0.0
    and row.get("close", 0.0) >= row.get("high_52w", float("inf")) * (1.0 - config.vcs_52_high_threshold_pct / 100.0)
    and row.get("trend_base", False)                              # 追加
)
```

---

### 2.7 scan_09 Weekly 20% Gainers — 上限追加

**重要度: 最低**

oratnekの⑫は `Weekly % 20-200%` で上限200%がある。現scan_09は `weekly_return >= 20.0` のみ。

修正:
```python
matched = bool(
    config.weekly_gainer_threshold
        <= row.get("weekly_return", 0.0)
        <= config.weekly_gainer_max                               # 200.0
)
```

実質的な影響は極めて小さい（週間200%超はほぼ存在しない）が、oratnek定義との整合性のため追加。

---

## 3. 新規スキャン実装依頼書

### 3.1 概要

oratnekが新規追加した3つのスキャンはすべて、Structure Pivotインジケーターの拡張に基づく。現在のインジケーター実装（`src/indicators/core.py`）では LL-HL構造の検出と `break_val`（LL〜HL間のスイングハイ）は計算済みだが、フィボナッチレベルの計算は未実装。

実装は2段階で行う:
1. **インジケーター拡張**: フィボナッチ価格、スイングハイ価格、降下トレンドラインの計算
2. **スキャン追加**: 上記フィールドを使った3つのスキャン定義

### 3.2 インジケーター拡張仕様

#### 3.2.1 既存フィールドの確認

現在の `src/indicators/core.py` Structure Pivot関連で計算済みのフィールド:
- `structure_pivot_long_active`: LL-HL構造がアクティブか
- `pivot_price` (= `break_val`): LL〜HL間の high の最大値
- LL確定位置、HL確定位置（内部計算）

#### 3.2.2 新規計算フィールド

```python
# LL-HL構造がactiveの場合に計算

# swing_high: LL と HL の間の最高値（= 既存の break_val / pivot_price）
swing_high = pivot_price  # 既存フィールドの別名確認

# fib_618_pivot: HL と swing_high の間の 0.618 フィボナッチリトレースメント
# 「HLとスイングハイ間の0.618」= HL + (swing_high - HL) * 0.618
fib_618_pivot = hl_price + (swing_high - hl_price) * 0.618

# 1st Pivot = fib_618_pivot
# 2nd Pivot = swing_high
```

出力フィールド:
| フィールド名 | 型 | 説明 |
|---|---|---|
| `structure_pivot_hl_price` | float | 確定したHL（Higher Low）の価格 |
| `structure_pivot_swing_high` | float | LL〜HL間のスイングハイ価格（既存break_valと同値の可能性あり。要確認） |
| `structure_pivot_1st_pivot` | float | `hl_price + (swing_high - hl_price) * 0.618` |
| `structure_pivot_2nd_pivot` | float | `swing_high` そのもの |
| `structure_pivot_1st_break` | bool | `close > structure_pivot_1st_pivot` かつ前日 `close <= 1st_pivot` |
| `structure_pivot_2nd_break` | bool | `close > structure_pivot_2nd_pivot` かつ前日 `close <= 2nd_pivot` |

#### 3.2.3 降下トレンドライン計算（CT Break用）

oratnekの説明: 「LL-HLがまだ形成されていない株については、インジケーターが下降するレジスタンストレンドラインも描画します」

これは LL-HL 構造が**未確定**の銘柄に対して適用される。

実装方針:
```python
# LL-HL構造がまだ形成されていない場合:
# 直近の確定ピボットハイ（スイングハイ）を2点以上結んで降下トレンドラインを計算
# トレンドラインを現在の日付まで延長し、その値を ct_trendline_value とする

# ct_break: close がトレンドラインを上抜けした日
ct_trendline_value = interpolated_descending_resistance_at_current_bar
ct_break = (close > ct_trendline_value) & (close.shift(1) <= ct_trendline_value.shift(1))
```

出力フィールド:
| フィールド名 | 型 | 説明 |
|---|---|---|
| `ct_trendline_value` | float | 現在のバーにおける降下レジスタンストレンドラインの値 |
| `ct_trendline_break` | bool | closeがトレンドラインを上抜けした日 |

**要確認事項**: トレンドラインの起点となるピボットハイの選定ロジック。oratnekのインジケーターが具体的にどの2点を使っているかは公開情報からは確定できない。最も一般的な実装は「直近の2つの確定スイングハイを結ぶ降下直線」。

---

### 3.3 scan_24 LL-HL Structure 1st Pivot

#### Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `LL-HL Structure 1st Pivot` |
| UI display name | `LL-HL 1st` |
| Implementation owner | `src/scan/rules.py::_scan_llhl_1st_pivot` |
| Output | `bool` |
| Scan number | 24 |

#### oratnek定義

```
MC≥1B / Vol≥1M / ADR 4-15% / RS(1M) 60+ / LL-HL 1st Break
```

MC / Vol / ADR はユニバースフィルタ側で処理。スキャン本体の条件:

#### Canonical Boolean Definition

```python
matched = bool(
    _raw_rs(row, 21) >= config.llhl_1st_rs21_min                  # 60.0
    and row.get("structure_pivot_1st_break", False)                 # True
)
```

#### Required Inputs

| Field | Producer | Missing/default | Scan use |
|---|---|---|---|
| `raw_rs21` / `rs21` | `src/scoring/rs.py` | `nan` | `>= 60.0` |
| `structure_pivot_1st_break` | `src/indicators/core.py` | `False` | must be `True` |

#### Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.llhl_1st_rs21_min` | `60.0` | RS下限 |

---

### 3.4 scan_25 LL-HL Structure 2nd Pivot

#### Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `LL-HL Structure 2nd Pivot` |
| UI display name | `LL-HL 2nd` |
| Implementation owner | `src/scan/rules.py::_scan_llhl_2nd_pivot` |
| Output | `bool` |
| Scan number | 25 |

#### oratnek定義

```
MC≥1B / Vol≥1M / ADR 4-15% / RS(1M) 60+ / LL-HL 2nd Break
```

#### Canonical Boolean Definition

```python
matched = bool(
    _raw_rs(row, 21) >= config.llhl_2nd_rs21_min                  # 60.0
    and row.get("structure_pivot_2nd_break", False)                 # True
)
```

#### Required Inputs

| Field | Producer | Missing/default | Scan use |
|---|---|---|---|
| `raw_rs21` / `rs21` | `src/scoring/rs.py` | `nan` | `>= 60.0` |
| `structure_pivot_2nd_break` | `src/indicators/core.py` | `False` | must be `True` |

#### Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.llhl_2nd_rs21_min` | `60.0` | RS下限 |

---

### 3.5 scan_26 LL-HL Structure Trend Line Break

#### Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `LL-HL Structure Trend Line Break` |
| UI display name | `CT Break` |
| Implementation owner | `src/scan/rules.py::_scan_llhl_ct_break` |
| Output | `bool` |
| Scan number | 26 |

#### oratnek定義

```
MC≥1B / Vol≥1M / ADR 4-15% / LL-HL CT Break
```

注意: このスキャンにはRS条件がない（①②と異なる）。

#### Canonical Boolean Definition

```python
matched = bool(
    row.get("ct_trendline_break", False)                           # True
)
```

#### Required Inputs

| Field | Producer | Missing/default | Scan use |
|---|---|---|---|
| `ct_trendline_break` | `src/indicators/core.py` | `False` | must be `True` |

#### Direct Config Dependencies

なし（v1はハードコード）。

#### 特記事項

- LL-HL構造が**未形成**の銘柄にのみ発火する
- LL-HL構造がactiveの銘柄では `ct_trendline_break` は常に `False`
- トレンドラインのピボットハイ選定ロジックの詳細確認が必要（後述の要確認事項参照）

---

### 3.6 新規スキャンの実装前に確認すべき事項

1. **フィボナッチ計算の方向**: 「HLとスイングハイ間の0.618」は `HL + (swing_high - HL) * 0.618` の解釈で正しいか。逆方向（スイングハイからの0.618リトレースメント = `swing_high - (swing_high - HL) * 0.618`）の可能性もある。前者はHL寄り、後者はswing_high寄りの値になる。通常のフィボナッチリトレースメントの慣例では後者（上からの0.618）だが、oratnekは「0.618フィボナッチレベルが1st Pivot」と言っているため、上から0.618（= 下から0.382相当）のリトレースメントレベルと解釈するのが自然。

   推奨解釈:
   ```python
   # 0.618 retracement from swing_high down to HL
   fib_618_pivot = swing_high - (swing_high - hl_price) * 0.618
   # = hl_price + (swing_high - hl_price) * 0.382
   ```

   **これはoratnekに直接確認できない限り、両方の計算結果をログに出して実チャートで検証する必要がある。**

2. **CTトレンドラインのピボットハイ選定**: 直近2つの確定スイングハイを使う想定だが、oratnekのインジケーターの具体的な実装は不明。length パラメータとの関係も要確認。

3. **既存scan_21との関係**: scan_21 (`structure_pivot_long_active`) は新スキャン①②の前提条件（LL-HL構造がactive）と重なる。scan_21を残すか、①②に吸収するかの判断が必要。推奨は、scan_21はactiveフラグのみで breakout判定を含む別スキャンなので共存させる。

---

## 4. ユニバースフィルタ改修仕様

### 4.1 ADR上限の拡大

| 項目 | 現在 | oratnek | 修正 |
|---|---|---|---|
| ADR上限（通常） | 10.0% | 15.0% | **10.0 → 15.0** |
| ADR上限（4% Bullish） | 10.0% | 30.0% | スキャン別ADRオーバーライドが必要 |

修正方針:
- グローバルADR上限を `15.0` に変更
- `4% Bullish` スキャンにはスキャン単位のADR上限オーバーライド (`30.0`) を実装

実装オプション:
```yaml
# Option A: ユニバースフィルタでスキャン別上書き
universe.adr_max: 15.0
universe.scan_overrides:
  "4% bullish":
    adr_max: 30.0

# Option B: ユニバースは最大値（30.0）にして、各スキャンがADRを自前でチェック
# → 推奨しない（既存全スキャンにADRチェックの追加が必要）
```

推奨: Option A。ユニバース側でスキャン別オーバーライドをサポートする。

### 4.2 ADR下限の修正

| 項目 | 現在 | oratnek | 修正 |
|---|---|---|---|
| ADR下限 | 3.5% | 4.0% | **3.5 → 4.0** |

### 4.3 Real Estate セクター除外

| 項目 | 現在 | oratnek | 修正 |
|---|---|---|---|
| 除外セクター | Healthcare | Healthcare, **Real Estate** | **Real Estate を追加** |

修正箇所: `src/data/universe.py` のセクター除外リスト、および `config/default/scan.yaml` の該当設定。

### 4.4 Momentum 97 スキャン別Market Cap下限

oratnekの⑥は MC ≥ 0.2B で運用されている。他のスキャンは全て MC ≥ 1B。

現システムのユニバースフィルタは全スキャン共通で MC ≥ 1B のため、Momentum 97だけ MC を下げる仕組みがない。

実装方針:
```yaml
# ユニバースフィルタのスキャン別オーバーライド（4.1と同じ仕組み）
universe.market_cap_min: 1000000000  # 1B（デフォルト）
universe.scan_overrides:
  "Momentum 97":
    market_cap_min: 200000000  # 0.2B
```

影響範囲:
- ユニバース構築時にスキャン別条件を考慮する必要がある
- 現在の設計では eligible universe は全スキャン共通なので、**最も緩い条件（0.2B）で候補を取得し、各スキャン実行時にスキャン別フィルタを適用する** 設計変更が必要
- これは `src/data/universe.py` と `src/scan/runner.py` の両方に影響する

---

## 5. その他システム改修項目

### 5.1 Pocket Pivot (scan_07) の再定義

現scan_07は「今日PPが発生 + close > sma50」だが、oratnekの⑦は「過去20日に1回以上PPあり」（close > sma50 なし）。

これは概念的に異なるスキャン:
- 現scan_07 = **シグナル検出**（今日のイベント）
- oratnek⑦ = **活動フィルタ**（最近のPP実績）

対応方針の選択肢:

**Option A**: scan_07をoratnek⑦に合わせて再定義（`pp_count_window >= 1`、close > sma50 を削除）
- メリット: oratnekとの完全整合
- デメリット: 現在のscan_07をEntry SignalやPresetで「PP発生日」として使っている箇所がすべて壊れる

**Option B**: scan_07はそのまま残し、oratnek⑦を新しいスキャン（scan_27等）として追加
- メリット: 既存のPreset/Entry Signal構成が壊れない
- デメリット: スキャン数が増える

**Option C**: scan_07をoratnek⑦に修正し、現scan_07のロジックはEntry Signal側に移管
- メリット: oratnek整合 + 「今日のPP」は元々Entry Signalの責務に近い
- デメリット: 移行コスト

推奨: **Option C**。理由は、scan_to_entry_workflow.mdの設計思想（スキャン=候補抽出、Entry Signal=タイミング）に照らすと、「今日PPが発生した」はタイミング情報であり、Entry Signalの責務。「最近PPがあった」はフィルタ/候補抽出であり、スキャンの責務。

### 5.2 Trend Base のスキャン本体組み込み方針

oratnekの12プリセットのうち、以下のスキャンは Trend Base を条件に含んでいる:

- ④ 21EMA Structure
- ⑤ 4% Bullish
- ⑥ Momentum 97
- ⑧ PP 3+ times (20D)
- ⑩ VCS 52W High

現システムでは Trend Base は annotation filter として実装されており、preset レベルで適用される。oratnek定義ではスキャン本体の条件として記載されている。

判断ポイント:
- annotation filter として残す場合: preset側でTrend Baseを有効にすればoratnekと同等の候補が出る。ただしスキャンカード上では Trend Base なしの銘柄も表示される
- scan 本体に組み込む場合: oratnekの定義と完全に一致するが、Trend Base なしの「やや広い候補」が見えなくなる

推奨: **scan 本体に組み込む**（oratnekの定義に合わせる）。理由は、oratnekのスクリーナー定義が「これらの条件をすべて満たす銘柄を抽出する」意図で書かれており、Trend Base は optional ではなく required 条件。annotationでの後付けフィルタとは意図が異なる。

ただし、Trend Base を含まない独自スキャン（scan_16 Pullback Quality、scan_17 Reclaim、scan_20 Trend Reversal Setup 等）はこの変更の対象外。これらは oratnek の12プリセットに含まれていない独自追加スキャンなので、現定義を維持する。

### 5.3 スキャンドキュメント整備

以下のドキュメント更新が必要:

- `doc/SystemDocs/Scan/scan_00_index.md` — Active Scan Specs テーブルに scan_24, 25, 26 を追加
- 各修正スキャンの spec ドキュメント更新
- 新規スキャンの spec ドキュメント作成（scan_24, 25, 26）
- `config/default/scan.yaml` のデフォルト値変更に伴う watchlist_presets ドキュメント更新
- ユニバースフィルタのドキュメント更新（ADR、セクター除外、スキャン別オーバーライド）

---

## 6. 対応優先度マトリクス

| # | 対応項目 | 重要度 | 影響範囲 | 推奨順序 |
|---|---|---|---|---|
| 1 | ユニバースフィルタ: Real Estate除外追加 | 高 | 全スキャン | 最初 |
| 2 | ユニバースフィルタ: ADR上限 10→15 | 高 | 全スキャン | 最初 |
| 3 | ユニバースフィルタ: ADR下限 3.5→4.0 | 中 | 全スキャン | 最初 |
| 4 | scan_15 Volume Accumulation 再実装 | 最高 | scan_15 + 関連preset | 第2波 |
| 5 | scan_14 VCS 52W Low 閾値修正 | 高 | scan_14 + 関連preset | 第2波 |
| 6 | scan_01 21EMA 条件追加+再有効化 | 中高 | scan_01 | 第2波 |
| 7 | scan_02 4% Bullish 条件追加 | 中 | scan_02 | 第2波 |
| 8 | scan_08 PP Count 条件追加 | 中 | scan_08 | 第2波 |
| 9 | scan_13 VCS 52W High RS削除+Trend Base | 低 | scan_13 | 第2波 |
| 10 | scan_09 Weekly Gainers 上限追加 | 最低 | scan_09 | 第2波 |
| 11 | インジケーター拡張: フィボ+CT計算 | 高 | indicators | 第3波 |
| 12 | scan_24 LL-HL 1st Pivot 新規 | 高 | 新規 | 第3波（11の後） |
| 13 | scan_25 LL-HL 2nd Pivot 新規 | 高 | 新規 | 第3波（11の後） |
| 14 | scan_26 CT Break 新規 | 高 | 新規 | 第3波（11の後） |
| 15 | Pocket Pivot scan_07 再定義 | 中 | scan_07 + preset + entry signal | 第4波 |
| 16 | ユニバース: スキャン別MC/ADR対応 | 中 | universe + runner | 第4波 |
| 17 | ドキュメント整備 | 中 | docs | 各波の完了後 |

第1波（ユニバース基盤）→ 第2波（既存スキャン修正）→ 第3波（新規スキャン）→ 第4波（構造変更）の順で実施することで、依存関係を最小化できる。

---

## 付録: oratnek 12プリセット vs 現システム対応表

| # | oratnek プリセット | 対応する現スキャン | 対応状況 |
|---|---|---|---|
| ① | LL-HL Structure 1st Pivot | なし | **新規実装** |
| ② | LL-HL Structure 2nd Pivot | なし | **新規実装** |
| ③ | LL-HL Structure Trend Line Break | なし | **新規実装** |
| ④ | 21 EMA Structure | scan_01 (disabled) | **修正+再有効化** |
| ⑤ | 4% Bullish | scan_02 | **条件追加** |
| ⑥ | Momentum 97 | scan_04 | ロジック一致、**MC下限のみ差異** |
| ⑦ | PP (Vol >10D) | scan_07 | **定義が概念的に異なる** |
| ⑧ | PP 3+ times (20D) | scan_08 | **条件追加** |
| ⑨ | Volume Accumulation | scan_15 | **再実装** |
| ⑩ | VCS 52W High | scan_13 | **微修正** |
| ⑪ | VCS 52W Low | scan_14 | **大幅修正** |
| ⑫ | Weekly 20% + Gainers | scan_09 | **上限追加（軽微）** |

現システムにのみ存在するスキャン（oratnekの12に含まれない独自追加）:
- scan_05 97 Club
- scan_10 Near 52W High
- scan_11 Three Weeks Tight
- scan_12 RS Acceleration
- scan_16 Pullback Quality
- scan_17 Reclaim
- scan_19 Sustained Leadership
- scan_20 Trend Reversal Setup
- scan_21 Structure Pivot（①②③とは部分的に重複）
- scan_22 21EMA Pattern H
- scan_23 21EMA Pattern L
