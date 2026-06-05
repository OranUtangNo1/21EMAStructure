# Analysis and Tracking Database

## 1. Purpose

This document defines the current preset-hit tracking design implemented in SQLite and rendered through the Analysis page.

The tracking system answers:

- which export-enabled preset hit which ticker on which hit date
- which scans and selected filters were attached at detection time
- what the ticker returned after 1, 5, 10, 20, and 21 business days
- how preset performance compares with a selected benchmark over the same hit-date-aligned horizon
- which valid `Ready Now` EntrySignal events reached TP1, reached SL, or timed out over the 20-business-day review window

It does not implement portfolio positions, sizing, order execution, discretionary stop management, trade exits, or realized P&L.

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
- `close_at_1d`, `close_at_5d`, `close_at_10d`, `close_at_20d`, `close_at_21d`
- `return_1d`, `return_5d`, `return_10d`, `return_20d`, `return_21d`
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

### 3.5 signal_pool_entry

`signal_pool_entry` stores EntrySignal monitoring pools created from preset duplicate output.

Grain:

- one row per `signal_name x ticker x first_detected_date`

Current role:

- records the preset sources that contributed the ticker to a signal pool
- tracks active, invalidated, expired, and orphaned pool lifecycle state
- preserves the detection-time snapshot used by later daily EntrySignal evaluation

### 3.6 signal_evaluation

`signal_evaluation` stores each daily EntrySignal evaluation snapshot.

Grain:

- one row per `signal_name x ticker x eval_date`

Current role:

- records setup maturity, timing, risk/reward, and integrated entry-strength scores
- stores the mechanical Entry Plan fields, including `plan_type`, `entry_price`, `stop_loss`, `tp1`, `rr_current`, `rr_ideal`, rejection codes, SL quality/source fields, TP1 source, and plan detail JSON
- keeps rejected and downgraded plans auditable without treating them as entry events

### 3.7 signal_entry_event

`signal_entry_event` stores valid `Ready Now` EntrySignal plans for outcome review.

Grain:

- one row per `signal_name x ticker x event_date`

Current role:

- records the exact Entry Plan snapshot used for outcome tracking
- stores `action_bucket` and normalized `market_env` for Entry Ready origin analysis
- stores fixed 1D, 5D, 10D, 20D, and 21D closes and returns from `entry_price`
- stores TP1/SL hit flags, first hit dates, first outcome, days to first outcome, result R, and 20D / 21D maximum gain and drawdown
- treats same-day TP1-and-SL hits as `ambiguous_same_day` and assigns the conservative `-1R` outcome

## 4. Write And Refresh Flow

### 4.1 App sync

`app/main.py` calls `src/dashboard/effectiveness.py::sync_preset_effectiveness_logs()` after artifact load.

Current behavior:

- full pipeline recompute registers new detections and refreshes returns
- same-day saved-run restore also registers export-enabled preset detections from saved watchlist and scan-hit artifacts, then refreshes returns
- EntrySignal event outcomes are refreshed for due `signal_entry_event` rows using the same price-history loading path
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

### 4.3 Preset forward-return refresh

Forward horizons are fixed:

- 1 business day
- 5 business days
- 10 business days
- 20 business days
- 21 business days

Target dates are calculated from `hit_date + BDay(horizon_days)`.

Refresh behavior:

- load price histories for tickers that still need detection updates
- fill `close_at_hit` from the first close on or after `hit_date`
- fill each horizon close from the first close on or after the target business date
- compute return percentage from `close_at_hit` to the horizon close
- mark a detection `closed` after the 20D return is filled; continue to backfill 21D fields on later refreshes

This design allows non-trading days and missing price dates to be handled by using the next available close.

### 4.4 EntrySignal event outcome refresh

EntrySignal event refresh is limited to rows in `signal_entry_event`.

Refresh behavior:

- select only events that still need a horizon return, TP1/SL outcome, first outcome, or 20D / 21D excursion metric
- load price histories only for due event tickers
- compute fixed 1D, 5D, 10D, 20D, and 21D returns from `entry_price`
- scan future daily bars after `event_date` through the 20-business-day window for SL and TP1 touches
- set `first_outcome` to `tp1`, `sl`, `ambiguous_same_day`, or `time_20d`
- compute `outcome_r` as `1.0` for TP1 first, `-1.0` for SL first or same-day ambiguity, or the 20D close result in R units for timeouts
- compute `max_gain_20d`, `max_drawdown_20d`, `max_gain_21d`, and `max_drawdown_21d` from the future high/low windows

### 4.5 Manual refresh helper

The CLI helper is:

- `src/utils/run_tracking_refresh.py`

It calls `refresh_tracking_detection_prices()` and can refresh preset target closes, preset returns, and EntrySignal event outcomes without running a full screening recompute.

## 5. Views

The SQLite schema defines these views:

- `v_detection_detail`
- `v_preset_horizon_performance`
- `v_preset_scan_performance`
- `v_preset_summary`
- `v_scan_combo_performance`
- `v_signal_entry_performance`
- `v_preset_overlap`

Current app usage:

- Analysis reads `v_detection_detail` through `read_detection_detail()`
- repository functions expose horizon, scan, and Entry Ready event performance views for analysis and future UI use

`v_signal_entry_performance` groups EntrySignal events by `action_bucket`, `signal_name`, and `market_env`. It reports event/ticker counts, 5D/10D/21D returns, 21D win rate, TP1/SL counts and rates, timeout and ambiguous outcome counts, average result R, average days to first outcome, and 21D MFE/MAE.

## 6. Analysis UI

Page owner:

- `app/main.py::render_analysis`

Filters:

- `Preset Universe`: multiselect over built-in preset names
- `Horizon`: one selected value from `1`, `5`, `10`, `21`
- `Hit Date Range`: detection `hit_date` range
- `Hit Market Env`: multiselect over `bull`, `neutral`, `weak`, `bear`
- `Benchmark`: one selected value from `SPY`, `QQQ`, `IWM`

Benchmark behavior:

- the default Analysis horizon is `21D`
- benchmark return is calculated per hit date and selected horizon
- the comparison window is not the overall UI date range
- the benchmark target date uses the same business-day horizon logic as detections
- benchmark prices are loaded through `YFinancePriceDataProvider` and the normal cache layer
- `20D` outcome columns are retained for persisted-data compatibility and internal backfill, but the Analysis UI exposes `21D` as the main monthly horizon instead

Result areas:

- `Ranking`: grouped preset performance for the selected scope and horizon
- `EntrySignal Connection Candidates`: selected-scope connection review for configured preset-to-signal candidates, currently `Fresh Stage 2 Breakout` toward `Accumulation Breakout Entry`
- `Entry Ready Performance`: signal-level `Ready Now` event performance from `v_signal_entry_performance`, grouped by action bucket, signal name, and market environment
- `Detail`: row-level detection records for the selected scope, including fixed horizon close and return columns through the selected horizon
- observation CSV export: one row per detection horizon with available target data
- detection-scan CSV export: one row per detection and hit scan
- Setting page: diagnostics only

Ranking display:

- uses readable column names such as `Tier`, `Preset`, `Market`, `Avg Return (%)`, `Excess vs Benchmark (%)`, `Win Rate (%)`, and `Detections`
- does not display the raw benchmark return column
- highlights positive excess-return rows green and negative excess-return rows red

Preset tier logic keeps groups with `Detections < 30` in `Observing` regardless of apparent return strength. Mature groups can become `Core`, `Candidate`, `Mixed`, `Downgrade Review`, or `Needs Data` based on selected-horizon average return, benchmark excess return, and win rate.

The connection-candidate table reuses the same preset tier logic and the same selected horizon. It is a review surface only. It identifies whether the candidate preset is currently `Connected`, `Connected Elsewhere`, or `Measurement Only`, and shows `Connection Candidate` only when the selected-scope tier is `Core` or `Candidate`. It does not write to `signal_pool_entry`, does not change `entry_signals.yaml`, and does not directly connect a preset to EntrySignal evaluation.

Detail display:

- uses readable column names instead of raw SQLite field names
- formats percentage values with `(%)`
- hides `benchmark_return_pct`
- displays the selected-horizon excess return against the selected benchmark
- shows later horizons as `-`
- highlights positive excess-return rows green and negative excess-return rows red

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
