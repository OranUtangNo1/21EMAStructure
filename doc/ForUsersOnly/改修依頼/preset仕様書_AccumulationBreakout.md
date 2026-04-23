## Accumulation Breakout — Duplicate Rule

```
duplicate_rule.mode: grouped_threshold
required_scans: [VCS 52 High]
optional_groups:
  - group_name: Accumulation Evidence
    scans: [PP Count, Volume Accumulation]
    min_hits: 1
  - group_name: Breakout Trigger
    scans: [Pocket Pivot, 4% bullish]
    min_hits: 1
```

---

### 論理的な意味

```
タイトな構造が52週高値圏で形成されている（VCS 52 High）
  + 蓄積の証拠が存在する（PP Count ≥ 3 or Volume Accumulation）
  + ブレイクアウトイベントが発生した（Pocket Pivot or 4% bullish）
```

---

### Required: VCS 52 High をアンカーにする根拠

VCS 52 Highは3つの条件を同時に課す。VCS ≥ 55がボラティリティ収縮を、RS21 > 25が最低限の相対強度を、dist_from_52w_high ≥ -20%が52週高値からの近接性を保証する。この3条件の同時成立が「レンジブレイクアウトの器（タイトベース）」の存在を確認する。

ここで重要なのは、VCS 52 Highを必須にすることで「蓄積が起きている場所の品質」を先に固定している点。PP Countが3以上でも、構造が緩ければ（VCSが低い、52週高値から遠い）蓄積の意味が弱まる。VCS 52 Highが通過した銘柄でのみ蓄積とブレイクを見ることで、「タイトな器の中で蓄積 → その器を壊す」という一連のストーリーに意味が生まれる。

---

### Group 1: Accumulation Evidence の設計思想

PP CountとVolume Accumulationは、いずれも「ブレイクアウト前の需要蓄積」を測定するが、測定角度が異なる。

PP Count（scan 08）は直近ウィンドウ内でPocket Pivotが3回以上発生したことを要求する。これは「機関買いが1回ではなく繰り返し入っている」ことの証拠。ベース期間中に複数回のPocket Pivotが出ているということは、異なるタイミングで複数の機関がポジションを構築している、あるいは同一の機関が分割して買い増しているということを意味する。

Volume Accumulation（scan 15）はU/D出来高比率 ≥ 1.5 + 相対出来高 ≥ 1.0 + 当日上昇を要求する。これは中期的な買い蓄積パターンを1日のスナップショットで検出する。PP Countが「繰り返しの点」を数えるのに対し、Volume Accumulationは「面」として需給バランスを見る。

min_hits: 1とする理由は、どちらか1つでも「蓄積がある」という判断には十分であり、両方を要求すると候補が極端に減るため。PP Count ≥ 3かつVolume Accumulationの同時ヒットは最も信頼度が高いが、これをmin_hits: 2にすると、Volume Accumulationの当日上昇条件（daily_change_pct > 0）が足枷になる。ベース内の横ばい日にはdaily_change_pctがマイナスの日も多く、PP Count単体で蓄積が十分に証明されるケースを不当に落とすことになる。

---

### Group 2: Breakout Trigger の設計思想

Pocket Pivotと4% bullishは、ともに「ブレイクアウト日」のイベントを検出するが、爆発力の閾値が異なる。

Pocket Pivot（scan 07）はclose > SMA50かつ当日出来高が直近10日間の最大値を超える陽線。出来高の相対比較で「異常な需要日」を検出するため、4%未満の穏やかな上昇でもヒットしうる。VCS 52 Highの銘柄でPocket Pivotが出るということは、タイトなレンジ内で出来高が異常に増加した日であり、機関がレンジブレイクに動いた最初のシグナルとなる。

4% bullish（scan 02）は4%以上の日次上昇 + 相対出来高 ≥ 1.0 + from_open_pct > 0。Pocket Pivotより価格変動の閾値が明示的で厳しい。4%上昇はタイトベース（VCS ≥ 55）からの動きとしては大きく、レンジの上限を突破するケースが多い。

min_hits: 1とする理由は、Pocket Pivotと4% bullishは排他的ではないが、ブレイクアウト日のイベントとしてはどちらか1つで十分だから。Pocket Pivotが出た日に4%以上上昇していれば両方ヒットするが、2-3%の上昇でPocket Pivotだけがヒットするケースも「ブレイクアウトの初動」として有効。両方をmin_hits: 2にすると、穏やかだが出来高に裏付けられたブレイクを不当に除外する。

---

### 3グループ合流の時系列的整合性

このDuplicate Ruleの最大の強みは、3層が暗黙の時系列を持っている点にある。

VCS 52 High → ベース期間中に成立する条件（ボラ収縮は数日-数週間かけて進行する）。
Accumulation Evidence → ベース期間中に蓄積される条件（PP Countはウィンドウ内の累積、Volume Accumulationは中期的な需給比率）。
Breakout Trigger → ブレイクアウト日に発火する条件（Pocket Pivotも4% bullishも1日イベント）。

つまり、Duplicate Tickersに入るためには「ベースが存在する + ベース内で蓄積が起きている + 今日ブレイクイベントが起きた」という時系列が自動的に内蔵される。scan層で時系列を明示的に制約する仕組みはないが、各スキャンの条件特性により、実質的に「蓄積 → ブレイク」の順序が保証される。

---

### 代表的なヒットパターン

**パターン1**：VCS 52 High + PP Count + Pocket Pivot
数週間にわたりPPが3回以上蓄積された後、さらに追加のPPが発火してレンジ上限を突破。「繰り返し買い → 最終的にブレイク」の最もクリーンなパターン。

**パターン2**：VCS 52 High + PP Count + 4% bullish
PP蓄積後に4%以上の大陽線でレンジを一気に突破。ギャップアップでブレイクするケースが多い。Pocket Pivotの出来高条件よりも価格変動の閾値が明示的で、「力強い離脱」を捉える。

**パターン3**：VCS 52 High + Volume Accumulation + Pocket Pivot
U/D出来高比率で中期蓄積を確認し、PPがブレイクイベントを検出。PP Countが3未満でもVolume Accumulationが蓄積を別角度で証明しているパターン。

**パターン4**：VCS 52 High + Volume Accumulation + 4% bullish
U/D需給 + 大陽線ブレイク。PP Countなしでも成立するため、IPO後の若い銘柄（PPの蓄積ウィンドウがまだ短い）でもヒットしうる。