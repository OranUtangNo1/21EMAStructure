# EntrySignal Catalog

この文書は active EntrySignal の検出元、評価軸、数値しきい値をまとめる。
条件は `config/default/entry_signals.yaml` と `src/signals/evaluators/*.py` に基づく。

## 共通構造

EntrySignal は、WatchList Preset duplicate から候補を signal pool に登録する。
その後、pool 内の候補を毎日評価する。

共通出力:

- Setup Maturity
- Timing
- Risk/Reward
- Entry Strength
- Action Bucket
- Entry Plan

Entry Strength は setup、timing、risk/reward の加重平均である。
どれかの軸が min_axis_threshold を下回ると capped_strength で上限がかかる。

## 共通 Context Guard

Context guard は enabled。

共通設定:

- weak_market_score_threshold: 30.0
- cap_below_signal_detected: true
- earnings warning field: earnings_in_7d
- earnings today field: earnings_today

signal 別 weak market threshold:

- orderly_pullback_entry: 30.0
- pullback_resumption_entry: 30.0
- momentum_acceleration_entry: 40.0
- accumulation_breakout_entry: 40.0
- power_gap_pullback_entry: 30.0

Market Score が threshold 未満、または earnings warning / today がある場合、Entry Strength は signal_detected threshold 未満に cap される。

## 共通 Display / Action

Display Bucket:

- Entry Strength が signal_detected 以上: Signal Detected
- Entry Strength が approaching 以上: Approaching
- それ未満: Tracking

Action Bucket:

- Entry Ready: display bucket が Signal Detected で、entry_ready 条件をすべて満たす。
- Watch Setup: setup_maturity と risk_reward が watch_setup 条件を満たす。
- Needs Review: 上記未満、または plan が Poor R/R / Invalid。
- Avoid / Invalid: pool が inactive または invalidated。

## Orderly Pullback Entry

目的: Pullback Trigger から発生した、21EMA reclaim 型の押し目入口を評価する。

検出元:

- preset_sources: Pullback Trigger
- detection_window_days: 10

無効化条件:

- close が sma50 未満。
- drawdown_from_20d_high_pct が 20.0 超。
- rs21 が 40.0 未満。
- sma50_slope_10d_pct が 0.0 以下。

Setup Maturity:

- volume_exhaustion weight 0.30、volume_ma5_to_ma20_ratio は 0.60 で 100、0.80 で 55、1.00 で 0。
- support_convergence weight 0.25、atr_21ema_zone は 0.00 で 100、-0.25 または 0.25 で 95、1.00 で 0。
- pullback_duration weight 0.20、検出後 4から5営業日で 100、10営業日で 10。
- trend_integrity weight 0.15、ema21_slope と sma50_slope の composite。
- rs_resilience weight 0.10、検出時からの rs21 delta が 0 以上で 100、-10 で 50。

Timing:

- ema_reclaim_event weight 0.30。
- volume_confirmation weight 0.25、volume_ratio_20d は 1.30 で 70、1.50 で 90、2.00 で 95。
- close_quality weight 0.20、dcr_percent は 60 で 60、70 で 80、80 で 100。
- micro_structure_breakout weight 0.15。
- demand_footprint weight 0.10。

Risk / Reward:

- stop reference: low_since_detection
- atr_buffer: 0.25
- min_distance_atr: 0.40
- target primary: snapshot_rolling_20d_close_high
- target secondary: high_52w
- R/R scoring: 0.5=5、1.0=25、1.5=50、2.0=70、2.5=85、3.0=95

Entry Strength:

- setup weight 0.25
- timing weight 0.40
- risk/reward weight 0.35
- min_axis_threshold 20
- capped_strength 30

Display / Action:

- signal_detected: 50
- approaching: 35
- Entry Ready: entry_strength 50以上、timing 50以上、risk_reward 50以上、R/R 2.0以上、setup 40以上
- Watch Setup: setup 45以上、risk_reward 30以上

## Pullback Resumption Entry

目的: Pullback Trigger、50SMA Defense、Reclaim Trigger から、押し目再開候補を評価する。

検出元:

- preset_sources: Pullback Trigger、50SMA Defense、Reclaim Trigger
- detection_window_days: 7

無効化条件:

- close が sma50 の 0.97 倍未満。
- drawdown_from_20d_high_pct が 20.0 超。
- rs21 が 40.0 未満。

Setup Maturity:

- pullback_depth_rr_quality weight 0.35。
- volume_dry_up weight 0.25、volume_ma5_to_ma20_ratio は 0.60 で 100、0.80 で 55、1.00 で 0。
- rs_resilience weight 0.20、rs21 は 40 で 0、60 で 55、80 で 100。
- trend_health weight 0.20、sma50_slope_10d_pct は 0.00 で 25、0.10 で 80、0.20 で 100。

Timing:

- pattern_trigger weight 0.30。
- ma_reclaim_event weight 0.25。
- volume_confirmation weight 0.25、rel_volume は 1.30 で 65、1.50 で 85、2.00 で 100。
- demand_footprint weight 0.20。

Risk / Reward:

- stop reference: depth_adaptive
- atr_buffer: 0.50
- min_distance_atr: 0.50
- target primary: snapshot_rolling_20d_close_high
- target secondary: high_52w

Entry Strength:

- setup weight 0.35
- timing weight 0.40
- risk/reward weight 0.25
- min_axis_threshold 15
- capped_strength 30

Display / Action:

- signal_detected: 48
- approaching: 32
- Entry Ready: entry_strength 48以上、timing 48以上、risk_reward 48以上、R/R 1.8以上、setup 40以上
- Watch Setup: setup 45以上、risk_reward 30以上

## Momentum Acceleration Entry

目的: Momentum Ignition から発生した、強い momentum の加速日を評価する。

検出元:

- preset_sources: Momentum Ignition
- detection_window_days: 3

無効化条件:

- daily_change_pct が -4.0 未満。
- close が sma50 未満。
- weekly_return_rank が 80.0 未満。

Setup Maturity:

- vcs_quality weight 0.40、vcs は 55 で 55、65 で 80、75 で 100。
- pp_density weight 0.30、pp_count_window は 1 で 35、2 で 70、3 で 100。
- momentum_rank weight 0.30、weekly_return_rank は 80 で 20、90 で 55、97 で 100。

Timing:

- acceleration_event weight 0.35。
- volume_confirmation weight 0.30、rel_volume は 1.50 で 75、2.00 で 100、5.00 で 65。
- close_quality weight 0.20、dcr_percent は 60 で 60、70 で 80、80 で 100。
- follow_through weight 0.15。

Acceleration event score:

- daily_change_pct 4.0以上かつ rel_volume 1.0以上なら 100。
- daily_change_pct 4.0以上、または 4% bullish hit なら 80。
- pp_count_window 3以上、または PP Count hit なら 75。
- Momentum 97 hit のみなら 35。

Risk / Reward:

- stop reference: acceleration_day_low
- atr_buffer: 0.25
- min_distance_atr: 0.25
- target primary: rolling_20d_close_high
- target secondary: high_52w
- risk_in_atr が 2.0 超なら risk_reward score は最大 35。

Entry Strength:

- setup weight 0.20
- timing weight 0.45
- risk/reward weight 0.35
- min_axis_threshold 20
- capped_strength 30

Display / Action:

- signal_detected: 55
- approaching: 40
- Entry Ready: entry_strength 55以上、timing 55以上、risk_reward 45以上、R/R 1.8以上、setup 35以上
- Watch Setup: setup 50以上、risk_reward 25以上

Guard:

- rel_volume が 5.0 以上なら climax_warning。
- dist_from_52w_high が -1.0 以上、かつ daily_change_pct が 6.0 以上なら climax_warning。
- pool 初日で dcr_percent が 50.0 未満なら climax_warning。

## Accumulation Breakout Entry

目的: Accumulation Breakout、RS Breakout Setup、VCP 3T Breakout から、蓄積後の breakout を評価する。

検出元:

- preset_sources: Accumulation Breakout、RS Breakout Setup、VCP 3T Breakout
- detection_window_days: 5

無効化条件:

- close が sma50 未満。
- rs21 が 45.0 未満。
- weekly_return_rank が 70.0 未満。
- daily_change_pct が -5.0 未満。

Setup Maturity:

- vcs_quality weight 0.25、vcs は 55 で 55、65 で 80、75 で 100。
- rs_leadership weight 0.25、rs21、weekly_return_rank、quarterly_return_rank の composite。
- accumulation_quality weight 0.20、Pocket Pivot、pp_count_window、Volume Accumulation を加点。
- base_tightness weight 0.15、vcs、drawdown_from_20d_high_pct、ema21_cloud_width、three_weeks_tight を評価。
- resistance_context weight 0.15、close の resistance clearance、resistance_test_count、breakout_body_ratio を評価。

Timing:

- breakout_event weight 0.35。
- volume_confirmation weight 0.25、rel_volume は 1.30 で 65、1.50 で 85、2.50 で 100、5.00 で 70。
- close_quality weight 0.20、dcr_percent は 60 で 60、70 で 80、80 で 100。
- follow_through weight 0.20。

Breakout event score:

- close が breakout reference から 0.0% 以上 3.0% 以下なら 100。
- 3.0% 超 6.0% 以下なら 75。
- -1.0% 以上 0.0% 未満なら 55。
- reference 不明で RS New High または VCS 52 High hit なら 70。

Risk / Reward:

- stop reference: breakout_adaptive
- atr_buffer: 0.25
- min_distance_atr: 0.50
- target primary: high_52w
- target secondary: measured_move
- risk_in_atr が 2.0 超なら risk_reward score は最大 35。
- reward_in_atr が 1.5 未満なら risk_reward score は最大 25。

Entry Strength:

- setup weight 0.30
- timing weight 0.35
- risk/reward weight 0.35
- min_axis_threshold 20
- capped_strength 30

Display / Action:

- signal_detected: 55
- approaching: 38
- Entry Ready: entry_strength 55以上、timing 50以上、risk_reward 50以上、R/R 1.8以上、setup 45以上
- Watch Setup: setup 50以上、risk_reward 35以上

Guard:

- close が detection 時 snapshot low 未満なら breakout_failure。
- R/R が 1.5 未満なら risk_cap_reason。
- rel_volume 5.0以上かつ daily_change_pct 6.0以上なら climax_warning。
- dist_from_52w_high が -1.0以上かつ daily_change_pct 6.0以上なら climax_warning。
- dcr_percent が 50.0 未満なら low_dcr_warning。

## Power Gap Pullback Entry

目的: Power Gap 後の初回整理を待ち、reclaim と需要再流入を評価する。

検出元:

- preset_sources: Power Gap Pullback
- detection_window_days: 10

無効化条件:

- close が sma50 未満。
- drawdown_from_20d_high_pct が 18.0 超。
- rs21 が 45.0 未満。
- days_since_power_gap が 20.0 超。
- daily_change_pct が -5.0 未満。

Setup Maturity:

- gap_quality weight 0.25、power_gap_up_pct、rel_volume、dcr_percent を評価。
- pullback_orderliness weight 0.30、volume_ma5_to_ma20_ratio、drawdown_from_20d_high_pct、atr_21ema_zone を評価。
- support_proximity weight 0.20、atr_low_to_ema21_high、atr_low_to_ema21_low、ema21_low_pct を評価。
- rs_resilience weight 0.15、rs21 と weekly_return_rank を評価。
- accumulation_return weight 0.10、Pocket Pivot、Volume Accumulation、pp_count_window を評価。

Timing:

- reclaim_trigger weight 0.35。
- volume_reentry weight 0.25。
- close_quality weight 0.20、dcr_percent は 65 で 75、80 で 100。
- pullback_age weight 0.20、days_since_power_gap は 3 で 80、5から12で 100、20で 20。

Risk / Reward:

- stop reference: power_gap_pullback_adaptive
- atr_buffer: 0.25
- min_distance_atr: 0.50
- target primary: rolling_20d_close_high
- target secondary: high_52w
- risk_in_atr が 2.0 超なら risk_reward score は最大 30。

Entry Strength:

- setup weight 0.35
- timing weight 0.35
- risk/reward weight 0.30
- min_axis_threshold 18
- capped_strength 30

Display / Action:

- signal_detected: 52
- approaching: 35
- Entry Ready: entry_strength 52以上、timing 50以上、risk_reward 50以上、R/R 1.5以上、setup 45以上
- Watch Setup: setup 45以上、risk_reward 35以上

Guard:

- days_since_power_gap が 1.0 以下なら gap_chase_warning。
- close が low_since_detection 未満なら gap_failure。
- drawdown_from_20d_high_pct が 18.0 超なら gap_failure。
- R/R が 1.5 未満なら risk_cap_reason。
- rel_volume 5.0以上かつ daily_change_pct 6.0以上なら climax_warning。
- dcr_percent が 50.0 未満なら low_dcr_warning。

## Entry Plan 共通判定

Plan Type:

- Ready Now: current R/R が signal の min R/R 以上で、Action Bucket が Entry Ready。
- Wait Trigger: current R/R は足りているが、Action Bucket が Watch Setup または Needs Review。
- Wait Pullback: ideal R/R は min R/R 以上で、entry zone までの距離が 7.5% 以下。
- Poor R/R: R/R が不足、または entry zone が遠すぎる。
- Invalid: stop、target、entry、ATR、support quality に hard reject がある。

Hard reject:

- entry_or_atr_unavailable
- inactive_pool
- sl_unavailable
- tp1_unavailable
- sl_not_below_entry
- tp1_not_above_entry
- sl_too_wide
- sl_quality_weak

EntrySignal は entry plan を出すが、これは実注文指示ではない。
目的は、候補の入口品質を再現性のある形で評価することである。
