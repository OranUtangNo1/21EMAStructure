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

The app reloads artifacts when the user presses `Refresh data` or when the tuple `(config_path, symbols, force_universe_refresh, force_price_refresh)` changes.

Current load behavior:

- explicit `Refresh` always recomputes the pipeline
- otherwise the app reuses the current in-session artifacts until the artifact key changes
- when the artifact key changes without explicit refresh or force-refresh controls, the app first attempts same-day saved-run restore through `ResearchPlatform.load_latest_run_artifacts()`
- if same-day restore succeeds, the app skips full pipeline recomputation
- if same-day restore fails, the app recomputes through `ResearchPlatform.run()`
- `Force weekly universe refresh` bypasses weekly universe snapshot reuse for symbol resolution
- `Force price data refresh` bypasses the price-cache TTL for the active run while keeping existing cached price rows as merge/fallback data

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
- built-in presets marked `hidden_enabled` or `disabled` remain out of the picker
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

- legacy card defaults come from `scan.default_selected_scan_names` or all card sections when unspecified and are loaded as optional cards
- presets with `grouped_threshold` duplicate rules load their required scans and condition groups into the matching controls
- presets with legacy `required_plus_optional_min` duplicate rules load as one condition group
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
- each full pipeline recompute syncs export-enabled preset detections into `data_runs/tracking.db`
- same-day saved-run restore refreshes existing tracking prices but does not register new detections
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
- legacy optional-only selections still use the simple `min_count` duplicate rule
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

The page currently does not render the same-day earnings card. The underlying artifact remains available for future re-enablement.

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
  - `Signal universe` selectbox
  - `Entry signal logic` multiselect from enabled entry signal definitions
- result grain:
  - one row per ticker that matches at least one selected entry signal
- result columns include:
  - `Ticker`
  - `Entry Signals`
  - `Universe Sources`
  - `Close`
  - `RS21`
  - `VCS`
  - `Rel Volume`
  - `Dist 52W High`
  - `Risk Reference`
  - `Entry Note`

The page evaluates whether a ticker in the selected signal universe is at a reasonable entry point today. The default universe remains duplicate-focused, but the page can broaden evaluation to Today's Watchlist or the eligible universe.

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
- `Horizon`: one of `1D`, `5D`, `10D`, `20D`
- `Hit Date Range`: date range over recorded detection hit dates
- `Hit Market Env`: multiselect over `bull`, `neutral`, `weak`, and `bear`
- `Benchmark`: one of `SPY`, `QQQ`, or `IWM`

Current behavior:

- preset and market-environment filters use OR semantics within each control
- horizon selection requires a filled return for that horizon to appear in ranking
- benchmark returns are aligned to each detection hit date and selected horizon, not to the overall analysis period start
- benchmark prices are loaded through the same yfinance price provider and cache layer used by the app
- filter state is persisted in Streamlit session state separately from widget state so tab transitions do not reset the selected preset universe

Current result areas:

- `Ranking`: grouped by `preset_name x market_env`
- `Detail`: row-level detection detail for the selected scope; horizon return and close columns are shown for all fixed horizons, with horizons later than the selected horizon displayed as `-`
- `Export Observations CSV`: analysis-oriented observation export with one row per detection horizon that has target data
- `Export Detection Scans CSV`: bridge export from detection to hit scan names
- tracking health diagnostics are rendered on the separate `Setting` page

Current ranking columns:

- `Preset`
- `Market`
- `Avg Return (%)`
- `Excess vs Benchmark (%)`
- `Max Return (%)`
- `Min Return (%)`
- `Win Rate (%)`
- `Detections`

The ranking table does not display the benchmark return column. Positive excess-return rows are highlighted with a green background and negative excess-return rows with a red background.

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
  - `Performance Overview`
  - `High & VIX`

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

Current `Performance Overview` items:

- `% YTD`
- `% 1W`
- `% 1M`
- `% 1Y`

Current `High, VIX & Safe Haven` items:

- `S2W High`
- `VIX`
- `Safe Haven`

### 7.5 Core / Leadership / External

The page renders three snapshot sections using the same card layout:

- `Core`
- `Leadership`
- `External`

`Core` is the only universe used for the current Market Score when `market.calculation_mode = etf`.
`Leadership` and `External` are display-only sections and do not feed the score directly.

Current market-score composition notes:

- raw breadth and participation percentages are still shown in the metric panels
- the composite score itself now applies score-specific transforms instead of directly summing raw percentages
- `Safe Haven` is derived from the configured risk-on vs risk-off ETF spread

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
- mini bars for the 1W and 1M values

The underlying result frame still includes `REL 1Y %`, but the active page does not render it.

### 7.7 S5TH chart

The page does not render the S5TH chart.

The underlying result object may still carry `result.s5th_series`, but the active Market Dashboard does not display it.

## 8. Setting

The `Setting` tab is the future home for app-wide settings.

Current behavior:

- renders tracking-store diagnostics from the existing tracking health payload
- does not yet expose editable global settings

## 9. Current UI Conventions

- page navigation is defined from a centralized page-definition list and rendered as a top tab selector
- the app loads all page data through `PlatformArtifacts`
- the watchlist page then performs additional UI projection from raw watchlist data and raw scan hits
- numeric display formatting is handled in page-specific helpers
- duplicate highlighting in watchlist cards depends on the projected `duplicate_ticker` field after current watchlist selections are applied
