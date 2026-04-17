# Dashboard UI Spec

## 1. Active UI Scope

The active Streamlit app exposes exactly five pages:

1. `Today's Watchlist`
2. `Entry Signals`
3. `Tracking Analytics`
4. `RS Radar`
5. `Market Dashboard`

There is no active chart, cockpit, sizing, or exit page in the current app.

## 2. Shared UI Behavior

### 2.1 Sidebar controls

The sidebar always exposes:

- `Manual Symbols (optional)`
- `Force Weekly Universe Refresh`
- `Force Price Data Refresh`
- `Refresh` button

The default config path is resolved internally to `config/default.yaml` and is not currently exposed in the sidebar UI.

The main content area exposes a top page tab bar:

- `Today's Watchlist`
- `Entry Signals`
- `Tracking Analytics`
- `RS Radar`
- `Market Dashboard`

Current navigation behavior:

- page switching uses a full-width top button row, not a sidebar radio
- each top page button uses the whole visible button area as the pointer and click target
- the app resolves the active page from a page-definition registry so additional tabs can be added without reshaping the main flow
- page-specific sidebar controls are rendered from the active page definition only

The app reloads artifacts when the user presses `Refresh` or when the tuple `(config_path, manual_symbols, force_universe_refresh, force_price_refresh)` changes.

Current load behavior:

- explicit `Refresh` always recomputes the pipeline
- otherwise the app reuses the current in-session artifacts until the artifact key changes
- when the artifact key changes without explicit refresh or force-refresh controls, the app first attempts same-day saved-run restore through `ResearchPlatform.load_latest_run_artifacts()`
- if same-day restore succeeds, the app skips full pipeline recomputation
- if same-day restore fails, the app recomputes through `ResearchPlatform.run()`
- `Force Weekly Universe Refresh` bypasses weekly universe snapshot reuse for symbol resolution
- `Force Price Data Refresh` bypasses the price-cache TTL for the active run while keeping existing cached price rows as merge/fallback data

### 2.2 Shared context and health

All pages can show:

- a context strip with `Data source: <artifacts.data_source_label>`
- a warning banner when sample fallback is present
- an info banner when stale cache or missing datasets exist
- a `Data Health` expander with `artifacts.fetch_status`, `artifacts.universe_snapshot_path` when present, and `artifacts.run_directory` when present

### 2.3 Watchlist preference persistence

The watchlist page persists its sidebar state through `UserPreferenceStore`.

Current implemented behavior:

- persistence group for current sidebar state: `watchlist_controls`
- named preset collection group: `watchlist_presets`
- namespace: resolved config path
- current sidebar state stores:
  - `selected_scan_names`
  - `required_scan_names`
  - `optional_scan_names`
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

### 3.2 Sidebar-only watchlist controls

On `Today's Watchlist`, the sidebar additionally exposes:

- saved-preset selectbox
- `Load Preset` action
- `Delete Preset` action
- required-card multiselect
- optional-card multiselect
- optional-threshold input
- post-scan annotation filter multiselect
- duplicate subfilter multiselect
- preset-name input
- `Save Preset` action
- `Update Preset` action
- `Export Preset CSV` download action

Current defaults:

- legacy card defaults come from `scan.default_selected_scan_names` or all card sections when unspecified and are loaded as optional cards
- presets with `required_plus_optional_min` duplicate rules load their required and optional cards into the matching sidebar controls
- annotation-filter defaults come from `scan.enabled_annotation_filters`
- duplicate-subfilter default is empty
- optional threshold defaults to `scan.duplicate_min_count` for optional-only legacy controls or the preset rule's `optional_min_hits`
- preset-name input defaults to empty until the user loads or saves a preset

Preset load behavior:

- saved presets are dropped when they reference scan names that are not available in the current config
- invalid annotation-filter names are ignored against the current config
- optional threshold is clamped to the current optional-card count
- required-card and optional-card UI roles are persisted separately from `duplicate_rule` so required-only selections survive page navigation
- duplicate rules are loaded, editable, and persisted from the required-card, optional-card, and optional-threshold controls
- built-in presets cannot be deleted or updated from the UI
- `Update Preset` overwrites the currently selected saved preset
- `Export Preset CSV` uses the currently selected saved preset record, not unsaved sidebar edits

Preset export CSV behavior:

- one row per selected saved preset
- fixed leading columns: `Output Target`, `Preset Name`, `Duplicate Tickers`
- one additional column per selected scan card using `<display_name> Hit Tickers`
- `Duplicate Tickers` stores the comma-separated ticker list from the preset's projected duplicate band
- each scan-card column stores the comma-separated ticker list shown in that preset's projected card
- file encoding is UTF-8 with BOM for spreadsheet compatibility

Preset tracking behavior:

- each full pipeline recompute syncs export-enabled preset detections into `data_runs/tracking.db`
- same-day saved-run restore refreshes existing tracking prices but does not register new detections
- this sync is automatic and separate from the manual `Export Preset CSV` action
- Tracking Analytics reads from the SQLite tracking database and renders analysis tables

### 3.3 Duplicate Tickers priority band

The page renders a dedicated `Duplicate Tickers` band before the scan cards.

Current logic:

- source rows are rebuilt from raw `artifacts.watchlist` plus raw `artifacts.scan_hits`
- selected annotation filters narrow the displayed watchlist first
- selected required and optional cards determine overlap counting
- required cards must all hit when both required and optional cards are selected
- optional threshold requires at least that many optional-card hits
- when required cards are empty, optional cards use the existing simple `min_count` duplicate rule
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

The page renders a separate ticker card titled `Earnings for today (liquid)`.

Current source:

- `artifacts.earnings_today`
- built from `earnings_today == True` in the eligible snapshot
- sorted by `Hybrid-RS` descending before display when that column is available

The active page displays ticker symbols only.

## 4. Entry Signals

The Entry Signals page is a timing layer, not a scan layer.

Current behavior:

- universe source:
  - default: duplicate tickers from built-in presets whose `preset_status` allows export plus duplicate tickers from the current selected watchlist card set
  - selectable alternatives: preset duplicates only, current-selection duplicates only, Today's Watchlist, or the eligible universe
- sidebar controls:
  - the same watchlist card and duplicate controls used by Today's Watchlist
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

## 6. Tracking Analytics

Tracking Analytics is a preset-hit performance analysis page backed by `data_runs/tracking.db`.

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
- `Detail`: row-level detection detail for the selected scope and horizon
- `Export Observations CSV`: analysis-oriented observation export with one row per detection horizon that has target data
- `Export Detection Scans CSV`: bridge export from detection to hit scan names
- `Tracking Health`: compact diagnostic expander, not a primary analysis surface

Current ranking columns:

- `preset`
- `env`
- `avg%`
- `bench%`
- `excess%`
- `max%`
- `min%`
- `win`
- `n`

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

## 8. Current UI Conventions

- page navigation is defined from a centralized page-definition list and rendered as a top tab selector
- the app loads all page data through `PlatformArtifacts`
- the watchlist page then performs additional UI projection from raw watchlist data and raw scan hits
- numeric display formatting is handled in page-specific helpers
- duplicate highlighting in watchlist cards depends on the projected `duplicate_ticker` field after current sidebar selections are applied
