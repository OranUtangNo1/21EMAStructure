# [ARCHIVED] Entry, Exit, and Risk Spec

## Archive Notice

This document is archived from the active screening system scope.
It preserves entry evaluation, exit rules, position sizing, and risk management research
for future use in building a separate entry decision system.

The screening system (Today's Watchlist, Market Dashboard, RS Radar) does not use this logic.
Entry evaluation is performed in TradingView using the 21EMA Cockpit, Structure Pivot, VCS, and Position Size Calculator.

---

## 1. 基本方針

エントリー条件は非公開であり、完全再現は不可能。
そのため `my_entry_criteria` を独自設計対象とし、
公開情報をもとに初期仮説を置き、後から改善する。

entry 判定の基盤として使っているフレームは:
**21EMA Cockpit + Structure Pivot + RS / Growth + Risk**

---

## 2. 21EMA 構造

### 2.1 21EMA Low
- `21EMA Low = EMA(low, 21)`
- 役割: initial stop, Phase 1 exit, Final trailing exit, risk distance の基準

### 2.2 21EMA High
- `21EMA High = EMA(high, 21)`
- 役割: 21EMA Cloud の上限, 上昇時の price containment 確認

### 2.3 21EMA Cloud
- `band(EMA21 High, EMA21 Low)`
- 役割: トレンド環境の可視化, Main Chart 側で確認

---

## 3. Core Stats を使った entry 前評価

### 3.1 ADR%
- 良好レンジ: 3.5% 〜 8.0%

### 3.2 ATR 21EMA
- 良好レンジ: -0.5 ATR 〜 +1.0 ATR

### 3.3 ATR 10WMA
- 週足ベースの押し目判定

### 3.4 ATR 50SMA
- <= +3.0 ATR を良好ゾーン

### 3.5 21EMA Low %
- <= 5%: フルエントリー候補
- > 5% and <= 8%: サイズ調整候補
- > 8%: エントリー見送り候補

### 3.6 3-Weeks Tight
- YES なら VCP 的収縮の補強

### 3.7 ATR% from 50SMA
- >= 7 で過熱の補助シグナル

---

## 4. Structure Pivot

### 4.1 強気構造
1. LL（Lowest Low）
2. HL（Higher Low）
3. Pivot Line = LL と HL の間の最も高い High

### 4.2 エントリー上の意味
- HL 構造が完成していること
- Pivot Line を breakout trigger とみなす

### 4.3 Priority Mode
- tightest / longest / shortest

---

## 5. my_entry_criteria 初期仮説

### 5.1 必須候補
- ema21_low_pct <= 8%
- close >= ema21_low
- price is within or above 21EMA cloud
- ATR 21EMA が良好レンジ
- ATR 50SMA が良好レンジ
- close > 50sma
- Higher Low structure がある
- Structure Pivot が形成されている
- RS21 / RS63 が高水準
- Growth / Fundamental が一定水準
- Industry が弱すぎない

### 5.2 優先加点候補
- ema21_low_pct <= 5%
- VCS >= 80
- three_weeks_tight = true
- hybrid_score 高値
- duplicate ticker = true
- volume confirmation = true
- pivot breakout = true

---

## 6. 売却ルール

- Phase 1: 1R 到達前、終値が 21EMA Low を下回ったら撤退
- Phase 2: 1R 到達後、終値が entry price を下回ったら撤退
- Trim: 3R 到達で 33% 利確
- Final TP: 3R 到達後、終値が 21EMA Low を下回ったら撤退
- 補助: ATR% from 50SMA >= 7 で一部利確検討

---

## 7. R の定義

- initial_stop = ema21_low_at_entry
- initial_risk = entry_price - initial_stop
- target_1r = entry_price + initial_risk
- target_3r = entry_price + 3 * initial_risk

---

## 8. Position Sizing

- fixed-% stop mode
- ATR-based stop mode
- 入力: account size, risk per trade %, entry price, stop price
- 出力: position size, max loss amount, stop distance, risk ratio

---

## 9. 今後の設計課題

- 1トレードあたりの許容損失
- 最大同時保有数
- セクター集中上限
- Bearish 時の建玉制限
- earnings 跨ぎルール
- portfolio-level position sizing
- final entry confirmation
- gap 許容条件
