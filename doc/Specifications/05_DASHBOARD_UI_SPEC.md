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

- source: `artifacts.duplicate_tickers`
- each row is built from raw scan-hit overlap, not list overlap
- displayed columns available in the artifact:
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

Card rows are built from the matching scan-hit subset and currently expose:

- `Ticker`
- `Name`
- `Hybrid-RS`
- `Overlap`
- `VCS`
- `Duplicate`
- `Earnings`

Only scan-based cards are supported by config.

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

### 5.1 Header and top stats

The page header is centered and shows the update time.

The top stat cards currently show:

- `Market Score`
- `Label`
- `1W Ago`
- `1M Ago`
- `VIX`

### 5.2 Market Conditions block

The Market Conditions section currently renders:

- current score
- current label
- a progress bar from `score / 100`
- a short explanatory panel

### 5.3 Score timeline

The page renders a table with:

- `Now`
- `1D Ago`
- `1W Ago`
- `1M Ago`
- `3M Ago`

### 5.4 Summary tables

The current Market Dashboard renders separate tables for:

- `Breadth & Trend Metrics`
- `Performance Overview`
- `High & VIX`
- `Component Scores`

### 5.5 Market Snapshot

The page renders a `Market Snapshot` table sourced from configured symbols.

Current columns:

- `TICKER`
- `NAME`
- `PRICE`
- `DAY %`
- `VOL vs 50D %`
- `21EMA POS`

The current 21EMA position labels are:

- `below 21EMA Low`
- `inside 21EMA Cloud`
- `above 21EMA High`
- `unknown`

### 5.6 Factors vs SP500

The page renders a `Factors vs SP500` table.

Current columns:

- `TICKER`
- `NAME`
- `REL 1W %`
- `REL 1M %`
- `REL 1Y %`

### 5.7 S5TH chart

The page renders a line chart from `result.s5th_series` using the `pct_above_sma200` series.

---

## 6. Current UI conventions

- The app uses the configured universes from `config/default.yaml`.
- Numeric display formatting is handled in the page-specific builders.
- Duplicate highlighting in watchlist cards depends on the `duplicate_ticker` field from the raw watchlist rows.
- UI data is always sourced from `PlatformArtifacts`, not recomputed inside the page renderer except for presentation-only formatting.
