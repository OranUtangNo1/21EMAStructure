# Preset Hit 状態分析（2026-06-22）

## 結論

Preset Hit が全9件で0になった主因は、相場条件ではなく、現在の `ScanService` がRS・VCS・Industryスコアリングを通さずにIndicator出力を直接Scanへ渡しているパイプライン欠落である。

この結果、全2262評価銘柄で `raw_rs21`、RS新高値フラグ、`vcs` などが利用できず、全Preset共通の `Stage 2 Quality Score` が0件になった。`Mature / Late Stage Risk Filter` と `Industry Leadership Gate` も同じ入力欠落の影響を受けている。

診断CSV自体の件数整合性は正常であり、「Preset集計が誤って0件を表示した」問題ではない。上流のScan入力生成が不完全なため、正しく0件へ絞り込まれた状態である。

## 対象ファイル

- `C:\reository\21EMAStructure\data_runs\service_outputs\preset_diagnostics\20260622_manifest.json`
- `C:\reository\21EMAStructure\data_runs\service_outputs\preset_diagnostics\20260622_scan_counts.csv`
- `C:\reository\21EMAStructure\data_runs\service_outputs\preset_diagnostics\20260622_annotation_counts.csv`
- `C:\reository\21EMAStructure\data_runs\service_outputs\preset_diagnostics\20260622_preset_steps.csv`
- `C:\reository\21EMAStructure\data_runs\service_outputs\preset_diagnostics\20260622_preset_ticker_steps.csv`
- `C:\reository\21EMAStructure\data_runs\service_outputs\scan\20260622.csv`
- `C:\reository\21EMAStructure\data_runs\service_outputs\scan_diagnostics\20260622.csv`

## データ整合性

以下はすべて一致した。

- Watchlist: 1736銘柄
- Scan Hit: 2370行、1736ユニーク銘柄
- Scan集計: 22行
- Annotation集計: 5行
- Preset: 9件、46ステップ
- Tickerステップ: 79856行（1736銘柄 × 46ステップ）
- 各ステップの `input - output = rejected`
- 各Presetで前ステップのoutput件数と次ステップのinput件数が一致

したがって、Manifest、CSV出力、Presetファネル間に件数破損はない。

## Presetファネル

| Preset | 最初に0件になった条件 | 入力 | 通過 | 判定 |
|---|---|---:|---:|---|
| Reclaim Trigger | Stage 2 Quality Score | 1736 | 0 | 異常候補 |
| Fresh Stage 2 Breakout | Stage 2 Quality Score | 1736 | 0 | 異常候補 |
| Accumulation Breakout | Stage 2 Quality Score | 1736 | 0 | 異常候補 |
| VCP 3T Breakout | Stage 2 Quality Score | 1736 | 0 | 異常候補 |
| 50SMA Defense | Stage 2 Quality Score | 1736 | 0 | 異常候補 |
| Power Gap Pullback | Stage 2 Quality Score | 70 | 0 | 上流欠落。別途、Recent Power GapとScan条件の組み合わせでも0件 |
| RS Breakout Setup | Stage 2 Quality Score | 1736 | 0 | 異常候補 |
| Pullback Trigger | Stage 2 Quality Score | 1736 | 0 | 上流欠落。ただしScan候補はStage 4銘柄 |
| Momentum Ignition | Stage 2 Quality Score | 1736 | 0 | 実質的なHit取りこぼし候補あり |

Annotation全体の通過件数は次のとおりだった。

| Annotation | 通過数 |
|---|---:|
| Stage 2 Quality Score | 0 |
| Mature / Late Stage Risk Filter | 0 |
| Industry Leadership Gate | 0 |
| Recent Power Gap | 70 |
| Trend Template | 0 |

## 原因分析

### 1. Stage 2 Qualityが全件Falseになる直接原因

`src/scan/rules.py` のStage 2確認には次が必要である。

- `stage_label == "stage2_candidate"`
- `trend_template_price_score >= 5`
- `raw_rs21 >= 60`
- Stage 2 Quality Scoreが75以上

Indicator出力には `stage_label` と `trend_template_price_score` は存在するが、次のスコアリング由来フィールドが存在しない。

- `raw_rs21` / `raw_rs63`
- `rs21` / `rs63`
- `vcs`
- `industry_score`
- `rs_ratio_at_52w_high` / `rs_ratio_at_3y_high`

実キャッシュからNVDAをIndicatorServiceで再構築すると、2026-06-22時点で `stage_label=stage2_candidate`、`trend_template_price_score=6` だが、`raw_rs21` は列自体が存在しなかった。このため、RS条件で必ずFalseになる。

### 2. 現在のScanServiceにスコアリング段階がない

現在の経路は次のとおりである。

`PriceDataService → IndicatorService → ScanService → ScanRunner`

`src/services/indicator_service.py` はIndicator計算のみを行う。`src/services/scan_service.py` はそのフレームを直接 `ScanRunner` に渡しており、`RSScorer`、`VCSCalculator`、`IndustryScorer` を呼んでいない。

旧パイプラインではScan前に次を順番に付加していた。

`RSScorer → FundamentalScorer → IndustryScorer → HybridScoreCalculator → VCSCalculator`

現在のモジュール化経路でこの責務が移植されていないことが、今回の中心的な実装ギャップである。

### 3. 補助診断との一致

`scan_diagnostics\20260622.csv`では、全2262銘柄について次が通過0だった。

- `raw_rs21_gte_threshold`
- `stage2_confirmed`
- `vcs_gte_threshold`
- `rs_ratio_at_52w_high`
- `rs_ratio_at_3y_high`

Pocket Pivotは1642件、Volume Accumulationは82件など価格・出来高だけで判定できるScanは動作している。この偏りも、価格Indicatorは存在し、スコアリング派生列だけが欠落しているという結論と一致する。

## Scan条件だけで見たNear-miss

Annotationを除外してPresetのScan組み合わせだけを評価した。

| Preset | Scan条件通過数 | 補足 |
|---|---:|---|
| Reclaim Trigger | 0 | 必須Reclaim scanが0 |
| Fresh Stage 2 Breakout | 0 | 必須Fresh Stage 2 Breakoutが0 |
| Accumulation Breakout | 0 | 必須VCS 52 Highが0 |
| VCP 3T Breakout | 0 | VCP 3Tは3件だがRS/VCSリーダー条件が0 |
| 50SMA Defense | 0 | 必須50SMA Reclaimが0 |
| Power Gap Pullback | 1 | ESTC。ただしRecent Power Gap不通過 |
| RS Breakout Setup | 0 | 必須VCS 52 Highが0 |
| Pullback Trigger | 1 | ESTC。ただし `stage4_avoid` |
| Momentum Ignition | 11 | Stage 2候補を含む |

Momentum IgnitionのScan条件通過11銘柄：

`ALOY, ASX, CHRN, CRDO, HIVE, HQ, ICHR, KEEL, UMC, VICR, WYFI`

このうち価格Indicator上で `stage2_candidate` なのは次の8銘柄だった。

`ALOY, ASX, CHRN, CRDO, ICHR, KEEL, UMC, VICR`

これら8銘柄はRSスコアが復元されればPreset Hitになり得る。ただし、正しい全ユニバースRS、Stage 2 Quality、Mature Riskを再計算するまで最終Hitとは断定できない。

VCP 3Tの3銘柄 `ARMK, CZR, SILA` も全て価格Indicator上は `stage2_candidate` だったが、RS/VCS由来のLeadership条件が欠落しているため最終評価不能である。

## 診断機能側の問題

`src/services/scan_service.py` のScan診断は、各条件をboolへ変換した後に `missing_count=0` を固定出力している。そのため、入力列欠落と正常な条件不合格をCSVだけでは区別できない。

今回 `raw_rs21` が存在しないにもかかわらず `missing_count=0` だったのはこのためである。Preset分析Skillでは、全件False条件を検出した場合に必要入力列の存在確認を追加する必要がある。

## 原因分類

| 分類 | 判定 |
|---|---|
| 市場変化による正常な0件 | 否定的 |
| 元株価データ欠損 | 主因ではない |
| Scan/Preset集計不具合 | なし |
| Annotation設定値が厳しすぎる | 主因ではない |
| スコアリング派生列の欠落 | 主因、高確度 |
| 診断のmissing可視化不足 | 副次的不具合 |

## レビュー判定

分析結果は件数、コード経路、単一銘柄再現、Scan診断の4経路で整合している。主因の確度は高い。

次フェーズでは、以下をレビュー対象とする。

1. ScanServiceへRS・VCS・Industry・Hybridスコアリングを戻す責務境界
2. Scan前スコアリングを独立サービス化するか、IndicatorServiceを拡張するか
3. `missing_count`を実際の入力欠落として記録する診断改善
4. 修正後に同一日付でPreset diagnosticsを再生成し、Near-miss候補の最終Hitを確認する
