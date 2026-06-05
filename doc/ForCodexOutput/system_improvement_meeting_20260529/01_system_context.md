# システムのコンテキスト

## 最大目的

このシステムの最大目的は、短中期限定のロングオンリー・スイング投資において、再現性と期待値の高い投資判断を支援することである。

ここでの「提供」は、売買執行や最終裁量判断を代替することではない。
現行システムは、良い投資候補を見つける、候補の質を比較する、入口に近い状態を評価する、という意思決定前の情報整理を担っている。

## 現行システムの中心思想

現行システムは、Stage 2、RS、出来高需要、押し目・ブレイクアウト、EntrySignal の順に候補を絞る構造である。

主要な判断軸は次の通り。

- 市場環境がリスクを取りやすいか。
- 銘柄が Stage 2 または上昇トレンドとして十分か。
- RS が市場や同業種に対して強いか。
- 出来高、Pocket Pivot、Volume Accumulation が需要を示しているか。
- 押し目、リクレイム、ブレイクアウト、Power Gap 後の再エントリーが確認できるか。
- EntrySignal 上で setup、timing、risk/reward が同時に成立しているか。

## 現在の active scope

現行 UI の active page は以下の 6 つ。

- Watchlist
- Entry Signal
- Market Dashboard
- RS
- Analysis
- Setting

現行の active workflow は、データ取得、指標計算、スコアリング、scan、WatchList、EntrySignal、Market Dashboard、RS Radar、Preset effectiveness tracking で構成される。

## 現在の対象外範囲

以下は active system の責務ではない。

- 最終的な個別チャート裁量判断。
- ポジションサイズ決定。
- 実際の注文執行。
- 保有後の細かい利確、損切り、トレーリング管理。
- ショート戦略、ボトムフィッシング、52週安値からの回復狙いを主軸にした運用。

ただし EntrySignal は、入口候補の評価として active scope に含まれている。
EntrySignal の plan 情報は、実行命令ではなく「この候補を入口候補として扱えるか」を判断するための評価情報である。

## 目的との整合性

現行システムは、再現性を上げるために scan と EntrySignal の条件を数値化している。
期待値を上げるために、Stage 2、RS、業種リーダーシップ、出来高需要、R/R を重ねて候補を絞っている。

現行実装は、短期から中期の swing entry timing に寄っており、短中期限定という目的と整合している。
EntrySignal の detection window は 3 から 10 営業日が中心で、Analysis の forward return も 1D、5D、10D、20D を主に扱う。
会議では、短中期スイングの主評価時間軸を 5日、10日、20/21日のどこに置くかを明確にする必要がある。

## 現行システムの強み

- scan の条件が明示的で、検出理由を追跡しやすい。
- WatchList Preset が複数 scan の重なりを使うため、単独条件のノイズを減らしている。
- EntrySignal は setup、timing、risk/reward を分離しているため、なぜ entry ready でないかを説明できる。
- data source、cache、stale、sample、missing などのデータ品質情報を保持している。
- Market Dashboard と RS Radar により、個別銘柄だけでなく市場環境と業種リーダーシップを確認できる。
- Analysis で preset hit 後の forward return を追跡できる。

## 現行システムの弱点

- 短中期スイングの期待値を直接最大化する objective がまだ十分に明文化されていない。
- EntrySignal は入口評価に強いが、短中期スイングの継続期待値や中期トレンド持続の評価は限定的である。
- scan の数が多く、どの scan が本当に期待値に貢献しているかを定量比較する運用が必要である。
- WatchList Preset は設計意図が明確だが、Preset ごとの勝率、平均リターン、最大逆行、業種別効き方を改善会議で継続確認する必要がある。
- 現在の EntrySignal は候補の「入口の近さ」を評価するが、「短中期で期待値が高い候補」を直接ランクする機能はまだ改善余地がある。

## 会議での前提

改善案は、scan を増やすことよりも、期待値の高い候補を安定して上位に出すことを優先する。
追加する条件は、既存の Stage 2、RS、業種、出来高、R/R のどれを改善するのかを明確にする。
既存の active workflow に影響する変更は、Preset effectiveness tracking で検証できる形にする。
