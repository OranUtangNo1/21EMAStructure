# 改修依頼書：新規スキャン・指標・アノテーションフィルターの追加

## メタ情報

| 項目 | 内容 |
|---|---|
| ドキュメント種別 | 改修依頼書（実装仕様） |
| 作成日 | 2026-04-23 |
| 対象システム | OraTek スキャン・指標パイプライン |
| 改修目的 | 未カバーの高確率セットアップを検出するためのスキャン・指標・アノテーションの追加 |
| 改修の背景 | 既存のプリセット体系が「50SMA圏への深い押し目からの回復」「ギャップアップ後のファーストプルバック」「RS新高値が価格新高値に先行するパターン」の3セットアップをカバーできていないことが判明した |

## 改修サマリ

| No | 変更種別 | 名称 | 実装形態 | 理由 |
|---|---|---|---|---|
| 1 | 新規指標 | `close_crossed_above_sma50` | indicator field | 50SMA Reclaim scan の必須入力 |
| 2 | 新規指標 | `min_atr_50sma_zone_5d` | indicator field | 50SMA Reclaim scan の必須入力 |
| 3 | 新規スキャン | `50SMA Reclaim` | scan boolean | 50SMA防御回復セットアップの候補抽出 |
| 4 | 新規指標 | `power_gap_up_pct` | indicator field | Recent Power Gap アノテーションの必須入力 |
| 5 | 新規指標 | `days_since_power_gap` | indicator field | Recent Power Gap アノテーションの必須入力 |
| 6 | 新規アノテーション | `Recent Power Gap` | annotation filter | ギャップアップ後のプルバック候補に文脈を付与 |
| 7 | 新規指標 | `rs_ratio` | indicator/scoring field | RS New High scan の必須入力 |
| 8 | 新規指標 | `rs_ratio_52w_high` | indicator/scoring field | RS New High scan の必須入力 |
| 9 | 新規指標 | `rs_ratio_at_52w_high` | indicator/scoring field | RS New High scan の必須入力 |
| 10 | 新規スキャン | `RS New High` | scan boolean | RS先行ブレイクアウトセットアップの候補抽出 |

---

# 変更1・2：新規指標 `close_crossed_above_sma50` / `min_atr_50sma_zone_5d`

## 実装先

`src/indicators/core.py::IndicatorCalculator.calculate`

## 定義

```python
# close_crossed_above_sma50
close_crossed_above_sma50 = (close > sma50) & (close.shift(1) <= sma50.shift(1))

# min_atr_50sma_zone_5d
min_atr_50sma_zone_5d = atr_50sma_zone.rolling(5).min()
```

## 設計根拠

既存の `close_crossed_above_ema21` と `min_atr_21ema_zone_5d`（Reclaim scan の入力フィールド）の50SMA版。実装パターンは完全に同一であり、対象MAを21EMAから50SMAに変更するだけ。

## 上流依存

| フィールド | プロデューサー | 既存/新規 |
|---|---|---|
| `close` | price row | 既存 |
| `sma50` | `IndicatorCalculator.calculate` | 既存 |
| `atr_50sma_zone` | `IndicatorCalculator.calculate` | 既存（`(close - sma50) / atr`）|

## Missing値の扱い

- `close_crossed_above_sma50`：`sma50` が NaN の場合は `False`。shift(1) が NaN の場合も `False`
- `min_atr_50sma_zone_5d`：`atr_50sma_zone` が NaN を含む場合、`rolling(5).min()` は pandas の標準挙動に従い NaN を返す

## テスト要件

- `close` が SMA50 を上方クロスした日に `close_crossed_above_sma50 == True` になること
- 前日 close ≤ SMA50、当日 close > SMA50 の組み合わせのみで `True` になること
- SMA50 上方に継続している場合は `False` であること
- `min_atr_50sma_zone_5d` が直近5日間の `atr_50sma_zone` の最小値と一致すること
- ウォームアップ期間（50日未満）では NaN であること

---

# 変更3：新規スキャン `50SMA Reclaim`

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `50SMA Reclaim` |
| UI display name | `50SMA Reclaim` |
| Implementation owner | `src/scan/rules.py::_scan_50sma_reclaim` |
| Output | `bool` |
| Direct scan config | none (v1 hard-coded thresholds) |
| Default status | `enabled` in `config/default/scan.yaml` |
| Scan number | 次の空き番号（27） |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`
- Reads only precomputed indicator fields
- All conditions are combined with `AND`
- Intended as a **50SMA reclaim trigger scan** after a deep pullback below the 21EMA
- This scan is responsible for detecting the moment a stock recovers its 50SMA after pulling back through the 21EMA zone
- This scan is the 50SMA counterpart of `Reclaim scan` (21EMA reclaim)

## Canonical Boolean Definition

```python
weekly_return = row.get("weekly_return", float("nan"))
matched = bool(
    row.get("sma50_slope_10d_pct", float("nan")) > 0.0
    and 0.0 <= row.get("atr_50sma_zone", float("nan")) <= 1.0
    and row.get("close_crossed_above_sma50", False)
    and row.get("min_atr_50sma_zone_5d", float("nan")) <= -0.25
    and row.get("dcr_percent", 0.0) >= 60.0
    and row.get("volume_ratio_20d", float("nan")) >= 1.10
    and 3.0 <= row.get("drawdown_from_20d_high_pct", float("nan")) <= 20.0
)
```

## Intent / Scan Role

このスキャンは、アップトレンド中に21EMAを超えて深く調整した銘柄が、50SMAを出来高を伴って回復した日を検出する。

matchした銘柄は以下をすべて満たしている：

- 50SMAがまだ上向き（中期トレンドが健全）
- 直近5日以内に50SMAの下にいた（実際に50SMA圏まで調整した証拠）
- 今日closeが50SMAを上方クロスした（リクレイムイベント）
- 20日高値からの調整が3-20%の範囲（21EMA押し目より深いが、崩壊ではない）
- close品質が良い（dcr_percent ≥ 60）
- 出来高が20日平均比1.1倍以上（需要を伴ったリクレイム）

このスキャンは以下を意図的に除外する：

- 50SMAが下向きの銘柄（中期トレンドが崩壊）
- 50SMAの下に落ちていなかった銘柄（リクレイムではなく通常の継続）
- 弱いclose品質のリクレイム試行
- 出来高を伴わない受動的な戻り

## Condition Design Notes

**トレンド健全性**
`sma50_slope_10d_pct > 0.0`

50SMAが上向きであることを保証する。下降中の50SMAへの接触は「ブレイクダウン進行中の一時的な反発」であり、リクレイムとしての期待値が低い。Reclaim scan の `ema21_slope_5d_pct > 0.0` に対応するが、MAの時間軸に合わせて10日勾配を使用する。

**注意：Reclaim scan には `ema21_slope_5d_pct > 0.0` と `sma50_slope_10d_pct > 0.0` の両方が含まれるが、50SMA Reclaim では `sma50_slope_10d_pct > 0.0` のみを含む。21EMAの勾配条件を含まない理由は、50SMAまで深く調整した銘柄では21EMAが一時的にフラット化または下向きになることがあり、この段階で21EMAの勾配を要求すると正当な50SMAリクレイムを不当に除外するため。**

**リクレイム位置**
`0.0 <= atr_50sma_zone <= 1.0`

closeが50SMAの直上（0-1 ATR）にある。まさにリクレイムした直後の位置。Reclaim scan の `atr_21ema_zone` 条件に対応するが、対象MAが異なる。

**直近の50SMA下回り証拠**
`min_atr_50sma_zone_5d <= -0.25`
`close_crossed_above_sma50 == True`

この2条件がリクレイムイベントの核心。`min_atr_50sma_zone_5d <= -0.25` は直近5日以内に50SMAの-0.25 ATR以下にいたことを証明する。`close_crossed_above_sma50` は当日のクロスイベント自体を検出する。Reclaim scan の `min_atr_21ema_zone_5d <= -0.25` + `close_crossed_above_ema21` と完全に対称。

**調整深度**
`3.0 <= drawdown_from_20d_high_pct <= 20.0`

Reclaim scan の上限12%に対し、50SMA Reclaim は20%まで許容する。理由は、50SMAテストは21EMA押し目より構造的に深い調整であるため。下限3%は「調整が実際に発生した」ことの最低条件。

**トリガー確認**
`dcr_percent >= 60.0`（Reclaim scan と同一）
`volume_ratio_20d >= 1.10`（Reclaim scan と同一）

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `sma50_slope_10d_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `> 0.0` |
| `atr_50sma_zone` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `0.0 <= value <= 1.0` |
| `close_crossed_above_sma50` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |
| `min_atr_50sma_zone_5d` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `<= -0.25` |
| `dcr_percent` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | `>= 60.0` |
| `volume_ratio_20d` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `>= 1.10` |
| `drawdown_from_20d_high_pct` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `3.0 <= value <= 20.0` |

## Direct Config Dependencies

None. `_scan_50sma_reclaim` uses hard-coded thresholds only in v1.

## Upstream Field Definitions

- `sma50_slope_10d_pct = ((sma50 / sma50.shift(10)) - 1.0) * 100.0`（既存）
- `atr_50sma_zone = (close - sma50) / atr`（既存）
- `close_crossed_above_sma50 = (close > sma50) & (close.shift(1) <= sma50.shift(1))`（新規：変更1）
- `min_atr_50sma_zone_5d = atr_50sma_zone.rolling(5).min()`（新規：変更2）
- `dcr_percent = ((close - low) / (high - low)) * 100.0`（既存）
- `volume_ratio_20d = volume / volume.rolling(20).mean()`（既存）
- `drawdown_from_20d_high_pct = ((close.rolling(20).max() - close) / close.rolling(20).max()) * 100.0`（既存）

## 既存スキャンとの排他性検証

| 比較対象 | 排他性の根拠 |
|---|---|
| Reclaim scan | `atr_50sma_zone ≥ 0.75`（Reclaim）vs `0.0-1.0`（本scan）。Reclaim は close が SMA50 から 0.75 ATR 以上離れている銘柄のみ通過するため、50SMA付近の銘柄は構造的に排除される。さらに cross 対象MA が異なる（ema21 vs sma50）|
| Pullback Quality scan | PB Quality は `atr_50sma_zone 0.75-3.5` を要求。50SMA 付近は除外。また PB Quality はリクレイムイベント（cross条件）を含まず、「押し目の状態」を判定する。時系列的に前後の関係 |
| 21EMA Pattern H/L | 21EMA ゾーンの浅い/深いパターン検出。MAレベルが異なる |
| Pocket Pivot | 出来高イベント検出。同一日に両方ヒット可能だが、それは正当な合流 |

## scan_status_map への追加

```yaml
50SMA Reclaim:
  status: enabled
  scan_number: 27
```

## Scan Document

`doc/SystemDocs/Scan/scan_27_50sma_reclaim.md` を本セクションの内容で作成すること。

## テスト要件

- SMA50 が上向きで、直近5日以内に SMA50 の下にいた銘柄が、今日 SMA50 を上方クロスし、出来高・close品質条件を満たす場合に `True`
- SMA50 が下向きの銘柄では `False`
- `min_atr_50sma_zone_5d > -0.25`（50SMA の下に落ちていなかった）場合は `False`
- `close_crossed_above_sma50 == False`（今日クロスしていない）場合は `False`
- drawdown が 3% 未満または 20% 超の場合は `False`
- volume_ratio_20d < 1.10 の場合は `False`
- Reclaim scan と同一日・同一銘柄でヒットしないこと（atr_50sma_zone の範囲が排他的であるため）

---

# 変更4・5：新規指標 `power_gap_up_pct` / `days_since_power_gap`

## 実装先

`src/indicators/core.py::IndicatorCalculator.calculate`

## 定義

```python
# gap_up_pct: 各日のギャップアップ率（始値が前日終値に対してどれだけ高いか）
gap_up_pct = ((open / close.shift(1)) - 1.0) * 100.0

# power_gap_threshold はconfig駆動（default: 10.0）
# is_power_gap: gap_up_pct が閾値以上の日にTrue
is_power_gap = gap_up_pct >= config.power_gap_threshold

# days_since_power_gap: 直近のpower_gap発生日からの経過営業日数
# power_gapが一度も発生していない場合はNaN
days_since_power_gap = <直近のis_power_gap==Trueの日からの日数を前方フィル>

# power_gap_up_pct: 直近のpower_gap発生日のgap_up_pct
# power_gapが一度も発生していない場合はNaN
power_gap_up_pct = <直近のis_power_gap==Trueの日のgap_up_pctを前方フィル>
```

実装の詳細：

```python
# 推奨実装パターン
gap_up_pct = ((open / close.shift(1)) - 1.0) * 100.0
is_power_gap = gap_up_pct >= config.power_gap_threshold

# days_since_power_gap の計算
# is_power_gap が True の日に 0 をセットし、それ以外の日は NaN
# 前方フィルで最も近い True 日からの距離を累積
gap_day_marker = pd.Series(np.nan, index=close.index)
gap_day_marker[is_power_gap] = 0
# グループごとにカウントアップ
gap_group = is_power_gap.cumsum()
days_since_power_gap = gap_group.groupby(gap_group).cumcount()
# power_gap 未発生区間は NaN
days_since_power_gap[gap_group == 0] = np.nan

# power_gap_up_pct の計算
# is_power_gap が True の日の gap_up_pct を前方フィル
power_gap_up_pct = gap_up_pct.where(is_power_gap).ffill()
# power_gap 未発生区間は NaN のまま
```

## Config依存

| Config key | Default | Used as |
|---|---|---|
| `indicators.power_gap_threshold` | `10.0` | gap_up_pct がこの値以上の場合に power gap と判定（%）|

## 設計根拠

`power_gap_up_pct` と `days_since_power_gap` は、アノテーションフィルター `Recent Power Gap` の入力フィールドである。

スキャンではなくアノテーションの入力とした理由：
- 「最近、大きなギャップアップが発生した」は銘柄のコンテキスト（文脈）であり、候補を作る条件ではない
- 候補抽出は既存の Pullback Quality scan、21EMA Pattern H/L、Reclaim scan 等が行う
- ギャップ文脈を独立させることで、任意のスキャンと組み合わせ可能
- 専用スキャンを作ると、PB Quality の条件と6条件が重複する

## 上流依存

| フィールド | プロデューサー | 既存/新規 |
|---|---|---|
| `open` | price row | 既存 |
| `close` | price row | 既存 |

## Missing値の扱い

- `open` または `close.shift(1)` が NaN の場合、`gap_up_pct` は NaN
- `is_power_gap` は NaN 日に対して `False`
- `days_since_power_gap` は、対象銘柄で power gap が一度も発生していない場合は全期間 NaN
- `power_gap_up_pct` も同様に、未発生銘柄では全期間 NaN

## スナップショットへの出力

最新日の `power_gap_up_pct` と `days_since_power_gap` をスナップショットに含めること。

## テスト要件

- 当日の open が前日 close の 10% 以上高い場合、当日の `is_power_gap == True`
- `is_power_gap == True` の日に `days_since_power_gap == 0`
- `is_power_gap == True` の翌日に `days_since_power_gap == 1`
- `power_gap_up_pct` が直近の power gap 日の `gap_up_pct` と一致すること
- power gap が複数回発生した場合、常に直近の gap に対する値が出力されること
- power gap が一度も発生していない銘柄では両フィールドが NaN であること
- `power_gap_threshold` の config 変更が反映されること

---

# 変更6：新規アノテーションフィルター `Recent Power Gap`

## 実装先

`src/scan/rules.py::ANNOTATION_FILTER_REGISTRY`

## 定義

```python
# Recent Power Gap annotation filter
def _annotation_recent_power_gap(row, config):
    power_gap_up_pct = row.get("power_gap_up_pct", float("nan"))
    days_since = row.get("days_since_power_gap", float("nan"))
    return bool(
        pd.notna(power_gap_up_pct)
        and power_gap_up_pct >= config.power_gap_annotation_min_pct
        and pd.notna(days_since)
        and days_since <= config.power_gap_annotation_max_days
    )
```

## Canonical Condition

```
power_gap_up_pct >= power_gap_annotation_min_pct
AND days_since_power_gap <= power_gap_annotation_max_days
```

## Config依存

| Config key | Default | Used as |
|---|---|---|
| `scan.power_gap_annotation_min_pct` | `10.0` | アノテーション表示のための最小ギャップ率（%）|
| `scan.power_gap_annotation_max_days` | `20` | ギャップからの最大経過営業日数 |

## 設計根拠

Trend Base（`trend_base == True`）や Fund Score > 70（`fundamental_score >= 70.0`）と同じ粒度のアノテーションフィルター。候補を作るのではなく、既にスキャンで抽出された候補に「最近パワーギャップがあった」という文脈を付与する。

プリセットでの使い方の例：

```yaml
# ギャップ後ファーストプルバック プリセット
selected_scan_names: [Pullback Quality scan, 21EMA Pattern H, 21EMA Pattern L, Volume Accumulation, Pocket Pivot]
selected_annotation_filters: [Recent Power Gap, Trend Base]
duplicate_rule:
  mode: grouped_threshold
  required_scans: [Pullback Quality scan]
  optional_groups:
    - group_name: Pattern Trigger
      scans: [21EMA Pattern H, 21EMA Pattern L]
      min_hits: 1
    - group_name: Demand Confirmation
      scans: [Volume Accumulation, Pocket Pivot]
      min_hits: 1
```

この構成で「PB Quality が押し目品質を保証 + Pattern が21EMAパターンを検出 + Demand が需要を確認 + Recent Power Gap がギャップ文脈をフィルター」という分離が維持される。

## 既存アノテーションとの重複チェック

| 比較対象 | 重複の有無 |
|---|---|
| `RS 21 >= 63` | RS 条件。無関係 |
| `High Est. EPS Growth` | EPS 条件。無関係 |
| `PP Count (20d)` | PP カウント条件。ギャップとは独立。ギャップ日に PP が出ることはあるが、概念が異なる |
| `Trend Base` | トレンド状態条件。ギャップ後の銘柄が Trend Base であるケースは多いが、Trend Base はギャップの有無を判定しない |
| `Fund Score > 70` | ファンダメンタル条件。無関係 |

既存アノテーションとの完全な重複はない。

## ANNOTATION_FILTER_REGISTRY への追加

```python
ANNOTATION_FILTER_REGISTRY["Recent Power Gap"] = _annotation_recent_power_gap
```

## テスト要件

- `power_gap_up_pct >= 10.0` かつ `days_since_power_gap <= 20` の銘柄で `True`
- `days_since_power_gap > 20` の銘柄で `False`
- `power_gap_up_pct < 10.0` の銘柄で `False`
- power gap が一度も発生していない銘柄（NaN）で `False`
- config の `power_gap_annotation_min_pct` と `power_gap_annotation_max_days` の変更が反映されること

---

# 変更7・8・9：新規指標 `rs_ratio` / `rs_ratio_52w_high` / `rs_ratio_at_52w_high`

## 実装先

`src/scoring/rs.py::RSScorer.score`（rs_ratio の出力追加）
`src/indicators/core.py::IndicatorCalculator.calculate`（52w high 比較の計算）

## 定義

```python
# rs_ratio: パーセンタイル変換前のRS比率（銘柄close / ベンチマークclose）
# RSScorer 内で既に計算されている中間値を、スナップショットに出力する
rs_ratio = close / benchmark_close

# rs_ratio_52w_high: rs_ratio の52週（252日）ローリング最大値
rs_ratio_52w_high = rs_ratio.rolling(252).max()

# rs_ratio_at_52w_high: rs_ratio が52週高値に達しているか
# tolerance は config 駆動（default: 1.0%）
rs_ratio_at_52w_high = rs_ratio >= rs_ratio_52w_high * (1.0 - config.rs_new_high_tolerance / 100.0)
```

## 実装の詳細

### rs_ratio の出力追加

`RSScorer.score()` は現在、パーセンタイル変換後の `rs21`、`rs63`、`rs126` を出力している。`rs_ratio` はパーセンタイル変換前の中間値であり、RSScorer 内で既に計算されているが、スナップショットには出力されていない。

変更内容：RSScorer の score メソッドの出力に `rs_ratio`（21日ベースの `close / benchmark_close` の最新値）を追加する。

**注意：rs_ratio はパーセンタイルではなく絶対比率。** rs21 = 80 は「上位20%」を意味するが、rs_ratio = 1.05 は「ベンチマークに対して5%のプレミアム」を意味する。両者は異なる次元の情報。

### rs_ratio_52w_high / rs_ratio_at_52w_high の計算

rs_ratio がスナップショットに出力された後、IndicatorCalculator（または RSScorer 内の追加処理）で52週ハイとの比較を行う。

```python
# rs_ratio の時系列が必要なため、RSScorer 内で計算するのが自然
rs_ratio_series = close_series / benchmark_close_series
rs_ratio_52w_high = rs_ratio_series.rolling(252, min_periods=126).max()
rs_ratio_at_52w_high = rs_ratio_series >= rs_ratio_52w_high * (1.0 - config.rs_new_high_tolerance / 100.0)
```

`min_periods=126` により、上場後126日（約半年）以降から52週ハイの評価を開始する。これにより、IPO直後の銘柄で自明に `rs_ratio_at_52w_high == True` になることを防ぐ。

## Config依存

| Config key | Default | Used as |
|---|---|---|
| `scoring.rs_new_high_tolerance` | `1.0` | RS比率が52週ハイの何%以内であれば「新高値圏」と判定するか（%）|

## 設計根拠

RS比率の新高値は、RS21 のパーセンタイルとは異なる情報を持つ。RS21 = 97 は「直近21日のリターンが上位3%」を意味するが、RS比率の新高値は「銘柄の対ベンチマーク累積パフォーマンスが52週間で最も高い」を意味する。短期的にRS21が低くても（例：押し目中）、累積的なRS比率が新高値にある場合がある。

tolerance を 1.0% に設定している理由：RS比率は日次の微小な変動で「ちょうど52週ハイ」を外れることがある。1%の tolerance により、52週ハイの99%以内であれば新高値圏と判定し、ノイズによる脱落を防ぐ。

## 上流依存

| フィールド | プロデューサー | 既存/新規 |
|---|---|---|
| `close` | price row | 既存 |
| `benchmark_close` | `RSScorer` 内でのベンチマーク価格取得 | 既存（内部中間値）|
| `rs_ratio` | `RSScorer.score` | 新規出力（変更7）|

## Missing値の扱い

- `benchmark_close` が NaN の場合、`rs_ratio` は NaN
- `rs_ratio` のヒストリが126日未満の場合、`rs_ratio_52w_high` は NaN（`min_periods=126`）
- `rs_ratio_at_52w_high` は上記いずれかが NaN の場合 `False`

## スナップショットへの出力

最新日の `rs_ratio`、`rs_ratio_52w_high`、`rs_ratio_at_52w_high` をスナップショットに含めること。

## テスト要件

- `rs_ratio` が `close / benchmark_close` と一致すること
- `rs_ratio_52w_high` が直近252日間の `rs_ratio` の最大値と一致すること
- `rs_ratio` が `rs_ratio_52w_high` の99%以上である場合に `rs_ratio_at_52w_high == True`
- `rs_ratio` が `rs_ratio_52w_high` の99%未満である場合に `rs_ratio_at_52w_high == False`
- 上場後126日未満の銘柄では `rs_ratio_at_52w_high == False`（NaN扱い）
- `rs_new_high_tolerance` の config 変更が反映されること

---

# 変更10：新規スキャン `RS New High`

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `RS New High` |
| UI display name | `RS New High` |
| Implementation owner | `src/scan/rules.py::_scan_rs_new_high` |
| Output | `bool` |
| Direct scan config | `scan.rs_new_high_price_dist_max`, `scan.rs_new_high_price_dist_min` |
| Default status | `enabled` in `config/default/scan.yaml` |
| Scan number | 次の空き番号（28） |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`
- Reads a precomputed RS ratio new-high flag and distance from the 52-week price high
- All conditions are combined with `AND`
- Intended as a **RS-leads-price divergence scan**
- Detects stocks where the RS line has reached a new 52-week high while the price has NOT yet reached its own 52-week high

## Canonical Boolean Definition

```python
matched = bool(
    row.get("rs_ratio_at_52w_high", False)
    and row.get("dist_from_52w_high", float("nan")) <= config.rs_new_high_price_dist_max
    and row.get("dist_from_52w_high", float("nan")) >= config.rs_new_high_price_dist_min
)
```

## Intent / Scan Role

このスキャンは、RS線（銘柄リターン / ベンチマークリターン）が52週の新高値に達しているが、価格はまだ52週高値に達していない「RS先行」ダイバージェンスを検出する。

matchした銘柄は以下をすべて満たしている：

- RS比率が52週ハイ圏にある（対ベンチマーク累積パフォーマンスが過去1年で最高水準）
- 価格は52週高値から5-30%離れている（まだベース内にいる / ブレイクアウト前）

このスキャンが検出するダイバージェンスの意味：

- 価格がまだ高値を更新していないのにRSが新高値ということは、ベンチマークが上昇している中で銘柄がさらに強くアウトパフォームしている、あるいはベンチマークが下落している中で銘柄がほぼ横ばいを維持している
- いずれの場合も、価格がベース内にある段階で相対強度が突出しており、価格のブレイクアウト時にフォロースルーが強い傾向がある

このスキャンは以下を意図的に除外する：

- 価格も52週新高値にある銘柄（`dist_from_52w_high > -5.0`）。これは「RS先行」ではなく「RS + 価格の同時新高値」であり、Near 52W High scan の領域
- 52週高値から30%以上離れた銘柄。RS新高値が「受動的」である可能性（市場急落中の横ばい維持）が高く、銘柄自体の需要増を反映していない場合が多い

## Condition Design Notes

**RS新高値**
`rs_ratio_at_52w_high == True`

RS比率が52週ハイの99%以内（tolerance 1.0%）にあること。核心条件。

**価格は新高値ではない**
`dist_from_52w_high <= -5.0`

価格が52週高値から5%以上離れている。これにより「RSが先行している」状態を保証する。-5.0%の閾値は、52週高値から明確に距離がある（まだベース内 / 調整中 / 上昇途上）ことを意味する。

**過度な乖離を排除**
`dist_from_52w_high >= -30.0`

52週高値から30%以上離れた銘柄を除外する。大幅下落銘柄のRS新高値は、Low-Zone Spring プリセットの VCS 52 Low が対処する領域であり、本スキャンの「RS先行ブレイクアウト予兆」の thesis とは異なる。

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `rs_ratio_at_52w_high` | `src/scoring/rs.py::RSScorer.score` | `False` | must be `True` |
| `dist_from_52w_high` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | `<= rs_new_high_price_dist_max` and `>= rs_new_high_price_dist_min` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.rs_new_high_price_dist_max` | `-5.0` | 52週高値からの最大距離（価格が新高値ではないことの保証）|
| `scan.rs_new_high_price_dist_min` | `-30.0` | 52週高値からの最小距離（過度な乖離の排除）|

## Upstream Field Definitions

- `rs_ratio_at_52w_high` は変更7-9で定義。`rs_ratio >= rs_ratio_52w_high * (1.0 - tolerance/100.0)`
- `dist_from_52w_high = ((close / high_52w) - 1.0) * 100.0`（既存）
- `high_52w = high.rolling(252).max()`（既存）

## 既存スキャンとの排他性検証

| 比較対象 | 排他性の根拠 |
|---|---|
| Near 52W High（scan 10、無効） | Near 52W High は `close >= high_52w * 0.95`（5%以内）を要求。RS New High は `dist_from_52w_high <= -5.0`（5%以上離れている）を要求。検出範囲が排他的 |
| VCS 52 High（scan 13） | VCS 52 High は `dist_from_52w_high >= -20.0` を要求。RS New High は `-30.0 <= dist_from_52w_high <= -5.0` を要求。-20.0 ≤ dist ≤ -5.0 の範囲で重複するが、VCS 52 High は VCS ≥ 55 を要求し、RS New High は rs_ratio_at_52w_high を要求する。測定対象が根本的に異なる（ボラ収縮 vs RS比率新高値）。重複部分は「ボラ収縮 + RS先行」の正当な合流 |
| VCS 52 Low（scan 14） | `dist_from_52w_high ≤ -65`（VCS 52 Low）vs `≥ -30.0`（RS New High）。完全に排他的 |
| Momentum 97（scan 04） | リターンランクのパーセンタイル vs RS比率の絶対水準新高値。概念が異なる。RS比率が新高値でも weekly_return_rank が97%タイル未満のケースは多い |
| RS Acceleration（scan 12、無効） | `rs21 > rs63`（加速条件）vs rs_ratio_at_52w_high（水準条件）。加速と水準は独立した概念 |

## scan_status_map への追加

```yaml
RS New High:
  status: enabled
  scan_number: 28
```

## Scan Document

`doc/SystemDocs/Scan/scan_28_rs_new_high.md` を本セクションの内容で作成すること。

## テスト要件

- `rs_ratio_at_52w_high == True` かつ `-30.0 <= dist_from_52w_high <= -5.0` の銘柄で `True`
- `rs_ratio_at_52w_high == False` の銘柄で `False`
- `dist_from_52w_high > -5.0`（価格が高値圏）の銘柄で `False`
- `dist_from_52w_high < -30.0`（過度な乖離）の銘柄で `False`
- Near 52W High と同一日・同一銘柄でヒットしないこと（dist_from_52w_high の範囲が排他的であるため）
- config の `rs_new_high_price_dist_max` と `rs_new_high_price_dist_min` の変更が反映されること

---

# 実装順序の推奨

以下の依存関係に基づく実装順序：

```
Phase 1: 指標追加
  1-a. close_crossed_above_sma50（変更1）
  1-b. min_atr_50sma_zone_5d（変更2）
  1-c. power_gap_up_pct + days_since_power_gap（変更4・5）
  1-d. rs_ratio + rs_ratio_52w_high + rs_ratio_at_52w_high（変更7・8・9）
  → 全指標の単体テスト

Phase 2: スキャン・アノテーション追加
  2-a. 50SMA Reclaim scan（変更3）← 1-a, 1-b に依存
  2-b. Recent Power Gap annotation（変更6）← 1-c に依存
  2-c. RS New High scan（変更10）← 1-d に依存
  → 全スキャン・アノテーションの単体テスト
  → 既存スキャンとの排他性テスト

Phase 3: config・ドキュメント更新
  3-a. config/default/scan.yaml に新規スキャン・アノテーションの default 値を追加
  3-b. scan_status_map に scan 27, 28 を追加
  3-c. ANNOTATION_FILTER_REGISTRY に Recent Power Gap を追加
  3-d. scan doc（scan_27, scan_28）を作成
  3-e. scan_00_index.md を更新
```

---

# config 変更サマリ

## config/default/scan.yaml への追加

```yaml
# 変更4-5: Power Gap indicators
indicators:
  power_gap_threshold: 10.0

# 変更7-9: RS ratio new high
scoring:
  rs_new_high_tolerance: 1.0

# 変更6: Recent Power Gap annotation
scan:
  power_gap_annotation_min_pct: 10.0
  power_gap_annotation_max_days: 20

# 変更10: RS New High scan
  rs_new_high_price_dist_max: -5.0
  rs_new_high_price_dist_min: -30.0
```

## scan_status_map への追加

```yaml
50SMA Reclaim:
  status: enabled
  scan_number: 27

RS New High:
  status: enabled
  scan_number: 28
```

---

# ドキュメント更新チェックリスト

- [ ] `doc/SystemDocs/Scan/scan_27_50sma_reclaim.md` 新規作成
- [ ] `doc/SystemDocs/Scan/scan_28_rs_new_high.md` 新規作成
- [ ] `doc/SystemDocs/Scan/scan_00_index.md` に scan 27, 28 を追加
- [ ] `doc/SystemDocs/Scan/scan_00_index.md` の Active Scan Specs テーブルに 2行追加
- [ ] `doc/SystemDocs/Scan/scan_00_index.md` の annotation filter テーブルに `Recent Power Gap` を追加
- [ ] `scan_preset_enablestate.md` に scan 27, 28 の行を追加
