# Output Layout And Reuse Contract

## Status

Target contract for completing the no-GUI migration while preserving the current modular output layout.

## 1. Decisions

- OraTek has no GUI in the target state.
- The system does not restore global application state, UI state, or `PlatformArtifacts` from saved files.
- Users review previous results directly from persisted output files.
- Explicit CLI/service execution performs recalculation.
- Persisted calculation outputs are retained only for review, downstream processing, audit, and explicitly required history.
- The current `data_runs/service_outputs/` module layout remains the canonical calculation-output layout.
- The current `data_runs/documents/` layout remains the canonical manually generated document layout.
- `data_runs/legacy_pipeline/` and GUI saved-run directories are removed.
- No additional `runs/<run_id>/` or per-service `meta/` hierarchy is introduced.

## 2. Final `data_runs` Layout

```text
data_runs/
  service_outputs/
    indicators/
    scan/
    preset/
    scan_diagnostics/
    market/
    market_snapshot/
    market_factors/
    rs_radar_sector/
    rs_radar_industry/
    rs_radar_top_daily/
    rs_radar_top_weekly/
    market_context/
    market_report_input/
    preset_exports/
  documents/
    stock_cards/
    compressed_tape/
  market_reports/
  tracking.db
  .gitkeep
```

Directories are created only when their owning command writes an output.
Empty optional directories do not need to exist.
`tracking.db` remains optional and is not used to restore general service results.

## 3. Calculation Outputs

`data_runs/service_outputs/<module>/` remains date-addressable and module-owned.

- frame result: `YYYYMMDD.csv`
- frame metadata: `YYYYMMDD.json`
- JSON result: `YYYYMMDD.json`
- JSON metadata: `YYYYMMDD.meta.json`
- latest-only result where configured: `latest.json` or `latest.md`

Readers use the module name and explicit date key.
Downstream commands may use `latest` only when the output policy explicitly defines latest-only behavior.

## 4. Document Outputs

`data_runs/documents/` contains explicit user/AI document exports rather than reusable calculation state.

- `stock_cards/`: canonical stock-card JSON and optional Markdown rendering
- `compressed_tape/`: standalone compressed-tape exports when requested independently

Final human-facing market reports remain under `data_runs/market_reports/`.

## 5. No Restore Contract

The removed behavior is:

```text
launch GUI -> find latest saved run -> reconstruct global objects -> render prior state
```

The supported behavior is:

```text
review existing output file
run one CLI/service command
run a downstream command using an explicit upstream output
```

Rules:

1. Process startup performs no calculation and no saved-state restoration.
2. Reviewing a prior result performs no calculation.
3. A service run calculates a new result unless it explicitly implements compatible upstream-artifact reuse.
4. Downstream processing loads only declared inputs, not a global saved-run bundle.
5. Missing or incompatible upstream outputs require a clear error or explicit recomputation.
6. No command silently substitutes a nearby date, different config, or unrelated output directory.

## 6. Downstream Reuse

| Downstream operation | Allowed persisted inputs |
| --- | --- |
| Scan | Explicit indicator/snapshot output for the requested date and universe. |
| Market Context | Explicit Market and RS Radar outputs for the same effective date. |
| Market Document | Explicit market summary, RS Radar leadership outputs, and required market history. |
| Final Market Report | One canonical Market Document only. |
| EntrySignal evaluation | Explicit snapshot plus scan/preset results; general UI state is not restored. |
| Stock Card | Shared price history plus explicitly supplied metadata. |

Adjacent metadata files provide row counts, source details, and saved timestamps.
They do not represent restorable application state.

## 7. Removed Directories

```text
data_runs/legacy_pipeline/
data_runs/eligible_snapshot/
data_runs/run_metadata/
data_runs/universe_snapshots/
data_runs/preset_diagnostics/
data_runs/entry_signals/
data_runs/market_context/
data_runs/market_documents/
data_runs/market_summary/
data_runs/radar_summary/
```

Equivalent modular results under `data_runs/service_outputs/` are retained.
User-generated documents and final reports are retained.

## 8. GUI Removal

The target system uses CLI and service APIs only.

Remove:

- the Streamlit application entrypoint
- Streamlit startup scripts
- UI-only rendering, widget state, and saved-run restoration code
- tests that validate only deleted GUI behavior

Reusable calculations, exporters, and data contracts must live under `src/` services, builders, or CLI modules before UI files are removed.

## 9. Migration Rules

1. Keep `service_outputs`, `documents`, `market_reports`, and the shared price cache in place.
2. Stop all writers to `legacy_pipeline` and GUI saved-run directories.
3. Remove global saved-run readers and `DataSnapshotStore` after no active CLI/service depends on them.
4. Delete old generated directories after confirming their useful outputs already exist in retained locations or are no longer required.
5. Do not create duplicate compatibility outputs after cutover.
6. Update defaults so every active output path points only to the retained layout.

## 10. Acceptance Criteria

- No active source or default config references `data_runs/legacy_pipeline`.
- No active source reconstructs global state from saved pipeline artifacts.
- No Streamlit entrypoint or startup script remains.
- CLI/service commands continue to write their existing modular outputs.
- Market Context and Market Document generation works from retained modular outputs.
- Reviewing existing outputs requires no process startup or recalculation.
- Removed directories are not recreated by tests or CLI smoke tests.
