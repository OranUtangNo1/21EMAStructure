# 改善計画と追加機能提案

作成日: 2026-05-29

位置づけ: `01`〜`08` の現行ドキュメントを前提に、短中期限定・米国株専用・ロングオンリー swing という目的に対して、ダッシュボードが「期待値・再現性の高い投資判断」を支援するための改善方針と、追加機能候補をまとめる。改善の論拠は米国市場の一般コンセンサスに限定し、特定地域に限ったアノマリーは用いない。

---

## 1. 前提の確定

会議の最初に、評価と検証の土台を固定する。

- 目的: 短中期限定・米国株・ロングオンリー swing(保有はおおむね 1〜6 週間相当)。
- 主評価 horizon: 21D。補助: 5D / 10D。診断: 63D(中期リーダーシップ持続の確認に限定)。
- トレードの評価単位: EntrySignal が Entry Ready に到達した日。preset hit 起点は入口より数日早く、期待値を過大評価するため主単位にしない。
- 期待値の主指標: R 倍率期待値(自前 SL/TP1 を基準)+ 21D benchmark excess return。
- 根拠の制約: 米国市場/一般コンセンサスのみ。

---

## 2. 改善の中心軸は「地合いゲートの作り込み」

米国の swing / モメンタム運用で最も再現性が確認されている一般則は、ブレイクアウト・モメンタム戦略の成績が地合いに強く依存し、特に下落相場明けの高ボラ局面で momentum crash を起こす、という点である。これは学術側(Daniel–Moskowitz, "Momentum Crashes")と実務側(O'Neil の「市場の方向が最重要、概ね 4 銘柄中 3 は地合いに従う」、Minervini の「確認された上昇局面でのみ攻める」)が一致して支持する。

ここから導かれる結論は明確である。このシステムで期待値に最も効くレバーは、個別 scan の精緻化ではなく、Market Dashboard を「攻守の切替ゲート」として正しく機能させることである。改善はこの軸を中心に置く。

---

## 3. Market Dashboard / ゲートの具体的改善

### 3.1 VIX ペナルティの非線形化

現行 `vix_score = 50 − (VIX − 17) × 5` は線形で、VIX 20 で 35、22 で 25、27 で 0(下限)に達する。VIX と safe_haven で Market Score の 0.30 を占めるため、VIX が高 teens〜低 20 台に乗っただけでゲートが大きく閉じる。米国の一般的な見方では、VIX がリーダー株の重しになるのは概ね持続的な 25〜30 超や急騰局面であり、低 20 台は必ずしも弱気を意味しない。

改善:

- VIX 寄与を区分線形/非線形にし、20 前後までは中立近辺に保ち、stress 帯でだけ強く効かせる。
- slope と閾値は、Market Score バケット別に preset の前向き期待値がどこで崩れるかを実測して決める。
- スポット VIX の水準だけでなく、後述する VIX term structure(7.3)で regime を補強する。

### 3.2 safe_haven の金利耐性

現行 `safe_haven_score = 50 + (SPY 20日 − TLT 20日) × 4`。20 日 SPY−TLT スプレッドは金利主導の局面で誤作動しうる。2022 年型の利上げ局面のように株債同時安だと TLT が大きく下げ、「リスクオン」を過大表示する。株債の逆相関が崩れる局面は米国でも繰り返し起きている。

改善:

- 金利主導局面でこの component が地合い判断を歪めていないかを検証対象にする。
- リスクオン/オフの主軸を、金利の影響を受けにくいクレジット指標(7.3 の HYG/LQD)に寄せる、または併用する。

### 3.3 業種リーダーシップ・ゲートの検証付き拡張

RS Radar が 1W:1M を 2:2 と日次より重くしているのは、短期急騰の一発屋より持続的リーダーを上位に出す設計で、「リーダーは先導業種から出る」という O'Neil 系コンセンサスに沿っており方向は正しい。ただし業種リーダーシップ・ゲート(Industry Leadership Gate)は現状 RS Breakout Setup の annotation だけにかかっている。

改善:

- 業種ゲートを他 preset へ広げる価値があるかは、ゲート有無で preset 期待値が実際に改善するかで判断する(感覚で全 preset に広げない)。

### 3.4 地合い × preset の期待値層別

現行 context guard は Market Score と earnings で Entry Strength を cap するが、その閾値(market score 30/40、breadth 70)は推測値のままである。地合い依存が強い以上、ここは実証で決める。

改善:

- market label × preset の前向き期待値を層別し、(i) どの label 以上で breakout 系を主力にするか、(ii) どの breadth 水準を割ったら breakout を降格して pullback / reclaim 系を相対的に優先するかを、実データで決定する。
- これは新機能ではなく、既存 Analysis の層別を地合い軸で強化するだけで実装できる。

---

## 4. 計測・検証基盤(再現性の核)

ゲートを実証ベースで詰めるには、期待値の測り方そのものを米国の運用検証コンセンサスに揃える必要がある。

- R 倍率で期待値を測る(Van Tharp の expectancy: 勝率 × 平均勝ち R − 負け率 × 平均負け R)。システムは SL/TP1 を持つため、自前 stop を前提にした R が最も再現性が高い。固定 horizon の生リターンは補助に留める。
- MFE/MAE(最大順行・最大逆行)を保存する(Sweeney の Maximum Adverse Excursion)。stop の妥当性と現実的に取れる R を検証できる。平均ではなく分布で見る。
- 評価単位は Entry Ready 到達日に固定する。
- 再現性の担保は walk-forward / out-of-sample(Pardo)で行う。
- point-in-time universe で survivorship を除く。現行 Finviz の 7 日 snapshot は脱落銘柄が消えるため、過去検証が上振れる。
- 9 preset × 多数の閾値を試すことによる data-snooping を抑えるため、最小 N(例: 30 トレード未満は「観察中」固定)と「2 つ以上の regime で成立」を昇格条件にする(White の Reality Check、Bailey–López de Prado の backtest overfitting 警告)。

---

## 5. 既存実装で確認済みの構造的な穴

- Fresh Stage 2 Breakout が EntrySignal に未接続。preset として存在し、主力候補にも挙げられているが、現行 `06` を確認したところ、どの EntrySignal の `preset_sources` にも入っておらず、入口評価の経路がない。主力にするなら Accumulation Breakout Entry の source に加えるか、専用 evaluator を用意する。
- Analysis の forward return が 1D / 5D / 10D / 20D で主軸 21D に届いていない。最低でも 21D、できれば 42D まで延ばす。

---

## 6. scan / preset の整理(役割 × 限界寄与)

scan は役割グループ(Trend/Stage、Leadership、Demand、Pullback/Reclaim、Structure/Base、Momentum)で扱う。整理基準は単独 hit 数ではなく preset 期待値への限界寄与とする。

- 各 preset の optional group から scan を 1 つ外す ablation を行い、期待値(R 倍率・21D excess)が落ちる scan は残し、変わらない scan は annotation に降格する。
- preset は R 期待値でティア分け(主力/条件付き/観察中)し、最小 N と複数 regime 成立を昇格条件にする。直近の強気相場 1 回だけで効いた preset を主力にしない。

---

## 7. 追加機能提案: 市場方向性指標の組み込み

目的は、Market Dashboard の「方向性判断(攻守ゲート)」を、現在使っていない米国コンセンサス指標で補強することである。

### 7.0 選定基準

以下の 3 条件をすべて満たすものに限定した。

- 市場の方向性判断に有用で、米国市場で一般コンセンサスがある。
- 現行システムが活用していない(現行は %above MA、%positive、IWO/IWN、スポット VIX、SPY/TLT、sector/style RS が中心)。
- 現行パイプラインで取得可能(既存 universe の価格データ、または yfinance で取得できる ETF / 指数)。

候補は 3 群に分かれる。7.1 は追加データ不要(既存 universe から算出)、7.2 は指数の価格・出来高から算出、7.3 は数銘柄を追加取得するだけで算出できる。

### 7.1 内部 breadth から新規算出(追加データ不要)

これらは現行が保持する universe(約 2,500 銘柄、3 年分の価格)から計算できる。ただし重要な注意として、古典的 breadth 指標は本来 NYSE 全銘柄で算出され、しきい値もそれを前提に較正されている。本システムの universe は時価総額・出来高・ADR・除外セクターでフィルタ済みのため、しきい値はそのまま流用せず、この universe 上で経験的に再較正するか、z-score などの相対表現で扱う。

**(a) Net New High − New Low(52 週)**

- 内容: universe のうち 52 週新高値を付けた銘柄数 − 新安値を付けた銘柄数。
- 根拠: 新高値が萎む一方で価格指数が高値更新する乖離は、米国で広く使われる古典的な天井警戒シグナル(StockCharts / Worden 系)。
- 現行との差: 現行は銘柄ごとの `dist_from_52w_high` と短期高値系(S5TH)を持つが、universe 全体の NH−NL オシレーターは持たない。
- 接続: 指数の高値更新 vs NH−NL の divergence を「攻め継続 / 警戒」のフラグにする。

**(b) Advance/Decline Line(累積)**

- 内容: 日次の advancers − decliners を累積した線。
- 根拠: A/D ラインと指数の乖離は、参加の細りを捉える定番(Zweig も A/D の有効性を強調)。
- 現行との差: 現行は %positive を持つが累積 A/D ラインと divergence 判定は持たない。
- 接続: SPY 高値更新を A/D ラインが確認しない局面を breadth divergence として警戒側に倒す。

**(c) McClellan Oscillator / Summation Index**

- 内容: ratio-adjusted net advances = ((Adv − Decl) / (Adv + Decl)) × 1000 を作り、その 19 日 EMA − 39 日 EMA を Oscillator とする。累積が Summation Index。
- 根拠: breadth モメンタムとスラスト/divergence の標準指標(McClellan)。universe サイズが変動しても ratio-adjusted 版なら比較可能。
- 現行との差: breadth の「水準」は持つが breadth の「モメンタム」は持たない。
- 接続: ゼロライン超え・スラストを上昇転換の補助確認に、divergence を警戒に使う。

**(d) Zweig Breadth Thrust**

- 内容: A / (A + D) の 10 日 EMA。
- 根拠: Zweig の定義では、この比率が 0.40 未満から 10 営業日以内に 0.615 超へ急騰すると、強い新規上昇の開始シグナルとされる(`Winning on Wall Street`)。発生は稀だが、歴史的に中期の強い上昇に先行した例が多い。
- 現行との差: 現行に thrust 検出はない。下落明けの「攻めへの切替」を早く捉える数少ない指標。
- 接続: 発生時に攻めゲートを引き上げる(breakout 系 preset の優先度を上げる)補助トリガー。発生頻度が低い前提で、単独トリガーにはしない。
- 注意: 0.40 / 0.615 は NYSE 全銘柄前提の閾値。フィルタ済み universe では要再較正。

**(e) % of universe in Stage 2(参加の質)**

- 内容: universe のうち Stage 2 条件を満たす銘柄割合。
- 根拠: 単なる「200 日線上の割合」より厳しい、トレンド参加の質の breadth。本システムは Stage 2 を銘柄単位で既に算出している。
- 現行との差: Stage 2 を集計した market 指標がない。
- 接続: この割合が低下する局面では、たとえ Market label が Positive でも breakout 系を慎重に扱う材料にする。

### 7.2 指数の価格・出来高から算出(SPY / QQQ)

**(f) Follow-Through Day(FTD)**

- 内容: 下落からの反発局面で、初の上昇日(Day 1)を起点に、Day 4 以降に主要指数が前日比で大きく上昇(目安 +1.2% 以上)し、かつ出来高が前日を上回ると、新規上昇トレンドの確認とみなす。Day 1 の安値を割ると反発の試みは無効化。
- 根拠: O'Neil / IBD の市場方向モデルの中核。新しい上昇相場の開始を確認するための定番手法。
- 現行との差: 現行に「下落明けの上昇転換確認」のロジックがない。
- 接続: FTD 成立で攻めゲートを開く(breakout 系 preset を主力に戻す)。Daniel–Moskowitz の momentum crash は下落明けに集中するため、攻めの再開を確認で縛る意義は大きい。
- データ: SPY と QQQ の価格・出来高のみ(QQQ は既存ダッシュボード ETF に含まれる)。

**(g) Distribution Day count**

- 内容: 主要指数が前日比 −0.2% 以上下落し、かつ出来高が前日を上回った日を distribution day とし、直近 25 営業日でカウントする。指数が当該日から +5% 上昇するか 25 日経過で除外。
- 根拠: O'Neil / IBD が institutional の売り(distribution)の蓄積を測る定番。短期間に 5〜6 本のクラスタは天井/調整の警戒サインとされる。
- 現行との差: 現行に index レベルの売り圧蓄積カウントがない(銘柄単位の `ud_volume_ratio` はあるが別物)。
- 接続: クラスタ発生で守りゲートに寄せ、breakout 系の優先度を下げる。FTD と対で「攻守の切替」を構成する。
- データ: SPY / QQQ の価格・出来高のみ。

### 7.3 追加 ETF / 指数の取得で算出

**(h) VIX term structure(VIX / VIX3M)**

- 内容: スポット VIX を VIX3M(3 か月の期待ボラティリティ)で割った比率。1.0 未満は contango(平常/リスクオン)、1.0 超は backwardation(ストレス/リスクオフ)。
- 根拠: CBOE は VIX と VIX3M を公表しており、term structure の形状は vol レジームの速い指標として広くコンセンサスがある。歴史的に契約は約 8 割の期間 contango で、backwardation は急性ストレス局面に対応する。
- 現行との差: 現行はスポット VIX の水準(対 17)だけ。term structure は「水準」より regime を捉える。3.1 の線形ペナルティ問題の補完になる。
- 接続: vix_score を term structure で調整。contango 安定なら攻めを許容、backwardation 転換で守りに寄せる。
- データ: `^VIX3M` を yfinance で追加取得(`^VIX` は既存)。実装コストは小さい。

**(i) Credit spread proxy(HYG / LQD、補助 HYG / IEF)**

- 内容: 高利回り社債 ETF(HYG)を投資適格社債 ETF(LQD)で割った比率。上昇 = HY 優位 = spread 縮小 = リスクオン、低下 = spread 拡大 = リスクオフ。補助として HYG / IEF(国債)を見ると金利要因と分離しやすい。
- 根拠: クレジット市場は株式より先に default リスクを織り込むことが多く、HY スプレッドの拡大は株式ストレスの先行指標として米国で定番(ICE BofA US High Yield OAS が代表)。
- 現行との差: 現行のリスクオン/オフは SPY/TLT(safe haven)と IWO/IWN のみ。クレジットは独立した、かつ金利混入の少ない別軸。3.2 の safe_haven 弱点を補う。
- 接続: リスクオン/オフ判定の主軸または併用。HYG/LQD が低下しつつ SPY が高値更新する乖離は確認の喪失として警戒に倒す。
- データ: HYG / LQD / IEF を yfinance で追加取得。実装コストは小さい。
- 限界: クレジット主導の下落(2007–08、2015–16 のエネルギー)では有効だが、ディスカウントレート・ショック(2022)や純粋なボラ/レバレッジ事象(2020、2024)では空振りしやすい。単独で使わず、VIX term structure と breadth と併用する。

### 7.4 組み込みの優先順位

実装コストと、現行の弱点をどれだけ直接埋めるかで順位付けする。

1. VIX term structure(VIX/VIX3M)と Credit spread(HYG/LQD)。取得が容易で、3.1・3.2 の既知の弱点を直接補う。最優先。
2. Follow-Through Day と Distribution Day count。指数データのみで、Daniel–Moskowitz の「下落明けの危険」を攻守ゲートに直結できる。
3. McClellan / NH−NL / A/D divergence。universe から算出でき、参加の細りを早期に捉える。再較正が必要。
4. Zweig Breadth Thrust と % in Stage 2。稀少だが価値の高い転換シグナルと参加の質。補助トリガー扱い。

### 7.5 共通の実装・検証注意

- いずれもまず「診断フラグ」として Dashboard に追加し、Market Score の重みにすぐ畳み込まない。
- 各指標の状態別に preset の前向き期待値(R 倍率・21D excess)を層別し、実際に判別力がある指標だけを、4 章の検証を通したうえで Market Score の component か context guard か preset 優先度に正式採用する。
- breadth 系は universe フィルタの影響で古典的しきい値が効かないため、この universe 上で較正するか z-score 化する。
- 追加取得銘柄(`^VIX3M`、HYG、LQD、IEF)は既存の data quality / cache 機構に載せ、欠損時は中立扱いにする。

---

## 8. 進め方(フェーズ)

- Phase 0(確定): 1 章の前提を確定。Fresh Stage 2 Breakout を入口評価に乗せるか決定。
- Phase 1(計測): Analysis を EntrySignal の Action Bucket 起点でも集計し、5/10/21D return・MFE/MAE・R 倍率・サンプル数・信頼区間・market label 層別を出力。Analysis horizon を 21D まで延伸。7 章の市場方向性指標を「診断フラグ」として Dashboard に追加。
- Phase 2(検証と剪定): preset を R 期待値でティア分け(最小 N・複数 regime 必須)。preset 内 scan の ablation。VIX 寄与形・safe_haven 金利耐性・context guard 閾値・業種ゲート拡張、および 7 章の各指標の判別力を実証。
- Phase 3(磨き込み): 検証を通ったものだけ入口品質を詰め、感度分析で閾値の頑健性を確認してから凍結。

---

## 9. 会議で確定すること

1. 主軸 horizon を 21D で確定するか。
2. トレード単位を Entry Ready にするか。
3. 期待値の主指標を R 倍率にするか。
4. Fresh Stage 2 Breakout を入口評価に乗せるか。
5. 地合いゲート(VIX 寄与形・safe_haven・context guard 閾値・業種ゲート)を Phase 2 の実証対象として明示するか。
6. 7 章の市場方向性指標のうち、Phase 1 で診断フラグとして先行追加するものを 1〜2 群に絞るか。
