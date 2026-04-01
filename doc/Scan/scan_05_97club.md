# Scan Spec: 97 Club

## Canonical Metadata

| Item | Value |
|---|---|
| Canonical name | `97 Club` |
| UI display name | `97 Club` |
| Implementation owner | `src/scan/rules.py::_scan_97_club` |
| Output | `bool` |

## Evaluation Context

- Evaluated on one latest row after `enrich_with_scan_context()`.
- `_raw_rs(row, 21)` reads `raw_rs21` first and falls back to `rs21`.
- All conditions are combined with `AND`.

## Canonical Boolean Definition

```python
raw_rs21 = _raw_rs(row, 21)
matched = bool(
    row.get("hybrid_score", 0.0) >= config.club_97_hybrid_threshold
    and raw_rs21 >= config.club_97_rs21_threshold
    and row.get("trend_base", False)
)
```

## Required Inputs

| Field | Producer | Missing/default used by scan | Scan use |
|---|---|---|---|
| `hybrid_score` | `src/scoring/hybrid.py::HybridScoreCalculator.score` | `0.0` | `>= config.club_97_hybrid_threshold` |
| `raw_rs21` | `src/scoring/rs.py::RSScorer.score` | fallback to `rs21`, then `nan` | `>= config.club_97_rs21_threshold` |
| `rs21` | `src/scoring/rs.py::RSScorer.score` | `nan` | fallback only |
| `trend_base` | `src/indicators/core.py::IndicatorCalculator.calculate` | `False` | must be `True` |

## Direct Config Dependencies

| Config key | Default | Used as |
|---|---|---|
| `scan.club_97_hybrid_threshold` | `90.0` | lower bound for `hybrid_score` |
| `scan.club_97_rs21_threshold` | `97.0` | lower bound for `raw_rs21` |

## Upstream Field Definitions

- `hybrid_score` is the weighted average of `rs21`, `rs63`, `rs126`, `fundamental_score`, and `industry_score`
- default hybrid weights: `1.0, 2.0, 2.0, 2.0, 3.0`
- default missing policy: `fill_neutral_50`
- hybrid owner: `src/scoring/hybrid.py::HybridScoreCalculator.score`
- `raw_rs21` owner: `src/scoring/rs.py::RSScorer.score`
- `trend_base = (close > sma50) & (wma10_weekly > wma30_weekly)`
