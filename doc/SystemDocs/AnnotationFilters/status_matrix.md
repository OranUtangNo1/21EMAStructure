# Annotation Filter Status Matrix

Source of truth:
- config: `config/default/scan.yaml -> scan.annotation_filter_status_map`
- runtime: `src/scan/rules.py::ScanConfig.from_dict`

Column meaning:
- `Status`: available at runtime after config load.
- `Startup`: selected by default in Watchlist controls.

Current totals:
- active enabled: 13
- startup selected: 0

| Annotation filter | Status | Startup |
| --- | --- | --- |
| `RS 21 >= 63` | `enabled` | `no` |
| `High Est. EPS Growth` | `enabled` | `no` |
| `PP Count (20d)` | `enabled` | `no` |
| `Trend Base` | `enabled` | `no` |
| `Stage 2 Confirmed` | `enabled` | `no` |
| `Stage 2 Quality Score` | `enabled` | `no` |
| `Trend Template` | `enabled` | `no` |
| `Mature / Late Stage Risk Filter` | `enabled` | `no` |
| `Industry Leadership Gate` | `enabled` | `no` |
| `Stage 4 Avoid` | `enabled` | `no` |
| `Fund Score > 70` | `enabled` | `no` |
| `Resistance Tests >= 2` | `enabled` | `no` |
| `Recent Power Gap` | `enabled` | `no` |
