# Output Artifact Inventory 2026-06-15

Purpose: classify current `data_runs/` outputs by data character, decide default retention policy, and prepare the next implementation step for output selection and directory cleanup.

## Classification Model

Use three classes, not two.

1. `system_internal`
   - Used by the application for restore, history, tracking, audit, or delta calculation.
   - Not intended as user-facing output.

2. `ai_input`
   - Generated artifacts intended to be read by AI/skills.
   - Usually reproducible from `system_internal` data.

3. `user_output`
   - Files a human requested, reviews, shares, or treats as final output.
   - Should normally be created by explicit UI/action, not merely by app startup.

Add one policy axis:

- `daily_history`: keep date-keyed history.
- `latest_only`: overwrite or keep only latest plus optional short history.
- `on_demand`: write only when the user explicitly requests export.
- `disabled`: do not write by default.

## Current Inventory

Snapshot observed on 2026-06-15:

| Path | Files | Size KB | Current trigger | Class | Current necessity | Proposed default |
| --- | ---: | ---: | --- | --- | --- | --- |
| `data_runs/run_metadata/` | 39 | 2158 | pipeline startup/run | `system_internal` | needed for same-day saved-run restore and audit | retain latest 5 saved runs |
| `data_runs/eligible_snapshot/` | 27 | 38366 | pipeline startup/run | `system_internal` | needed for saved-run restore and EntrySignal source rows; largest daily artifact | retain latest 5 saved runs |
| `data_runs/market_summary/` | 39 | 731 | pipeline startup/run | `system_internal` | source for market docs/context and weekly deltas | `daily_history`, retain 90 trading days |
| `data_runs/radar_summary/` | 39 | 722 | pipeline startup/run | `system_internal` | source for RS deltas and market context | `daily_history`, retain 90 trading days |
| `data_runs/universe_snapshots/` | 21 | 3021 | universe refresh | `system_internal` | latest is needed; dated weekly snapshots are audit/debug | `latest_only` plus retain 8 dated snapshots |
| `data_runs/tracking.db` | n/a | n/a | tracking sync/evaluation | `system_internal` | durable source for preset/effectiveness/entry events | keep; manage by DB policy, not file fanout |
| `data_runs/watchlist/` | 0 | 0 | optional pipeline run | `system_internal` | disabled by default; restore rebuilds from eligible snapshot | `disabled` by default |
| `data_runs/market_documents/` | 34 | 1288 | pipeline startup/run | `ai_input` | reproducible from market summary; useful for report skill | `latest_only` or `on_demand`; avoid full daily fanout by default |
| `data_runs/market_context/` | 6 | 10 | pipeline startup/run | `ai_input` | compact AI context; reproducible from market/radar summaries | `latest_only` by default; `daily_history` optional |
| `data_runs/compressed_tape/` | 2 | 2 | explicit UI/export | `ai_input` | on-demand ticker-level AI input | `on_demand` |
| `data_runs/stock_cards/` | 12 | 23 | explicit UI/export | `ai_input` | on-demand ticker-level AI input | `on_demand` |
| `data_runs/entry_signals/` | 18 | 344 | app startup evaluation export | mixed: `system_internal` review artifact | durable state is in `tracking.db`; CSV is inspectable run output | `latest_only` by default; bucket CSVs remain disabled |
| `data_runs/preset_exports/` | 101 | 582 | UI preset export path; startup only if explicitly enabled | `user_output` or review CSV | many intermediate CSVs; user-facing only when explicitly exported | `on_demand`; no startup write by default |
| `data_runs/market_reports/` | 14 | 101 | report-writing skill/manual action | `user_output` | human-facing final report | `on_demand`, keep daily reports |
| `data_runs/manual_price_exports/` | 1 | 132 | explicit manual export | `user_output` | user-requested raw export | `on_demand`, user-managed retention |
| `data_runs/startup_timing.log` | 1 | n/a | app startup | `system_internal` diagnostic | useful only for recent performance debugging | rotate or `latest_only` |

## Key Findings

1. The largest fanout is not Markdown; it is `eligible_snapshot/YYYYMMDD.csv`.
   - Current size is about 1.6 MB per trading day.
   - It is needed for same-day saved-run restore, but older copies are usually audit/debug only.

2. `market_documents` and `market_context` are derived artifacts.
   - Their source is `market_summary` plus recent summaries and radar rows.
   - They can be regenerated if the code/config version is known.
   - Keeping every generated Markdown/JSON by default is not necessary.

3. `entry_signals/YYYYMMDD_evaluations.csv` is a startup review export, not the durable source of truth.
   - Durable state is `tracking.db`.
   - Default should be `latest_only`; history can be explicitly enabled for debugging.

4. `preset_exports` should be treated as user-output only when explicitly requested.
   - Startup-time or automatic CSV fanout creates many files with low long-term value.
   - The tracking database already stores durable preset-hit/event data.

5. `compressed_tape` and `stock_cards` are correctly shaped as on-demand AI input exports.
   - Keep them out of startup writes.
   - Consider putting them under a shared `ai_inputs/ticker/` branch later.

## Proposed Directory Shape

Target shape, not an immediate migration requirement:

```text
data_runs/
  internal/
    restore/
      run_metadata/
      eligible_snapshot/
    summaries/
      market_summary/
      radar_summary/
    universe/
      latest.csv
      latest.json
      archive/
    tracking.db
    logs/
      startup_timing.log

  ai_inputs/
    market_context/
      latest.md
      latest.json
      archive/
    market_documents/
      latest.md
      latest.json
      archive/
    ticker/
      compressed_tape/
      stock_cards/

  exports/
    reports/
    preset_hits/
    entry_signal_reviews/
    manual_price/
```

## Proposed Config Surface

Use one common policy vocabulary.

```yaml
outputs:
  root: data_runs
  retention:
    default_trading_days: 60
    large_internal_trading_days: 10
    market_summary_trading_days: 90
    universe_snapshots: 8

  internal:
    run_metadata: latest_plus_5_runs
    eligible_snapshot: latest_plus_5_runs
    market_summary: daily_history
    radar_summary: daily_history
    universe_snapshot: latest_plus_retention
    startup_timing: latest_only

  ai_inputs:
    market_document: latest_only
    market_context: latest_only
    compressed_tape: on_demand
    stock_card: on_demand

  user_outputs:
    market_report: on_demand
    preset_export: on_demand
    entry_signal_review_csv: latest_only
    manual_price_export: on_demand
```

Compatibility rule:

- Existing paths should remain readable during transition.
- New writes can move first; old-read fallback can be removed after one stable period.

## Implementation Plan

Step 1: Add an output policy resolver.

- New module candidate: `src/data/output_policy.py`.
- Responsibilities:
  - normalize `daily_history/latest_only/on_demand/disabled`;
  - resolve output roots;
  - decide date-keyed path versus `latest` path;
  - expose retention settings.

Step 2: Apply policy to derived AI inputs first.

- `market_documents`: default `latest_only`.
- `market_context`: default `latest_only`.
- Keep `market_summary` and `radar_summary` date-keyed.
- This removes repeated AI artifact fanout while preserving source data.

Step 3: Change startup review exports.

- `entry_signals`: default `latest_only` for `evaluations.csv`.
- Keep bucket CSVs disabled.
- Add an explicit UI export path for historical review if needed.

Step 4: Make preset CSV export explicitly on-demand.

- Keep UI button behavior.
- Avoid automatic startup writes unless `preset_csv_export.mode=daily_history` is explicitly set.

Step 5: Add retention cleanup command.

- Non-destructive first: dry-run report.
- Then optional cleanup for:
  - old `eligible_snapshot`;
  - old `run_metadata`;
  - old `market_documents`/`market_context` archives;
  - old `entry_signals` CSVs.

## Recommended First Code Change

Start with the low-risk derived artifacts:

1. Add config keys for `market_report.output.mode` and `market_context.output.mode`.
2. Support `latest_only` in `DataSnapshotStore._save_market_document()` and `_save_market_context()`.
3. Keep current date-keyed behavior when mode is absent to avoid surprise.
4. Set default config to `latest_only` only after tests cover both modes.

This gives immediate file-count reduction without touching restore-critical data.
