# システム改善 実行計画

作成日: 2026-05-29

参照元: `doc/ForUsersOnly/09_improvement_plan.md`

対象目的: 短中期限定・米国株専用・ロングオンリー swing において、再現性と期待値の高い候補確認を支援する。

## 0. 結論

最初に実装すべきは、新しい Market Score の重み変更ではない。

優先順位は以下で固定する。

1. Entry Ready 起点の検証基盤を整える。
2. 21D、MFE、MAE、R 倍率、benchmark excess を保存・表示する。
3. VIX term structure と credit spread を Market Dashboard に診断フラグとして追加する。
4. FTD / Distribution Day、breadth momentum、Stage 2 breadth を診断フラグとして追加する。
5. 実測で効いたものだけを context guard、preset 優先度、Market Score component に昇格する。

理由は、会議結果の中心が「地合いゲートを実証で作る」ことだからである。
未検証の指標をすぐ Market Score に混ぜると、期待値改善ではなく説明不能なスコア変更になる。

## 1. 実装前提

- 現在の実装と `config/default.yaml` / `config/default/*.yaml` を挙動の source of truth とする。
- `doc/ForUsersOnly/09_improvement_plan.md` は会議結果として扱い、直接編集しない。
- 既存 worktree には多数の変更があるため、実装前に対象差分を確認し、無関係な変更は戻さない。
- 新指標は最初は dashboard / market document / analysis の診断フラグに留める。
- EntrySignal、WatchList、scan の既存ルールは、検証結果が出るまで直接変更しない。

## 2. Phase 0: 決定事項の固定

目的: 実装前に、計測単位と採用基準を固定する。

実施内容:

- 主評価 horizon を 21D に固定する。
- 補助 horizon を 5D / 10D にする。
- 63D は中期リーダーシップ持続の診断に限定する。
- 主評価イベントを `EntrySignal が Entry Ready に到達した日` に固定する。
- preset hit は入口前の候補検出として扱い、主評価ではなく補助評価にする。
- 期待値の主指標を `R倍率期待値 + 21D benchmark excess return` にする。
- 最小 N を決める。初期案は 30 件未満を `観察中` 固定。

成果物:

- SystemDocs または ForCodexOutput に、評価定義の短い決定メモを追加する。
- `tests/` で期待値 horizon と表示列の前提を固定する準備をする。

完了条件:

- 21D と Entry Ready 起点を、実装・テスト・ドキュメントで同じ意味として扱える。

## 3. Phase 1: 計測基盤の拡張

目的: 改善の成否を測れる状態にする。

対象候補:

- `src/dashboard/effectiveness.py`
- `src/data/tracking_schema.sql`
- `src/data/signal_tracking.py`
- `src/data/tracking_repository.py`
- `src/signals/runner.py`
- `tests/test_preset_effectiveness.py`
- `tests/test_signal_tracking.py`
- `tests/test_tracking_repository.py`

実施内容:

- `FORWARD_HORIZONS` を 1 / 5 / 10 / 20 から、少なくとも 1 / 5 / 10 / 20 / 21 に拡張する。
- 必要なら 42D を追加するが、最初は 21D 優先にする。
- `detection` と `signal_entry_event` に 21D の close / return / benchmark excess を追加する。
- `signal_entry_event` を Entry Ready 起点の主評価テーブルとして使えるようにする。
- SL / TP1 がある signal では、`outcome_r` を主指標として集計する。
- `MFE / MAE` を 21D で保存する。既存の `max_gain_20d` / `max_drawdown_20d` は互換用に残す。
- market label だけでなく、Market Score、breadth posture、Risk-On Ratio state、industry leadership posture をイベント時点で保存する。

設計注意:

- 既存カラムを削除しない。
- migration は `_ensure_tracking_columns` で既存DBへ後方互換に追加する。
- benchmark excess は benchmark close が取れない場合は null にする。
- EntrySignal ロジックは変更せず、評価イベントと outcome の保存を拡張する。

完了条件:

- Entry Ready イベントごとに、5D / 10D / 21D return、21D benchmark excess、MFE、MAE、R outcome が取得できる。
- Analysis で 21D を主評価として表示できる。

## 4. Phase 2: 低コストの市場方向性フラグ

目的: 現行 Market Dashboard の弱点である VIX 線形ペナルティと SPY/TLT safe haven の歪みを、まず診断フラグで補う。

対象候補:

- `config/default/market.yaml`
- `src/dashboard/market.py`
- `src/dashboard/market_report.py`
- `src/data/store.py`
- `src/pipeline.py`
- `tests/test_market_report.py`
- `tests/test_scoring.py` または market dashboard 用テスト

追加データ:

- `^VIX3M`
- `HYG`
- `LQD`
- `IEF`

実施内容:

- `VIX / VIX3M` を計算し、contango / neutral / backwardation を判定する。
- `HYG / LQD` と補助 `HYG / IEF` を計算し、credit risk-on / warning / risk-off を判定する。
- 欠損時は中立扱いにし、data quality に欠損を残す。
- Market Score にはまだ混ぜない。
- Market Dashboard、market document、daily report input に診断フラグとして出す。

完了条件:

- VIX term structure と credit spread proxy が毎回の market result に保存される。
- market document に level / change / significance が出る。
- 欠損時に pipeline が落ちず、中立扱いになる。

## 5. Phase 3: 攻守切替フラグ

目的: 下落明けの攻め再開と天井警戒を、指数価格・出来高と breadth momentum から確認する。

対象候補:

- `src/dashboard/market.py`
- `config/default/market.yaml`
- `tests/test_market_report.py`
- 新規テスト: `tests/test_market_direction_flags.py`

実施内容:

- SPY / QQQ の Follow-Through Day を診断フラグとして追加する。
- SPY / QQQ の Distribution Day count を追加する。
- universe 内部から Net New High - New Low を計算する。
- Advance / Decline Line を計算する。
- McClellan Oscillator / Summation Index を ratio-adjusted 版で計算する。
- % of universe in Stage 2 を計算する。
- Zweig Breadth Thrust は低頻度フラグとして追加するが、単独で攻め判定にしない。

設計注意:

- NYSE 全銘柄前提の古典しきい値をそのまま採用しない。
- 初期表示は raw value と z-score / percentile を併記する。
- Market Score への組み込みは Phase 5 まで保留する。

完了条件:

- Market Dashboard で、breadth の水準だけでなく momentum / divergence / thrust を確認できる。
- market document に、攻守切替に関わる変化として出力できる。

## 6. Phase 4: Analysis の層別と preset 検証

目的: preset と scan の限界寄与を、感覚ではなく実測で決める。

対象候補:

- `src/data/tracking_repository.py`
- `src/dashboard/effectiveness.py`
- `app/main.py`
- `tests/test_tracking_repository.py`
- `tests/test_app_watchlist_presets.py`

実施内容:

- Entry Ready 起点の performance view を追加する。
- market label × preset × horizon の集計を出す。
- market direction flag × preset × horizon の集計を出す。
- industry leadership あり / なしの集計を出す。
- preset 内 scan の ablation 表を出す。
- 最小 N、複数 regime 成立、R 期待値、21D excess で preset tier を出す。

初期 tier 案:

- 主力: N >= 30、21D excess 正、R期待値 正、2つ以上の regime で成立。
- 条件付き: N >= 30、特定 regime でのみ成立。
- 観察中: N < 30 または指標が矛盾。
- 降格候補: N >= 30 で 21D excess と R期待値がともに弱い。

完了条件:

- preset を主力 / 条件付き / 観察中 / 降格候補に分類できる。
- scan を preset 内の限界寄与で残す・annotation 化する判断材料が出る。

## 7. Phase 5: EntrySignal 接続の穴を塞ぐ

目的: Fresh Stage 2 Breakout を主力候補として扱う場合に、入口評価へ接続する。

確認済みの穴:

- Fresh Stage 2 Breakout は preset と scan として存在する。
- 現行の EntrySignal `preset_sources` には Fresh Stage 2 Breakout が入っていない。
- そのため、主力候補にするなら EntrySignal への経路が必要である。

選択肢:

1. `Accumulation Breakout Entry` の `preset_sources` に Fresh Stage 2 Breakout を追加する。
2. Fresh Stage 2 専用 evaluator を追加する。
3. まずは signal pool に入れず、Analysis だけで期待値を測る。

推奨:

- 最初は 3 を採用し、Phase 4 の検証で期待値を確認する。
- 期待値が十分なら 1 を採用する。
- 専用 evaluator は、Accumulation Breakout Entry と明確に違う timing / risk plan が必要になってから追加する。

完了条件:

- Fresh Stage 2 Breakout を EntrySignal に接続するかどうかを、期待値データで判断できる。

## 8. Phase 6: ゲート統合

目的: 実測で有効だった診断フラグだけを、実際の攻守ゲートへ昇格する。

実施内容:

- VIX score を区分線形または非線形に変更する。
- VIX term structure が backwardation のときだけ強いペナルティをかける。
- safe_haven_score を SPY/TLT 単独から credit spread 併用にするか判断する。
- context guard の Market Score 30 / 40、breadth 70 などを実測値で再設定する。
- industry leadership gate を他 preset に広げるか判断する。
- preset 表示優先度に market direction flags を反映する。

設計注意:

- Phase 2 / 3 の指標を全部採用しない。
- 採用条件は、Entry Ready 起点の 21D excess と R期待値で判別力があること。
- スコアに混ぜる前に、dashboard 上の説明可能性を確認する。

完了条件:

- Market Dashboard が「攻める / 通常 / 慎重 / 守る」の判断を、説明可能な指標で出せる。
- EntrySignal の解釈や preset 優先度が、検証済みの地合いゲートに従う。

## 9. Phase 7: ドキュメントと運用

目的: 実装後に仕様と運用が乖離しないようにする。

更新対象:

- `doc/SystemDocs/Specifications/05_DASHBOARD_UI_SPEC.md`
- `doc/SystemDocs/Specifications/08_PARAMETER_CATALOG.md`
- `doc/SystemDocs/Specifications/09_MARKET_DOCUMENT_AND_REPORT_SPEC.md`
- `doc/SystemDocs/Specifications/10_TRADING_METHOD_PLAYBOOK.md`
- `doc/SystemDocs/EntrySignal/`
- `doc/SystemDocs/WatchlistPresets/`

実施内容:

- 新しい診断フラグの定義、取得元、欠損時の扱いを書く。
- Entry Ready 起点の評価定義を書く。
- 21D / R / MFE / MAE / benchmark excess の意味を書く。
- Market Score に採用した指標と、診断止まりの指標を分けて書く。
- reportskill-1 が読む market document の項目を更新する。

完了条件:

- SystemDocs が実装と一致する。
- daily market report が新指標を外部要因なしで解釈できる。

## 10. 実装順の推奨

最短で価値を出す順序は以下である。

1. Phase 1: 21D / Entry Ready / R / MFE / MAE の計測基盤。
2. Phase 2: VIX term structure と credit spread の診断フラグ。
3. Phase 4: Analysis 層別と preset tier。
4. Phase 3: FTD / Distribution Day / breadth momentum。
5. Phase 5: Fresh Stage 2 Breakout の接続判断。
6. Phase 6: 実測で有効なものだけ gate に統合。
7. Phase 7: SystemDocs と reportskill-1 入力の同期。

## 11. 最初の実装チケット案

### Ticket 1: Tracking に 21D outcome を追加

- `FORWARD_HORIZONS` に 21 を追加する。
- `detection` / `signal_entry_event` に 21D close / return を追加する。
- view と repository read 関数に 21D を追加する。
- UI の horizon selector は 20D を出さず、21D を主評価 horizon として出す。
- テスト: tracking schema、repository、app watchlist preset。

### Ticket 2: Entry Ready 起点 performance を追加

- `signal_entry_event` を主評価として集計する view / repository 関数を追加する。
- Action Bucket 別、signal 名別、market label 別に集計する。
- R outcome、hit_sl、hit_tp1、first_outcome を集計に出す。
- テスト: signal tracking、tracking repository。

### Ticket 3: VIX term structure / credit spread 診断フラグ

- `^VIX3M`、HYG、LQD、IEF を market auxiliary symbols として設定化する。
- VIX/VIX3M、HYG/LQD、HYG/IEF を計算する。
- `MarketConditionResult` に diagnostic summaries を追加する。
- market document に `volatility_term_structure` と `credit_risk_proxy` を追加する。
- テスト: market dashboard、market report。

### Ticket 4: Preset tier analysis

- preset × market_env × horizon の 21D 集計を主表示にする。
- Entry Ready 起点の signal performance を追加表示する。
- N < 30 を観察中に固定する tier logic を追加する。
- テスト: repository、UI display helper。

### Ticket 5: FTD / Distribution Day

- SPY / QQQ の index state calculator を追加する。
- FTD、distribution day count、current rally attempt status を診断フラグで出す。
- Market Score には入れない。
- テスト: synthetic SPY / QQQ history で FTD と distribution count を検証する。

## 12. リスクと注意点

- 現在の worktree は大きく変更済みなので、実装前に対象ファイルの差分確認が必須。
- data_cache / data_runs の生成物を前提にしすぎると、過去検証が環境依存になる。
- yfinance の新規 symbols は欠損や ticker 仕様変更があり得るため、欠損時は中立に倒す。
- Market Score の重み変更は最後にする。
- scan や EntrySignal の追加より、先に「何が効いたか」を測る基盤を優先する。
