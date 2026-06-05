# Watchlist Presets と Annotation Filters

## Watchlist Preset の役割

Watchlist Preset は、複数 scan の組み合わせと annotation filter を使って、候補群を目的別に作る仕組みである。

scan 単体はノイズを含む。
Preset は「必須条件」と「補助確認」を分けることで、より期待値の高い候補に近づける。

## Duplicate Rule

duplicate rule は、候補を Preset 内で成立させるためのルールである。

mode は 3 種類。

- `min_count`: 指定 scan の hit 数が min_count 以上。
- `required_plus_optional_min`: required_scans をすべて満たし、optional_scans のうち optional_min_hits 以上を満たす。
- `grouped_threshold`: required_scans を満たし、optional_groups ごとの min_hits を満たす。

## Active Presets

### Reclaim Trigger

目的: 21EMA reclaim と Pocket Pivot を組み合わせた押し目再浮上。

条件:

- required: Reclaim scan
- optional: Pocket Pivot から 1 hit
- annotation: Stage 2 Quality Score、Mature / Late Stage Risk Filter

### Fresh Stage 2 Breakout

目的: Stage 2 初期の breakout と leadership を捕まえる。

条件:

- required: Fresh Stage 2 Breakout
- Leadership Confirmation: RS Leads Price Setup または VCS 52 High から 1 hit
- Demand Confirmation: Pocket Pivot または Volume Accumulation から 1 hit
- annotation: Stage 2 Quality Score、Mature / Late Stage Risk Filter

### Accumulation Breakout

目的: VCS 52 High を中心に、蓄積と breakout trigger を確認する。

条件:

- required: VCS 52 High
- Accumulation Evidence: PP Count または Volume Accumulation から 1 hit
- Breakout Trigger: Pocket Pivot、4% bullish、VCP 3T から 1 hit
- annotation: Stage 2 Quality Score、Mature / Late Stage Risk Filter

### VCP 3T Breakout

目的: 3段階の収縮からの breakout を leadership と需要で確認する。

条件:

- required: VCP 3T
- Leadership / High Tightness: VCS 52 High、RS New High、RS 3Y New High、RS Leads Price Setup から 1 hit
- Demand Confirmation: Pocket Pivot または Volume Accumulation から 1 hit
- annotation: Stage 2 Quality Score、Mature / Late Stage Risk Filter

### 50SMA Defense

目的: 50SMA を守った押し目からの再浮上。

条件:

- required: 50SMA Reclaim
- Pullback Quality: Pullback Quality scan から 1 hit
- Demand Confirmation: Volume Accumulation または Pocket Pivot から 1 hit
- annotation: Stage 2 Quality Score、Mature / Late Stage Risk Filter

### Power Gap Pullback

目的: Power Gap 後の初回整理からの再エントリー候補。

条件:

- required: Pullback Quality scan
- Reentry Trigger: 21EMA Pattern H、21EMA Pattern L、Reclaim scan から 1 hit
- Demand Confirmation: Volume Accumulation または Pocket Pivot から 1 hit
- annotation: Recent Power Gap、Stage 2 Quality Score、Mature / Late Stage Risk Filter

### RS Breakout Setup

目的: RS leadership と breakout event を重ねた候補。

条件:

- required: VCS 52 High
- RS Leadership: RS New High、RS 3Y New High、RS Leads Price Setup から 1 hit
- Breakout Event: Pocket Pivot、4% bullish、PP Count から 1 hit
- annotation: Stage 2 Quality Score、Mature / Late Stage Risk Filter、Industry Leadership Gate

### Pullback Trigger

目的: 良い押し目の中で pattern trigger と需要を確認する。

条件:

- required: Pullback Quality scan
- Pattern Trigger: 21EMA Pattern H または 21EMA Pattern L から 1 hit
- Demand Confirmation: Volume Accumulation または Pocket Pivot から 1 hit
- annotation: Stage 2 Quality Score、Mature / Late Stage Risk Filter

### Momentum Ignition

目的: Momentum 97 の強い銘柄に加速イベントと構造品質を重ねる。

条件:

- required: Momentum 97
- Acceleration Event: 4% bullish または PP Count から 1 hit
- Quality Structure: VCS 52 High または Volume Accumulation から 1 hit
- annotation: Stage 2 Quality Score、Mature / Late Stage Risk Filter

## Annotation Filters

### RS 21 >= 63

raw_rs21 または rs21 が 63.0 以上。

### High Est. EPS Growth

eps_growth_rank が 90.0 以上。

### PP Count (20d)

pp_count_window が 2 以上。

### Trend Base

trend_base が true。

### Stage 2 Confirmed

stage_label が `stage2_candidate`。
trend_template_price_score が 5 以上。
rs21 が 60 以上。

### Stage 2 Quality Score

Stage 2 Confirmed を満たす。
stage2_quality_score が 75.0 以上。
stage2_quality_score がない場合は価格スコア、RS、長期MA slope、52週位置、出来高需要から計算する。

### Trend Template

trend_template_price_score が 7 以上。
rs21 が 70 以上。

### Mature / Late Stage Risk Filter

Stage 2 Confirmed を満たす。
以下に該当しないこと。

- stage_label が stage4_avoid。
- atr_pct_from_50sma が 7.0 超。
- dist_from_52w_low が 250.0 超。
- days_since_stage2_start が 252 超、かつ dist_from_52w_low が 150 超。

### Industry Leadership Gate

industry_score が 70.0 以上。

### Stage 4 Avoid

stage_label が `stage4_avoid`。

### Fund Score > 70

fundamental_score が 70.0 以上。

### Resistance Tests >= 2

resistance_test_count が 2.0 以上。

### Recent Power Gap

power_gap_up_pct が 10.0 以上。
days_since_power_gap が 20 以下。
