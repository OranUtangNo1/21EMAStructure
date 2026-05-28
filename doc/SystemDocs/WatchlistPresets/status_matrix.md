# Watchlist Preset Status Matrix

Source of truth:
- config: `config/default/scan.yaml -> scan.watchlist_presets`
- runtime: `src/scan/rules.py::ScanConfig.from_dict`

Column meaning:
- `Status`: effective runtime preset status.
- `UI`: visible in the built-in preset picker.
- `Export`: included in built-in preset exports.
- `Inactive scans`: selected scans that are currently disabled. Any non-empty value forces runtime `Status` to `disabled`.

Current totals:
- enabled: 9
- hidden_enabled: 0
- disabled: 9

| Preset | Status | UI | Export | Inactive scans |
| --- | --- | --- | --- | --- |
| `Leader Breakout` | `disabled` | `no` | `no` | `97 Club`, `RS Acceleration`, `Three Weeks Tight` |
| `Orderly Pullback` | `disabled` | `no` | `no` | `RS Acceleration` |
| `Reclaim Trigger` | `enabled` | `yes` | `yes` | `-` |
| `Fresh Stage 2 Breakout` | `enabled` | `yes` | `yes` | `-` |
| `Momentum Surge` | `disabled` | `no` | `no` | `Sustained Leadership` |
| `Early Cycle Recovery` | `disabled` | `no` | `no` | `Trend Reversal Setup`, `VCS 52 Low` |
| `Base Breakout` | `disabled` | `no` | `no` | `97 Club`, `Three Weeks Tight` |
| `Accumulation Breakout` | `enabled` | `yes` | `yes` | `-` |
| `VCP 3T Breakout` | `enabled` | `yes` | `yes` | `-` |
| `50SMA Defense` | `enabled` | `yes` | `yes` | `-` |
| `Power Gap Pullback` | `enabled` | `yes` | `yes` | `-` |
| `RS Breakout Setup` | `enabled` | `yes` | `yes` | `-` |
| `Trend Pullback` | `disabled` | `no` | `no` | `RS Acceleration` |
| `Resilient Leader` | `disabled` | `no` | `no` | `Sustained Leadership`, `Near 52W High` |
| `Early Recovery` | `disabled` | `no` | `no` | `Trend Reversal Setup`, `Structure Pivot`, `VCS 52 Low` |
| `Screening Thesis` | `disabled` | `no` | `no` | `Trend Reversal Setup` |
| `Pullback Trigger` | `enabled` | `yes` | `yes` | `-` |
| `Momentum Ignition` | `enabled` | `yes` | `yes` | `-` |
