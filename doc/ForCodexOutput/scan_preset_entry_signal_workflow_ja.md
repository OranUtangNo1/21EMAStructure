# scan・preset・entry signal の関係メモ

作成日: 2026-04-26

## 前提

- このメモは現在の実装と設定ファイルを基準にした要約です。
- 対象は「銘柄を候補抽出して、Entry Signal 画面でタイミング評価するまで」です。
- 実売買、ポジションサイズ、執行、Exit はこの系統の責務外です。

## 先に結論

- `scan` は各銘柄に対する個別条件判定です。
- `preset` は複数の `scan` と annotation filter を束ねて、「この型の候補か」を再判定する watchlist 用のルールセットです。
- `entry signal` は `scan` を直接読むのではなく、`preset` が作った候補集合を source にして、その後段でエントリータイミングを評価します。

言い換えると、内部の主な流れは次の順です。

`snapshot -> scan hits -> preset duplicate判定 -> signal pool -> entry signal評価`

## 役割分担

### 1. scan

- `src/scan/rules.py` の各 scan ルールが、最新行ベースで各銘柄を判定します。
- 出力は `scan_hits` と watchlist 上のヒット情報です。
- scan は「その条件を満たしたか」を返す一次判定で、エントリー強度の総合点までは持ちません。

### 2. preset

- preset は `config/default/scan.yaml -> scan.watchlist_presets` で定義されています。
- 各 preset は以下を持ちます。
  - `selected_scan_names`
  - `selected_annotation_filters`
  - `duplicate_rule`
- 実際には `WatchlistViewModelBuilder.apply_selected_scan_metrics()` が、preset で選ばれた scan 群に対して duplicate 条件を再評価し、その preset に合う銘柄だけを残します。
- つまり preset は「scan の寄せ集め」ではなく、「複数 scan をどう組み合わせたら候補として採用するか」を定義する中間レイヤです。

### 3. entry signal

- entry signal 定義は `config/default/entry_signals.yaml` にあります。
- 現在の有効 signal は `orderly_pullback_entry` です。
- `EntrySignalRunner` は preset の duplicate 出力を signal の `pool.preset_sources` と照合して signal pool を作ります。
- その後、active pool に対して setup/timing/risk-reward を毎回評価し、`Entry Strength` と `Display Bucket` を出します。
- したがって entry signal は screening の入口ではなく、preset 通過後の「タイミング評価レイヤ」です。

## 現在の実装での具体的なつながり

### Orderly Pullback Entry の source

- `orderly_pullback_entry` の `pool.preset_sources` は次の 2 つです。
  - `Orderly Pullback`
  - `Trend Pullback`

### その意味

- `Orderly Pullback` か `Trend Pullback` の preset 条件を満たして duplicate 候補になった銘柄だけが、`orderly_pullback_entry` の signal pool 候補になります。
- つまり `Pullback Quality scan` や `Reclaim scan` が単独でヒットしても、それだけでは entry signal に入りません。
- 必ず一度 preset 側の組み合わせ条件を通る必要があります。

## 現在の built-in runtime 状態

- 現在の built-in preset では `Orderly Pullback` と `Trend Pullback` はどちらも `disabled` です。
- 主因は両 preset が `RS Acceleration` を参照しており、その scan が現在 `disabled` だからです。
- `EntrySignalRunner` は `export_enabled` な preset だけを signal source として読み込むため、現在の built-in 構成のままでは `orderly_pullback_entry` に新規 pool 候補が流れません。

要するに、定義上の関係は

`scan -> Orderly Pullback / Trend Pullback -> orderly_pullback_entry`

ですが、現在の built-in runtime ではこの経路は実質停止中です。

## 実務上の読み方

- scan: 部品
- preset: 候補抽出ロジック
- entry signal: 候補抽出後のエントリータイミング評価

このため、内部関係を最短で捉えるなら、

「scan が材料を作り、preset が候補を確定し、entry signal がその候補の今の入りやすさを点数化する」

と理解すれば十分です。
