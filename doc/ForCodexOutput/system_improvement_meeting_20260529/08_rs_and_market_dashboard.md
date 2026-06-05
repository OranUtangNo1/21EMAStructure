# RS Radar と Market Dashboard が提供する情報

## この文書の位置づけ

この文書は、会議で RS Radar と Market Dashboard の役割を確認するための詳細資料である。

システムの最大目的は「短中期限定のロングオンリー・スイング投資において、再現性、期待値の高い投資判断を支援すること」である。RS Radar と Market Dashboard は、個別銘柄のエントリー判断そのものではなく、環境認識、資金の向き、リスクオン度合い、リーダー領域の確認を担う。

## Market Dashboard の役割

Market Dashboard は、現在の市場環境がロングオンリーのスイング投資に適しているかを確認するための画面である。

主な役割は以下である。

- 市場全体の状態を `Market Score` と `label` で示す。
- breadth、participation、VIX、safe haven、risk-on ratio から市場の強弱を分解する。
- 主要指数、セクター、テーマETF、外部市場、factor ETF の状態を比較する。
- 1日、1週、1か月、3か月前との市場状態の変化を確認する。
- Watchlist や EntrySignal を強く使うべき局面か、警戒すべき局面かを判断する材料を提供する。

## Market Score

Market Score は 0 から 100 のスコアで、現行設定では `calculation_mode: etf` を使う。active symbols との blended mode 用に `etf_weight: 0.5` と `active_symbols_weight: 0.5` が定義されているが、現在の既定は ETF ベースである。

スコア構成要素と重みは以下である。

| component | weight | 意味 |
| --- | ---: | --- |
| `pct_above_sma20` | 0.12 | 20日SMAを上回る割合 |
| `pct_above_sma50` | 0.14 | 50日SMAを上回る割合 |
| `pct_above_sma200` | 0.14 | 200日SMAを上回る割合 |
| `pct_sma50_gt_sma200` | 0.08 | 50日SMAが200日SMAを上回る割合 |
| `pct_positive_1m` | 0.09 | 1か月リターンがプラスの割合 |
| `pct_positive_3m` | 0.08 | 3か月リターンがプラスの割合 |
| `pct_2w_high` | 0.05 | 2週高値に近い割合 |
| `safe_haven_score` | 0.15 | SPY と TLT の相対リターンから見るリスクオン度 |
| `vix_score` | 0.15 | VIX 水準から見るボラティリティ環境 |

未取得の component は中立値 `50.0` として扱われる。ratio 系 component は 0 から 100 に制限され、50を超える値は `50 + ((value - 50) / 50) * 30` で圧縮される。

Market label は以下のしきい値で決まる。

| label | 条件 |
| --- | --- |
| Bullish | score >= 80.0 |
| Positive | score >= 60.0 |
| Neutral | score >= 40.0 |
| Negative | score >= 20.0 |
| Bearish | score < 20.0 |

## Market Dashboard が提供する主な情報

Market Dashboard の結果は、少なくとも以下の情報を持つ。

| 情報 | 内容 |
| --- | --- |
| `trade_date` | 評価対象日 |
| `score` / `label` | 現在の Market Score と状態ラベル |
| `score_1d_ago` / `label_1d_ago` | 1日前の状態 |
| `score_1w_ago` / `label_1w_ago` | 1週前の状態 |
| `score_1m_ago` / `label_1m_ago` | 1か月前の状態 |
| `score_3m_ago` / `label_3m_ago` | 3か月前の状態 |
| `component_scores` | Market Score の内訳 |
| `breadth_summary` | SMA 上回り率などの市場 breadth |
| `participation_summary` | 1週、1か月、3か月、1年、年初来でプラスの割合 |
| `metric_deltas` | 主要指標の変化 |
| `performance_overview` | ベンチマークの YTD、1W、1M、1Y リターン |
| `high_vix_summary` | VIX 関連の状態 |
| `risk_on_ratio_summary` | IWO/IWN によるリスクオン比率 |
| `market_snapshot` | 主要ETFの価格、日次変化、出来高、21EMA位置 |
| `leadership_snapshot` | リーダー候補ETFの状態 |
| `external_snapshot` | 米国外・中国関連ETFの状態 |
| `factors_vs_sp500` | factor ETF の S&P 500 対比 |
| `sector_relative_strength` | セクターETFの相対強度と順位変化 |
| `style_pair_summary` | Growth/Value などの style pair 比較 |
| `defensive_cyclical_summary` | defensive と cyclical/growth の相対比較 |

## Market Snapshot

Market Snapshot は、主要ETFの現在状態を一覧化する。

表示項目は以下である。

| column | 内容 |
| --- | --- |
| `TICKER` | ETF ticker |
| `NAME` | ETF 名 |
| `PRICE` | 最新価格 |
| `DAY %` | 日次リターン |
| `VOL vs 50D %` | 50日平均出来高に対する相対出来高 |
| `21EMA POS` | 21EMA cloud に対する価格位置 |

`21EMA POS` は以下のいずれかで表示される。

- `below 21EMA Low`
- `inside 21EMA Cloud`
- `above 21EMA High`
- `unknown`

Market Snapshot の既定 universe は以下の 19 ETF である。

| ticker | name |
| --- | --- |
| SPY | S&P 500 |
| QQQ | Nasdaq 100 |
| DIA | Dow Jones |
| IWM | Russell 2000 |
| RSP | S&P 500 Equal Weight |
| QQQE | Nasdaq 100 Equal Weight |
| MDY | S&P MidCap 400 |
| IJR | S&P SmallCap 600 |
| XLB | Materials |
| XLC | Communication Services |
| XLE | Energy |
| XLF | Financials |
| XLI | Industrials |
| XLK | Technology |
| XLP | Consumer Staples |
| XLRE | Real Estate |
| XLU | Utilities |
| XLV | Health Care |
| XLY | Consumer Discretionary |

## Breadth and participation

Breadth は、価格が主要移動平均を上回っている割合や、移動平均の並びが改善している割合を見る。

主な breadth 指標は以下である。

- `pct_above_sma10`
- `pct_above_sma20`
- `pct_above_sma50`
- `pct_above_sma200`
- `pct_sma20_gt_sma50`
- `pct_sma50_gt_sma200`

Participation は、複数期間でプラスリターンの銘柄割合を見る。

主な participation 指標は以下である。

- `pct_positive_1w`
- `pct_positive_1m`
- `pct_positive_3m`
- `pct_positive_1y`
- `pct_positive_ytd`

市場レポート用設定では、breadth の判断目安として `strong: 70`、`weak: 50` が定義されている。S5TH など短期高値系の活性判断では `active: 30`、`weak: 15` が使われる。

## VIX and Safe Haven

VIX score は、VIX が中立水準からどれだけ離れているかを 0 から 100 で表す。

設定値は以下である。

- `vix_neutral_level: 17.0`
- `vix_score_slope: 5.0`

計算式は以下である。

```text
vix_score = 50 - ((vix_close - 17.0) * 5.0)
```

結果は 0 から 100 に制限される。VIX が 17 より低いほどスコアは高くなり、17 より高いほどスコアは低くなる。

市場レポート用の VIX 目安は以下である。

| 状態 | VIX |
| --- | ---: |
| low | 12 |
| neutral | 17 |
| elevated | 25 |
| stress | 30 |

Safe Haven score は、`SPY` と `TLT` の20日リターン差で見る。

```text
spread = SPY 20d return - TLT 20d return
safe_haven_score = 50 + spread * 4.0
```

結果は 0 から 100 に制限される。SPY が TLT を上回るほどリスクオン寄り、TLT が優位になるほどリスクオフ寄りとして扱う。

## Risk-On Ratio

Risk-On Ratio は、`IWO / IWN` を使う。

- numerator: `IWO`
- denominator: `IWN`
- high lookback: 756 trading days
- moving average windows: 20, 50, 200

出力項目は以下である。

| column | 内容 |
| --- | --- |
| `RATIO` | IWO/IWN の現在比率 |
| `REL 1W %` | 1週の相対変化 |
| `REL 1M %` | 1か月の相対変化 |
| `REL 3M %` | 3か月の相対変化 |
| `HIGH DIST %` | 756日高値からの距離 |
| `HIGH LOOKBACK DAYS` | 高値判定の lookback 日数 |
| `ABOVE MA COUNT` | 20/50/200MA のうち上回っている数 |
| `MA COUNT` | 判定対象MA数 |

Growth、小型、リスクオン側に資金が向いているかを見る補助指標である。

## Sector Rotation and Sector RS

Sector relative strength は、セクターETFのベンチマーク対比リターンと順位変化を提供する。

対象セクターは以下である。

- XLB Materials
- XLC Communication Services
- XLE Energy
- XLF Financials
- XLI Industrials
- XLK Technology
- XLP Consumer Staples
- XLRE Real Estate
- XLU Utilities
- XLV Health Care
- XLY Consumer Discretionary

表示項目は以下である。

| column | 内容 |
| --- | --- |
| `REL 1W %` | 5営業日のベンチマーク対比リターン |
| `REL 1M %` | 21営業日のベンチマーク対比リターン |
| `REL 3M %` | 63営業日のベンチマーク対比リターン |
| `REL 1M 1W AGO %` | 1週前時点の1か月相対リターン |
| `REL 1M 1M AGO %` | 1か月前時点の1か月相対リターン |
| `RANK 1M` | 現在の1か月相対順位 |
| `RANK DELTA 1W` | 1週前からの順位変化 |
| `RANK DELTA 1M` | 1か月前からの順位変化 |

Defensive / cyclical summary は、defensive sector と cyclical/growth sector の相対差を見る。

- defensive: XLP, XLU, XLV
- cyclical/growth: XLC, XLE, XLF, XLI, XLK, XLY
- periods: 1W, 1M, 3M

## Leadership, external, and factor ETFs

Leadership Snapshot は、テーマや業種のリーダーETFを確認する。

対象ETFは以下である。

| ticker | name |
| --- | --- |
| SMH | Semiconductors |
| SOXX | Semiconductors Broad |
| IGV | Software |
| FDN | Internet |
| HACK | Cybersecurity |
| XBI | Biotech |
| IBB | Biotech Large Cap |
| ITA | Aerospace and Defense |
| KRE | Regional Banks |
| XRT | Retail |
| XOP | Oil and Gas Exploration |
| TAN | Solar |
| IYT | Transportation |
| IPO | IPOs |

External Snapshot は、米国外や中国関連の状態を見る。

- EEM Emerging Markets
- FXI China Large Cap
- KWEB China Internet

Factor ETFs は、S&P 500 対比で style や size の強弱を見る。

- VUG Growth
- VTV Value
- VYM High Dividend
- MGC Large Cap
- VO Mid Cap
- VB Small Cap
- MTUM Momentum

## Style Pair Summary

Style Pair Summary は、資金の偏りを pair ratio で見る。

| pair | name |
| --- | --- |
| VUG/VTV | Growth vs Value |
| MTUM/SPY | Momentum vs Market |
| VB/MGC | Small vs Large |
| VO/MGC | Mid vs Large |
| VYM/SPY | Dividend vs Market |

出力項目は、`REL 1W %`、`REL 1M %`、`REL 3M %`、`ABOVE MA COUNT`、`MA COUNT` である。

## Market Report Inputs

Market report 用の設定では、短期、中期、長めの補助 horizon が以下で定義されている。設定キー名として `long` があるが、このシステムの投資前提は長期投資ではなく、短中期スイングである。

| horizon | trading days |
| --- | ---: |
| short | 5 |
| medium | 21 |
| long | 63 |

Regime score の変化判定は以下である。

- 1週改善: +3
- 1週悪化: -3
- 1か月改善: +5
- 1か月悪化: -5
- neutral floor: 40
- positive floor: 60

Confidence では `minimum_required_metric_coverage: 0.8` と `disagreement_penalty: 0.2` が定義されている。つまり、市場判断では metric の取得率と指標間の不一致も確認対象になる。

## RS Radar の役割

RS Radar は、セクターETFと業種ETFの相対強度を横断比較するための画面である。

主な役割は以下である。

- セクターと業種の強い領域をランキングする。
- 1日、1週、1か月の相対強度を同時に見る。
- 52週高値付近にいるETFを確認する。
- 日次と週次で急に強くなったETFを抽出する。
- Watchlist preset や scan 結果を見る前に、資金が向いている領域を確認する。

## RS Radar の計算

RS Radar は、各ETFのリターンからベンチマークのリターンを引いて相対リターンを作る。

計算期間は以下である。

| field | trading days |
| --- | ---: |
| `DAY %` | 1 |
| `WK %` | 5 |
| `MTH %` | 21 |
| `RS DAY%` | ETF 1日リターン - benchmark 1日リターン |
| `RS WK%` | ETF 5日リターン - benchmark 5日リターン |
| `RS MTH%` | ETF 21日リターン - benchmark 21日リターン |

`1D`、`1W`、`1M` は、それぞれ `RS DAY%`、`RS WK%`、`RS MTH%` の percentile rank である。

総合 `RS` は以下の重みで計算する。

| component | weight |
| --- | ---: |
| `1D` | 1.0 |
| `1W` | 2.0 |
| `1M` | 2.0 |

欠損値は無視して、取得できた component の重みだけで加重平均する。並び順は `RS`、`1W`、`1D` の降順である。

52週高値判定では `near_high_threshold_pct: 0.5` を使う。最新価格が 252日高値の 0.5% 以内なら `Yes`、それ以外は高値からの距離をパーセントで表示する。

Top movers は `top_movers_count: 3` で、日次上位3件、週次上位3件を表示する。

## RS Radar の出力テーブル

Sector leaders と Industry leaders は以下の情報を提供する。

| column | 内容 |
| --- | --- |
| `RS` | 1D/1W/1M percentile rank の加重平均 |
| `1D` | 日次相対強度 percentile |
| `1W` | 週次相対強度 percentile |
| `1M` | 月次相対強度 percentile |
| `TICKER` | ETF ticker |
| `NAME` | ETF 名 |
| `DAY %` | 1日リターン |
| `WK %` | 5日リターン |
| `MTH %` | 21日リターン |
| `RS DAY%` | 1日ベンチマーク対比 |
| `RS WK%` | 5日ベンチマーク対比 |
| `RS MTH%` | 21日ベンチマーク対比 |
| `52W HIGH` | 52週高値付近なら Yes、そうでなければ高値からの距離 |
| `MAJOR STOCKS` | Industry leaders のみ。代表銘柄 |

Top daily は `RS DAY%`、次に `RS` の降順で上位3件を出す。

Top weekly は `RS WK%`、次に `RS` の降順で上位3件を出す。

## RS Radar Universe

Sector ETF universe は以下である。

- QQQ
- QQQE
- RSP
- DIA
- IWM
- XLV
- XLE
- XLF
- XLRE
- XLB
- XLP
- XLU
- XLY
- XLK
- XLC
- XLI

Industry ETF universe は以下である。

| ticker | name |
| --- | --- |
| SLX | Steel |
| IBB | Biotechnology |
| KRE | Regional Bank |
| XBI | Biotech |
| PEJ | Leisure |
| LIT | Lithium |
| UFO | Space |
| JETS | Global Jets |
| SMH | Semiconductor |
| IYT | Transportation |
| MOO | Agribusiness |
| KARS | Electric Cars |
| TAN | Solar |
| WOOD | Timber |
| COPX | Copper Miners |
| QTUM | Quantum-Tech |
| URA | Uranium |
| IAI | Broker-Dealers |
| ICLN | Clean Energy |
| XOP | Oil & Gas Exp. |
| GDX | Gold Miners |
| XRT | Retail |
| SIL | Silver Miners |
| IPO | IPO |
| REMX | Rare Earth |
| KIE | Insurance |
| ITA | Aerospace |
| CIBR | Cybersecurity |
| ITB | Home Construction |
| BLOK | Blockchain |
| IGV | Tech-Software |
| KWEB | China Internet |
| IPAY | Mobile Payments |
| IHI | Med. Devices |
| FINX | FinTech |

`WGMI` Bitcoin Miners はコード上の既定値には残っているが、現在の設定ファイルではコメントアウトされているため、アクティブな既定 universe には含めない。

## 会議で確認すべき論点

RS Radar と Market Dashboard については、以下を会議で確認する価値が高い。

- Market Score の component weight は、短中期ロングオンリーの期待値改善に対して今の比率でよいか。
- VIX と safe haven の重みが合計 0.30 と大きいため、強い個別銘柄相場を抑制しすぎていないか。
- RS Radar の総合RSは 1W と 1M を重くしているため、短期急騰より持続的リーダーを優先できているか。
- RS Radar の ETF universe は、現在の投資対象や監視テーマを十分に反映しているか。
- Market Dashboard の breadth と participation を、scan hit 数や EntrySignal の有効率と結びつけるべきか。
- Market Dashboard の状態ラベルを Watchlist preset の推奨強度や EntrySignal 表示優先度に反映するべきか。
