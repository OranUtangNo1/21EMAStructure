# Scan 04 — Momentum 97

## 概要

短期（週次）と中期（四半期）の両モメンタムがユニバース内のトップ層に位置する銘柄をフィルタリングするスキャン。
単純な価格上昇ではなく、**ユニバース横断のパーセンタイルランク**を使って「他の銘柄より圧倒的に強い」銘柄を選別する。
名称の「97」は週次リターンが上位3%以内（パーセンタイル >= 97）という厳格な基準を指す。

**ソース:** `src/scan/rules.py` → `_scan_momentum_97()`  
**クロスセクショナルランク付与:** `rules.py` → `enrich_with_scan_context()`

---

## 条件一覧

| # | 条件 | 閾値 | 参照列 | config キー |
|---|------|------|--------|-------------|
| 1 | 週次リターン パーセンタイルランク | >= 97.0 | `weekly_return_rank` | `momentum_97_weekly_rank` |
| 2 | 四半期リターン パーセンタイルランク | >= 85.0 | `quarterly_return_rank` | `momentum_97_quarterly_rank` |
| 3 | Trend Base | True | `trend_base` | — |

---

## 各条件の計算式

### weekly_return_rank（週次リターン パーセンタイルランク）
```python
# ステップ1: 各銘柄の週次リターンを計算
weekly_return = close.pct_change(5) * 100.0   # 5営業日変化率

# ステップ2: ユニバース全銘柄の weekly_return に対してパーセンタイルランクを付与
# enrich_with_scan_context() 内で実施
weekly_return_rank = percent_rank(snapshot["weekly_return"])
# percent_rank: rank(method="average", pct=True) * 100  → 0〜100
```

`weekly_return_rank = 97` は、スキャン対象ユニバース（約 1,500 銘柄）の中で
週次リターンが上位 **3%** 以内に入っていることを意味する。

---

### quarterly_return_rank（四半期リターン パーセンタイルランク）
```python
# ステップ1: 63営業日変化率
quarterly_return = close.pct_change(63) * 100.0

# ステップ2: ユニバース内パーセンタイルランク
quarterly_return_rank = percent_rank(snapshot["quarterly_return"])
```

`quarterly_return_rank = 85` は、四半期リターンが上位 **15%** 以内であることを意味する。

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

**1. 今週の動きがユニバース内で突出している（週次ランク >= 97）**
スキャン対象の約 1,500 銘柄のうち、上位 45 銘柄程度（3%）のみが通過する極めて厳格なフィルタ。
単純に「今週 10% 上がった」のではなく、他の 1,455 銘柄と比較して最も強く動いた銘柄を抽出する。

絶対値ではなく相対ランクを使うことで、市場全体が弱い日でも「その中で最も強い銘柄」を特定できる。

**2. 3ヶ月を通じて強い（四半期ランク >= 85）**
週次の急騰だけでなく、中期的に持続的な強さを持つ銘柄であることを確認する。
「今週だけ急騰した一発屋」ではなく、3ヶ月を通じて上位 15% に入る銘柄のみ通過する。

週次 × 四半期の両方を要求することで、**短期モメンタムと中期トレンドの一致**を確認する。

**3. トレンド構造が健全（Trend Base）**
50SMA 超 + 週足 WMA クロス成立により、中期〜長期の上昇トレンドが継続中の銘柄に限定する。
急騰しているが構造が崩れているリバウンド銘柄（50SMA 割れ等）を除外する。

### 除外される銘柄の典型パターン

| パターン | 除外される理由 |
|----------|----------------|
| 今週上昇したが上位 3% 未満 | weekly_return_rank < 97 |
| 週次は強いが過去3ヶ月が弱い | quarterly_return_rank < 85 |
| 急騰したが 50SMA を割れている | trend_base = False |
| 市場全体の上昇に乗っただけの銘柄 | 相対ランクで上位 3% 未満 |

### クロスセクショナルランクの特性

このスキャンの最大の特徴は「絶対値ではなく相対ランク」を使う点にある。

- 相場全体が+3%の日: weekly_return が +3% 程度でも rank = 50（ユニバース中央値）となり通過しない
- 相場全体が-2%の日: weekly_return が +1% でも rank が 97 以上なら通過する

これにより「その週において最も際立って強かった銘柄」を市場環境に関わらず一定数抽出できる。

---

## 7リストとの対応

このスキャン結果は **List 1: Momentum 97** として流用される。  
ただし Trend Base 条件はリスト側では除外されている（weekly_return_rank と quarterly_return_rank のみ）。
