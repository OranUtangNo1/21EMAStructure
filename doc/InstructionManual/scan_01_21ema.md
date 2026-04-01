# Scan 01 — 21EMA scan

## 概要

21EMA Cloud に近接した「押し目」状態にある銘柄をフィルタリングするスキャン。
価格が 21EMA の適切なゾーン内に収まり、50SMA からも過度に乖離していない、
かつ機関投資家的な買いの痕跡（PP Count）と上昇トレンド構造を兼ね備えた銘柄を抽出する。

**ソース:** `src/scan/rules.py` → `_scan_21ema()`

---

## 条件一覧

| # | 条件 | 閾値 | 参照列 | config キー |
|---|------|------|--------|-------------|
| 1 | 週次リターン（下限） | >= 0.0% | `weekly_return` | — |
| 2 | 週次リターン（上限） | <= 15.0% | `weekly_return` | — |
| 3 | DCR%（日中レンジ内終値位置） | > 20.0% | `dcr_percent` | — |
| 4 | ATR 21EMA ゾーン（下限） | >= -0.5 ATR | `atr_21ema_zone` | `atr_21ema_good_min` |
| 5 | ATR 21EMA ゾーン（上限） | <= +1.0 ATR | `atr_21ema_zone` | `atr_21ema_good_max` |
| 6 | ATR 50SMA ゾーン（下限） | >= 0.0 ATR | `atr_50sma_zone` | — |
| 7 | ATR 50SMA ゾーン（上限） | <= +3.0 ATR | `atr_50sma_zone` | `atr_50sma_good_max` |
| 8 | PP Count 30d | > 1 回 | `pp_count_30d` | `pp_count_window_days` |
| 9 | Trend Base | True | `trend_base` | — |

---

## 各条件の計算式

### weekly_return
```python
weekly_return = close.pct_change(5) * 100.0
```
過去 5 営業日（約1週間）の終値変化率。

---

### dcr_percent（Daily Closing Range %）
```python
range_width = (high - low).replace(0, NaN)
dcr_percent = (close - low) / range_width * 100.0
# 分母ゼロの場合は 50.0 で fill
```
当日の高値〜安値レンジに対する終値の相対位置。0% = 安値引け、100% = 高値引け。

---

### atr_21ema_zone
```python
ema21_close = close.ewm(span=21, adjust=False).mean()
atr         = EMA(TrueRange, 14)          # alpha = 1/14
atr_21ema_zone = (close - ema21_close) / atr
```
終値と 21EMA（終値ベース）との距離を ATR 単位で表したもの。
正の値 = 21EMA より上、負の値 = 21EMA より下。

---

### atr_50sma_zone
```python
sma50 = close.rolling(50).mean()
atr_50sma_zone = (close - sma50) / atr
```
終値と 50SMA との距離を ATR 単位で表したもの。

---

### pp_count_30d（Pocket Pivot Count）
```python
# Pocket Pivot の定義（core.py: _calculate_pocket_pivot）
prior_volume_high = volume.rolling(10).max().shift(1)   # 直近10日最大出来高（前日まで）
pocket_pivot      = (close > open) & (volume > prior_volume_high)

# 30営業日内のカウント
pp_count_30d = pocket_pivot.rolling(30).sum().fillna(0).astype(int)
```

---

### trend_base
```python
wma10_weekly = WMA(weekly_close, 10)    # 週足 10期間 WMA
wma30_weekly = WMA(weekly_close, 30)    # 週足 30期間 WMA
trend_base   = (close > sma50) & (wma10_weekly > wma30_weekly)
```

---

## このスキャンでフィルタリングされる特性

### 通過する銘柄の特性

**1. 緩やかな押し目または横ばい週（週次 0〜15%）**
週次リターンに上限（15%）を設けることで、すでに急騰して過熱した銘柄を除外する。
ゼロ以上のフィルタにより、下落トレンドの中の銘柄も除外される。
「今週は上昇でも下落でもなく、適度に落ち着いている」銘柄が通過する。

**2. 当日の終値が強い（DCR% > 20%）**
レンジの下位20%未満で終値を引いた銘柄（弱い引け）を除外する。
中央値（50%）や高値引け（80〜100%）に近い銘柄が通過し、当日の売り圧力が限定的であることを示す。

**3. 21EMA の適切なゾーン内（-0.5R 〜 +1.0R）**
- 下限 -0.5 ATR: 21EMA を ATR 半分以上大きく割り込んだ銘柄を除外する
- 上限 +1.0 ATR: 21EMA から ATR 1本分を超えて大きく乖離した過熱銘柄を除外する

このゾーンは「21EMA Cloud に接触中〜わずかに上」の状態に相当する。
過度に乖離せず、かつ大きく崩れていない、トレードに適した距離感を持つ銘柄が残る。

**4. 50SMA との距離が適切（0〜+3.0R）**
- 下限 0: 50SMA を下回っている銘柄（中期トレンド崩壊）を除外する
- 上限 +3.0 ATR: 50SMA から ATR 3本分を超えて過熱した銘柄を除外する

50SMA の上に位置し、かつ過熱していない「中期トレンドの適正位置」にある銘柄が通過する。

**5. 機関投資家的な買いの痕跡（PP Count > 1）**
過去30日以内に Pocket Pivot（陽線かつ直近10日の最大出来高を超えた日）が2回以上発生している銘柄のみ通過する。
散発的な出来高増加ではなく、継続的な機関投資家の買い集めが示唆される銘柄を選別する。

**6. トレンド構造が健全（Trend Base）**
`close > sma50` かつ `週足10WMA > 週足30WMA` の両方を満たす銘柄のみ通過する。
日足・週足の両時間軸で上昇トレンドが確認できる銘柄に限定される。

### 除外される銘柄の典型パターン

| パターン | 除外される理由 |
|----------|----------------|
| 急騰後の銘柄（週次 +20%〜） | weekly_return > 15% |
| 安値引けの銘柄 | dcr_percent <= 20% |
| 21EMA から大きく乖離した銘柄 | atr_21ema_zone > 1.0 |
| 21EMA を大きく割り込んだ銘柄 | atr_21ema_zone < -0.5 |
| 50SMA 割れの銘柄 | atr_50sma_zone < 0 |
| 50SMA からの過熱銘柄 | atr_50sma_zone > 3.0 |
| PP Count が少ない銘柄 | pp_count_30d <= 1 |
| 50SMA 割れまたは週足 WMA 逆転 | trend_base = False |

---

## 7リストとの対応

このスキャン結果は **List 3: 21EMA Watch** としてそのまま流用される。
21EMA Watch リストの条件は以下のとおり（スキャン条件のサブセット）:
- `close >= ema21_low`
- `ema21_low_pct <= 8.0`
- `atr_21ema_zone` が -0.5 〜 +1.0 の範囲内
