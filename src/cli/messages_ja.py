from __future__ import annotations

CLI_MESSAGES: dict[str, str] = {
    'input_prompt': '入力',
    'exit_message': '終了します。',
    'menu_intro': '実行したい処理を選択してください。番号でも自然文でも入力できます。',
    'menu_price_fetch': '1. 株価データ更新 (Enterだけでデフォルトユニバースの日次差分更新)',
    'menu_stockcard': '2. StockCard出力',
    'menu_scan': '3. Scan実行 (対象入力でEnter=デフォルトユニバース)',
    'menu_market_environment': '4. Market Environment出力',
    'menu_exit': '0. 終了',
    'as_of_prompt': '対象日 YYYY-MM-DD / YYYYMMDD',
    'stockcard_force_refresh_prompt': '指定日まで価格データを強制更新しますか',
    'stockcard_confirm': 'StockCardを出力します',
    'scan_refresh_missing_prompt': 'キャッシュ不足時に価格データを取得しますか',
    'scan_confirm': 'Scanを実行します',
    'scan_symbol_prompt': 'スキャン対象ティッカーまたは @ファイル (Enter=デフォルトユニバース)',
    'market_refresh_missing_prompt': 'market用キャッシュ不足時に価格データを取得しますか',
    'market_confirm': 'Market Environmentを出力します',
    'price_title': '株価データ更新',
    'price_default_help': '- Enterだけで、デフォルトユニバースの日次差分更新を実行します。',
    'price_details_prompt': '詳細設定を開きますか',
    'price_target_prompt': '対象 1=デフォルトユニバース 2=ティッカー/ファイル指定',
    'price_period_prompt': '初回取得期間',
    'price_mode_prompt': '更新モード 1=日次差分 2=キャッシュ確認のみ 3=強制再取得',
    'price_confirm': '株価データを更新します',
    'stockcard_force_refresh_warning': '- 指定日まで更新したい場合は --force-refresh を付けて再実行してください。',
    'symbol_prompt': 'ティッカー 例: AAPL, AMD または @C:\\\\path\\\\universe.csv',
    'symbol_required': '少なくとも1銘柄を入力してください。',
    'confirm_prompt': '実行しますか',
}

YES_VALUES = frozenset({'y', 'yes', '1', 'true', '\u306f\u3044', 'h'})
