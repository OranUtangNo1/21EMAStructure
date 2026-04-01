# Scan Spec: Near 52W High

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `Near 52W High` |
| UI display name | `Near 52W High` |
| Implementation owner | `src/scan/rules.py::_scan_near_52w_high` |
| Output | `bool` |
| Direct scan config | `near_52w_high_threshold_pct`, `near_52w_high_hybrid_min` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- Reads precomputed indicator fields and a new field `high_52w` added to `IndicatorCalculator`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
matched = bool(
    pd.notna(row.get("high_52w", float("nan")))
    and row.get("high_52w", 0.0) > 0.0
    and row.get("close", 0.0) >= row.get("high_52w", float("inf")) * (1.0 - config.near_52w_high_threshold_pct / 100.0)
    and row.get("hybrid_score", 0.0) >= config.near_52w_high_hybrid_min
    and row.get("trend_base", False)
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `high_52w` | `src/indicators/core.py::IndicatorCalculator.calculate` | `float("nan")` | price >= high_52w * (1 - threshold_pct / 100) |
| `close` | `src/indicators/core.py::IndicatorCalculator.calculate` | `0.0` | compared against high_52w threshold |
| `hybrid_score` | `src/scoring/hybrid.py::HybridScoreCalculator.score` | `0.0` | `>= near_52w_high_hybrid_min` |
| `trend_base` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

| Config key | Location | Default | Scan use |
|---|---|---|---|
| `near_52w_high_threshold_pct` | `config/default.yaml::scan` | `5.0` | price distance allowance from 52W high (%) |
| `near_52w_high_hybrid_min` | `config/default.yaml::scan` | `70.0` | minimum hybrid score to pass |

## Upstream Field Definitions

- `high_52w = high.rolling(252).max()` — rolling 252-session high of the `high` column, computed in `IndicatorCalculator.calculate()`. **This field does not yet exist and must be added.**
- `hybrid_score` — weighted average of `[rs21, rs63, rs126, fundamental_score, industry_score]` with weights `[1, 2, 2, 2, 3]`; NaN filled with `50.0`
- `trend_base = (close > sma50) & (wma10_weekly > wma30_weekly)`

## New Field Required: `high_52w`

`high_52w` is not currently produced by `IndicatorCalculator`. The following line must be added to `IndicatorCalculator.calculate()` after `sma200` is computed:

```python
df["high_52w"] = df["high"].rolling(252).mean()
```

No new config key is required for the rolling window; 252 is the conventional trading-year constant and is hard-coded.

## New Config Keys Required

Add to `config/default.yaml` under the `scan:` block:

```yaml
scan:
  near_52w_high_threshold_pct: 5.0
  near_52w_high_hybrid_min: 70.0
```

Add to `ScanConfig` dataclass in `src/scan/rules.py`:

```python
near_52w_high_threshold_pct: float = 5.0
near_52w_high_hybrid_min: float = 70.0
```
