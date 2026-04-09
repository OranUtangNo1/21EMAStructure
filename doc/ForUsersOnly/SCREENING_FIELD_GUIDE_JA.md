# OraTek 項目ガイド

## 1. 目的

この文書は、OraTek が表示する指標、スコア、スキャンの意味を簡潔に説明するユーザー向けガイドです。
このシステムは候補抽出までを担当し、最終的な売買判断や執行は行いません。

## 2. 前提

- 母集団条件: 時価総額 10 億ドル以上, 50 日平均出来高 100 万株以上, ADR 3.5% 以上 10.0% 以下, Healthcare 除外
- Watchlist 採用条件: 1 つ以上の scan hit があること
- Annotation Filter: 候補追加ではなく表示絞込
- 重複の意味: `scan_hit_count` と `overlap_count` が高いほど複数の切り口で強い

## 3. Watchlist の主要項目

| 項目 | 意味 | 実務での見方 |
|---|---|---|
| `H` / `hybrid_score` | 総合順位. RS + 業績 + 業種 | 候補全体の優先順位 |
| `F` | EPS 成長と売上成長の強さ | 業績の勢いを確認 |
| `I` | 業種全体の強さ | 強い業種に属するかを確認 |
| `21 / 63 / 126` | SPY 対比 RS | 短中期の対指数優位性 |
| `rs5` | 5 日 RS | ごく短期の勢い |
| `vcs` | 値幅, 出来高, 標準偏差の収縮スコア | 高いほどベースが締まっている |
| `hit_scans` | 命中した scan 名 | なぜ候補になったかを見る最重要列 |
| `scan_hit_count` | 命中 scan 数 | 高いほど優先しやすい |
| `overlap_count` | 現在選択中 scan 集合での重複数 | UI 選択で変動する |
| `duplicate_ticker` | 重複閾値以上かどうか | 複数切り口で強い候補を見つける |
| `ema21_low_pct` | 21EMA 下限からの離れ | 低いほど押し目寄り |
| `atr_21ema_zone` | 21EMA からの ATR 距離 | 0 近辺は 21EMA 近辺 |
| `atr_50sma_zone` | 50SMA からの ATR 距離 | 大きいと伸びすぎ |
| `atr_pct_from_50sma` | 50SMA 基準の過熱指標 | 高すぎると追いかけにくい |
| `three_weeks_tight` | 3 週間の収縮 | 締まったベース候補 |
| `pp_count_window` | 20 日の Pocket Pivot 回数 | 需給の継続を確認 |
| `dist_from_52w_high` | 52 週高値からの距離. 0 が高値, 下はマイナス | 高値圏かどうかを見る |
| `dist_from_52w_low` | 52 週安値からの距離. 0 が安値, 上はプラス | 低位圏反転候補かを見る |
| `ud_volume_ratio` | 上昇日出来高 / 下落日出来高 | 買い優勢か売り優勢か |
| `earnings` | 7 日内決算の有無 | イベントリスクを確認 |
| `data_quality_*` | 欠損や鮮度の情報 | 順位より前にデータ品質を確認 |

補足:

- このシステムの RS は「銘柄同士の横比較」ではなく, 各銘柄自身の `株価 / SPY` 履歴の中での位置です
- `rs21 = 90` は 「21 営業日の SPY 対比でかなり強い位置」を意味します

## 4. Market Dashboard / RS Radar の見方

| 項目 | 意味 | 実務での見方 |
|---|---|---|
| Market score | 地合いの総合点 | 高いほど順張りの追い風 |
| `SMA 10 / 20 / 50 / 200` | 各 ETF が各移動平均線より上かの比率 | 地合いの広がりを確認 |
| `20 > 50`, `50 > 200` | 中長期トレンドの広がり | 上昇基調が広く浸透しているか |
| `S2W High` | 2 週間高値更新比率 | 高値更新が広がっているか |
| `VIX` | ボラティリティ指標 | 低いほど順張りに追い風 |
| `21EMA POS` | ETF が 21EMA の下, 中, 上のどこにいるか | 地合いの過熱や崩れを見る |
| Radar `RS` | sector / industry ETF の総合 RS | 強いグループを先に絞る |
| `RS DAY% / WK% / MTH%` | SPY 対比の相対強度差 | 直近の加速度を見る |
| `52W HIGH` | 52 週高値圏かどうか | 高値圏グループかを確認 |
| `MAJOR STOCKS` | 代表銘柄 | 業種の中身を確認 |

## 5. Annotation Filter

- `RS 21 >= 63`: 21 日 RS が上位寄り
- `High Est. EPS Growth`: 母集団内で EPS 成長が上位 10%
- どちらも候補追加ではなく、表示絞込用です

## 6. Scan 一覧

| Scan | 条件要約 | 出る銘柄 | 実務での使い方 |
|---|---|---|---|
| `21EMA scan` | 21EMA 近辺, 50SMA 上, PP 複数 | 押し目候補 | 21EMA 反発監視 |
| `4% bullish` | 当日 +4%, 出来高増, RS 良好 | 強い上昇日銘柄 | ブレイク候補の一次抽出 |
| `Vol Up` | 出来高増で陽線 | 動意株 | ノイズが多いので重複確認 |
| `Volume Accumulation` | 上昇日出来高優勢 + 当日出来高増 | 継続的に買われる銘柄 | 需給確認 |
| `Momentum 97` | 週次最上位級 + 3か月も強い | 主導株 | 勢いの中心を把握 |
| `97 Club` | Hybrid 高 + RS21 極強 | 最上位候補 | 優先監視, 過熱確認 |
| `VCS` | 収縮良好 + RS 良好 | ベース候補 | 仕込み前監視 |
| `VCS 52 High` | 52週高値から 20% 以内で収縮 + trend base | 高値圏継続候補 | ブレイク前監視 |
| `VCS 52 Low` | 52週安値圏かつ 52週高値から大きく下の収縮 | 厳選した反転候補 | 本数はだいぶ少なくなる |
| `Pocket Pivot` | 50SMA 上の出来高シグナル | 需要流入日 | 単発より他条件と併用 |
| `PP Count` | 20日 Pocket Pivot 3回以上 | 継続買い銘柄 | 需給の継続確認 |
| `Weekly 20% plus gainers` | 1週間 +20% 以上 | 短期主導株 | 過熱注意の監視用 |
| `Near 52W High` | 52週高値 5%以内 + Hybrid 良好 | 高値圏主導株 | ブレイク候補 |
| `Three Weeks Tight` | 3週間収縮 + trend base | 締まったベース | 継続候補 |
| `RS Acceleration` | RS21 > RS63 and RS21 >= 70 | 再加速リーダー | 継続性確認 |

注記:

- `PP Count` の UI 表示名は `3+ Pocket Pivots (20d)` で、実装条件は `pp_count_window >= 3` です

## 7. 21EMA scan だけやや詳しく

条件は次の通りです。

- `weekly_return` が 0 以上 15 以下
- `dcr_percent > 20`
- `atr_21ema_zone` が -0.5 から 1.0
- `atr_50sma_zone` が 0.0 から 3.0
- `trend_base = True`

読み方:

- 強いトレンドの中で, 21EMA 近辺まで押してきた銘柄を拾うスキャンです
- 「まだ上がる余地があるか」を見るには `ema21_low_pct` と `atr_pct_from_50sma` の併読が有効です
- `VCS`, `Three Weeks Tight`, `RS Acceleration` と重なると優先順位を上げやすくなります

## 8. 実務フロー

1. Market Dashboard で地合いを確認
2. RS Radar で強い sector / industry を確認
3. Watchlist で `hit_scans` と `scan_hit_count` を見る
4. `H`, `vcs`, `ema21_low_pct`, `atr_pct_from_50sma`, `earnings`, `data_quality_*` で優先順位を調整

目安:

- 押し目候補: `21EMA scan`, `VCS`, `Three Weeks Tight`
- ブレイク候補: `Near 52W High`, `4% bullish`, `RS Acceleration`
- 主導株把握: `Momentum 97`, `97 Club`, `Weekly 20% plus gainers`
- 需給確認: `Volume Accumulation`, `Pocket Pivot`, `PP Count`
