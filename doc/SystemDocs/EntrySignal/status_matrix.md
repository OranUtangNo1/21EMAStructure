# Entry Signal Status Matrix

Source of truth:
- config: `config/default/entry_signals.yaml -> entry_signals.signal_status_map`
- runtime: `src/signals/rules.py::EntrySignalConfig`

Column meaning:
- `Status`: available at runtime after config load.
- `Startup`: selected by default on the Entry Signal page.

Current totals:
- enabled: 5
- disabled: 0
- startup selected: 5

| Entry signal | Status | Startup |
| --- | --- | --- |
| `Pocket Pivot Entry` | `enabled` | `yes` |
| `Structure Pivot Breakout Entry` | `enabled` | `yes` |
| `Pullback Low-Risk Zone` | `enabled` | `yes` |
| `Volume Reclaim Entry` | `enabled` | `yes` |
| `Resistance Breakout Entry` | `enabled` | `yes` |
