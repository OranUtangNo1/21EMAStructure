# Dashboard UI Spec

## 1. Active UI Scope

The active Streamlit app exposes exactly three pages:

1. `Today's Watchlist`
2. `Entry Signals`
3. `RS Radar`
4. `Market Dashboard`

There is no active chart, cockpit, sizing, or exit page in the current app.

## 2. Shared UI Behavior

### 2.1 Sidebar controls

The sidebar always exposes:

- `Manual Symbols (optional)`
- `Force Weekly Universe Refresh`
- `Refresh` button

The default config path is resolved internally to `config/default.yaml` and is not currently exposed in the sidebar UI.

The main content area exposes a top page tab bar:

- `Today's Watchlist`
- `Entry Signals`
- `RS Radar`
- `Market Dashboard`

Current navigation behavior:

- page switching uses a single-select top tab control, not a sidebar radio
- the app resolves the active page from a page-definition registry so additional tabs can be added without reshaping the main flow
- page-specific sidebar controls are rendered from the active page definition only

The app reloads artifacts when the user presses `Refresh` or when the tuple `(config_path, manual_symbols, force_universe_refresh)` changes.

Current load behavior:

- explicit `Refresh` always recomputes the pipeline
- otherwise the app first tries to reuse the latest same-day saved run
- saved-run reuse is allowed only when config path, manual-symbol input, and expected trade date match, and `Force Weekly Universe Refresh` is off

### 2.2 Shared context and health

All pages can show:

- a context strip with `Data source: <artifacts.data_source_label>`
- a context strip item with `Load mode: Same-day saved run` or `Load mode: Pipeline recomputed`
- a warning banner when sample fallback is present
- an info banner when stale cache or missing datasets exist
- a `Data Health` expander with `Load mode`, `artifacts.fetch_status`, `artifacts.universe_snapshot_path` when present, and `artifacts.run_directory` when present

### 2.3 Watchlist preference persistence

The watchlist page persists its sidebar state through `UserPreferenceStore`.

Current implemented behavior:

- persistence group for current sidebar state: `watchlist_controls`
- named preset collection group: `watchlist_presets`
- namespace: resolved config path
- current sidebar state stores:
  - `selected_scan_names`
  - `selected_annotation_filters`
  - `selected_duplicate_subfilters`
  - `duplicate_threshold`
- preset records store:
  - `schema_version`
  - `kind`
  - `values`
- preset `values` currently contain the same four watchlist control fields
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
  - `Duplicate Threshold`

### 3.2 Sidebar-only watchlist controls

On `Today's Watchlist`, the sidebar additionally exposes:

- saved-preset selectbox
- `Load Preset` action
- `Delete Preset` action
- card multiselect used for watchlist-card display and duplicate counting
- post-scan annotation filter multiselect
- duplicate subfilter multiselect
- duplicate threshold input
- preset-name input
- `Save Preset` action
- `Update Preset` action
- `Export Preset CSV` download action

Current defaults:

- card defaults come from `scan.default_selected_scan_names` or all card sections when unspecified
- annotation-filter defaults come from `scan.enabled_annotation_filters`
- duplicate-subfilter default is empty
- duplicate threshold defaults to `scan.duplicate_min_count`
- preset-name input defaults to empty until the user loads or saves a preset

Preset load behavior:

- saved presets are dropped when they reference scan names that are not available in the current config
- invalid annotation-filter names are ignored against the current config
- duplicate threshold is clamped to the current selected-card count
- hidden preset duplicate rules are loaded and persisted, but are not editable from the current UI
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

Preset effectiveness log behavior:

- each artifact refresh also syncs cumulative preset-effectiveness files under `data_runs/preset_effectiveness/`
- this sync is automatic and separate from the manual `Export Preset CSV` action
- the current UI does not render these files directly

### 3.3 Duplicate Tickers priority band

The page renders a dedicated `Duplicate Tickers` band before the scan cards.

Current logic:

- source rows are rebuilt from raw `artifacts.watchlist` plus raw `artifacts.scan_hits`
- selected annotation filters narrow the displayed watchlist first
- selected scan cards determine overlap counting
- the sidebar duplicate threshold applies only when the current duplicate rule uses `min_count`
- when a loaded preset provides a hidden duplicate rule, that rule drives duplicate membership in the projected view
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

- only selected scan cards are shown
- card selection does not change the raw watchlist candidate set
- selected annotation filters can remove names from cards
- current duplicate threshold can change the duplicate badge state used by the card projection
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
  - duplicate tickers from built-in presets whose `preset_status` allows export
  - duplicate tickers from the current selected watchlist card set
- sidebar controls:
  - the same watchlist card and duplicate controls used by Today's Watchlist
  - an entry-signal multiselect from enabled entry signal definitions
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

The page evaluates whether an already-detected duplicate ticker is at a reasonable entry point today. It does not expand the candidate universe beyond duplicate tickers in the initial implementation.

## 5. RS Radar

### 5.1 Header

The page header shows:

- title: `RS Radar`
- subtitle: `ETF-based radar using configured sector and industry universes.`
- `Updated: HH:MM:SS`

### 4.2 Left column

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

### 4.3 Right and lower sections

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

## 6. Market Dashboard

### 6.1 Header

The page header is centered and shows:

- title: `Market Dashboard`
- `Updated: HH:MM:SS`

### 6.2 Top layout

The page uses a three-part top layout:

- `Market Conditions` hero panel
- prior-score stack for `1D Ago`, `1W Ago`, `1M Ago`, and `3M Ago`
- compact metric-card panels for:
  - `Breadth & Trend Metrics`
  - `Performance Overview`
  - `High & VIX`

The page does not render the older top stat-card row or a separate component-score table.

### 6.3 Market Conditions hero

The hero panel shows:

- the current `label`
- the current `score`
- a semicircle gauge filled from `score / 100`

The four prior-score cards show:

- the historical score
- the label derived from that historical score

### 6.4 Summary metric panels

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

### 5.5 Core / Leadership / External

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

### 5.6 Factors vs SP500

The page renders `Factors vs SP500` as stacked factor cards and uses the configured factor universe.

Each factor row currently shows:

- factor name
- factor ticker
- `REL 1W %`
- `REL 1M %`
- mini bars for the 1W and 1M values

The underlying result frame still includes `REL 1Y %`, but the active page does not render it.

### 5.7 S5TH chart

The page does not render the S5TH chart.

The underlying result object may still carry `result.s5th_series`, but the active Market Dashboard does not display it.

## 7. Current UI Conventions

- page navigation is defined from a centralized page-definition list and rendered as a top tab selector
- the app loads all page data through `PlatformArtifacts`
- the watchlist page then performs additional UI projection from raw watchlist data and raw scan hits
- numeric display formatting is handled in page-specific helpers
- duplicate highlighting in watchlist cards depends on the projected `duplicate_ticker` field after current sidebar selections are applied
