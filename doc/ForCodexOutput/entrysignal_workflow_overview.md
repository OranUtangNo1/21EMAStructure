# Entry Signal 改修後ワークフロー概要

## 目的

Entry Signal は、当日の Watchlist をその場で見るだけの仕組みではなく、  
「preset で早期検出した候補を一定期間追跡し、その後のエントリータイミングを日次評価する仕組み」へ変更された。

この文書は、実装詳細ではなく運用上の流れを簡潔に整理したもの。

## 全体フロー

### 1. 日次パイプラインで preset 候補を作る

- まず通常の scan / watchlist / preset duplicate 判定が走る
- 各 Entry Signal は、自分専用の `preset_sources` を持つ
- 当日その `preset_sources` のいずれかで duplicate 検出された銘柄が、Entry Signal の追跡候補になる

### 2. signal ごとの追跡 pool に登録する

- 候補銘柄は signal ごとの pool に入る
- pool は ticker 共通ではなく、`signal x ticker` 単位で管理される
- 同じ銘柄でも signal が違えば別の候補として扱う
- 同じ signal で再検出された場合は、既存の active pool を更新する
- すでに invalidated された過去候補は再利用せず、新しい候補として入り直す

### 3. pool は一定期間だけ生きる

pool に入った候補は永続追跡ではない。状態を持ちながら一定期間だけ評価対象になる。

- `active`
  現在追跡中。毎日 Entry Signal 評価の対象になる
- `invalidated`
  セットアップが壊れた。以後は評価対象から外れる
- `expired`
  detection window を過ぎた。時間切れとして追跡終了
- `orphaned`
  元になった preset が存在しなくなった。評価対象から外れる

## 日次評価フロー

### 4. active pool を毎日評価する

- 毎日、active な pool 候補だけを再評価する
- 評価は signal ごとに独立して行う
- 当日 scan に再度出ている必要はない
- 重要なのは「過去に pool に入っていて、まだ active かどうか」

### 5. 評価結果は boolean ではなく score になる

各候補に対して、少なくとも次の観点が日次で評価される。

- `setup_maturity`
  セットアップとして熟しているか
- `timing`
  今日がエントリータイミングとして良いか
- `risk/reward`
  現在位置がリスクに対して良いか
- `entry_strength`
  上記を統合した総合強度

これにより、従来のような「出た / 出ない」だけでなく、  
「まだ早い」「ほぼ良い」「かなり良い」が連続値で見られる。

## 旧方式との違い

### 6. 早期検出型 preset を後追いできる

旧方式では、その日の universe に残っている銘柄しか Entry Signal が見なかった。  
そのため、preset が先に出て、数日後に entry timing が来るタイプは取りこぼしやすかった。

改修後は、

- preset 検出時点で pool に入る
- その後の数営業日を追跡する
- entry timing が来た日に score が上がる

という流れになった。

### 7. custom preset も pool source にできる

- built-in preset だけでなく custom preset も pool の起点にできる
- ただし preset 自体が消えた場合、その候補は orphaned 扱いになる

## 利用者が見る流れ

利用者視点では、Entry Signal は次の順で理解するとよい。

1. どの preset 群で候補が作られるか
2. 候補が今 active か、もう無効か
3. 今日の timing / risk-reward がどうか
4. 総合的に entry_strength が高いか

つまり Entry Signal は、  
「今日の Watchlist 判定」ではなく、  
「preset 起点の候補追跡と日次タイミング判定」を行う画面になっている。

## 一言で言うと

改修後の Entry Signal は、

`presetで候補化 -> signalごとのpoolで追跡 -> 毎日score評価 -> 条件悪化で終了`

というワークフローで動く。
