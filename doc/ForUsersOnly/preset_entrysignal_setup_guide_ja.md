# Preset / EntrySignal が提供するセットアップ解説

作成日: 2026-05-01

## この文書の位置づけ

この文書は、現在の実装と設定を基準にして、OraTek がどのような「セットアップの銘柄」を候補として出すかを説明するものです。

主な参照元は次のファイルです。

- `config/default/scan.yaml`
- `config/default/entry_signals.yaml`
- `src/scan/rules.py`
- `src/signals/runner.py`
- `src/signals/evaluators/`
- `doc/SystemDocs/WatchlistPresets/`

ここでいうセットアップは、売買執行やポジション管理ではなく、候補抽出とエントリー評価までを指します。

## 全体像

OraTek の候補抽出は、次の順に狭まります。

`scan hits -> Watchlist Preset -> EntrySignal pool -> EntrySignal score`

- `scan` は、個別条件にヒットした銘柄を見つける一次判定です。
- `Preset` は、複数の scan と annotation filter を組み合わせて、特定のセットアップ候補を作ります。
- `EntrySignal` は、Preset から流れてきた候補を数営業日だけ追跡し、今日のエントリータイミング、セットアップ成熟度、リスク/リワードを点数化します。

つまり Preset は「どの型の銘柄か」を決め、EntrySignal は「その型の銘柄が今エントリーに近いか」を評価します。

## 現在有効な Preset が提供するセットアップ

現在の built-in Preset は 17 個あり、そのうち runtime で有効なのは 10 個です。有効な Preset だけが UI と export に出ます。

| Preset | 提供する銘柄のセットアップ | 中核条件の読み方 |
| --- | --- | --- |
| `Reclaim Trigger` | 上昇基調の中で重要水準を奪回し、需要の再発生が見える銘柄 | `Reclaim scan` が必須で、`Pocket Pivot` も必要。`Trend Base` filter でトレンド背景を要求する |
| `Early Cycle Recovery` | 下落・調整後に初期回復が始まり、反転の初動が出ている銘柄 | `Trend Reversal Setup` が必須で、`Pocket Pivot` / `VCS 52 Low` / `Volume Accumulation` のいずれかで補強する |
| `Accumulation Breakout` | 高値圏やベース内で蓄積が進み、ブレイクアウトの兆候が出ている銘柄 | `VCS 52 High` が必須。さらに蓄積証拠とブレイクアウトトリガーをそれぞれ最低 1 つ要求する |
| `VCP 3T Breakout` | VCP 型の収縮を経て、ピボット接近・需要確認・リーダー性がそろう銘柄 | `VCP 3T` が必須。`VCS 52 High` / `RS New High` と、`Pocket Pivot` / `Volume Accumulation` を組み合わせる |
| `50SMA Defense` | 50SMA 付近を守って反発し、調整継続ではなく再上昇の形を作る銘柄 | `50SMA Reclaim` が必須。Pullback Quality と需要確認を追加で要求する |
| `Power Gap Pullback` | パワーギャップ後に追いかけず、初回の秩序ある押し目と再突入タイミングを待つ銘柄 | `Recent Power Gap` と `Trend Base` が前提。Pullback Quality、21EMA/Reclaim 系トリガー、需要確認を組み合わせる |
| `RS Breakout Setup` | 相対強度が新高値を更新し、価格も高値圏でブレイク準備に入る銘柄 | `RS New High` と `VCS 52 High` が必須。`Pocket Pivot` / `4% bullish` / `PP Count` のいずれかでブレイクイベントを確認する |
| `Screening Thesis` | 初期反転の仮説を広めに拾う銘柄。まだ完成した上昇トレンドより、構造変化と需要回復を重視する | `Trend Reversal Setup` が必須。LL-HL 構造ブレイク群と需要確認をそれぞれ最低 1 つ要求する |
| `Pullback Trigger` | 押し目の質があり、21EMA パターンや需要確認で再上昇トリガーが出ている銘柄 | `Pullback Quality scan` が必須。21EMA Pattern H/L と Volume Accumulation/Pocket Pivot を組み合わせる |
| `Momentum Ignition` | 既に強いモメンタムがあり、さらに加速イベントと品質確認が重なる銘柄 | `Momentum 97` が必須。`4% bullish` / `PP Count` と、`VCS 52 High` / `Volume Accumulation` を組み合わせる |

## 検出されたティッカーの読み方

上の表は Preset ごとの「型」を説明しています。実際に検出された個別ティッカーについては、次の列を見ると、どのセットアップによって拾われたかを確認できます。

| 列 | 読み方 |
| --- | --- |
| `hit_presets` / `Hit Presets` | そのティッカーが通過した Preset 名。複数あれば、複数のセットアップ型に同時に該当している |
| `matched_scans` / `Matched Scans` | Preset 内で実際にヒットした scan。ここが「なぜこの Preset で検出されたか」の一番直接的な根拠 |
| `selected_scan_names` | その Preset が評価対象にした scan 群。`matched_scans` はこの中から実際にヒットしたもの |
| `duplicate_rule_modes` | Preset の組み合わせルール。`grouped_threshold` なら必須 scan と各 optional group の条件を満たしたという意味 |
| `selected_scan_hit_count` / `scan_hit_count` | その Preset 内で何個の scan に重なってヒットしたか。多いほど複数条件が重なっているが、それだけで投資判断は完結しない |

たとえば `Pullback Trigger` で検出されたティッカーでも、理由は一律ではありません。

- `Pullback Quality scan` + `21EMA Pattern H` + `Volume Accumulation` なら、押し目の質、21EMA 付近の反応、出来高の戻りが重なった候補です。
- `Pullback Quality scan` + `21EMA Pattern L` + `Pocket Pivot` なら、押し目の質、21EMA 下側からの反応、Pocket Pivot 型の需要が重なった候補です。

同じ Preset 名でも、実際の `matched_scans` によって意味は変わります。Preset 名だけで判断せず、必ず `matched_scans` と EntrySignal の `Entry Strength`、`Timing`、`Risk/Reward` を合わせて見ます。

## 投資判断に使う時の注意

Preset ヒットは「買ってよい」という意味ではありません。意味としては、「この銘柄は特定のセットアップ候補としてレビュー対象に入った」です。

特に注意すべき点は次の通りです。

- Preset は候補抽出です。エントリーの良し悪しは EntrySignal の `Timing` と `Risk/Reward` を見ないと判断できません。
- `matched_scans` が多くても、すでに伸び切っていて R/R が悪い銘柄はあります。
- `Signal Detected` でも、決算、地合い、出来高の異常、日足チャートの過熱、ギャップ後の失速は別途確認が必要です。
- `Tracking` や `Approaching` は、まだ監視対象であって、即エントリー候補とは限りません。
- このシステムは最終的な投資助言ではなく、チャートレビュー前の候補抽出とエントリー状態の定量化です。

実務上は、最低でも次の順で確認します。

1. `hit_presets` で、どのセットアップ型に分類されたかを見る。
2. `matched_scans` で、実際にどの条件が重なったかを見る。
3. EntrySignal の `Display Bucket`、`Entry Strength`、`Timing`、`Risk/Reward` を見る。
4. stop を置ける構造があるか、想定損失に対して reward が見合うかを見る。
5. 決算日、地合い、ニュース、流動性、直近の過熱を確認する。
6. 最後に日足・週足チャートを目視して、セットアップが本当に読み取れるか確認する。

したがって、Preset で検出されたティッカーは「投資してよい銘柄」ではなく、「投資判断の前に詳しく見る価値がある銘柄」です。

## 現在無効な Preset

次の Preset は定義としては存在しますが、現在の runtime では無効です。主に参照している scan が無効なため、現状の built-in UI/export には出ません。

| Preset | 狙うセットアップ | 現在の扱い |
| --- | --- | --- |
| `Leader Breakout` | 強い RS と高値圏のリーダーが、ベースからブレイクする形 | disabled |
| `Orderly Pullback` | 上昇トレンド中の秩序ある 21EMA 押し目 | disabled |
| `Momentum Surge` | 強い上昇日とモメンタム上位が重なる短期加速 | disabled |
| `Base Breakout` | 52週高値圏・Pocket Pivot・ベース内の抵抗テストを伴うブレイク | disabled |
| `Trend Pullback` | トレンド中の押し目から reclaim する再上昇候補 | disabled |
| `Resilient Leader` | 高ファンダメンタル・高 RS・52週高値近辺を維持する耐久型リーダー | disabled |
| `Early Recovery` | Trend Reversal と Structure Pivot を両方要求する早期回復 | disabled |

無効 Preset は「このリポジトリが設計上持っている型」ではありますが、現在の通常運用で提供される候補集合には含めません。

## EntrySignal が提供するセットアップ

EntrySignal は、Preset で検出された銘柄を signal ごとの pool に登録し、一定期間だけ追跡します。現在は 6 つすべてが enabled です。

| EntrySignal | 入り口になる Preset | 提供するセットアップ | 追跡期間 |
| --- | --- | --- | --- |
| `Orderly Pullback Entry` | `Pullback Trigger` | 21EMA 周辺まで秩序よく押した後、出来高・終値品質・21EMA reclaim で入れるかを見る押し目エントリー | 10 営業日 |
| `Pullback Resumption Entry` | `Pullback Trigger`, `50SMA Defense`, `Reclaim Trigger` | 21EMA/50SMA/reclaim 型の押し目再開。深さに応じた stop と R/R を見ながら再上昇の入り口を評価する | 7 営業日 |
| `Momentum Acceleration Entry` | `Momentum Ignition` | 既に強い銘柄に新しい加速イベントが出た場面。追いかけすぎを避けながら、加速当日の品質を評価する | 3 営業日 |
| `Accumulation Breakout Entry` | `Accumulation Breakout`, `RS Breakout Setup`, `VCP 3T Breakout` | 蓄積、RS、VCP、ベース突破が重なる初期ブレイクアウト。出来高、終値位置、R/R で chase になっていないかを評価する | 5 営業日 |
| `Early Cycle Recovery Entry` | `Early Cycle Recovery`, `Screening Thesis` | 完全な上昇トレンド確認前の早期回復。構造反転、MA reclaim、出来高、pivot low からの R/R を評価する | 8 営業日 |
| `Power Gap Pullback Entry` | `Power Gap Pullback` | パワーギャップ直後を追わず、初回の整った押し目から再び需要が戻る場面を評価する | 10 営業日 |

## EntrySignal の評価軸

各 EntrySignal は、単に「出た / 出ない」ではなく、次の 3 軸を点数化します。

| 軸 | 意味 |
| --- | --- |
| `Setup Maturity` | セットアップとして十分に熟しているか。押し目の深さ、出来高の乾き、RS の維持、トレンド修復などを見る |
| `Timing` | 今日が入りやすい日か。reclaim、breakout、出来高確認、終値品質、フォロースルーなどを見る |
| `Risk/Reward` | 想定 stop と reward target の比率がよいか。良い形でも R/R が悪ければ総合点は伸びにくい |

最終的な `Entry Strength` は、この 3 軸を signal ごとの重みで合成します。表示 bucket は `Signal Detected`、`Approaching`、`Tracking` に分類されます。

## EntrySignal ごとの実務的な読み方

### Orderly Pullback Entry

`Pullback Trigger` から来た銘柄を対象にします。狙いは、押し目の質があり、21EMA 近辺で出来高が落ち着き、その後の reclaim や終値品質で入れる銘柄です。

ただし、終値が 50SMA を割る、20日高値からの下落が 20% を超える、RS21 が 40 未満になる、50SMA slope が 0 以下になる場合は setup が崩れた扱いになります。

### Pullback Resumption Entry

`Pullback Trigger`、`50SMA Defense`、`Reclaim Trigger` を入口にします。21EMA 押し目だけでなく、50SMA 防衛や reclaim 型も含めた「上昇再開」の候補を評価します。

押し目の深さ、出来高の乾き、RS 維持、トレンド健全性を見たうえで、MA reclaim や pattern trigger が出ているかを確認します。

### Momentum Acceleration Entry

`Momentum Ignition` から来た銘柄を対象にします。モメンタム上位の銘柄に、さらに強い上昇日、PP Count、出来高確認が重なる場面を評価します。

追跡期間は 3 営業日と短く、加速イベントの鮮度を重視します。急落、50SMA 割れ、weekly return rank の低下は無効化要因です。

### Accumulation Breakout Entry

`Accumulation Breakout`、`RS Breakout Setup`、`VCP 3T Breakout` を入口にします。ベース内の蓄積、RS 新高値、VCP 収縮、52週高値圏の品質がそろうブレイクアウト候補です。

EntrySignal 側では、breakout event、volume confirmation、close quality、follow-through を見ます。高値を追いすぎる候補は R/R で抑制されます。

### Early Cycle Recovery Entry

`Early Cycle Recovery` と `Screening Thesis` を入口にします。下降局面からの初期反転、LL-HL 構造変化、pivot trigger、MA reclaim、出来高回復を評価します。

完全なリーダー銘柄だけを拾う signal ではなく、まだトレンド修復の途中にある候補を早めに追跡する設計です。

### Power Gap Pullback Entry

`Power Gap Pullback` から来た銘柄を対象にします。パワーギャップ当日を追うのではなく、その後の初回押し目が秩序的で、reclaim と需要回復が見えるかを評価します。

days since power gap、押し目の整い方、21EMA 近辺の支持、RS 維持、出来高の戻りを見ます。ギャップから時間が経ちすぎた候補や、深く崩れた候補は無効化されます。

## Preset と EntrySignal の対応関係

| Preset | つながる EntrySignal |
| --- | --- |
| `Pullback Trigger` | `Orderly Pullback Entry`, `Pullback Resumption Entry` |
| `50SMA Defense` | `Pullback Resumption Entry` |
| `Reclaim Trigger` | `Pullback Resumption Entry` |
| `Momentum Ignition` | `Momentum Acceleration Entry` |
| `Accumulation Breakout` | `Accumulation Breakout Entry` |
| `RS Breakout Setup` | `Accumulation Breakout Entry` |
| `VCP 3T Breakout` | `Accumulation Breakout Entry` |
| `Early Cycle Recovery` | `Early Cycle Recovery Entry` |
| `Screening Thesis` | `Early Cycle Recovery Entry` |
| `Power Gap Pullback` | `Power Gap Pullback Entry` |

現在無効な Preset は、通常の built-in EntrySignal pool には入りません。custom preset を使う場合は、`EntrySignalRunner` が `load_watchlist_preset_configs()` 経由で解決した preset source を使うため、設定上の source 名と実際の preset 名が一致している必要があります。

## セットアップ分類で見る一覧

| 分類 | 対応する Preset / EntrySignal | どんな銘柄か |
| --- | --- | --- |
| 押し目再開 | `Pullback Trigger`, `50SMA Defense`, `Reclaim Trigger`, `Orderly Pullback Entry`, `Pullback Resumption Entry` | 上昇トレンド内で押してから、21EMA/50SMA/reclaim と出来高確認で再上昇しそうな銘柄 |
| ブレイクアウト | `Accumulation Breakout`, `VCP 3T Breakout`, `RS Breakout Setup`, `Accumulation Breakout Entry` | 蓄積、RS、VCP、52週高値圏、出来高確認が重なり、ベースから出始める銘柄 |
| モメンタム加速 | `Momentum Ignition`, `Momentum Acceleration Entry` | すでに強い銘柄が、さらに上位モメンタムと出来高・価格加速を示す場面 |
| 初期回復 | `Early Cycle Recovery`, `Screening Thesis`, `Early Cycle Recovery Entry` | 下降・調整後に構造反転、MA reclaim、需要回復が出始めた銘柄 |
| パワーギャップ後の押し目 | `Power Gap Pullback`, `Power Gap Pullback Entry` | 大きなギャップアップ後の初回押し目で、追いかけではなく再突入の質を評価する銘柄 |

## まとめ

現在のリポジトリが通常運用で提供する候補は、大きく分けると次の 5 系統です。

1. 押し目再開型
2. 蓄積・VCP・RS ブレイクアウト型
3. モメンタム加速型
4. 初期回復・構造反転型
5. パワーギャップ後の初回押し目型

Preset はこれらの型に合う銘柄を候補化し、EntrySignal はその候補が「今、入れるタイミングに近いか」を点数化します。したがって、このシステムは銘柄を売買まで自動判断するものではなく、セットアップ候補の抽出とエントリー直前の状態評価を提供するものです。
