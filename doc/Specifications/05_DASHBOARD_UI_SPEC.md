# Dashboard UI Spec

## 1. Active UI scope

The active Streamlit app exposes exactly three pages:

1. `Today's Watchlist`
2. `RS Radar`
3. `Market Dashboard`

There is no active chart, cockpit, entry, sizing, or exit page in the current app.

---

## 2. Shared UI behavior

### 2.1 Sidebar controls

The sidebar currently exposes:

- `Config Path`
- `Manual Symbols (optional)`
- `Force Weekly Universe Refresh`
- page selection radio
- `Refresh` button

On `Today's Watchlist`, the sidebar also exposes page-local controls:

- card multiselect used for watchlist-card display
- post-scan annotation filter multiselect
- duplicate subfilter multiselect used only for duplicate-band output
- duplicate threshold input used for duplicate-band counting
- the watchlist control values are persisted per config path in the user-preferences store and restored on the next app start
- initial fallbacks still come from scan config defaults when no persisted value exists

### 2.2 Shared context and health

All pages can show:

- data-source context strip via `artifacts.data_source_label`
- data-health warning banner when stale or sample data exists
- `Data Health` expander with `fetch_status`, universe snapshot path, and run snapshot path

---

## 3. Today's Watchlist

### 3.1 Header area

The current page header shows:

- title: `Today's Watchlist`
- trading date from the latest snapshot row
- subtitle text: `Sorted by Hybrid-RS`
- `Universe Mode`
- `Universe Size`

### 3.2 Duplicate Tickers priority band

The page renders a dedicated `Duplicate Tickers` band before the scan cards.

Current logic:

- source rows are recomputed in the page layer from raw `watchlist` rows plus raw `scan_hits`
- only currently selected scan cards are counted in this band
- the sidebar duplicate threshold is applied to this band only
- duplicate-only subfilters are applied after duplicate rows are formed
- `Top3 HybridRS` keeps the three highest `hybrid_score` duplicate rows
- each row is built from scan overlap, not list overlap
- displayed columns currently include:
  - `Ticker`
  - `Scan Hits`
  - `Hybrid-RS`
  - `Overlap`
  - `VCS`

### 3.3 Scan-card grid

The page renders scan cards from `artifacts.watchlist_cards`.

Each card currently shows:

- display name from `scan.card_sections`
- ticker count
- a ticker grid built from the card rows

Current card behavior:

- only selected scan cards are shown
- card selection does not change the underlying watchlist candidate set
- only scan-based cards are supported by config
- detailed scan meaning is documented under `doc/Scan/`

Card rows are built from the matching scan-hit subset and currently expose:

- `Ticker`
- `Name`
- `Hybrid-RS`
- `Overlap`
- `VCS`
- `Duplicate`
- `Earnings`

### 3.4 Earnings for today

The page renders a separate ticker card titled `Earnings for today (liquid)`.

Current source:

- `artifacts.earnings_today`
- built from `earnings_today == True` in the eligible snapshot
- sorted by `hybrid_score desc`, then `market_cap desc`

---

## 4. RS Radar

### 4.1 Header

The page header shows:

- title: `RS Radar`
- subtitle: ETF-based radar using configured sector and industry universes
- `Updated: HH:MM:SS`

### 4.2 Left column

The left column contains two panels:

- `Top 3 RS% Change (Daily)`
- `Top 3 RS% Change (Weekly)`

Each panel is sourced from the ETF radar universe and currently shows:

- `RS`
- `TICKER`
- `NAME`
- `PRICE`
- one performance column (`DAY %` or `WK %`)
- one relative-strength change column (`RS DAY%` or `RS WK%`)

### 4.3 Right / lower sections

The page also renders:

- `Sector Leaders`
- `Industry Leaders`

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

---

## 5. Market Dashboard

### 5.1 Header

The page header is centered and shows:

- title: `Market Dashboard`
- `Updated: HH:MM:SS`

### 5.2 Top layout

The page now uses a three-part top layout instead of the former stat-card row.

Current rendered areas:

- `Market Conditions` hero panel with explanatory copy
- current score chip using the current market label
- semicircle score gauge derived from `score`
- four prior-score cards: `1D Ago`, `1W Ago`, `1M Ago`, `3M Ago`
- `Breadth & Trend Metrics` metric card grid
- `Performance Overview` metric card grid
- `High & VIX` metric card grid

The page no longer renders the old top stat cards or the separate `Component Scores` table.

### 5.3 Market Conditions hero

The hero panel currently shows:

- a short explanation of how market conditions are determined
- the current `label`
- the current `score`
- a semicircle gauge filled from `score / 100`

The prior-score stack currently shows one card each for:

- `1D Ago`
- `1W Ago`
- `1M Ago`
- `3M Ago`

Each prior-score card shows:

- the rounded prior score
- the label computed for that historical score

### 5.4 Summary metric panels

The Market Dashboard now renders compact metric cards instead of tables.

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

Current `High & VIX` items:

- `S2W High`
- `VIX`

### 5.5 Core / Leadership / External

The page renders three snapshot sections using the same card layout:

- `Core`
- `Leadership`
- `External`

`Core` is the only universe used for `Market Score`.
`Leadership` and `External` are display-only sections and do not feed the score.

Each card currently shows:

- configured symbol name
- `21EMA POS` badge
- display ticker
- `PRICE`
- `DAY %`
- `VOL vs 50D %`

The underlying 21EMA position labels are still sourced from the market snapshot builder:

- `below 21EMA Low`
- `inside 21EMA Cloud`
- `above 21EMA High`
- `unknown`

### 5.6 Factors vs SP500

The page renders `Factors vs SP500` as stacked factor cards instead of a table and uses the configured factors-only universe.

Each factor row currently shows:

- factor name
- factor ticker
- `REL 1W %`
- `REL 1M %`
- mini bars for the 1W and 1M values

The page does not render `REL 1Y %` in this panel even though the underlying result frame still includes it.

### 5.7 S5TH chart

The page no longer renders the S5TH chart.
The underlying result object may still carry `result.s5th_series`, but the active Market Dashboard does not display it.

---

## 6. Current UI conventions

- The app uses the configured universes from `config/default.yaml`.
- Numeric display formatting is handled in the page-specific builders.
- Duplicate highlighting in watchlist cards depends on the `duplicate_ticker` field from the raw watchlist rows.
- UI data is always sourced from `PlatformArtifacts`, not recomputed inside the page renderer except for presentation-only formatting.
