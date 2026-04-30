# スキャンからエントリ判断までのワークフローとシステム思想

## 1. このドキュメントの目的

このドキュメントは、OraTek が現在実装している「スキャンからエントリ判断まで」の判断ワークフローと、その背後にあるシステム設計思想を説明するものです。

対象は、アプリ内の以下の流れです。

```text
データ取得
  -> 銘柄ユニバース作成
  -> 指標・スコア計算
  -> スキャン実行
  -> Watchlist生成
  -> Duplicate Tickers抽出
  -> Entry Signal確認
  -> ユーザーによる最終確認
```

このドキュメントは新しい仕様要求ではありません。現時点の実装を読み解くための運用・設計ノートです。

主な実装参照:

- `src/pipeline.py`
- `src/data/universe.py`
- `src/scan/runner.py`
- `src/scan/rules.py`
- `src/dashboard/watchlist.py`
- `src/signals/runner.py`
- `src/signals/rules.py`
- `app/main.py`
- `config/default/scan.yaml`
- `config/default/entry_signals.yaml`

関連仕様:

- `doc/SystemDocs/Specifications/04_SCAN_AND_WATCHLIST_SPEC.md`
- `doc/SystemDocs/Specifications/05_DASHBOARD_UI_SPEC.md`
- `doc/SystemDocs/Specifications/06_MODULE_AND_INTERFACE_SPEC.md`
- `doc/SystemDocs/Specifications/10_TRADING_METHOD_PLAYBOOK.md`
- `doc/SystemDocs/Scan/scan_00_index.md`

## 2. 対象範囲

このドキュメントが扱う範囲:

- スキャン候補の抽出
- Watchlistでの候補整理
- Duplicate Tickersの優先付け
- presetによる重複条件の表現
- Entry Signalによるタイミング確認
- ユーザーが最終判断に進む前の確認観点

このドキュメントが扱わない範囲:

- 実際の売買執行
- ポジションサイズ決定
- 損切り価格の確定
- 利確・撤退ルール
- トレード管理
- 裁量チャートレビューの詳細手順

現在のシステムは「候補抽出とエントリータイミング確認」までを支援します。  
売買判断そのものを自動化するシステムではありません。

## 3. 基本思想

### 3.1 スキャンは「買いシグナル」ではなく「候補抽出」

スキャンの役割は、売買判断ではありません。

スキャンが答える問い:

- この銘柄は見る価値があるか
- どの種類の条件に該当したか
- 複数の独立した条件に該当しているか
- 優先的にレビューすべき候補か

スキャンが答えない問い:

- 今すぐ買うべきか
- どの価格で買うべきか
- どこにストップを置くべきか
- どれだけの資金を入れるべきか

この分離が重要です。  
スキャン結果をそのまま売買判断に使うと、候補抽出と執行判断が混ざります。

### 3.2 Entry Signalは「タイミング確認」であり、最終エントリー判断ではない

Entry Signalは、WatchlistやDuplicate Tickersで抽出された候補に対して、現在実装されているタイミング条件が発生しているかを確認する層です。

Entry Signalが答える問い:

- 候補銘柄に、実装済みのタイミング条件が出ているか
- どのEntry Signalが発火したか
- 参考になるリスク基準値はあるか

Entry Signalが答えない問い:

- 最終的に買うべきか
- 実際のストップ位置はどこか
- チャート形状は十分か
- マーケット環境に対してリスクを取るべきか

つまり Entry Signal は「候補に対してタイミング面の材料があるか」を見るためのものです。  
最終エントリー判断はユーザー側に残ります。

### 3.3 システムはブラックボックスではなく、判断根拠を見えるようにする

このシステムは、単一の総合スコアだけで候補を出す設計ではありません。

根拠を追跡できるように、以下が分離されています。

- どのスキャンに該当したか: `scan_hits`
- どのカードに表示されたか: Watchlist scan cards
- どのduplicate条件を満たしたか: duplicate rule
- どのpresetに該当したか: preset duplicate
- どのEntry Signalが出たか: Entry Signal table
- データ品質はどうか: Data Health

理想的な確認経路:

```text
eligible universe
  -> scan_hits
  -> Watchlist card
  -> Duplicate Tickers
  -> Entry Signal
  -> ユーザーの最終レビュー
```

### 3.4 スキャンは増える・変わる前提

このプロジェクトでは、今後もスキャンの新規追加や置き換えが発生します。

運用思想:

- 古くなったスキャンは削除しない
- 無効化して残す
- 新規スキャンの番号は末尾に追加する
- 無効化したスキャン番号は変更しない
- 通常実行では有効なスキャンのみを実行する

理由:

- 過去の判断やtracking結果との対応を壊さない
- scan indexの意味を安定させる
- 新旧ロジックの比較ができる
- 実行時間を不要に増やさない

### 3.5 Duplicate Tickersは「合流点」

Duplicate Tickersは、単に「複数のリストに出た銘柄」ではなく、複数の条件が合流した候補を優先表示するための仕組みです。

重複の考え方:

- 1つのスキャンだけでは弱い場合がある
- 複数の独立したスキャンが同じ銘柄を指すなら、優先度が上がる
- ただし単純な数だけではなく、条件の種類も重要

そのため現在は、単純な `min_count` だけでなく、`grouped_threshold` による階層化も実装されています。

例:

```text
必須:
  Pullback Quality scan

Optional Condition 1:
  21EMA Pattern H または 21EMA Pattern L のうち1つ以上

Optional Condition 2:
  RS Acceleration または Volume Accumulation のうち1つ以上
```

このようにすることで、単なる「3個ヒット」ではなく、

```text
押し目品質 + トリガー + 強さの確認
```

のような意味のある組み合わせを表現できます。

Optional Conditionの数は任意に変更できます。

## 4. レイヤーごとの責務

### 4.1 Data layer

データ層の責務:

- universe候補を取得する
- 株価履歴を取得する
- profile / fundamental データを取得する
- cacheを使う
- stale cacheやmissingを記録する
- Data Healthに必要な情報を残す

ここで重要なのは、データが完全でない場合でも、その状態を隠さないことです。

代表的なデータ状態:

- `live`: 今回取得できたデータ
- `cache_fresh`: 新鮮なcache
- `cache_stale`: 古いcacheを代替使用
- `sample`: sample fallback
- `missing`: 有効なデータなし

### 4.2 Indicator layer

Indicator layerは、価格履歴から再利用可能な指標を計算します。

代表的な指標:

- `ema21_high`
- `ema21_low`
- `ema21_close`
- `sma50`
- `sma200`
- `atr`
- `atr_21ema_zone`
- `atr_50sma_zone`
- `rel_volume`
- `ud_volume_ratio`
- `structure_pivot_long_*`
- `rs21`
- `rs63`
- `rs126`

この層は判断をしません。  
後続のスキャンやEntry Signalが使う材料を作るだけです。

### 4.3 Scoring layer

Scoring layerは、候補の優先度判断に使うスコアを作ります。

代表的なスコア:

- RS score
- fundamental score
- industry score
- hybrid score
- VCS

使い道:

- Watchlistの並び順
- Duplicate Tickersの優先度
- Entry Signal表での補助情報
- presetやscan結果の文脈確認

スコアは有用ですが、スコア単体で売買判断を完結させる設計ではありません。

### 4.4 Scan layer

Scan layerは、eligible snapshotに対して有効なスキャンを実行します。

責務:

- scan contextを追加する
- enabled scanのみを評価する
- annotation filterを評価する
- `scan_hits` を作る
- raw watchlistを作る
- backend duplicateを付ける

重要なルール:

```text
scan hitが1つ以上ある銘柄だけがraw Watchlist候補になる
annotation filterだけでは候補にならない
```

### 4.5 Watchlist layer

Watchlist layerは、raw watchlistをユーザーがレビューしやすい形に投影します。

責務:

- required scansを反映する
- optional condition groupsを反映する
- annotation filtersを適用する
- duplicate ruleを評価する
- Duplicate Tickers bandを作る
- scan cardsを作る
- preset exportを作る

この層での表示変更は、raw scan factそのものを書き換えるものではありません。

### 4.6 Entry Signal layer

Entry Signal layerは、選択された候補 universe に対して、タイミング条件を評価します。

責務:

- Entry Signal universeを作る
- enabled Entry Signalだけを評価する
- 発火したEntry Signal名を表示する
- universe sourceを表示する
- risk referenceを表示する

この層もまだ「レビュー支援」です。  
売買執行判断ではありません。

## 5. 実際のワークフロー

### 5.1 Universe準備

システムはまず、アクティブな銘柄集合を決めます。

通常の流れ:

1. freshなweekly universe snapshotがあれば再利用
2. なければ新しいuniverseを取得
3. 価格履歴を取得
4. profile / fundamental情報をsnapshotから取得
5. 足りないprofile / fundamentalをfallback providerで補完
6. データ取得状態を記録

この時点では、まだスキャン判断は行われていません。

### 5.2 Eligible universe filter

スキャン前に、広い意味で対象外の銘柄を除外します。

現在のdefault条件:

- 時価総額: `1B` 以上
- 50日平均出来高: `1M` 以上
- 株価: `0.0` 以上
- ADR: `3.5` 以上
- ADR: `10.0` 以下
- 除外セクター: `Healthcare`

目的:

- 流動性の低い銘柄を避ける
- 想定外の低ボラ・高ボラを避ける
- screening対象を実用的な範囲に保つ

### 5.3 指標とスコアの計算

eligible universeに進む前後で、各種指標とスコアが作られます。

主な流れ:

1. indicator historyを作る
2. 最新日のsnapshotを作る
3. データソース状態を付与
4. RS scoreを計算
5. fundamental scoreを計算
6. industry scoreを計算
7. hybrid scoreを計算
8. VCSを計算
9. earningsやIPO関連情報を付与
10. data quality scoreを付与

この段階では「評価材料」が揃っただけです。  
候補として採用されるには、次のスキャンを通過する必要があります。

### 5.4 Scan context enrichment

スキャン実行前に、横断的なrankが追加されます。

現在のscan context:

- `weekly_return_rank`
- `quarterly_return_rank`
- `eps_growth_rank`

これらは、その日のeligible universe内での相対順位です。

### 5.5 Enabled scan execution

有効化されているscanだけが実行されます。

現在の基本ルール:

```text
enabled scanに1つも該当しない -> Watchlistに入らない
enabled scanに1つ以上該当する -> raw Watchlist候補
```

各scan hitは `scan_hits` に記録されます。

`scan_hits` の粒度:

```text
ticker x scan name
```

1銘柄が複数スキャンに該当した場合、複数行になります。

### 5.6 Annotation filter

annotation filterは、候補生成ではなく補助的なフィルタです。

defaultで利用可能なannotation:

- `RS 21 >= 63`
- `High Est. EPS Growth`
- `PP Count (20d)`
- `Trend Base`
- `Fund Score > 70`

現在のdefaultでは、自動有効化されているannotation filterはありません。

使い方:

- Watchlist表示を絞る
- presetの補助条件にする
- 候補の品質確認に使う

使ってはいけない解釈:

```text
annotationだけで候補になった
```

これは現在の設計ではありません。

### 5.7 Raw Watchlist生成

raw Watchlistは、scan hitを持つ銘柄の集合です。

主なフィールド:

- `hit_scans`
- `scan_hit_count`
- `overlap_count`
- `duplicate_ticker`
- `annotation_hits`
- `annotation_hit_count`
- score fields
- data quality fields

defaultの並び順:

1. `hybrid_score`
2. `overlap_count`
3. `vcs`
4. `rs21`

つまり、defaultではquality寄りの候補が上に来ます。

### 5.8 Watchlist UI projection

Watchlistタブでは、raw Watchlistを現在のUI設定に基づいて再投影します。

重要な区別:

```text
raw Watchlist = backendの事実
Watchlist表示 = 現在のUI設定による見方
```

現在のWatchlist controls:

- preset load/save/update/delete
- required scans
- optional condition groups
- annotation filters
- duplicate rule

ここで変更されるのは「表示とduplicate判定の見方」です。  
scan hitの事実そのものではありません。

### 5.9 Duplicate Tickers

Duplicate Tickersは、Watchlist内の最優先レビュー対象です。

現在サポートされるduplicate rule:

#### min_count

指定数以上のscan hitがあることを要求します。

例:

```text
3つ以上の選択scanに該当した銘柄
```

#### required_plus_optional_min

required scansをすべて満たし、optional scansから指定数以上を満たすことを要求します。

これは旧形式との互換性を持つruleです。

#### grouped_threshold

required scansをすべて満たし、さらに複数のoptional groupそれぞれの条件を満たすことを要求します。

例:

```text
Required:
  Pullback Quality scan

Optional Condition 1:
  21EMA Pattern H, 21EMA Pattern L から1つ以上

Optional Condition 2:
  RS Acceleration, Volume Accumulation から1つ以上
```

この形式は、presetの意図を最も表現しやすい形式です。

### 5.10 Scan cards

scan cardsは、個別scanごとの該当銘柄を表示します。

役割:

- Duplicate Tickerがどのscanに支えられているか確認する
- 1つのscanだけに出ている候補を確認する
- scanごとの候補の偏りを見る

Duplicate bandは優先順位を見る場所です。  
Scan cardsは根拠を分解して見る場所です。

### 5.11 Preset

presetは、Watchlistの見方を保存したものです。

presetが持つ主な情報:

- selected scans
- required scans
- optional condition groups
- annotation filters
- duplicate rule
- preset status

preset status:

- `enabled`: UIに表示され、tracking/export対象
- `hidden_enabled`: UIには出さないがtracking/export対象
- `disabled`: 非アクティブ

presetの思想:

- scan群の束ではなく、レビュー仮説を保存する
- duplicate ruleによって候補抽出の意味を明確にする
- 過去の検出記録と現在の定義変更を分離する

### 5.12 Entry Signal universe

Entry Signalは、選択されたuniverseに対して実行されます。

選択可能なuniverse:

- `Preset + Current Duplicates`
- `Preset Duplicates`
- `Current Selection Duplicates`
- `Today's Watchlist`
- `Eligible Universe`

推奨される考え方:

```text
まずduplicate系universeで確認する
広いuniverseは探索目的で使う
```

理由:

- duplicate candidatesは既にconfluenceを持っている
- broad universeでは質の低い候補にもEntry Signalが出る可能性がある
- Entry Signalは、事前に抽出された候補に対して使う方が意味が強い

### 5.13 Entry Signal evaluation

現在有効なEntry Signal:

#### Pocket Pivot Entry

条件:

- `pocket_pivot` がtrue
- `close > sma50`

解釈:

- 50SMA上でのpocket pivot

#### Structure Pivot Breakout Entry

条件:

- `structure_pivot_long_breakout_first_day` がtrue

解釈:

- bullish structure pivotの初日ブレイク

#### Pullback Low-Risk Zone

条件:

- 21EMAまたは50SMA付近
- `rs21 > 50`
- `dcr_percent` が30未満ではない

解釈:

- RSが崩れていない押し目候補

#### Volume Reclaim Entry

条件:

- `close > sma50`
- `rel_volume >= 1.4`
- `daily_change_pct > 0`

解釈:

- 出来高を伴ったSMA50上回復

### 5.14 Entry Signal output

Entry Signal表の主な列:

- `Ticker`
- `Entry Signals`
- `Universe Sources`
- `Close`
- `RS21`
- `VCS`
- `Rel Volume`
- `Dist 52W High`
- `Risk Reference`
- `Entry Note`

並び順:

1. `RS21`
2. `VCS`
3. `Rel Volume`

強い候補が上に来るように設計されています。

## 6. 判断責務の分担

| 段階 | システムの責務 | ユーザーの責務 |
| --- | --- | --- |
| Data Health | データ状態を可視化する | 結果を信頼できるか判断する |
| Eligible universe | 対象外銘柄を除外する | 除外条件を理解する |
| Scan | 候補条件を検出する | どのscanが効いているか確認する |
| Annotation | 補助条件を付与する | 表示を絞るか判断する |
| Duplicate | confluence候補を優先表示する | レビュー対象を選ぶ |
| Scan cards | scan別の根拠を分解する | 候補の根拠を読む |
| Preset | 再利用可能な見方を保存する | presetの意図を調整する |
| Entry Signal | timing条件を検出する | 実行可能性を検討する |
| Final review | 対象外 | チャート、リスク、売買判断を行う |

## 7. 推奨されるユーザー操作フロー

### Step 1: Data Healthを確認する

最初にData Healthを見るべきです。

注意すべき状態:

- stale price cache
- missing price
- missing profile
- missing fundamentals
- sample fallback

重要な候補銘柄がstaleやmissingの場合、結果は暫定扱いにします。

### Step 2: Market DashboardとRSを見る

市場環境を確認します。

見る観点:

- breadthは強いか
- trend participationは広いか
- factorはrisk-onかrisk-offか
- RSの強いsector / industryはどこか

この情報はscan eligibilityを直接変えません。  
しかし、候補をどれだけ積極的に見るかに影響します。

### Step 3: WatchlistでDuplicate Tickersを見る

Watchlistでは、まずDuplicate Tickersを見ます。

確認すること:

- どの銘柄がconfluenceを持っているか
- preset由来かcurrent selection由来か
- どのscan群が根拠になっているか
- 1つのテーマに偏っていないか

### Step 4: Scan cardsで根拠を分解する

Duplicate Tickerだけでは、なぜ出たのかが十分に分かりません。

Scan cardsで確認すること:

- どのscanに出ているか
- required scanに該当しているか
- optional condition groupを満たしているか
- 他の候補と比べてどのscanで強いか

### Step 5: Watchlist controlsを必要に応じて調整する

調整例:

- presetを読み込む
- required scanを変更する
- optional conditionを追加する
- group内のrequired hitsを変更する
- annotation filterを追加する

注意点:

- 一度に多くの条件を変えない
- 候補が大きく変わった場合、どの条件が影響したか確認する
- preset保存前にduplicate ruleの意味を確認する

### Step 6: Entry Signalを見る

Entry Signalでは、まずduplicate系universeから確認するのが自然です。

推奨順:

1. `Preset + Current Duplicates`
2. `Preset Duplicates`
3. `Current Selection Duplicates`
4. `Today's Watchlist`
5. `Eligible Universe`

広いuniverseほど、候補品質のばらつきが増えます。

### Step 7: Entry Signalを解釈する

Entry Signal行を見るときの観点:

- どのEntry Signalが出たか
- universe sourceは何か
- RS21は十分か
- VCSは十分か
- rel volumeはあるか
- risk referenceは何を指しているか
- Watchlist側の根拠と矛盾していないか

Entry Signalは、

```text
候補銘柄にタイミング条件が出ている
```

という意味です。

```text
自動的に買う
```

という意味ではありません。

### Step 8: アプリ外で最終確認する

最後にユーザーが確認すべきもの:

- チャート構造
- base quality
- overhead supply
- 出来高と流動性
- 決算やイベントリスク
- ストップ候補
- ポジションサイズ
- ポートフォリオ全体のリスク

この段階は現在のアプリの責務外です。

## 8. よくある結果の解釈

### 8.1 WatchlistにはいるがDuplicateにはいない

意味:

- 少なくとも1つのscanには該当している
- しかし現在のduplicate ruleは満たしていない

対応:

- scan cardで根拠を確認する
- 優先度は低めに見る
- 探索目的ならduplicate条件を緩める

### 8.2 DuplicateにはいるがEntry Signalが出ていない

意味:

- candidate qualityやconfluenceはある
- しかし実装済みのtiming条件はまだ出ていない

対応:

- watch候補として残す
- 後日のrunを待つ
- 外部チャートで裁量確認する

### 8.3 Entry Signalは出ているがDuplicateではない

意味:

- timing条件は出ている
- ただしscan confluenceは弱い可能性がある

対応:

- Watchlistやscan cardで根拠を確認する
- broad universeで出たsignalは探索扱いにする

### 8.4 preset duplicateが何度も出る

意味:

- preset条件を継続的に満たしている
- tracking DBには既にactive detectionがある場合がある

対応:

- Analysisで過去のforward returnを見る
- 毎回新しい独立signalとは限らない点に注意する

### 8.5 fundamentalsがmissing

意味:

- price scanは成立している可能性がある
- ただしfundamental scoreやhybrid scoreの信頼性は落ちる

対応:

- Data Healthを見る
- fundamental要素を過信しない

## 9. 設計上の重要なトレードオフ

### 9.1 scanとannotationを分ける理由

scanは候補を作る条件です。

annotationは候補に文脈を付ける条件です。

これを混ぜると、例えば `Fund Score > 70` だけで技術的根拠のない候補がWatchlistに入る可能性があります。

現在の設計では、それを避けています。

### 9.2 duplicate ruleを柔軟にしている理由

単純なscan数だけでは、条件の意味を表現しきれません。

例えば、

```text
21EMA系が2つ出た
```

ことと、

```text
押し目品質 + 21EMA trigger + strength confirmation
```

は意味が違います。

`grouped_threshold` はこの違いを表現するための仕組みです。

### 9.3 Entry Signalをscanと分ける理由

scanはsetupを見ます。

Entry Signalはtimingを見ます。

この2つを混ぜると、

- 良いsetupだがまだtimingがない候補
- timingはあるがsetup品質が弱い候補

を区別しづらくなります。

現在の分離は、この違いを見えるようにするためです。

### 9.4 trackingを残す理由

presetやscanは将来変わります。

しかし、過去にシステムが何を候補として出したかは、後から分析できる必要があります。

そのため、Analysisは現在のpreset定義だけではなく、検出時点のrecordを使います。

## 10. 拡張時の設計原則

### 10.1 新しいscanを追加する場合

原則:

- 新しい番号は末尾に追加する
- 旧scanは削除せず無効化する
- `scan_status_map` で有効・無効を管理する
- 必要に応じてcardやpresetに追加する
- scan docを `doc/SystemDocs/Scan/` に追加する

### 10.2 新しいpresetを追加する場合

良いpresetは、単なるscanの寄せ集めではありません。

必要なもの:

- 明確なscreening thesis
- selected scans
- required scans
- optional condition groups
- groupごとのmin_hits
- 必要なannotation filters
- preset status

### 10.3 新しいEntry Signalを追加する場合

良いEntry Signalの条件:

- 実装済みfieldを使う
- 条件が検証しやすい
- risk referenceを持てる
- 最終売買判断と混同されない
- signal名とnoteが直感的

Entry Signalを「隠れたscan層」にしないことが重要です。

### 10.4 Settingタブに追加する場合

Settingタブは今後、全体設定の置き場になります。

向いているもの:

- 表示設定
- refresh関連設定
- tracking diagnostics
- 安全なglobal toggle

向いていないもの:

- 履歴解釈を silently に変える設定
- scan挙動をconfig外で隠れて変える設定
- trade executionやposition sizingに関する設定

## 11. 最終的なメンタルモデル

このシステムは、以下のファネルとして理解するのがよいです。

```text
Data Health
  -> Eligible Universe
  -> Indicators / Scores
  -> Enabled Scans
  -> Raw Watchlist
  -> Duplicate Logic
  -> Duplicate Tickers
  -> Entry Signal Universe
  -> Entry Timing Signals
  -> Human Final Review
```

短く言えば、

```text
広く集める
条件で絞る
重複で優先する
タイミングを確認する
最後は人間が判断する
```

という思想です。

このシステムは、透明な候補抽出ファネルとして使うと最も強いです。  
ブラックボックスの売買エンジンとして使う設計ではありません。
