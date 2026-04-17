# Scan Spec: RS Acceleration

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `RS Acceleration` |
| UI display name | `RS Accel` |
| Implementation owner | `src/scan/rules.py::_scan_rs_acceleration` |
| Output | `bool` |
| Direct scan config | `rs_acceleration_rs21_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads only precomputed scoring fields.
- `rs21` and `rs63` are the app RS fields, not RSI fields.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
rs21 = row.get("rs21", float("nan"))
rs63 = row.get("rs63", float("nan"))
matched = bool(
    pd.notna(rs21)
    and pd.notna(rs63)
    and float(rs21) > float(rs63)
    and float(rs21) >= config.rs_acceleration_rs21_min
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `rs21` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` with explicit `notna` guard | `rs21 > rs63` and `>= rs_acceleration_rs21_min` |
| `rs63` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` with explicit `notna` guard | `rs21 > rs63` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.rs_acceleration_rs21_min` | `70.0` | minimum absolute floor for `rs21` |

## Upstream Field Definitions

- `rs21` and `rs63` come from `RSScorer.score()`.
- Each RS field is computed from the symbol's own trailing `close / benchmark_close` ratio history.
- With the current default normalization method (`percentile`), the score is:

```python
ratio = stock_close / benchmark_close
window = ratio.tail(lookback)
rs_value = (window.le(window.iloc[-1]).sum() / len(window)) * 100.0
```

## Relationship To The Annotation Filter

The annotation filter `RS 21 >= 63` is broader than this scan.

- annotation filter: `rs21 >= 63`
- this scan: `rs21 > rs63` and `rs21 >= rs_acceleration_rs21_min`

The scan is therefore an acceleration condition, not just a simple RS floor.
