# Tracking Analytics and Database

## 1. Purpose

This document defines the current preset-hit tracking design implemented in SQLite and rendered through the Tracking Analytics page.

The tracking system answers:

- which export-enabled preset hit which ticker on which hit date
- which scans and selected filters were attached at detection time
- what the ticker returned after 1, 5, 10, and 20 business days
- how preset performance compares with a selected benchmark over the same hit-date-aligned horizon

It does not implement portfolio positions, sizing, stop logic, trade exits, or realized P&L.

## 2. Storage Model

The active database path is:

- `data_runs/tracking.db`

Schema ownership:

- schema SQL: `src/data/tracking_schema.sql`
- initialization: `src/data/tracking_db.py::initialize_tracking_db`
- connection helper: `src/data/tracking_db.py::connect_tracking_db`
- read API: `src/data/tracking_repository.py`

The database is initialized lazily when the app or helper code connects to it.

## 3. Tables

### 3.1 detection

`detection` is the main fact table.

Grain:

- one row per `hit_date x preset_name x ticker`

Current uniqueness rules:

- `UNIQUE(hit_date, preset_name, ticker)`
- one active detection per `preset_name x ticker` through a partial unique index where `status = 'active'`

Core fields:

- `hit_date`
- `preset_name`
- `ticker`
- `status`: `active` or `closed`
- `market_env`
- `close_at_hit`
- `close_at_1d`, `close_at_5d`, `close_at_10d`, `close_at_20d`
- `return_1d`, `return_5d`, `return_10d`, `return_20d`
- `rs21_at_hit`
- `vcs_at_hit`
- `atr_at_hit`
- `hybrid_score_at_hit`
- `duplicate_hit_count`
- `max_gain_20d`
- `max_drawdown_20d`
- optional entry-analysis fields currently reserved in schema: `entered`, `entry_date`, `entry_price`

Current behavior:

- new detections are registered only for export-enabled built-in presets
- the preset's own duplicate rule decides whether a ticker is emitted as a detection
- if the same `preset_name x ticker` already has an active detection, a later hit does not create a second active detection
- when migrated legacy CSVs contain multiple dates for the same `preset_name x ticker`, the oldest hit date is preferred

### 3.2 detection_scans

`detection_scans` stores the scan names that contributed to a tracked detection.

Grain:

- one row per `detection_id x scan_name`

This table preserves detection-time scan context for later analysis even if preset definitions change.

### 3.3 detection_filters

`detection_filters` stores selected annotation filters associated with the preset at detection time.

Grain:

- one row per `detection_id x filter_name`

### 3.4 scan_hits

`scan_hits` stores date-level scan hit history.

Grain:

- one row per `hit_date x ticker x scan_name`

Current role:

- supports saved-run restoration of watchlist scan hits
- gives analysis and migration code a durable scan-hit source outside per-day CSV files

## 4. Write And Refresh Flow

### 4.1 App sync

`app/main.py` calls `src/dashboard/effectiveness.py::sync_preset_effectiveness_logs()` after artifact load.

Current behavior:

- full pipeline recompute registers new detections and refreshes returns
- same-day saved-run restore refreshes existing returns but does not register new detections
- scan-hit history is inserted into `scan_hits`
- tracking health counts are saved into Streamlit session state for diagnostics

### 4.2 Detection registration

For each export-enabled built-in preset:

1. apply the preset's selected annotation filters to the raw watchlist
2. project selected scan metrics with the preset's duplicate rule
3. keep rows where projected `duplicate_ticker` is true
4. insert a detection row with detection-time fields
5. insert bridge rows for hit scans and selected filters

Preset hit history is therefore based on what the preset emitted at runtime, not on the latest preset definition alone.

### 4.3 Forward-return refresh

Forward horizons are fixed:

- 1 business day
- 5 business days
- 10 business days
- 20 business days

Target dates are calculated from `hit_date + BDay(horizon_days)`.

Refresh behavior:

- load price histories for tickers that still need detection updates
- fill `close_at_hit` from the first close on or after `hit_date`
- fill each horizon close from the first close on or after the target business date
- compute return percentage from `close_at_hit` to the horizon close
- mark a detection `closed` after the 20D return is filled

This design allows non-trading days and missing price dates to be handled by using the next available close.

### 4.4 Manual refresh helper

The CLI helper is:

- `src/utils/run_tracking_refresh.py`

It calls `refresh_tracking_detection_prices()` and can refresh target closes and returns without running a full screening recompute.

## 5. Views

The SQLite schema defines these views:

- `v_detection_detail`
- `v_preset_horizon_performance`
- `v_preset_scan_performance`
- `v_preset_summary`
- `v_scan_combo_performance`
- `v_preset_overlap`

Current app usage:

- Tracking Analytics reads `v_detection_detail` through `read_detection_detail()`
- repository functions expose horizon and scan performance views for analysis and future UI use

## 6. Tracking Analytics UI

Page owner:

- `app/main.py::render_tracking_analytics`

Filters:

- `Preset Universe`: multiselect over built-in preset names
- `Horizon`: one selected value from `1`, `5`, `10`, `20`
- `Hit Date Range`: detection `hit_date` range
- `Hit Market Env`: multiselect over `bull`, `neutral`, `weak`, `bear`
- `Benchmark`: one selected value from `SPY`, `QQQ`, `IWM`

Benchmark behavior:

- benchmark return is calculated per hit date and selected horizon
- the comparison window is not the overall UI date range
- the benchmark target date uses the same business-day horizon logic as detections
- benchmark prices are loaded through `YFinancePriceDataProvider` and the normal cache layer

Result areas:

- `Ranking`: grouped preset performance for the selected scope and horizon
- `Detail`: row-level detection records for the selected scope
- observation CSV export: one row per detection horizon with available target data
- detection-scan CSV export: one row per detection and hit scan
- Tracking Health expander: diagnostics only

## 7. Analysis Interpretation

Tracking rows are historical observations.

If a preset is renamed or its contents change:

- existing rows remain valid database records
- later analysis may need manual mapping to compare old and new preset definitions
- the system should not rewrite old rows to match current config

This is intentional. The database preserves what was observed, while preset config controls what will be emitted in future runs.

## 8. Legacy CSV Migration

Legacy tracking files can be migrated from:

- `data_runs/preset_effectiveness/events.csv`
- `data_runs/preset_effectiveness/outcomes.csv`
- `data_runs/scan_hits/*.csv`

Migration owner:

- `src/data/tracking_migration.py::backfill_tracking_db_from_csvs`

Migration rule:

- when multiple legacy rows exist for the same `preset_name x ticker`, the oldest hit date is kept

Those CSVs are not the current authoritative tracking store after migration.
