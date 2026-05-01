# Entry Signal 設計一覧 — Preset Coverage Map

## preset → entry signal マッピング

| Enabled Preset | Entry Signal | Trade Thesis |
|---|---|---|
| `Power Gap Pullback` | **Gap Reentry Entry** | catalyst gap の構造を R/R に変換 |
| `RS Breakout Setup` | **RS Lead Breakout Entry** | RS-price divergence の解消に賭ける |
| `Accumulation Breakout` | **RS Lead Breakout Entry** | accumulation + breakout trigger |
| `Pullback Trigger` | **Pullback Resumption Entry** | 浅い pullback からの 21EMA 反転 |
| `50SMA Defense` | **Pullback Resumption Entry** | 深い pullback からの 50SMA reclaim |
| `Reclaim Trigger` | **Pullback Resumption Entry** | 中間深度の pullback からの reclaim |
| `Screening Thesis` | **Recovery Breakout Entry** | LL-HL 構造転換 + structure break |
| `Early Cycle Recovery` | **Recovery Breakout Entry** | dead cross 下での PP ベース recovery |
| `Momentum Ignition` | **Momentum Acceleration Entry** | top 3% momentum の二階微分 |

## 設計思想の比較

| Entry Signal | 最重視軸 | detection_window | SL の性質 | R/R の源泉 |
|---|---|---|---|---|
| Gap Reentry | timing (0.40) | 10 日 | gap low（構造的） | gap の値幅が R/R を自動的に定義 |
| RS Lead Breakout | timing (0.40) | 7 日 | contraction low | RS-price 乖離が潜在エネルギー |
| Pullback Resumption | timing (0.40) | 7 日 | 深度に応じて適応 | pullback が深いほど R/R が良い |
| Recovery Breakout | maturity (0.40) | 14 日 | break 段階に応じて適応 | 1st break が最良 R/R |
| Momentum Acceleration | timing (0.50) | 3 日 | acceleration day low | 短期 continuation + trailing |

## 各 signal の創造的要素

### Gap Reentry Entry
- **gap low / gap high を機械的 SL/TP に使用**。裁量ゼロの R/R 設定が可能な唯一のセットアップ

### RS Lead Breakout Entry
- **RS-Price 乖離スコア**（M2）: RS が新高値 + 価格が離れている = 「バネの圧縮」。乖離が -10%〜-20% で最大スコア

### Pullback Resumption Entry
- **Pullback 深度 R/R マッピング**（M1）: 深い pullback ほど高スコア。50SMA Defense 経由が自動的に最高位。直感に反するが、R/R は構造的に深い pullback が優位

### Recovery Breakout Entry
- **1st break 最重視**: 2nd break（確認）ではなく 1st break（0.618）を最高評価。R/R が最良のタイミングで機械的にエントリする

### Momentum Acceleration Entry
- **timing 0.50（最大重み）**: momentum play はタイミングが全て。加えて **climax 対策フラグ** を固有に持つ（異常出来高、新高値圏での大幅上昇、intraday reversal）
