# Scan Status Matrix

Source of truth:
- config: `config/default/scan.yaml -> scan.scan_status_map`
- runtime: `src/scan/rules.py::ScanConfig.from_dict`

Column meaning:
- `Status`: enabled for scan evaluation.
- `Card`: visible in Watchlist scan controls after `card_sections` filtering.
- `Startup`: selected at app startup after `default_selected_scan_names` is filtered to active cards.

Current totals:
- enabled scan rules: 20
- visible scan cards: 19
- startup selected scans: 16

| Scan | Status | Card | Startup |
| --- | --- | --- | --- |
| `21EMA scan` | `enabled` | `no` | `no` |
| `21EMA Pattern H` | `enabled` | `yes` | `yes` |
| `21EMA Pattern L` | `enabled` | `yes` | `yes` |
| `Pullback Quality scan` | `enabled` | `yes` | `yes` |
| `Reclaim scan` | `enabled` | `yes` | `yes` |
| `4% bullish` | `enabled` | `yes` | `yes` |
| `Vol Up` | `disabled` | `no` | `no` |
| `Volume Accumulation` | `enabled` | `yes` | `yes` |
| `Momentum 97` | `enabled` | `yes` | `yes` |
| `97 Club` | `disabled` | `no` | `no` |
| `VCS` | `disabled` | `no` | `no` |
| `VCS 52 High` | `enabled` | `yes` | `yes` |
| `VCS 52 Low` | `enabled` | `yes` | `yes` |
| `Pocket Pivot` | `enabled` | `yes` | `yes` |
| `PP Count` | `enabled` | `yes` | `yes` |
| `Weekly 20% plus gainers` | `enabled` | `yes` | `yes` |
| `Near 52W High` | `disabled` | `no` | `no` |
| `Three Weeks Tight` | `disabled` | `no` | `no` |
| `VCP 3T` | `enabled` | `yes` | `yes` |
| `RS Acceleration` | `disabled` | `no` | `no` |
| `Sustained Leadership` | `disabled` | `no` | `no` |
| `Trend Reversal Setup` | `enabled` | `yes` | `yes` |
| `Structure Pivot` | `disabled` | `no` | `no` |
| `LL-HL Structure 1st Pivot` | `enabled` | `yes` | `no` |
| `LL-HL Structure 2nd Pivot` | `enabled` | `yes` | `no` |
| `LL-HL Structure Trend Line Break` | `enabled` | `yes` | `no` |
| `50SMA Reclaim` | `enabled` | `yes` | `yes` |
| `RS New High` | `enabled` | `yes` | `yes` |
