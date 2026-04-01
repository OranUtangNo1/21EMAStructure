# Scan 06 — VCS（Volatility Contraction Score）

## 概要

ボラティリティ・値幅・出来高が短期的に収縮しており、かつ相対強度が一定以上にある銘柄をフィルタリングするスキャン。
「圧縮が成熟した状態にある銘柄」を抽出することで、次のブレイクアウト候補を事前に特定する。

VCS はエントリーシグナルではなく「圧縮状態の成熟度」を数値化した補助スコアであり、単独では買いシグナルにならない。

**ソース:** `src/scan/rules.py` → `_scan_vcs()`  
**VCS 計算:** `src/scoring/vcs.py` → `VCSCalculator.calculate_series()`

---

## 条件一覧

| # | 条件 | 閾値 | 参照列 | config キー |
|---|------|------|--------|-------------|
| 1 | VCS スコア | >= 60.0 | `vcs` | `vcs_min_threshold` |
| 2 | Raw RS21 | > 60.0 | `raw_rs21`（fallback: `rs21`） | — |

---

## 各条件の計算式

### vcs（Volatility Contraction Score）

VCS は以下の 4 成分の合成スコア（0〜100）。

```python
# ---- 1. ボラティリティ成分（満点 40 点）----
returns   = close.pct_change()
short_vol = returns.rolling(len_short).std()      # 短期ボラ（13日）
long_vol  = returns.rolling(len_long).std()       # 長期ボラ（63日）
vol_ratio = (short_vol / long_vol).clip(0, 2)
vol_component = (1.0 - vol_ratio / 2.0) * 40.0
# short_vol << long_vol のとき高得点（圧縮中）
# short_vol == long_vol のとき 20 点
# short_vol >= 2 * long_vol のとき 0 点

# ---- 2. 値幅成分（満点 45 点）----
short_range = ((high - low) / close).rolling(len_short).mean()   # 短期 H/L レンジ率
long_range  = ((high - low) / close).rolling(len_long).mean()    # 長期 H/L レンジ率
range_ratio = (short_range / long_range).clip(0, 2)
range_component = (1.0 - range_ratio / 2.0) * 45.0

# ---- 3. 出来高ボーナス（満点 bonus_max=15 点）----
short_volume = volume.rolling(len_short).mean()   # 短期出来高平均
long_volume  = volume.rolling(len_volume).mean()  # 長期出来高平均（50日）
vol_ratio_v  = (short_volume / long_volume).clip(0, 2)
volume_bonus = (1.0 - vol_ratio_v / 2.0) * bonus_max
# 短期出来高が枯れているほど高得点

# ---- 4. トレンドペナルティ ----
trend_penalty = 15.0 * trend_penalty_weight  if close < sma50  else 0.0
# 50SMA 割れの場合 -15 点

# ---- 合成 ----
vcs = (vol_component + range_component) * min(sensitivity, 2.0) / 2.0
    + volume_bonus
    + 5.0           # ベーススコア
    - trend_penalty
vcs = vcs.clip(0.0, 100.0)
```

デフォルトパラメータ:

| パラメータ | 値 | 内容 |
|-----------|-----|------|
| `len_short` | 13 | 短期窓（営業日） |
| `len_long` | 63 | 長期窓（営業日） |
| `len_volume` | 50 | 出来高長期窓 |
| `sensitivity` | 2.0 | 合成スコアの感度乗数 |
| `trend_penalty_weight` | 1.0 | ペナルティ倍率 |
| `bonus_max` | 15.0 | 出来高ボーナス上限 |

---

### raw_rs21
```python
ratio    = ticker_close / spy_close
window   = ratio.tail(21)
raw_rs21 = percentile_rank(window).iloc[-1]   # 0〜100
```

---

## VCS スコアの満点構造

| 成分 | 満点 | 高得点の条件 |
|------|------|-------------|
| ボラティリティ成分 | 40 点 | 短期ボラが長期ボラの 0% に近い（完全収縮） |
| 値幅成分 | 45 点 | 短期 H/L レンジが長期の 0% に近い（ローソクが詰まっている） |
| 出来高ボーナス | 15 点 | 短期出来高が長期の 0% に近い（出来高が枯れている） |
| ベーススコア | 5 点 | 常時加算 |
| トレンドペナルティ | -15 点 | 50SMA 割れの場合に減点 |
| **合計上限** | **100 点** | clip(0, 100) |

---

## このスキャンでフィルタリングされる特性

### 通過する銘柄の特性

**1. 短期的なボラティリティが収縮している（VCS >= 60）**
直近 13 日間のリターン標準偏差が、過去 63 日間の標準偏差と比べて大きく低下している状態。
価格が一定のレンジ内でタイトに推移しており、「エネルギーが蓄積されている」状態の銘柄が通過する。

**2. 値幅も同様に収縮している**
ローソク足の高値・安値レンジ（H/L ratio）が直近 13 日で短縮している状態。
単なるボラティリティ低下ではなく、ローソク足そのものが詰まっている視覚的な圧縮を確認する。

**3. 出来高も低水準（ボーナス加点）**
出来高が平均より低い状態では VCS にボーナスが加算される。
「価格が動かず出来高も少ない静かな状態」が VCS を高める。
ただし出来高条件は必須ではなく、ボーナス加点の形で反映される。

**4. トレンドが崩れていない（ペナルティ回避）**
50SMA を下回っている場合は 15 点のペナルティが課される。
圧縮中だが 50SMA 割れの銘柄は VCS が抑制され、閾値 60 を超えにくくなる。

**5. 直近の相対強度も維持（Raw RS21 > 60）**
圧縮しながらも対 SPY 比率が自己比較の中央値（50）を上回る状態を要求する。
「ただ横ばいなだけ」ではなく、相対的に强さを維持したまま収縮している銘柄を選別する。

### VCS スコアの目安

| VCS | 解釈 |
|-----|------|
| >= 80 | 強い圧縮状態（優先候補） |
| 60〜79 | 候補として監視 |
| < 60 | 収縮不十分（スキャン通過せず） |

### 除外される銘柄の典型パターン

| パターン | 除外される理由 |
|----------|----------------|
| ボラタイルな動きが続いている銘柄 | vol_component が低く VCS < 60 |
| 50SMA 割れの圧縮銘柄 | trend_penalty により VCS 抑制 |
| 圧縮中だが RS が弱い | raw_rs21 <= 60 |
| 直近急騰後の一時的な落ち着き | long_vol がまだ高いため vol_ratio が高く VCS 低 |

---

## 7リストとの対応

このスキャン結果は **List 2: Volatility Contraction Score** としてそのまま流用される（条件は同一）。
