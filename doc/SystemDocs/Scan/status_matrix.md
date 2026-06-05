# Scan Status Matrix

Source of truth:
- config: `config/default/scan.yaml -> scan.scan_status_map`
- runtime: `src/scan/rules.py::ScanConfig.from_dict`

Column meaning:
- `Status`: enabled for scan evaluation.
- `Card`: visible in Watchlist scan controls after `card_sections` filtering.
- `Startup`: selected at app startup after `default_selected_scan_names` is filtered to active cards.

Current totals:
- active scan rules documented here: 22
- visible scan cards: 21
- startup selected scans: 18

| Scan | Status | Card | Startup |
| --- | --- | --- | --- |
| `21EMA scan` | `enabled` | `no` | `no` |
| `21EMA Pattern H` | `enabled` | `yes` | `yes` |
| `21EMA Pattern L` | `enabled` | `yes` | `yes` |
| `Pullback Quality scan` | `enabled` | `yes` | `yes` |
| `Reclaim scan` | `enabled` | `yes` | `yes` |
| `4% bullish` | `enabled` | `yes` | `yes` |
| `Volume Accumulation` | `enabled` | `yes` | `yes` |
| `Momentum 97` | `enabled` | `yes` | `yes` |
| `VCS 52 High` | `enabled` | `yes` | `yes` |
| `Pocket Pivot` | `enabled` | `yes` | `yes` |
| `PP Count` | `enabled` | `yes` | `yes` |
| `Weekly 20% plus gainers` | `enabled` | `yes` | `yes` |
| `VCP 3T` | `enabled` | `yes` | `yes` |
| `LL-HL Structure 1st Pivot` | `enabled` | `yes` | `no` |
| `LL-HL Structure 2nd Pivot` | `enabled` | `yes` | `no` |
| `LL-HL Structure Trend Line Break` | `enabled` | `yes` | `no` |
| `50SMA Reclaim` | `enabled` | `yes` | `yes` |
| `RS New High` | `enabled` | `yes` | `yes` |
| `RS 3Y New High` | `enabled` | `yes` | `yes` |
| `RS Leads Price Setup` | `enabled` | `yes` | `yes` |
| `Trend Template` | `enabled` | `yes` | `yes` |
| `Fresh Stage 2 Breakout` | `enabled` | `yes` | `yes` |
