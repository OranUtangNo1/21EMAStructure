# Scan 05 — 97 Club

## 概要

Hybrid Score（複合ランキングスコア）と Raw RS21（短期相対強度）の両方がトップ層にある銘柄をフィルタリングするスキャン。
**価格強度・成長性・業界力を合成した Hybrid Score >= 90** と、**直近 21 日の相対強度 >= 97** を同時に要求する最も選別度の高いスキャン。

9 スキャンの中で唯一 Hybrid Score をスキャン条件として使用する。

**ソース:** `src/scan/rules.py` → `_scan_97_club()`

---

## 条件一覧

| # | 条件 | 閾値 | 参照列 | config キー |
|---|------|------|--------|-------------|
| 1 | Hybrid Score | >= 90.0 | `hybrid_score` | `club_97_hybrid_threshold` |
| 2 | Raw RS21 | >= 97.0 | `raw_rs21`（fallback: `rs21`） | `club_97_rs21_threshold` |
| 3 | Trend Base | True | `trend_base` | — |

---

## 各条件の計算式

### hybrid_score（Hybrid Score）
```python
# 構成要素（すべて 0〜100 のスコア）
rs21   # Raw RS21（21日窓、銘柄自己比較パーセンタイル）
rs63   # Raw RS63（63日窓）
rs126  # Raw RS126（126日窓）
fundamental_score  # EPS成長 + 売上成長 の加重パーセンタイル
industry_score     # 業界内 RS21 平均のパーセンタイル

# 重み: RS(21/63/126) = 1:2:2、ファンダメンタル = 2、業界 = 3
weights = [1.0, 2.0, 2.0, 2.0, 3.0]
values  = [rs21, rs63, rs126, fundamental_score, industry_score]

# NaN は 50.0 で fill（hybrid_missing_value_policy = "fill_neutral_50"）
hybrid_score = weighted_average(values_with_nan_filled, weights)
# 合計重み = 10 → スコアは 0〜100
```

Hybrid Score の内訳表示用エイリアス:
- `H` = `hybrid_score`
- `F` = `fundamental_score`
- `I` = `industry_score`
- `21` = `rs21`, `63` = `rs63`, `126` = `rs126`

---

### raw_rs21（Raw RS — 21日窓）
```python
ratio    = ticker_close / spy_close           # SPY との価格比率
window   = ratio.tail(21)                      # 直近21日
raw_rs21 = percentile_rank(window).iloc[-1]   # 自己比較パーセンタイル（0〜100）
```
銘柄自身の過去 21 日間の ratio 時系列の中で、現在の ratio がどの位置にあるかを示す。
`raw_rs21 = 97` は「直近 21 日の中で現在の対 SPY 比率が上位 3% に位置する」ことを意味する。

---

### trend_base
```python
trend_base = (close > sma50) & (wma10_weekly > wma30_weekly)
```

---

## このスキャンでフィルタリングされる特性

### 通過する銘柄の特性

**1. 複合スコアでもトップ層（Hybrid Score >= 90）**
価格モメンタムだけでなく、ファンダメンタルズ（EPS・売上成長）と業界の強さを組み合わせたスコアで上位10%に入る銘柄を要求する。

- **RS 成分（重み 5/10）**: 21日・63日・126日の自己比較パーセンタイルランク
- **Fundamental 成分（重み 2/10）**: ユニバース内の EPS 成長 + 売上成長パーセンタイル平均
- **Industry 成分（重み 3/10）**: 所属業界の RS21 平均パーセンタイルランク

「価格は強いが業績が伴わない」銘柄や「個別は強いが業界が弱い」銘柄は Hybrid Score が抑制され、通過しにくくなる。

**2. 直近 21 日の自己比較でも圧倒的に強い（Raw RS21 >= 97）**
Hybrid Score は中長期の合成スコアであるため、直近の強さが薄れた銘柄が高スコアを保持しているケースがある。
Raw RS21 >= 97 を追加することで、「今まさに強い」という直近の勢いも確認する。

Raw RS21 の閾値 97 は非常に高く、銘柄自身の過去 21 日間の対 SPY 比率の中で**上位 3% 以内**であることを要求する。

**3. トレンド構造が健全（Trend Base）**
50SMA 超 + 週足 WMA クロス成立により、トレンドが崩れた銘柄を除外する。

### RS の二層構造（このスキャンの重要な設計意図）

97 Club は意図的に **Hybrid RS**（スコアリング・ランキング用）と **Raw RS21**（直近強度フィルタ）の両方を使用している。

| RS の種類 | 使用目的 | 算出方法 |
|-----------|----------|----------|
| Hybrid Score 内の rs21/63/126 | 複合ランキング成分 | 自己比較パーセンタイル（各窓） |
| Raw RS21（スキャン条件） | 直近の強度フィルタ | 自己比較パーセンタイル（21日窓のみ） |

Hybrid Score が高くても Raw RS21 が低い場合（過去は強かったが直近は失速した銘柄）は除外される。

### 除外される銘柄の典型パターン

| パターン | 除外される理由 |
|----------|----------------|
| 価格は強いが業績・業界が弱い | hybrid_score < 90（F・I成分が低い） |
| Hybrid は高いが最近失速した | raw_rs21 < 97 |
| 両スコアが高いが 50SMA 割れ | trend_base = False |
| 直近急騰したが中長期が弱い | hybrid_score < 90（RS63/126が低い） |

---

## 7リストとの対応

97 Club スキャンは 7 リストへの直接流用はない。  
Duplicate Ticker の集計にはスキャン hit として記録される。
