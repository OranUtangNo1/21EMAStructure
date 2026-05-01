# Entry Signal Status Matrix

Source of truth:
- config: `config/default/entry_signals.yaml -> entry_signals.signal_status_map`
- runtime: `src/signals/rules.py::EntrySignalConfig`

Column meaning:
- `Status`: available at runtime after config load.
- `Startup`: selected by default on the Entry Signal page.

Current totals:
- enabled: 6
- disabled: 0
- startup selected: 6

| Entry signal | Status | Startup |
| --- | --- | --- |
| `orderly_pullback_entry` | `enabled` | `yes` |
| `pullback_resumption_entry` | `enabled` | `yes` |
| `momentum_acceleration_entry` | `enabled` | `yes` |
| `accumulation_breakout_entry` | `enabled` | `yes` |
| `early_cycle_recovery_entry` | `enabled` | `yes` |
| `power_gap_pullback_entry` | `enabled` | `yes` |
