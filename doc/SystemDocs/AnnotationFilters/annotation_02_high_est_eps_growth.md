# Annotation Filter Spec: High Est. EPS Growth

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical filter name | `High Est. EPS Growth` |
| Implementation owner | `src/scan/rules.py::_annotation_high_eps_growth` |
| Output | `bool` |
| Direct config dependencies | `scan.high_eps_growth_rank_threshold` |

## Canonical Boolean Definition

```python
matched = bool(row.get("eps_growth_rank", 0.0) >= config.high_eps_growth_rank_threshold)
```

## Required Inputs

| Field | Producer | Missing/default | Use |
|---|---|---|---|
| `eps_growth_rank` | `src/scan/rules.py::enrich_with_scan_context` | `0.0` | compare against configured threshold |

## Direct Config Dependencies

| Config key | Default |
|---|---|
| `scan.high_eps_growth_rank_threshold` | `90.0` |
