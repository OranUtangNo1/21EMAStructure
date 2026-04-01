# Scan 08 — PP Count（3+ Pocket Pivots in 30 Days）

## 概要

過去 30 営業日以内に Pocket Pivot が 3 回以上発生している銘柄をフィルタリングするスキャン。
Pocket Pivot スキャン（当日発生検出）とは異なり、**累積的・継続的な買い集めの蓄積**を確認する。
散発的な出来高急増ではなく、複数回にわたる繰り返しの機関投資家的な参入を検出する。

**ソース:** `src/scan/rules.py` → `_scan_pp_count()`  
**PP Count 算出:** `src/indicators/core.py` → `pp_count_30d`

---

## 条件一覧

| # | 条件 | 閾値 | 参照列 | config キー |
|---|------|------|--------|-------------|
| 1 | PP Count 30d | > 3 回（= 4 回以上） | `pp_count_30d` | `pp_count_window_days` |
| 2 | Trend Base | True | `trend_base` | — |

---

## 各条件の計算式

### pp_count_30d
```python
# ステップ1: 各日の Pocket Pivot フラグ
prior_volume_high = volume.rolling(10).max().shift(1)
pocket_pivot      = (close > open) & (volume > prior_volume_high)

# ステップ2: 直近 30 営業日のカウント
pp_count_30d = pocket_pivot.rolling(30).sum().fillna(0).astype(int)
```

条件の `> 3` は「4 回以上」を意味する（`> 3` → 最小 4）。

---

### trend_base
```python
wma10_weekly = WMA(weekly_close, 10)
wma30_weekly = WMA(weekly_close, 30)
trend_base   = (close > sma50) & (wma10_weekly > wma30_weekly)
```

---

## このスキャンでフィルタリングされる特性

### 通過する銘柄の特性

**1. 過去 30 日間で 4 回以上の Pocket Pivot（> 3）**
直近 1.5 ヶ月の間に、機関投資家的な出来高を伴う陽線が 4 回以上発生していることを要求する。
1〜2 回の発生はノイズとして除外し、複数回にわたる継続的な買いの痕跡を持つ銘柄のみ通過する。

発生頻度の目安:
- 30 営業日に 4 回 = 約 7〜8 日に 1 回のペース
- 30 営業日に 6 回 = 約 5 日に 1 回のペース（週次で発生）

**2. トレンド構造が健全（Trend Base）**
50SMA 超 + 週足 WMA クロス成立により、中期トレンドが維持されている銘柄に限定する。

### Pocket Pivot スキャン（Scan 07）との比較

| 項目 | PP Count（Scan 08） | Pocket Pivot（Scan 07） |
|------|---------------------|------------------------|
| 検出対象 | 過去 30 日の蓄積 | 当日発生 |
| 最小発生回数 | 4 回以上 | 1 回 |
| 追加条件 | Trend Base | close > sma50 |
| 示すもの | 継続的な買い集め | 本日の機関参入シグナル |
| ノイズ耐性 | 高い | 低い |

PP Count は「過去に積み重なった買い集めの質」を評価するのに対し、
Pocket Pivot は「今日まさに発生した一発のシグナル」を検出する。

### 除外される銘柄の典型パターン

| パターン | 除外される理由 |
|----------|----------------|
| PP が 1〜3 回しかない銘柄 | pp_count_30d <= 3 |
| PP が多いが 50SMA 割れ | trend_base = False（close <= sma50） |
| PP が多いが週足 WMA 逆転 | trend_base = False（wma10 <= wma30） |
| 30 日超前に PP が集中している | rolling(30) の窓外は カウントされない |

### 21EMA scan との違い

21EMA scan も `pp_count_30d > 1`（2 回以上）を条件に含むが、PP Count スキャンはより高い閾値（4 回以上）と
Trend Base のみで判定する。21EMA scan が「ゾーン・ DCR・ATR 等の複合条件」であるのに対し、
PP Count は「蓄積された買い集めの量」に特化したシンプルなスキャンである。

---

## 7リストとの対応

PP Count スキャンは 7 リストへの直接流用はない。  
Duplicate Ticker の集計にはスキャン hit として記録される。
