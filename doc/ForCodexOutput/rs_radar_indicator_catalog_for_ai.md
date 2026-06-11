# RS Radar Indicator Catalog For AI

- 区分: RS Radar
  名前: Sector Leaders
  定義: configured `sector_etfs` のETF群をRS降順に並べた表
  想定用途: セクター/主要指数グループの相対優位判定

- 区分: RS Radar
  名前: Industry Leaders
  定義: configured `industry_etfs` のETF群をRS降順に並べた表; `MAJOR STOCKS`を含む
  想定用途: 業種リーダーシップと候補確認優先群の判定

- 区分: RS Radar
  名前: Top Daily
  定義: universeを`RS DAY%`降順、同値補助で`RS`降順に並べ、`top_movers_count`件を抽出
  想定用途: 日次で急速に相対改善したグループ検出

- 区分: RS Radar
  名前: Top Weekly
  定義: universeを`RS WK%`降順、同値補助で`RS`降順に並べ、`top_movers_count`件を抽出
  想定用途: 週間で相対改善したグループ検出

- 区分: RS Radar
  名前: PRICE
  定義: ETF latest close
  想定用途: ETF現在値参照

- 区分: RS Radar
  名前: DAY %
  定義: ETF closeの1営業日リターン
  想定用途: 絶対日次騰落率判定

- 区分: RS Radar
  名前: WK %
  定義: ETF closeの5営業日リターン
  想定用途: 絶対週間騰落率判定

- 区分: RS Radar
  名前: MTH %
  定義: ETF closeの21営業日リターン
  想定用途: 絶対月次騰落率判定

- 区分: RS Radar
  名前: RS DAY%
  定義: `ETF DAY % - benchmark DAY %`
  想定用途: ベンチマーク対比の日次相対強度判定

- 区分: RS Radar
  名前: RS WK%
  定義: `ETF WK % - benchmark WK %`
  想定用途: ベンチマーク対比の週間相対強度判定

- 区分: RS Radar
  名前: RS MTH%
  定義: `ETF MTH % - benchmark MTH %`
  想定用途: ベンチマーク対比の月次相対強度判定

- 区分: RS Radar
  名前: 1D
  定義: universe内の`RS DAY%` percent rank
  想定用途: 日次RS順位スコア

- 区分: RS Radar
  名前: 1W
  定義: universe内の`RS WK%` percent rank
  想定用途: 週間RS順位スコア

- 区分: RS Radar
  名前: 1M
  定義: universe内の`RS MTH%` percent rank
  想定用途: 月次RS順位スコア

- 区分: RS Radar
  名前: RS
  定義: weighted average of `[1D,1W,1M]` using `overall_rs_weights`; default weights=`[1.0,2.0,2.0]`; NaNは除外
  想定用途: 総合RS順位スコア

- 区分: RS Radar
  名前: 52W HIGH
  定義: rolling 252-session high基準; `price >= rolling_high*(1-near_high_threshold_pct/100)`なら`Yes`; otherwise `(price/rolling_high-1)*100`を表示
  想定用途: 52週高値近接度判定

- 区分: RS Radar
  名前: MAJOR STOCKS
  定義: `industry_etfs`設定の`major_stocks`をカンマ連結した表示専用フィールド
  想定用途: 業種ETFに紐づく主要個別株参照

- 区分: RS Radar
  名前: Universe Sort Order
  定義: universeは`RS desc, 1W desc, 1D desc`でソート
  想定用途: Leader tableの優先順位解釈

- 区分: RS Radar
  名前: Sector ETF Universe
  定義: `config/default/radar.yaml:radar.sector_etfs`
  想定用途: Sector Leaders算出対象の特定

- 区分: RS Radar
  名前: Industry ETF Universe
  定義: `config/default/radar.yaml:radar.industry_etfs`
  想定用途: Industry Leaders算出対象の特定

- 区分: RS Radar
  名前: top_movers_count
  定義: Top Daily/Top Weeklyの抽出件数; default `3`
  想定用途: 短期モメンタム表示件数制御

- 区分: RS Radar
  名前: overall_rs_weights
  定義: `RS`計算時の`[1D,1W,1M]`重み; default `[1.0,2.0,2.0]`
  想定用途: 総合RSが短期/中期をどの程度重視するかの解釈

- 区分: RS Radar
  名前: near_high_threshold_pct
  定義: `52W HIGH`を`Yes`にする rolling high 近接閾値; default `0.5`
  想定用途: 52週高値近接判定の閾値解釈
