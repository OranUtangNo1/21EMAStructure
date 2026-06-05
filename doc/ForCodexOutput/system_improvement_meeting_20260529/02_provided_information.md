# 提供している情報

## Watchlist

Watchlist は、scan にヒットした銘柄を候補として表示する画面である。

主な提供情報:

- Ticker、name、sector、industry。
- Hybrid-RS、Fundamental、Industry、RS 系スコア。
- scan hit 数、annotation hit 数、重複 hit 数。
- hit_scans と matched_scan_rules。
- annotation_hits と matched_annotation_filters。
- VCS、52週高値からの距離、52週安値からの距離、3年高値情報。
- Stage 2 quality、stage_label、days_since_stage2_start。
- ud_volume_ratio、Pocket Pivot count、VCP 3T 関連値。
- earnings_in_7d、earnings_today。
- data_quality_label、data_quality_score、data_warning。

Watchlist は、候補を直接買うためのリストではなく、検討対象を絞るための一次出力である。

## Watchlist Presets

Watchlist Preset は、複数 scan と annotation filter を組み合わせて、より意味のある候補群を作る。

active preset は以下の 9 件。

- Reclaim Trigger
- Fresh Stage 2 Breakout
- Accumulation Breakout
- VCP 3T Breakout
- 50SMA Defense
- Power Gap Pullback
- RS Breakout Setup
- Pullback Trigger
- Momentum Ignition

Preset は duplicate rule を使い、必須 scan と補助 scan の組み合わせで候補を成立させる。
単独 scan のノイズを減らすため、Preset 単位の確認が重要である。

## Entry Signal

Entry Signal は、WatchList / Preset duplicate から発生した候補を signal pool に登録し、一定期間にわたり入口評価を行う。

提供される主な情報:

- Signal、Signal Key。
- Action Bucket: Entry Ready、Watch Setup、Needs Review、Avoid / Invalid。
- Display Bucket: Signal Detected、Approaching、Tracking。
- Action Reason、Missing Piece。
- Setup Maturity、Timing、Risk/Reward、Entry Strength。
- Plan Status、Plan Type、Entry Type。
- Entry Price、Current Price、Entry Zone、Max Entry Price。
- Stop Loss、TP1、R/R Current、R/R Ideal。
- SL Quality、SL Source、SL Basis、SL Safety。
- First Detected、Latest Detected、Pool Days、Detection Count。

Entry Ready は、現時点の価格で timing と R/R が entry ready 条件を満たした状態である。
Watch Setup は、setup は形成中だが timing、R/R、価格位置のいずれかが不足している状態である。
Needs Review は、候補として残るが、現行条件では期待値が弱い可能性が高い状態である。

## Market Dashboard

Market Dashboard は、個別候補の期待値を市場環境から補正するための情報を提供する。

主な提供情報:

- Market Score。
- Market label: Bullish、Positive、Neutral、Negative、Bearish 相当の regime。
- Breadth: SMA20、SMA50、SMA200 以上の比率。
- Positive 1M / 3M、2週高値比率。
- VIX score と Safe Haven score。
- Risk-On Ratio: IWO / IWN。
- Sector rotation。
- factor/style: Momentum、Growth、Value、Dividend、Large/Mid/Small。
- market report 用の market document と final report。

Market Score の設定値:

- bullish_threshold: 80.0
- positive_threshold: 60.0
- neutral_threshold: 40.0
- negative_threshold: 20.0
- VIX neutral level: 17.0

## RS Radar

RS Radar は ETF ベースで sector / industry leadership を確認する画面である。

提供される主な列:

- RS
- 1D、1W、1M percentile
- TICKER、NAME、PRICE
- DAY %、WK %、MTH %
- RS DAY%、RS WK%、RS MTH%
- 52W HIGH

RS Radar の overall RS weights は 1D:1、1W:2、1M:2 である。
near high threshold は 0.5% である。
Top movers count は 3 件である。

## Analysis

Analysis は Watchlist Preset の効果を追跡するための画面である。

主な提供情報:

- preset hit の検出履歴。
- forward return: 1D、5D、10D、20D。
- benchmark 比較。
- market environment 別の成績。
- preset 別の hit count、平均リターン、勝率、最大リターン、最小リターン。

この情報は、どの Preset が目的に合うかを会議で検証する中心材料になる。

## Setting

Setting は、tracking store や保存済みデータの診断に使う。

主な目的:

- Tracking DB の状態確認。
- 保存済み run / snapshot の状態確認。
- データ更新やトラッキングの問題検出。

## CSV / 永続出力

システムは以下のような出力を保存する。

- `data_runs/` 配下の run snapshot。
- `data_runs/entry_signals/YYYYMMDD_evaluations.csv`。
- `data_runs/preset_exports/` の preset export。
- `data_runs/market_documents/YYYYMMDD.md` と `.json`。
- `data_runs/market_reports/YYYYMMDD.md`。
- tracking SQLite DB。

保存物は、再現性と後日検証のために重要である。
