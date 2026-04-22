# システム改修依頼: Breakout Quality（ブレイク品質判定）

## 1. 改修の目的

現在のシステムには「抵抗帯に対するブレイクアウトの質」を直接測定する層が存在しない。
本改修は、以下の3要素を既存レイヤーに分解して導入する。

| 要素 | 対応する新規実装 | 導入先レイヤー |
|---|---|---|
| 抵抗帯でのテスト回数 | `resistance_test_count` | Indicator layer |
| ブレイクバーの実体品質 | `breakout_body_ratio` | Indicator layer |
| 抵抗テスト回数による候補品質確認 | `Resistance Tests >= 2` | Annotation Filter |
| ブレイク品質を含むタイミング条件 | `Resistance Breakout Entry` | Entry Signal layer |

出来高（②）は既存フィールド `rel_volume` およびVolume Accumulation等のスキャンでカバー済みのため、新規Indicatorは不要。

## 2. 改修スコープ

### In Scope

- Indicator layer: 2フィールド追加
- Config: Indicatorパラメータ追加
- Annotation Filter: 1フィルタ追加
- Entry Signal: 1シグナル追加
- Preset: 2プリセットの `selected_annotation_filters` 更新
- Scan spec / Preset spec ドキュメント更新

### Out Of Scope

- 既存スキャンのブール条件変更（スキャン層には手を入れない）
- 新規スキャンの追加
- UI変更
- トレード管理・ポジションサイズ

---

## 3. Indicator Layer

### 3.1 resistance_test_count

**目的:** 直近N日の高値ゾーンに対して、終値では突破できなかったテスト回数を計測する。

**算出ロジック:**

```python
# params (from config)
lookback = indicators.resistance_test_lookback          # default: 20
zone_width_factor = indicators.resistance_zone_width_atr  # default: 0.5
count_window = indicators.resistance_test_count_window    # default: 20

# calculation
resistance_level = high.rolling(lookback).max().shift(1)
zone_threshold = atr * zone_width_factor
tested = (high >= resistance_level - zone_threshold) & (close < resistance_level)
resistance_test_count = tested.rolling(count_window, min_periods=count_window).sum()
```

**設計判断:**

- `shift(1)`: 当日highを含めない。ブレイク当日に自己参照で抵抗レベルが上がることを防ぐ。
- `close < resistance_level`: 高値がゾーンに届いたが終値で突破できなかったバーのみカウント。終値突破日はテストではなくブレイクアウト候補。
- `min_periods=count_window`: データ不足時は NaN。スキャン層で `row.get(..., 0)` により fail closed。
- 連続日数のセッション分離: v1 では不要。rolling sum で実装する。将来の改善余地として残す。

**参照する既存フィールド:** `high`, `close`, `atr`（すべて `src/indicators/core.py::IndicatorCalculator.calculate` の既存産物）

**既存Indicatorとの関係:**

- `rolling_20d_close_high`（close基準）とは別に、high基準の rolling max を使用。抵抗帯はヒゲを含めた到達点で形成されるため、high基準が正しい。
- lookback=20 は `rolling_20d_close_high` と同じ時間軸。Pullback Quality / Reclaim scan と組み合わせた際に時間軸の不整合が生じない。

### 3.2 breakout_body_ratio

**目的:** ブレイクアウトバーの実体がバー全体に占める方向性付き比率を計測する。

**算出ロジック:**

```python
bar_range = high - low
body = close - open
breakout_body_ratio = body / bar_range.replace(0, np.nan)
```

**設計判断:**

- `abs()` を取らない。陰線は負値となり、スキャン/Entry Signal層で陽線ブレイクとの区別が自然にできる。
- ゼロレンジ（high == low）は NaN。`dcr_percent` の既存処理（50.0埋め）とは異なるが、レンジゼロのバーで body ratio は意味を持たないため NaN が正しい。

**`dcr_percent` との違い:**

- `dcr_percent`: バー内での終値の位置（0%=安値、100%=高値）
- `breakout_body_ratio`: 実体がバー全体のどれだけを占めるか

両方が高いバーが最も質の高いブレイクアウトバー。相補的であり、置き換えではない。

**コンフィグパラメータ:** なし。計算式固定。閾値判断はスキャン層/Entry Signal層の責務。

---

## 4. Config 追加

**対象ファイル:** `config/default.yaml`（indicators セクション）

```yaml
indicators:
  resistance_test_lookback: 20
  resistance_zone_width_atr: 0.5
  resistance_test_count_window: 20
```

`resistance_test_lookback` と `resistance_test_count_window` は v1 では同一値で運用するが、将来の非対称設定（例: 50日高値に対する20日間のテスト回数）に備えて別キーとする。

---

## 5. Annotation Filter

**対象ファイル:** `src/scan/rules.py::ANNOTATION_FILTER_REGISTRY`

### 追加定義

| Annotation filter | Canonical condition |
|---|---|
| `Resistance Tests >= 2` | `resistance_test_count >= 2` |

**閾値の根拠:**

- 1回 = たまたま高値圏に到達した可能性がある
- 2回以上 = そのレベルが市場に意識されている最小条件
- 3回以上は 20日 window で該当銘柄が極端に少なくなる

**`breakout_body_ratio` について:** Annotation Filter にはしない。これは特定の1本のバーの質を測る指標であり、持続的な状態を表す Annotation（Trend Base、RS 21 >= 63 など）とは性質が異なる。Entry Signal 層で使用する。

---

## 6. Entry Signal

**対象ファイル:** `src/signals/rules.py`, `config/default/entry_signals.yaml`

### Resistance Breakout Entry

**条件:**

```python
matched = bool(
    row.get("resistance_test_count", 0) >= 2
    and row.get("close", 0.0) > row.get("resistance_level_20d", float("inf"))
    and row.get("breakout_body_ratio", 0.0) >= 0.6
    and row.get("rel_volume", 0.0) >= 1.5
)
```

**必要フィールド:**

| Field | Producer | Missing/default | Signal use |
|---|---|---|---|
| `resistance_test_count` | 本改修で追加 | `0` | `>= 2` |
| `resistance_level_20d` | 本改修で追加（`high.rolling(20).max().shift(1)` を公開） | `float("inf")` | 終値が抵抗レベルを上回ったか |
| `breakout_body_ratio` | 本改修で追加 | `0.0` | `>= 0.6` |
| `rel_volume` | 既存 | `0.0` | `>= 1.5` |

**Note:** `resistance_level_20d` は `resistance_test_count` の算出過程で計算される中間値。Entry Signal で「終値が抵抗レベルを突破した」判定に必要なため、Indicator として公開する。追加計算コストはゼロ（既存の中間値を保存するだけ）。

**Risk Reference:** `resistance_level_20d`（ブレイクした抵抗レベル自体がサポート転換候補）

**解釈:** 複数回テストされた抵抗帯を、明確な陽線実体かつ出来高増加で突破した初日。

---

## 7. Preset 更新

### 対象プリセット

| Preset | 変更内容 |
|---|---|
| `Leader Breakout` | `selected_annotation_filters` に `Resistance Tests >= 2` を追加 |
| `Base Breakout` | `selected_annotation_filters` に `Resistance Tests >= 2` を追加 |

### 変更しないプリセット（理由）

| Preset | 理由 |
|---|---|
| `Orderly Pullback` | プルバック品質の検出。ブレイクアウトが目的ではない |
| `Reclaim Trigger` | 21EMA リクレイムの検出。抵抗帯突破とは異なる |
| `Trend Pullback` | リクレイム + プルバック品質。ブレイク前提ではない |
| `Momentum Surge` | 勢いのある上昇日の検出。抵抗帯との関係は必須ではない。運用データを見て将来判断 |
| `Resilient Leader` | RS持続性の検出。ブレイク検出ではない |
| `Early Cycle Recovery` | 底打ち反転の検出。高値圏ブレイクとは逆の局面 |
| `Early Recovery` | 同上 |

### 更新後の Leader Breakout payload

```yaml
preset_name: Leader Breakout
selected_scan_names: [97 Club, VCS 52 High, RS Acceleration, Three Weeks Tight]
selected_annotation_filters: [Trend Base, Resistance Tests >= 2]  # ← 追加
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: required_plus_optional_min
  required_scans: [97 Club, VCS 52 High]
  optional_scans: [RS Acceleration, Three Weeks Tight]
  optional_min_hits: 1
preset_status: enabled
```

### 更新後の Base Breakout payload

```yaml
preset_name: Base Breakout
selected_scan_names: [VCS 52 High, Pocket Pivot, 97 Club, Three Weeks Tight]
selected_annotation_filters: [Trend Base, Resistance Tests >= 2]  # ← 追加
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: required_plus_optional_min
  required_scans: [VCS 52 High, Pocket Pivot]
  optional_scans: [97 Club, Three Weeks Tight]
  optional_min_hits: 1
preset_status: enabled
```

---

## 8. ドキュメント更新

| 対象 | 内容 |
|---|---|
| `doc/SystemDocs/Scan/scan_00_index.md` | Annotation Filter テーブルに `Resistance Tests >= 2` を追加 |
| `doc/SystemDocs/WatchlistPresets/leader_breakout.md` | `selected_annotation_filters` の変更を反映 |
| `doc/SystemDocs/WatchlistPresets/base_breakout.md` | 同上 |
| Entry Signal ドキュメント（該当ファイル） | `Resistance Breakout Entry` の仕様を追加 |

---

## 9. 実装ファイルと変更範囲

| ファイル | 変更種別 |
|---|---|
| `src/indicators/core.py` | `resistance_test_count`, `resistance_level_20d`, `breakout_body_ratio` の3フィールド追加 |
| `config/default.yaml` | indicators セクションに3キー追加 |
| `src/scan/rules.py::ANNOTATION_FILTER_REGISTRY` | `Resistance Tests >= 2` 追加 |
| `config/default/scan.yaml` | `Leader Breakout`, `Base Breakout` の annotation filters 更新 |
| `src/signals/rules.py` | `Resistance Breakout Entry` 追加 |
| `config/default/entry_signals.yaml` | `Resistance Breakout Entry` 定義追加 |

---

## 10. 影響範囲と非影響範囲

**影響あり:**

- Indicator 計算: 3フィールド追加（計算コストは既存 VCS 1本の 1/5 以下、パイプライン全体への影響は計測誤差レベル）
- Annotation Filter: 1フィルタ追加（既存フィルタと同じ仕組み、UI変更なし）
- Entry Signal: 1シグナル追加（既存シグナルと同じ仕組み）
- Preset: 2プリセットの annotation filter 設定変更

**影響なし:**

- 既存スキャンのブール条件: 変更しない
- 既存 Annotation Filter: 変更しない
- 既存 Entry Signal: 変更しない
- 変更対象外の7プリセット: 変更しない
- Eligible Universe Filter: 変更しない
- Duplicate Rule: 変更しない
- UI: 変更しない
