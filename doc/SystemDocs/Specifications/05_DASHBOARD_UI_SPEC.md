# Dashboard UI Spec

## 1. Active UI Scope

The active Streamlit app exposes exactly six pages:

1. `Watchlist`
2. `Entry Signal`
3. `Market Dashboard`
4. `RS`
5. `Analysis`
6. `Setting`

There is no active chart, cockpit, sizing, or exit page in the current app.

## 2. Shared UI Behavior

### 2.1 Run controls

The sidebar is not used for primary controls.

The main content area exposes a collapsed `Run options` expander with:

- `Force weekly universe refresh`
- `Force price data refresh`
- `Recompute from cache`
- `Refresh data` button

The default config path is resolved internally to `config/default.yaml` and is not currently exposed in the run controls.
Manual symbol entry is not exposed in the active UI.

The main content area exposes a top page tab bar:

- `Watchlist`
- `Entry Signal`
- `Market Dashboard`
- `RS`
- `Analysis`
- `Setting`

Current navigation behavior:

- page switching uses a full-width top button row, not a sidebar radio
- each top page button uses the whole visible button area as the pointer and click target
- the app resolves the active page from a page-definition registry so additional tabs can be added without reshaping the main flow
- page-specific controls render in the main content area

The app reloads artifacts when the user presses `Refresh data` or when the tuple `(config_path, symbols, force_universe_refresh, force_price_refresh, force_recompute_from_cache)` changes.

Current load behavior:

- explicit `Refresh` always recomputes the pipeline
- otherwise the app reuses the current in-session artifacts until the artifact key changes
- when the artifact key changes without explicit refresh or force-refresh controls, the app first attempts same-day saved-run restore through `ResearchPlatform.load_latest_run_artifacts()`
- if same-day restore succeeds, the app skips full pipeline recomputation
- if same-day restore fails, the app recomputes through `ResearchPlatform.run()`
- `Force weekly universe refresh` bypasses weekly universe snapshot reuse for symbol resolution
- `Force price data refresh` bypasses the price-cache TTL for the active run while keeping existing cached price rows as merge/fallback data
- `Recompute from cache` bypasses same-day saved-run restore without forcing a live price refresh, so the app rebuilds local `data_runs` artifacts from the current cache when cache files have been replaced externally

### 2.2 Shared context and health

All pages can show:

- a context strip with `Data source: <artifacts.data_source_label>`
- a warning banner when sample fallback is present
- an info banner when stale cache or missing datasets exist
- a `Data Health` expander with `artifacts.fetch_status`, `artifacts.universe_snapshot_path` when present, and `artifacts.run_directory` when present

### 2.3 Watchlist preference persistence

The watchlist page persists its main control state through `UserPreferenceStore`.

Current implemented behavior:

- persistence group for current watchlist control state: `watchlist_controls`
- named preset collection group: `watchlist_presets`
- namespace: resolved config path
- current watchlist state stores:
  - `selected_scan_names`
  - `required_scan_names`
  - `optional_scan_names`
  - `optional_scan_groups`
  - `selected_annotation_filters`
  - `selected_duplicate_subfilters`
  - `duplicate_threshold`
  - editable `duplicate_rule`
- preset records store:
  - `schema_version`
  - `kind`
  - `values`
- preset `values` currently contain those watchlist control fields plus hidden `duplicate_rule` when present
- the preset picker merges saved presets from the preference store with built-in config presets whose `preset_status` is `enabled`
- maximum saved presets per namespace: 10

## 3. Today's Watchlist

### 3.1 Header area

The current page header shows:

- title: `Today's Watchlist`
- subtitle: latest trade date from `artifacts.snapshot`
- meta block:
  - `Sorted by Hybrid-RS`
  - `Universe Mode`
  - `Universe Size`
  - `Cards Selected`
  - `Post-scan Filters`
  - `Duplicate Subfilters`
  - `Duplicate Rule`

### 3.2 Watchlist Controls

On `Watchlist`, preset and rule editing controls are placed in a collapsed `Watchlist presets and controls` expander above the preset-hit and duplicate outputs. The expander stays collapsed by default so hit review remains the primary working surface.

The collapsed control panel exposes:

- saved-preset selectbox
- `Load Preset` action
- `Delete Preset` action
- required-card multiselect
- `Add optional condition` action
- `Remove last condition` action
- one scan multiselect and required-hit input per optional condition group
- post-scan annotation filter multiselect
- duplicate subfilter multiselect
- preset-name input
- `Save Preset` action
- `Update Preset` action
- `Export Preset CSV` download action

Current defaults:

- startup card defaults come from `scan.default_selected_scan_names` or all card sections when unspecified and are loaded as optional cards
- presets with `grouped_threshold` duplicate rules load their required scans and condition groups into the matching controls
- presets with `required_plus_optional_min` duplicate rules load as one condition group
- annotation-filter defaults come from `scan.enabled_annotation_filters`
- duplicate-subfilter default is empty
- each optional condition group threshold defaults to its saved `min_hits`
- newly added generic groups use the `Optional Condition N` naming pattern
- preset-name input defaults to empty until the user loads or saves a preset

Preset load behavior:

- saved presets are dropped when they reference scan names that are not available in the current config
- invalid annotation-filter names are ignored against the current config
- each optional condition group threshold is clamped to that group's selected scan count
- required scans and condition groups are persisted separately from `duplicate_rule` so selections survive page navigation
- duplicate rules are loaded, editable, and persisted from the required-scan and condition-group controls
- built-in presets cannot be deleted or updated from the UI
- `Update Preset` overwrites the currently selected saved preset
- `Export Preset CSV` uses the currently selected preset record, not unsaved watchlist edits

Preset-hit panel behavior:

- the `Preset Hits` panel appears on the Watchlist page before the `Duplicate Tickers` band
- it evaluates active built-in presets and saved custom presets against the current watchlist run
- a hit means the ticker satisfies that preset's annotation filters and duplicate rule
- the summary table groups by ticker and shows hit presets, preset count, built-in/custom split, matched scans, and rule modes
- `Download preset hits CSV` downloads the long one-row-per-`preset_name x ticker` hit table
- `Write preset CSV files` writes `preset_summary.csv`, `preset_hits.csv`, and, when enabled, `preset_details.csv` to the configured preset export folder

Manual selected-preset export CSV behavior:

- one row per selected preset
- fixed leading columns: `Output Target`, `Preset Name`, `Duplicate Tickers`
- one additional column per selected scan card using `<display_name> Hit Tickers`
- `Duplicate Tickers` stores the comma-separated ticker list from the preset's projected duplicate band
- each scan-card column stores the comma-separated ticker list shown in that preset's projected card
- file encoding is UTF-8 with BOM for spreadsheet compatibility

Preset tracking behavior:

- each full pipeline recompute writes preset CSV files when `scan.preset_csv_export.enabled` is true
- each artifact load syncs export-enabled preset detections into `data_runs/tracking.db`, including same-day saved-run restores
- same-day saved-run restore uses the saved watchlist and scan-hit artifacts for idempotent detection registration
- tracking sync is automatic and separate from manual CSV actions
- Analysis reads from the SQLite tracking database and renders analysis tables

### 3.3 Duplicate Tickers priority band

The page renders a dedicated `Duplicate Tickers` band before the scan cards.

The current duplicate rule summary is available in a collapsed `Current duplicate rule` expander below the priority band.

Current logic:

- source rows are rebuilt from raw `artifacts.watchlist` plus raw `artifacts.scan_hits`
- selected annotation filters narrow the displayed watchlist first
- selected required scans and condition groups determine overlap counting
- required scans must all hit
- every condition group is required, and each group has its own `min_hits` threshold
- optional-only selections use the simple `min_count` duplicate rule
- duplicate-only subfilters are applied after duplicate rows are formed

The band currently renders:

- section title
- explanatory note
- duplicate count
- ticker symbols only

The underlying duplicate frame includes `Ticker`, `Scan Hits`, `Hybrid-RS`, `Overlap`, and `VCS`, but the active page displays only the ticker list.

### 3.4 Scan-card grid

The page rebuilds scan cards from the current projected watchlist. It does not render the prebuilt `artifacts.watchlist_cards`.

Current card behavior:

- only selected required and optional scan cards are shown
- required-card and optional-card selections are distinguished by card border color
- card selection does not change the raw watchlist candidate set
- selected annotation filters can remove names from cards
- current duplicate rule can change the duplicate badge state used by the card projection
- cards render ticker symbols only, not row tables

### 3.5 Earnings for today

The page currently does not render the same-day earnings card.

Current source:

- `artifacts.earnings_today`
- built from `earnings_today == True` in the eligible snapshot
- sorted by `Hybrid-RS` descending before display when that column is available

When re-enabled, the intended display is ticker symbols only.

## 4. Entry Signals

The Entry Signals page is a timing layer, not a scan layer.

Current behavior:

- universe source:
  - default: duplicate tickers from built-in presets whose `preset_status` allows export plus duplicate tickers from the current selected watchlist card set
  - selectable alternatives: preset duplicates only, current-selection duplicates only, Today's Watchlist, or the eligible universe
- watchlist controls:
  - the same watchlist preset and duplicate controls used by Today's Watchlist when the Entry Signals page is active
- page-body controls:
  - `Entry signal logic` multiselect from enabled entry signal definitions
- result grain:
  - one row per active signal pool entry for each selected entry signal
- primary decision sections:
  - `Entry Ready`: timing and risk/reward meet execution thresholds
  - `Watch Setup`: setup is forming, but timing or R/R is not ready
  - `Needs Review`: lower-quality candidates are collapsed by default
- primary decision table columns:
  - `Ticker`
  - `Signal`
  - `Action Bucket`
  - `Plan Status`
  - `Entry Type`
  - `Entry Price`
  - `Stop Loss`
  - `TP1`
  - `TP2`
  - `R/R TP1`
  - `Plan Verdict`
  - `Plan Reject Reason`
  - `Missing Piece`
  - `Preset Sources`
  - `Entry Strength`
  - `Timing`
  - `Risk/Reward`
  - `Risk In ATR`
  - `Setup Maturity`
  - `Pool Days`
- detail columns are shown in a collapsed `Signal details` expander per signal section and include plan verdict, reject codes, plan invalidation, SL quality/source/basis/safety, TP1 source, TP2 plan, plan note, plan detail JSON, detection dates, tracking fields, detail JSON, pool status, signal version, and pool entry id.

The page evaluates whether a preset-sourced active pool entry is at a reasonable entry point today. The primary table is intentionally limited to expected-value decision fields: action bucket, missing piece, timing, risk/reward, stop, target, setup maturity, setup source, and pool freshness.

Current action-bucket semantics:

- `Entry Ready`: `Signal Detected`, no market or earnings guard, and the selected signal's configured `action.entry_ready` thresholds are met.
- `Watch Setup`: no market or earnings guard, the selected signal's configured `action.watch_setup` thresholds are met, but one or more execution conditions are still missing.
- `Needs Review`: active candidates that do not meet the `Entry Ready` or `Watch Setup` thresholds.
- `Avoid / Invalid`: inactive, invalidated, expired, or transitioned pool entries.

Action-bucket thresholds are signal-specific and live in `config/default/entry_signals.yaml` under each signal definition's `action` section. This keeps fast momentum entries, pullback entries, and breakout entries from sharing one coarse global threshold.

`Missing Piece` is generated from the selected signal's maturity detail, timing detail, risk/reward values, and guard warnings. It should name the blocking condition as specifically as the evaluator can support, such as `waiting for EMA reclaim`, `volume confirmation weak`, `R/R below 2`, `stop is too wide`, or `weak market warning`, instead of only showing a generic timing or R/R label.

Entry plans are generated as EntrySignal outputs for user review only; automated order placement is out of scope. The main table uses `Plan Type`, `Current Price`, `Entry Zone Low`, `Entry Zone High`, `Max Entry Price`, `Stop Loss`, `TP1`, `R/R Current`, `R/R Ideal`, and `Trigger Condition` as the primary execution context. `Ready Now` means the current close satisfies the signal's minimum R/R. `Wait Pullback` means the setup is valid but current R/R is insufficient, while the calculated entry zone would satisfy the minimum R/R if reached. `Wait Trigger` means price and plan quality are acceptable but the signal still needs confirmation. `Poor R/R` and `Invalid` are diagnostic or review states rather than actionable entries. `TP2` is not price-calculated in the active system; it is displayed as `Future trailing stop` for the planned trailing-stop workflow. Plan exclusions and downgrades are traceable through `Plan Reject Codes`, `Plan Reject Reason`, and `Plan Detail`.

Valid `Ready Now` plans are persisted to `signal_entry_event` for outcome review. Tracking refresh updates those event rows with fixed-horizon returns, TP1/SL hit flags, first outcome, result R, and 20D / 21D maximum gain/drawdown. These event outcomes are diagnostics for EntrySignal calibration and do not represent broker orders or realized P&L.

On app artifact load, the startup-selected EntrySignal set is also evaluated and exported to `data_runs/entry_signals/` as the date-keyed `YYYYMMDD_evaluations.csv` review artifact. Bucket-specific CSV and summary JSON write paths remain available in the runner but are disabled by default. `data_runs/tracking.db` remains the durable source for pool state, evaluations, and entry events.

## 5. RS Radar

### 5.1 Header

The page header shows:

- title: `RS Radar`
- subtitle: `ETF-based radar using configured sector and industry universes.`
- `Updated: HH:MM:SS`

### 5.2 Left column

The left column contains two styled mover panels:

- `Top 3 RS% Change (Daily)`
- `Top 3 RS% Change (Weekly)`

Each panel is sourced from the ETF radar universe and is driven by `radar.top_movers_count`, which currently defaults to `3`.

Each mover row is built from:

- `RS`
- `TICKER`
- `NAME`
- `PRICE`
- one performance column (`DAY %` or `WK %`)
- one relative-strength change column (`RS DAY%` or `RS WK%`)

### 5.3 Right and lower sections

The page also renders:

- `Sector Leaders`
- `Industry Leaders`

These sections use styled dataframes.

Current `Sector Leaders` columns:

- `RS`
- `1D`
- `1W`
- `1M`
- `TICKER`
- `NAME`
- `DAY %`
- `WK %`
- `MTH %`
- `RS DAY%`
- `RS WK%`
- `RS MTH%`
- `52W HIGH`

Current `Industry Leaders` columns:

- all sector-leader columns above
- `MAJOR STOCKS`

## 6. Analysis

Analysis is a preset-hit performance analysis page backed by `data_runs/tracking.db`.

Current scope controls:

- `Preset Universe`: multiselect over built-in preset names
- `Horizon`: one of `1D`, `5D`, `10D`, `21D`
- `Hit Date Range`: date range over recorded detection hit dates
- `Hit Market Env`: multiselect over `bull`, `neutral`, `weak`, and `bear`
- `Benchmark`: one of `SPY`, `QQQ`, or `IWM`

Current behavior:

- preset and market-environment filters use OR semantics within each control
- the default horizon is `21D`
- horizon selection requires a filled return for that horizon to appear in ranking
- `20D` outcomes remain stored for compatibility, but are not exposed as a user-selectable Analysis horizon
- benchmark returns are aligned to each detection hit date and selected horizon, not to the overall analysis period start
- benchmark prices are loaded through the same yfinance price provider and cache layer used by the app
- filter state is persisted in Streamlit session state separately from widget state so tab transitions do not reset the selected preset universe

Current result areas:

- `Ranking`: grouped by `preset_name x market_env`
- `EntrySignal Connection Candidates`: measurement-only preset-to-signal connection review for configured connection candidates
- `Entry Ready Performance`: signal-level `Ready Now` event performance from `v_signal_entry_performance`, filtered by selected market environments
- `Detail`: row-level detection detail for the selected scope; horizon return and close columns are shown for all fixed horizons, with horizons later than the selected horizon displayed as `-`
- `Export Observations CSV`: analysis-oriented observation export with one row per detection horizon that has target data
- `Export Detection Scans CSV`: bridge export from detection to hit scan names
- tracking health diagnostics are rendered on the separate `Setting` page

Current ranking columns:

- `Tier`
- `Preset`
- `Market`
- `Avg Return (%)`
- `Excess vs Benchmark (%)`
- `Max Return (%)`
- `Min Return (%)`
- `Win Rate (%)`
- `Detections`

Tier logic:

- `Observing`: `Detections < 30`
- `Core`: `Detections >= 30`, positive selected-horizon average return, positive benchmark excess return, and win rate at least `55%`
- `Candidate`: `Detections >= 30`, positive selected-horizon average return, and positive benchmark excess return
- `Downgrade Review`: `Detections >= 30`, negative selected-horizon average return, and negative benchmark excess return
- `Mixed` or `Needs Data`: remaining mature or incomplete groups

The ranking table does not display the benchmark return column. Positive excess-return rows are highlighted with a green background and negative excess-return rows with a red background.

Current EntrySignal connection-candidate behavior:

- the initial configured candidate is `Fresh Stage 2 Breakout` toward `Accumulation Breakout Entry`
- the candidate table is derived from the same selected-scope ranking data and selected horizon
- it shows connection status, target signal, preset tier, selected-horizon average return, benchmark excess, win rate, and detection count
- `Fresh Stage 2 Breakout` remains `Measurement Only` while it is absent from every EntrySignal `pool.preset_sources`
- a preset row can become `Connection Candidate` only after the selected-scope tier is `Core` or `Candidate`
- the table does not mutate `config/default/entry_signals.yaml`, create signal pools, or change EntrySignal evaluation

Current detail display:

- uses user-facing column names instead of raw database field names
- formats percentage columns with `(%)`
- hides `benchmark_return_pct`
- displays one selected-horizon excess-return column, labeled for the selected benchmark
- highlights positive excess-return rows with a green background and negative excess-return rows with a red background

The page is intended to help compare preset effectiveness. It is not a trade-management or position-performance ledger.

## 7. Market Dashboard

### 7.1 Header

The page header is centered and shows:

- title: `Market Dashboard`
- `Updated: HH:MM:SS`

### 7.2 Top layout

The page uses a three-part top layout:

- `Market Conditions` hero panel
- prior-score stack for `1D Ago`, `1W Ago`, `1M Ago`, and `3M Ago`
- compact metric-card panels for:
  - `Breadth & Trend Metrics`
  - `Participation Momentum`
  - `Performance Overview`
  - `High, VIX & Safe Haven`
  - `Risk-On Ratio IWO/IWN`

The page does not render the older top stat-card row or a separate component-score table.

### 7.3 Market Conditions hero

The hero panel shows:

- the current `label`
- the current `score`
- a semicircle gauge filled from `score / 100`

The four prior-score cards show:

- the historical score
- the label derived from that historical score

### 7.4 Summary metric panels

Current `Breadth & Trend Metrics` items:

- `SMA 10`
- `SMA 20`
- `SMA 50`
- `SMA 200`
- `20 > 50`
- `50 > 200`

Breadth metric-card labels use a three-state UI threshold: `Strong` at `>= 70.0`, `Mixed` from `50.0` to below `70.0`, and `Weak` below `50.0`. This matches the report breadth reference levels and avoids conflicting current-value interpretation between the dashboard and report text.

Current `Participation Momentum` items:

- `Pos 1W`
- `Pos 1M`
- `Pos 3M`
- `Pos 1Y`
- `Pos YTD`

Participation metric-card labels use a display-only three-state threshold: `Strong` at `>= 60.0`, `Mixed` from `50.0` to below `60.0`, and `Weak` below `50.0`. This differs from Breadth because Participation measures positive-return share rather than moving-average trend participation. Future config may promote these display thresholds into `market_report.participation` settings.

Current `Performance Overview` items:

- `% YTD`
- `% 1W`
- `% 1M`
- `% 1Y`

Current `High, VIX & Safe Haven` items:

- `S2W High`
- `VIX`
- `Safe Haven`

`S2W High` uses `Strong` at `>= 30.0`, `Mixed` from `15.0` to below `30.0`, and `Weak` below `15.0`.

Current `Risk-On Ratio IWO/IWN` items:

- `1M` relative ratio change
- `3M` relative ratio change
- `High Delta` versus the configured lookback high, capped by loaded price history
- `MA` count of configured ratio moving averages currently below the ratio

Metric cards for breadth, participation, high/VIX/safe-haven, and risk-on ratio values may show compact, color-coded `Delta 1D / 1W / 2W / 1M` text computed from already loaded histories. Percentage deltas are displayed as `pt` because they represent percentage-point changes, not percent returns. These deltas do not require extra provider symbols or a longer configured price period.

Market Dashboard sections expose a circular `?` help control next to the section title. Clicking it opens Japanese explanatory text that describes what the section measures and how the values should be interpreted for short-to-medium-term long-only swing context. This help text is explanatory only and does not change scoring, scans, Watchlist output, or EntrySignal evaluation.

Market Dashboard computation also produces non-scoring diagnostics for `breadth_momentum_summary` (A20 current value and 1D/5D/10D/21D deltas), `breadth_internal_summary` (active-universe advancers/decliners, A/D line, 52W new high-low net, Stage 2 percentage, McClellan oscillator/summation, and Zweig breadth thrust flag), `volatility_term_structure` (`VIX9D/VIX`, `VIX/VIX3M`, front inversion, and full backwardation flags), `credit_risk_proxy` (`HYG/LQD`, `HYG/IEF`, and FRED high-yield OAS / delta OAS), `index_state_summary` (`SPY` / `QQQ` FTD, rally-attempt day, distribution-day count, and pressure flag), and `drawdown_summary` (`DD 252D %`, `T_DD`, and rolling high by configured index). These are persisted in market summary JSON for report inputs; the active UI does not render dedicated cards for them yet.

### 7.5 Core / External

The page renders two snapshot sections using the same card layout:

- `Core`
- `External`

`Core` is the only universe used for the current Market Score when `market.calculation_mode = etf`.
`External` is display-only and does not feed the score directly.

Market Dashboard does not render or compute the former `Leadership` ETF snapshot. Sector and industry leadership discovery belongs to RS Radar.

Current market-score composition notes:

- raw breadth and participation percentages are still shown in the metric panels
- the composite score itself now applies score-specific transforms instead of directly summing raw percentages
- `Safe Haven` is derived from the configured risk-on vs risk-off ETF spread
- `Risk-On Ratio IWO/IWN` is display-only and does not feed the composite Market Score

Each card currently shows:

- configured symbol name
- `21EMA POS` badge
- display ticker
- `PRICE`
- `DAY %`
- `VOL vs 50D %`

The underlying 21EMA position labels are:

- `below 21EMA Low`
- `inside 21EMA Cloud`
- `above 21EMA High`
- `unknown`

### 7.6 Factors vs SP500

The page renders `Factors vs SP500` as stacked factor cards and uses the configured factor universe.

Each factor row currently shows:

- factor name
- factor ticker
- `REL 1W %`
- `REL 1M %`
- `REL 1Y %`
- mini bars for the 1W, 1M, and 1Y values

`Factors vs SP500` remains display-only and does not feed the composite Market Score.

### 7.7 S5TH chart

The page does not render the S5TH chart.

The underlying result object may still carry `result.s5th_series`, but the active Market Dashboard does not display it.

### 7.8 Daily market document

The pipeline may persist a deterministic daily AI-input market document under `data_runs/market_documents/`. The final report-writing skill may later write the human-facing report under `data_runs/market_reports/`.

The active Market Dashboard does not render this document or the final report yet. The current UI continues to render the Market Conditions hero, metric panels, Core / External snapshots, and Factors vs SP500 sections described above.

## 8. Setting

The `Setting` tab is the tracking diagnostics page.

Current behavior:

- renders tracking-store diagnostics from the existing tracking health payload
- does not yet expose editable global settings

## 9. Current UI Conventions

- page navigation is defined from a centralized page-definition list and rendered as a top tab selector
- the app loads all page data through `PlatformArtifacts`
- the watchlist page then performs additional UI projection from raw watchlist data and raw scan hits
- numeric display formatting is handled in page-specific helpers
- duplicate highlighting in watchlist cards depends on the projected `duplicate_ticker` field after current watchlist selections are applied
