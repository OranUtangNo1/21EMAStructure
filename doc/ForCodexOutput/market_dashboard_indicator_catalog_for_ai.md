# Market Dashboard Indicator Catalog For AI

- 区分: 市況判断
  名前: Market Score
  定義: `sum(component_scores[name] * component_weights[name])`; default weights=`pct_above_sma20:0.12,pct_above_sma50:0.14,pct_above_sma200:0.14,pct_sma50_gt_sma200:0.08,pct_positive_1m:0.09,pct_positive_3m:0.08,pct_2w_high:0.05,safe_haven_score:0.15,vix_score:0.15`
  想定用途: 市場環境の総合判定

- 区分: 市況判断
  名前: Market Label
  定義: `score>=80 Bullish; >=60 Positive; >=40 Neutral; >=20 Negative; else Bearish`
  想定用途: ロング候補確認の強弱判定

- 区分: 市況判断
  名前: Score History
  定義: `score_1d_ago,score_1w_ago,score_1m_ago,score_3m_ago` and matching labels
  想定用途: 市況改善/悪化の時系列判定

- 区分: 市況判断
  名前: Metric Delta
  定義: `current_metric - metric_at_offset`; offsets=`1D:1,1W:5,2W:10,1M:21`
  想定用途: レベルではなく変化量の判定

- 区分: 市況判断
  名前: Component Score
  定義: breadth/participation percent inputs use `clamp(value,0,100)` if `<=50`, else `50+((value-50)/50)*30`; `vix_score` and `safe_haven_score` use dedicated formulas
  想定用途: Market Score構成要素の分解

- 区分: 市況判断
  名前: Performance Overview
  定義: benchmark close return `% YTD,% 1W,% 1M,% 1Y`
  想定用途: 代表指数の期間別パフォーマンス判定

- 区分: 市況判断
  名前: Drawdown Summary
  定義: per index symbol: `DD 252D %=(latest/rolling_high-1)*100`, `T_DD=days_since_rolling_high`, `ROLLING HIGH`, `DRAWDOWN WINDOW DAYS`
  想定用途: 指数の高値回復距離と調整継続期間判定

- 区分: 市況判断
  名前: Index Rally Attempt Day
  定義: latest close above recent low within `rally_low_lookback`; value=`sessions_since_low`, else `0`
  想定用途: 指数の反発試行段階判定

- 区分: 市況判断
  名前: Index FTD Flag
  定義: after minimum rally day, daily gain `>=ftd_min_gain_pct` and volume > previous volume and close > rally low
  想定用途: Follow-through day成立判定

- 区分: 市況判断
  名前: Distribution Day Count
  定義: count in lookback where daily return `<=distribution_decline_pct` and volume > previous volume
  想定用途: 指数売り圧力判定

- 区分: 市況判断
  名前: Under Pressure Flag
  定義: `Distribution Day Count >= distribution_pressure_count`
  想定用途: 指数環境の警戒判定

- 区分: 市況判断
  名前: pct_above_sma10
  定義: 対象ユニバース内で `close>=sma10` の比率
  想定用途: 超短期Breadth判定

- 区分: 市況判断
  名前: pct_above_sma20
  定義: 対象ユニバース内で `close>=sma20` の比率
  想定用途: 短期Breadth判定

- 区分: 市況判断
  名前: pct_above_sma50
  定義: 対象ユニバース内で `close>=sma50` の比率
  想定用途: 中期Breadth判定

- 区分: 市況判断
  名前: pct_above_sma200
  定義: 対象ユニバース内で `close>=sma200` の比率
  想定用途: 長期Breadth判定

- 区分: 市況判断
  名前: pct_sma20_gt_sma50
  定義: 対象ユニバース内で `sma20>=sma50` の比率
  想定用途: 短中期トレンド整合性判定

- 区分: 市況判断
  名前: pct_sma50_gt_sma200
  定義: 対象ユニバース内で `sma50>=sma200` の比率
  想定用途: 中長期トレンド整合性判定

- 区分: 市況判断
  名前: pct_positive_1w
  定義: 対象ユニバース内で5営業日リターンが正の比率
  想定用途: 短期参加率判定

- 区分: 市況判断
  名前: pct_positive_1m
  定義: 対象ユニバース内で21営業日リターンが正の比率
  想定用途: 中期参加率判定

- 区分: 市況判断
  名前: pct_positive_3m
  定義: 対象ユニバース内で63営業日リターンが正の比率
  想定用途: 3カ月参加率判定

- 区分: 市況判断
  名前: pct_positive_1y
  定義: 対象ユニバース内で252営業日リターンが正の比率
  想定用途: 年間参加率判定

- 区分: 市況判断
  名前: pct_positive_ytd
  定義: 対象ユニバース内で年初来リターンが正の比率
  想定用途: 年初来参加率判定

- 区分: 市況判断
  名前: pct_2w_high
  定義: 対象ユニバース内で現在終値が10営業日高値以上の比率
  想定用途: 短期高値参加率判定

- 区分: 市況判断
  名前: A20
  定義: `pct_above_sma20`
  想定用途: Breadth momentum基準値

- 区分: 市況判断
  名前: A20 DELTA
  定義: `pct_above_sma20`の`1D,5D,10D,21D`差分
  想定用途: Breadth改善/悪化速度判定

- 区分: 市況判断
  名前: A20 MOMENTUM FLAG
  定義: `A20 DELTA 10D`絶対値`>=15`なら符号、else `A20 DELTA 5D`絶対値`>=10`なら符号、else `0`
  想定用途: Breadth momentum急変判定

- 区分: 市況判断
  名前: Advance/Decline Internals
  定義: `UNIVERSE COUNT,ADVANCERS,DECLINERS,ADVANCE DECLINE NET,ADVANCE RATIO,AD LINE`
  想定用途: 内部参加の広がり判定

- 区分: 市況判断
  名前: New High/New Low Internals
  定義: `NEW HIGH 52W COUNT,NEW LOW 52W COUNT,NET NEW HIGH LOW,NET NEW HIGH LOW %`
  想定用途: 52週高値/安値の内部強弱判定

- 区分: 市況判断
  名前: STAGE2 %
  定義: 対象ユニバース内で`stage_label=="stage2_candidate"`の比率
  想定用途: Stage 2候補環境判定

- 区分: 市況判断
  名前: McClellan Oscillator
  定義: `advance_ratio`由来のadjusted netに対するEMA19 minus EMA39
  想定用途: 短期Breadth oscillator判定

- 区分: 市況判断
  名前: McClellan Summation
  定義: `McClellan Oscillator`累積値
  想定用途: Breadth trend持続性判定

- 区分: 市況判断
  名前: Zweig Breadth Thrust
  定義: `advance_ratio`のEMA10
  想定用途: Breadth thrust判定

- 区分: 市況判断
  名前: Zweig Thrust Flag
  定義: prior 10D min of Zweig Breadth Thrust `<0.4` and current `>0.615`
  想定用途: 急速な内部改善判定

- 区分: 各セクターや特性
  名前: Market Snapshot PRICE
  定義: configured ETF latest close
  想定用途: Core/External ETF水準確認

- 区分: 各セクターや特性
  名前: Market Snapshot DAY %
  定義: configured ETF latest `daily_change_pct`
  想定用途: Core/External ETF日次強弱判定

- 区分: 各セクターや特性
  名前: Market Snapshot VOL vs 50D %
  定義: `(rel_volume-1)*100`
  想定用途: 出来高の平常比判定

- 区分: 各セクターや特性
  名前: Market Snapshot 21EMA POS
  定義: `close<ema21_low => below 21EMA Low; close>ema21_high => above 21EMA High; else inside 21EMA Cloud`
  想定用途: ETFの21EMA帯位置判定

- 区分: 各セクターや特性
  名前: Factors vs SP500 REL 1W/1M/1Y %
  定義: factor ETF return minus SPY return over `5,21,252` sessions
  想定用途: Growth/Value/Dividend/Size/Momentum相対優位判定

- 区分: 各セクターや特性
  名前: Style Pair REL 1W/1M/3M %
  定義: pair ratio return for `VUG/VTV,MTUM/SPY,VB/MGC,VO/MGC,VYM/SPY` over `5,21,63` sessions
  想定用途: スタイルペア優劣判定

- 区分: 各セクターや特性
  名前: Style Pair ABOVE MA COUNT
  定義: pair ratioが configured MA windows `20,50,200` の何本以上にあるか
  想定用途: スタイル優位の持続性判定

- 区分: 各セクターや特性
  名前: Defensive/Cyclical REL 1W/1M/3M %
  定義: average return of cyclical_growth sectors `(XLC,XLE,XLF,XLI,XLK,XLY)` minus defensive sectors `(XLP,XLU,XLV)`
  想定用途: 景気敏感/成長 vs 防御セクター判定

- 区分: 各セクターや特性
  名前: Sector Relative Strength REL 1W/1M/3M %
  定義: sector ETF return minus benchmark return over `5,21,63` sessions; function exists; current scorer output is not wired
  想定用途: セクター相対優位判定

- 区分: 各セクターや特性
  名前: Sector RS Rank Delta
  定義: current sector `REL 1M %` rank versus 1W/1M ago rank; function exists; current scorer output is not wired
  想定用途: セクターローテーション変化判定

- 区分: センチメント判断
  名前: VIX
  定義: `^VIX` latest close
  想定用途: ボラティリティ水準判定

- 区分: センチメント判断
  名前: vix_score
  定義: `clamp(50 - ((VIX - vix_neutral_level) * vix_score_slope),0,100)`; default `vix_neutral_level=17`, `vix_score_slope=5`
  想定用途: VIXをMarket Score用の好悪スコアへ変換

- 区分: センチメント判断
  名前: SAFE HAVEN %
  定義: `SPY` 20D return minus `TLT` 20D return by default
  想定用途: 株式対安全資産の選好判定

- 区分: センチメント判断
  名前: safe_haven_score
  定義: `clamp(50 + SAFE_HAVEN% * safe_haven_score_scale,0,100)`; default scale=`4`
  想定用途: Safe HavenをMarket Score用の好悪スコアへ変換

- 区分: センチメント判断
  名前: Risk-On Ratio
  定義: `IWO close / IWN close` by default
  想定用途: 小型グロース対小型バリューのリスク選好判定

- 区分: センチメント判断
  名前: Risk-On REL 1W/1M/3M %
  定義: Risk-On Ratio return over `5,21,63` sessions
  想定用途: リスク選好の期間別変化判定

- 区分: センチメント判断
  名前: Risk-On HIGH DIST %
  定義: `Risk-On Ratio / rolling_high(risk_on_ratio_high_window) - 1` times `100`
  想定用途: リスクオン比率の高値距離判定

- 区分: センチメント判断
  名前: Risk-On ABOVE MA COUNT
  定義: Risk-On Ratioが configured MA windows `20,50,200` の何本以上にあるか
  想定用途: リスクオン状態の持続性判定

- 区分: センチメント判断
  名前: VIX/VIX3M RATIO
  定義: `^VIX close / ^VIX3M close`
  想定用途: VIX期間構造判定

- 区分: センチメント判断
  名前: VIX Term Inversion Flag
  定義: `VIX/VIX3M RATIO >= 1`
  想定用途: 期近VIXストレス判定

- 区分: センチメント判断
  名前: VIX9D/VIX RATIO
  定義: `^VIX9D close / ^VIX close`
  想定用途: 超短期VIXストレス判定

- 区分: センチメント判断
  名前: Front Inversion Flag
  定義: `VIX9D/VIX RATIO >= 1`
  想定用途: フロントVIX逆転判定

- 区分: センチメント判断
  名前: Full Backwardation Flag
  定義: `VIX9D >= VIX >= VIX3M`
  想定用途: VIX全面バックワーデーション判定

- 区分: センチメント判断
  名前: HYG/LQD Ratio REL 1W/1M/3M %
  定義: `(HYG/LQD)` ratio return over `5,21,63` sessions
  想定用途: ハイイールド対投資適格の信用リスク選好判定

- 区分: センチメント判断
  名前: HYG/IEF Ratio REL 1W/1M/3M %
  定義: `(HYG/IEF)` ratio return over `5,21,63` sessions
  想定用途: ハイイールド対国債の信用リスク選好判定

- 区分: センチメント判断
  名前: Credit Risk-Off Flag
  定義: `HYG/LQD REL 1W % < 0` and `HYG/IEF REL 1W % < 0`
  想定用途: 信用市場のリスクオフ判定

- 区分: センチメント判断
  名前: HY OAS
  定義: configured high yield OAS series latest close; default `BAMLH0A0HYM2`
  想定用途: 信用スプレッド水準判定

- 区分: センチメント判断
  名前: HY OAS DELTA 5D/21D BPS
  定義: `(current HY OAS - prior HY OAS) * 100` for `5,21` sessions
  想定用途: 信用スプレッド拡大/縮小判定

- 区分: センチメント判断
  名前: HY OAS WIDENING 5D FLAG
  定義: `HY OAS DELTA 5D BPS >= 25`
  想定用途: 急速な信用悪化判定
