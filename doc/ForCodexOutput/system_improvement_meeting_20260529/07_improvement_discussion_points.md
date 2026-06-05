# 改善会議の論点

## 基本方針

最大目的は、短中期限定のロングオンリー・スイング投資において、再現性と期待値の高い投資判断を支援することである。

改善会議では、機能追加の数ではなく、次の問いに答えることを優先する。

- どの候補群が最も期待値が高いのか。
- どの条件がノイズを減らしているのか。
- どの条件が良い候補を落としすぎているのか。
- どの情報を上位表示、確認順序、EntrySignal 解釈に使うべきか。
- 短中期目的に対して、現行の timing 指標と候補品質評価の重みは適切か。

## 最優先論点 1: 期待値の検証単位を固定する

現行 Analysis は 1D、5D、10D、20D forward return を扱う。
market report は 5日、21日、63日 horizon を持つ。

短中期ロングオンリー swing を目的にするため、会議では以下を決めるべき。

- 主評価 horizon を 5日、10日、20/21日のどこに置くか。
- 63日は主評価ではなく、中期トレンド継続の補助指標にするか。
- preset 別の期待値は平均リターン、勝率、最大逆行、benchmark excess のどれを主指標にするのか。

提案:

- 主要評価: 10D / 20D または 21D excess return。
- 補助評価: 5D return は entry quality、63D は中期 leadership persistence。
- Preset 改善は 5D、10D、20/21D を中心に見て、63D は補助確認に留める。

## 最優先論点 2: WatchList Preset の期待値順位を定期評価する

現在は 9 つの active preset がある。
会議では、Preset ごとに以下を比較する必要がある。

- hit count。
- 5D / 10D / 20D average excess return。
- 5D / 10D / 20D win rate。
- market label 別の成績。
- sector / industry leadership ありなしの成績。
- EntrySignal に進んだ割合。
- Entry Ready になった割合。

提案:

- Preset を「主力」「条件付き」「観察中」に分類する。
- 主力は Fresh Stage 2 Breakout、RS Breakout Setup、VCP 3T Breakout、Accumulation Breakout を候補にする。
- Pullback 系は market が Positive 以上かつ industry leadership がある時に優先する。
- Momentum Ignition は climax warning と R/R の影響を重点検証する。

## 最優先論点 3: 短中期 leadership / quality score を追加する

現行 system は EntrySignal の入口評価が強い。
一方で、短中期スイングで期待値が高い候補を直接評価する score はまだ改善余地がある。

提案する追加 score:

- leadership_persistence_score
- stage2_durability_score
- industry_tailwind_score
- pullback_expectancy_score
- medium_term_quality_score

候補指標:

- rs21、rs63 の同時強さ。
- RS New High / RS 3Y New High。
- industry_score 70 以上。
- stage2_quality_score 75 以上。
- mature_late_stage_risk_filter pass。
- 52週高値から -3% から -20% の位置。
- 50SMA と 150/200SMA slope の良さ。
- 10D / 20D の relative return。63D は補助的に中期持続性を見る場合のみ使う。

## 論点 4: EntrySignal を「入口評価」と「短中期候補評価」に分ける

現行 EntrySignal は 3から10営業日の短い detection window が中心である。
これは timing evaluation として有効だが、候補そのものの短中期期待値評価とは役割が違う。

提案:

- EntrySignal は入口評価として維持する。
- 別に Candidate Quality / Swing Expectancy のような短中期 score を作る。
- EntrySignal の Action Bucket は、Candidate Quality が低い場合は上位表示しない。
- Candidate Quality が高いが timing が未成熟なものは、Watch Setup より上の「High Quality Waiting」に分類する。

## 論点 5: Market context を EntrySignal の解釈により明示的に使う

現行 context guard は Market Score と earnings warning で Entry Strength を cap する。
これは有効だが、Market Score だけでは業種リーダーシップや Risk-On Ratio の改善を十分に反映しない。

提案:

- EntrySignal 出力に market_context_bonus / penalty を明示する。
- Risk-On Ratio が risk_on、Breadth strong、Industry Leadership confirmed の時は、強い業種からの EntrySignal を優先表示する。
- weak industries からの EntrySignal は自動で lower priority 表示にする。
- market label が Positive 以上でも、Breadth が 70 未満なら breakout 系を慎重に扱う。

## 論点 6: Scan の整理と役割定義

現行 scan は 22 件あり、目的が近いものもある。

会議では scan を次の役割に分類する。

- Trend / Stage: Trend Template、Fresh Stage 2 Breakout、Stage 2 annotation。
- Leadership: RS New High、RS 3Y New High、RS Leads Price Setup、VCS 52 High。
- Demand: Pocket Pivot、PP Count、Volume Accumulation、4% bullish。
- Pullback / Reclaim: Pullback Quality scan、Reclaim scan、50SMA Reclaim、21EMA Pattern H/L。
- Structure / Base: VCP 3T、LL-HL Structure 1st/2nd、CT Break。
- Momentum: Momentum 97、Weekly 20% plus gainers。

提案:

- scan 単体の表示より、Preset 内での役割を強調する。
- 期待値が低い scan は削除ではなく、Preset から外す、または annotation 扱いにする。
- scan hit 数ではなく、役割グループの充足数を見る。

## 論点 7: 既存 Preset の改善候補

Fresh Stage 2 Breakout:

- 現行は days_since_stage2_start 21日以内、base 20日以上、rs21 70以上。
- 短中期目的では rs21 / rs63 の強さを加える余地がある。

RS Breakout Setup:

- 現行は VCS 52 High required、RS leadership group と breakout event group が必要。
- industry_score 70 以上を annotation で要求している点は良い。
- 改善候補は、RS New High があるが価格が伸びすぎた候補を別表示すること。

VCP 3T Breakout:

- 現行は VCP 3T required。
- 収縮品質と出来高 dry-up が明確なので、短中期向け主力候補になりやすい。
- 改善候補は、breakout 後の follow-through 成否を Analysis に連携すること。

Momentum Ignition:

- 現行は Momentum 97 required。
- 期待値が高い可能性はあるが、climax と chase のリスクが高い。
- 改善候補は、52週高値距離、rel_volume 5.0超、daily_change 6.0超をより強く警告すること。

Pullback 系:

- 現行は 21EMA / 50SMA の押し目に強い。
- 短中期目的では、押し目候補の quality と industry leadership をより強く見るべき。

## 論点 8: 出口管理は active scope 外だが、検証指標は必要

システムは exit management を提供しない。
しかし期待値検証には、出口ルールに相当する測定基準が必要である。

提案:

- Analysis では固定 horizon return を使い続ける。
- 追加で max favorable excursion、max adverse excursion を保存する。
- 5D / 10D / 20D の最高値、最安値、終値を記録する。63D は中期持続性の補助検証が必要な場合だけ追加する。
- これは売買指示ではなく、Preset の期待値検証用データとして扱う。

## 論点 9: 会議で決めたいこと

1. 主評価 horizon は 5D、10D、20/21D のどれか。
2. 主力 Preset をどれにするか。
3. EntrySignal の役割を入口評価に限定するか、中期候補評価を追加するか。
4. 業種リーダーシップを WatchList / EntrySignal の上位表示にどれだけ反映するか。
5. Momentum Ignition を主力にするか、警戒用にするか。
6. Pullback 系を market context によって昇格 / 降格するか。
7. Analysis に追加すべき検証指標は何か。

## 推奨アクション

短期:

- Preset 別の 5D / 10D / 20D 成績を集計する。
- EntrySignal の Action Bucket 別成績を集計する。
- Industry Leadership Gate あり / なしで成績を比較する。

中期:

- Candidate Quality score を追加する。
- WatchList の上位表示を Hybrid-RS だけでなく、Stage 2 durability と industry tailwind で補正する。
- EntrySignal に market / industry context の説明列を追加する。

継続改善:

- Preset と EntrySignal の条件を、forward return 実績から定期的に見直す。
- 短中期限定のロングオンリー swing に特化した primary objective を定義し、機能追加はその objective に対する改善として扱う。
