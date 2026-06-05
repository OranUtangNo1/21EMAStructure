# システム改善会議用ドキュメント一覧

作成日: 2026-05-29

目的: 短中期限定のロングオンリー・スイング投資において、再現性と期待値の高い投資判断を支援するため、現行システムの状態と改善論点を会議で検討できる形に整理する。

参照元:

- 実装: `src/`
- 設定: `config/default.yaml` と `config/default/*.yaml`
- 画面: `app/main.py`
- SystemDocs: `doc/SystemDocs/`

## ファイル構成

1. `01_system_context.md`
   - システムの目的、現在の責務、対象外範囲、目的とのギャップ。
2. `02_provided_information.md`
   - ユーザーに提供している画面、テーブル、CSV、レポート、判断材料。
3. `03_internal_information_and_pipeline.md`
   - 内部で利用しているデータ、指標、スコア、保存物、データ品質情報。
4. `04_watchlist_presets_and_filters.md`
   - WatchList Preset、annotation filter、duplicate rule の現行構造。
5. `05_scan_catalog.md`
   - active scan の概要と具体的な検出条件。
6. `06_entry_signal_catalog.md`
   - active EntrySignal の概要、検出元、無効化条件、評価軸、数値しきい値。
7. `07_improvement_discussion_points.md`
   - 会議で議論すべき改善案と優先順位。
8. `08_rs_and_market_dashboard.md`
   - RS Radar と Market Dashboard が提供する情報、計算方法、しきい値、対象ETF universe。

## 読み方

最初に `01_system_context.md` で目的と現在地を確認する。
次に `02_provided_information.md` と `03_internal_information_and_pipeline.md` で、ユーザーに見えている情報と内部計算を分けて確認する。
RS / Market Dashboard の具体的な提供情報は `08_rs_and_market_dashboard.md` を使う。
具体的な検出条件は `05_scan_catalog.md` と `06_entry_signal_catalog.md` を参照する。
改善会議では最後に `07_improvement_discussion_points.md` を議題リストとして使う。
