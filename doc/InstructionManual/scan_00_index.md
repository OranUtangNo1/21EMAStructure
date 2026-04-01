# Scan Documentation — Index

各スキャンの詳細定義・計算式・フィルタリング特性を記載したドキュメント一覧。

---

## ファイル一覧

| ファイル | スキャン名 | 一言サマリー |
|----------|-----------|-------------|
| [scan_01_21ema.md](scan_01_21ema.md) | 21EMA scan | 21EMA ゾーン内の押し目 + PP Count + Trend Base |
| [scan_02_4pct_bullish.md](scan_02_4pct_bullish.md) | 4% bullish | 当日 4% 以上上昇 + 出来高 + RS + 引け強し |
| [scan_03_vol_up.md](scan_03_vol_up.md) | Vol Up | 出来高 1.5x 以上 + 当日上昇 |
| [scan_04_momentum97.md](scan_04_momentum97.md) | Momentum 97 | 週次・四半期の両モメンタムがユニバース上位 |
| [scan_05_97club.md](scan_05_97club.md) | 97 Club | Hybrid Score >= 90 + Raw RS21 >= 97 |
| [scan_06_vcs.md](scan_06_vcs.md) | VCS | ボラ・値幅・出来高の収縮スコア >= 60 |
| [scan_07_pocket_pivot.md](scan_07_pocket_pivot.md) | Pocket Pivot | 当日 Pocket Pivot 発生（陽線 + 出来高超過） |
| [scan_08_pp_count.md](scan_08_pp_count.md) | PP Count | 過去 30 日で PP が 4 回以上 |
| [scan_09_weekly20pct.md](scan_09_weekly20pct.md) | Weekly 20%+ Gainers | 週次リターン >= 20% |

---

## スキャンの役割分類

### セットアップ品質系（構造・ゾーン確認）
- **21EMA scan**: 21EMA 近接の押し目構造。ATR ゾーン + DCR + PP Count の複合判定
- **VCS**: ボラティリティ収縮の成熟度。ブレイクアウト前の圧縮状態を定量化

### 当日モメンタム系（当日の動き）
- **4% bullish**: 強い上昇 + 出来高 + RS の三点揃い
- **Vol Up**: 出来高異常を広く検出
- **Pocket Pivot**: 出来高を伴う陽線（機関参入シグナル）の当日発生

### 相対強度・ランク系（他との比較）
- **Momentum 97**: 週次・四半期の両モメンタムがユニバース上位 3% / 15%
- **97 Club**: Hybrid Score（複合）+ Raw RS21 のトップ層

### 蓄積・継続性系（過去のパターン）
- **PP Count**: 過去 30 日の Pocket Pivot 蓄積回数

### 異常値アラート系
- **Weekly 20%+ Gainers**: 週次 20% 超という異常な急騰の検出

---

## 7リストとスキャンの対応

| リスト名 | 対応スキャン |
|----------|-------------|
| List 1: Momentum 97 | Scan 04 Momentum 97（Trend Base 除外） |
| List 2: Volatility Contraction Score | Scan 06 VCS（条件同一） |
| List 3: 21EMA Watch | Scan 01 21EMA（サブセット条件） |
| List 4: 4% Gainers | Scan 02 4% bullish（daily_change_pct >= 4% のみ） |
| List 5: Relative Strength 21 > 63 | 独立条件（rsi21 > rsi63） |
| List 6: Vol Up Gainers | Scan 03 Vol Up（条件同一） |
| List 7: High Est. EPS Growth | 独立条件（eps_growth_rank >= 90） |

---

## 参照ソース

| ファイル | 内容 |
|----------|------|
| `src/scan/rules.py` | 全スキャン・リストルールの実装 |
| `src/indicators/core.py` | 前提指標の計算（ATR ゾーン、PP Count、Trend Base 等） |
| `src/scoring/rs.py` | Raw RS / Hybrid RS の算出 |
| `src/scoring/vcs.py` | VCS の算出 |
| `config/default.yaml` | 全閾値・パラメータのデフォルト値 |
