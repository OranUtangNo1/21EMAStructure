# Annotation Filter Status Matrix

Source of truth:
- config: `config/default/scan.yaml -> scan.annotation_filter_status_map`
- runtime: `src/scan/rules.py::ScanConfig.from_dict`

Column meaning:
- `Status`: available at runtime after config load.
- `Startup`: selected by default in Watchlist controls.

Current totals:
- enabled: 7
- disabled: 0
- startup selected: 0

| Annotation filter | Status | Startup |
| --- | --- | --- |
| `RS 21 >= 63` | `enabled` | `no` |
| `High Est. EPS Growth` | `enabled` | `no` |
| `PP Count (20d)` | `enabled` | `no` |
| `Trend Base` | `enabled` | `no` |
| `Fund Score > 70` | `enabled` | `no` |
| `Resistance Tests >= 2` | `enabled` | `no` |
| `Recent Power Gap` | `enabled` | `no` |
