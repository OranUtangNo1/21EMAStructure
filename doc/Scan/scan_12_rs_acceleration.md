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
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    pd.notna(row.get("rs21", float("nan")))
    and pd.notna(row.get("rs63", float("nan")))
    and row.get("rs21", 0.0) > row.get("rs63", float("inf"))
    and row.get("rs21", 0.0) >= config.rs_acceleration_rs21_min
    and row.get("trend_base", False)
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `rs21` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` → `notna` guard rejects | `rs21 > rs63` and `>= rs_acceleration_rs21_min` |
| `rs63` | `src/scoring/rs.py::RSScorer.score` | `float("nan")` → `notna` guard rejects | `rs21 > rs63` |
| `trend_base` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

| Config key | Location | Default | Scan use |
|---|---|---|---|
| `rs_acceleration_rs21_min` | `config/default.yaml::scan` | `70.0` | minimum rs21 absolute floor |

## Upstream Field Definitions

- `rs21 = raw_rs21` — percentile rank (0–100) of the current `ticker_close / spy_close` ratio within that symbol's own trailing 21-session ratio window:
  ```python
  ratio    = ticker_close / spy_close
  window   = ratio.tail(21)
  rs21     = percentile_rank(window).iloc[-1]
  ```
- `rs63` — same method over a trailing 63-session window:
  ```python
  window   = ratio.tail(63)
  rs63     = percentile_rank(window).iloc[-1]
  ```
- Both fields are self-relative (within the symbol's own history), not cross-sectional.
- `trend_base = (close > sma50) & (wma10_weekly > wma30_weekly)`

## Relationship to Annotation Filter (RS 21 >= 63)

The annotation filter `RS 21 >= 63` uses the app's RS field (`rs21`) and checks a simple floor: `rs21 >= 63`. This scan remains distinct because it requires both `rs21 > rs63` and `rs21 >= rs_acceleration_rs21_min`, plus `trend_base`. The filter is a broad strength gate. This scan is an acceleration-and-trend condition.

## New Config Key Required

Add to `config/default.yaml` under the `scan:` block:

```yaml
scan:
  rs_acceleration_rs21_min: 70.0
```

Add to `ScanConfig` dataclass in `src/scan/rules.py`:

```python
rs_acceleration_rs21_min: float = 70.0
```
