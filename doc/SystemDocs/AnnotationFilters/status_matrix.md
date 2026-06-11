# Annotation Filter Status Matrix

Source of truth:
- config: `config/default/scan.yaml -> scan.annotation_filter_status_map`
- runtime: `src/scan/rules.py::ScanConfig.from_dict`

Column meaning:
- `Status`: available at runtime after config load.
- `Startup`: selected by default in Watchlist controls.

Current totals:
- active enabled: 5
- startup selected: 0

| Annotation filter | Status | Startup |
| --- | --- | --- |
| `Stage 2 Quality Score` | `enabled` | `no` |
| `Mature / Late Stage Risk Filter` | `enabled` | `no` |
| `Industry Leadership Gate` | `enabled` | `no` |
| `Recent Power Gap` | `enabled` | `no` |
| `Trend Template` | `enabled` | `no` |

Compatibility-only evaluators remain in `src/scan/rules.py::ANNOTATION_FILTER_REGISTRY` for custom and older configs, but are not listed in the default runtime filter set.
