# Watchlist Preset Status Matrix

Source of truth:
- config: `config/default/scan.yaml -> scan.watchlist_presets`
- runtime: `src/scan/rules.py::ScanConfig.from_dict`

Column meaning:
- `Status`: effective runtime preset status.
- `UI`: visible in the built-in preset picker.
- `Export`: included in built-in preset exports.

Current totals:
- active enabled: 9

| Preset | Status | UI | Export |
| --- | --- | --- | --- |
| `Reclaim Trigger` | `enabled` | `yes` | `yes` |
| `Fresh Stage 2 Breakout` | `enabled` | `yes` | `yes` |
| `Accumulation Breakout` | `enabled` | `yes` | `yes` |
| `VCP 3T Breakout` | `enabled` | `yes` | `yes` |
| `50SMA Defense` | `enabled` | `yes` | `yes` |
| `Power Gap Pullback` | `enabled` | `yes` | `yes` |
| `RS Breakout Setup` | `enabled` | `yes` | `yes` |
| `Pullback Trigger` | `enabled` | `yes` | `yes` |
| `Momentum Ignition` | `enabled` | `yes` | `yes` |
