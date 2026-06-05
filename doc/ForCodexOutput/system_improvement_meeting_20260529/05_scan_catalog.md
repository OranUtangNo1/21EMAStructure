# Scan Catalog

この文書は、現行 active scan の目的と具体的な検出条件をまとめる。
条件は `src/scan/rules.py` と `config/default/scan.yaml` に基づく。

## Active Scan 一覧

現行で enabled な scan:

- 21EMA scan
- 21EMA Pattern H
- 21EMA Pattern L
- Pullback Quality scan
- Reclaim scan
- 4% bullish
- Volume Accumulation
- Momentum 97
- VCS 52 High
- Pocket Pivot
- PP Count
- Weekly 20% plus gainers
- VCP 3T
- 50SMA Reclaim
- LL-HL Structure 1st Pivot
- LL-HL Structure 2nd Pivot
- LL-HL Structure Trend Line Break
- RS New High
- RS 3Y New High
- RS Leads Price Setup
- Trend Template
- Fresh Stage 2 Breakout

## 21EMA scan

概要: 21EMA 付近にある通常の押し目候補。

検出条件:

- weekly_return が 0.0 以上 15.0 以下。
- dcr_percent が 20.0 超。
- atr_21ema_zone が -0.5 以上 1.0 以下。
- atr_50sma_zone が 0.0 以上 3.0 以下。

## 21EMA Pattern H

概要: 21EMA high 側を使った短期 pattern breakout。

検出条件:

- atr_50sma_zone が 0.0 以上 3.0 以下。
- atr_21ema_zone が 0.3 以上 1.0 以下。
- atr_low_to_ema21_high が -0.2 以上。
- high が prev_high を上回る。

## 21EMA Pattern L

概要: 21EMA low 側を使った押し目からの切り返し。

検出条件:

- atr_50sma_zone が 0.0 以上 3.0 以下。
- atr_21ema_zone が -0.5 以上 -0.1 以下。
- atr_low_to_ema21_low が 0.0 未満。
- atr_21emaL_zone が 0.0 超。
- high が prev_high を上回る。

## Pullback Quality scan

概要: 上昇トレンド内の静かな押し目。

検出条件:

- ema21_slope_5d_pct が 0.0 超。
- sma50_slope_10d_pct が 0.0 超。
- atr_21ema_zone が -1.25 以上 0.25 以下。
- atr_50sma_zone が 0.75 以上 3.5 以下。
- weekly_return が -8.0 以上 3.0 以下。
- dcr_percent が 50.0 以上。
- drawdown_from_20d_high_pct が 3.0 以上 15.0 以下。
- volume_ma5_to_ma20_ratio が 0.85 以下。

## Reclaim scan

概要: 21EMA 付近から再び上に戻る reclaim。

検出条件:

- ema21_slope_5d_pct が 0.0 超。
- sma50_slope_10d_pct が 0.0 超。
- atr_21ema_zone が 0.0 以上 1.0 以下。
- atr_50sma_zone が 0.75 以上 4.0 以下。
- weekly_return が -3.0 以上 10.0 以下。
- dcr_percent が 60.0 以上。
- drawdown_from_20d_high_pct が 2.0 以上 12.0 以下。
- volume_ratio_20d が 1.10 以上。
- close_crossed_above_ema21 が true。
- min_atr_21ema_zone_5d が -0.25 以下。

## 4% bullish

概要: 1日で強い陽線と出来高を伴う加速。

検出条件:

- rel_volume が 1.0 以上。
- daily_change_pct が 4.0 以上。
- from_open_pct が 0.0 超。

## Volume Accumulation

概要: 上昇日の出来高需要が強い候補。

検出条件:

- ud_volume_ratio が 1.5 以上。
- rel_volume が 1.0 以上。
- daily_change_pct が 0.0 超。

## Momentum 97

概要: 週次と四半期の相対パフォーマンスが非常に強い候補。

検出条件:

- weekly_return_rank が 97.0 以上。
- quarterly_return_rank が 85.0 以上。

## VCS 52 High

概要: VCS が高く、52週高値に近い強い構造候補。

検出条件:

- vcs が 55.0 以上。
- raw_rs21 または rs21 が 25.0 超。
- dist_from_52w_high が -20.0 以上。

## Pocket Pivot

概要: 直近 20日 window 内で pocket pivot が存在する候補。

検出条件:

- pp_count_window が 1 以上。

## PP Count

概要: pocket pivot が複数回出ている蓄積候補。

検出条件:

- pp_count_window が 3 以上。

## Weekly 20% plus gainers

概要: 週次で大きく上昇している候補。

検出条件:

- weekly_return が 20.0 以上。

## VCP 3T

概要: 3段階の収縮と breakout を持つ VCP 候補。

検出条件:

- vcp_prior_uptrend_pct が 30.0 以上。
- vcp_t1_depth_pct が 10.0 以上。
- vcp_t2_depth_pct が vcp_t1_depth_pct の 0.85 倍未満。
- vcp_t3_depth_pct が vcp_t2_depth_pct の 0.75 倍未満。
- vcp_t3_depth_pct が 7.0 以下。
- vcp_tight_days が 3 以上。
- vcp_volume_dryup_ratio が 0.8 以下。
- vcp_pivot_breakout が true。
- vcp_pivot_proximity_pct が 0.0 以上 5.0 以下。
- volume_ratio_20d が 1.0 以上。
- dcr_percent が 55.0 以上。
- rs21 が 60.0 以上。

## 50SMA Reclaim

概要: 50SMA を割り込んだ後に再び上へ戻る防衛型候補。

検出条件:

- sma50_slope_10d_pct が 0.0 超。
- atr_50sma_zone が 0.0 以上 1.0 以下。
- close_crossed_above_sma50 が true。
- min_atr_50sma_zone_5d が -0.25 以下。
- dcr_percent が 60.0 以上。
- volume_ratio_20d が 1.10 以上。
- drawdown_from_20d_high_pct が 3.0 以上 20.0 以下。

## LL-HL Structure 1st Pivot

概要: long structure pivot の初回 break。

検出条件:

- rs21 が 60.0 以上。
- structure_pivot_1st_break が true。

## LL-HL Structure 2nd Pivot

概要: long structure pivot の 2回目 break。

検出条件:

- rs21 が 60.0 以上。
- structure_pivot_2nd_break が true。

## LL-HL Structure Trend Line Break

概要: counter trend line break。

検出条件:

- ct_trendline_break が true。

## RS New High

概要: RS ratio が 52週高値を更新し、価格がまだ高値から適度に離れている候補。

検出条件:

- rs_ratio_at_52w_high が true。
- dist_from_52w_high が -30.0 以上 -5.0 以下。

## RS 3Y New High

概要: RS ratio が 3年高値を更新し、価格がまだ高値から適度に離れている候補。

検出条件:

- rs_ratio_at_3y_high が true。
- dist_from_52w_high が -35.0 以上 -5.0 以下。

## RS Leads Price Setup

概要: RS が先に高値更新し、価格がまだ追いつき切っていない setup。

検出条件:

- Stage 2 Confirmed を満たす。
- Mature / Late Stage Risk Filter を満たす。
- rs21 が 75.0 以上。
- stage2_quality_score が 70.0 以上。
- rs_ratio_at_52w_high または rs_ratio_at_3y_high が true。
- dist_from_52w_high が -30.0 以上 -3.0 以下。

## Trend Template

概要: Minervini 型の価格 trend template と RS を満たす候補。

検出条件:

- trend_template_price_score が 7 以上。
- rs21 が 70.0 以上。

## Fresh Stage 2 Breakout

概要: Stage 2 開始直後の fresh breakout 候補。

検出条件:

- Stage 2 Confirmed を満たす。
- Mature / Late Stage Risk Filter を満たす。
- days_since_stage2_start が 0.0 以上 21 以下。
- stage_base_days_3m が 20 以上。
- rs21 が 70.0 以上。
- close が sma50 を上回る。
- 次のいずれかを満たす: vcp_pivot_breakout、structure_pivot_long_breakout_first_day、dist_from_52w_high が -5.0 以上。
- volume_ratio_20d が 1.2 以上。
- dcr_percent が 60.0 以上。
