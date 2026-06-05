# Scan Spec: VCP 3T

## Canonical Metadata

| Item | Value |
| --- | --- |
| Canonical name | `VCP 3T` |
| UI display name | `VCP 3T` |
| Implementation owner | `src/scan/rules.py::_scan_vcp_3t` |
| Indicator owner | `src/indicators/core.py::_calculate_vcp_3t_fields` |
| Runtime status | `enabled` |

## Purpose

Detects a VCP-style tightening setup that is contracting, drying up, and waiting just below the mechanical pivot:

- recent ADR is materially below the prior base ADR
- the measured T1/T2/T3 contraction depths are progressively narrowing (`T1 > T2 > T3`)
- the base formed after a configured prior uptrend
- recent high-low span is tight
- recent volume is below the base average volume
- current close is below the prior pivot but within the configured proximity band
- price is in a Stage 2 moving-average context
- same-day pivot breakout is not required and is not used by this scan

## Rule Logic

```python
matched = bool(row.get("vcp_tightening", False))
```

## Required Inputs

| Field | Source | Meaning |
| --- | --- | --- |
| `vcp_tightening` | `IndicatorCalculator` | integrated VCP setup state used by this scan |
| `vcp_is_contracting` | `IndicatorCalculator` | recent ADR is below the configured ratio of base ADR and below the ADR ceiling |
| `vcp_is_3t_contracting` | `IndicatorCalculator` | measured contraction depths satisfy `vcp_t1_depth_pct > vcp_t2_depth_pct > vcp_t3_depth_pct` |
| `vcp_has_prior_uptrend` | `IndicatorCalculator` | prior uptrend percentage is at or above the configured minimum |
| `vcp_is_tight` | `IndicatorCalculator` | recent high-low span is below the configured range ceiling |
| `vcp_is_dryup` | `IndicatorCalculator` | recent average volume is below the configured VDU ratio of base average volume |
| `vcp_is_under_pivot` | `IndicatorCalculator` | current close is below the prior pivot and within the proximity band |
| `vcp_stage2_context` | `IndicatorCalculator` | close and moving averages are in Stage 2 order |
| `vcp_pivot_price` | `IndicatorCalculator` | prior high over the configured pivot lookback |
| `vcp_pivot_breakout` | `IndicatorCalculator` | current close crosses above the pivot price on the first edge; not required by this scan |
| `vcp_pivot_proximity_pct` | `IndicatorCalculator` | current close distance from pivot, positive above pivot and negative below pivot |
| `vcp_dist_to_pivot` | `IndicatorCalculator` | decimal distance from close to pivot when close is below pivot |

## Config Keys

| Key | Default | Role |
| --- | ---: | --- |
| `indicators.vcp_base_lookback` | `50` | base window for ADR and volume comparison |
| `indicators.vcp_tight_window` | `10` | recent tightening window |
| `indicators.vcp_pivot_lookback` | `20` | mechanical pivot lookback |
| `indicators.vcp_prior_uptrend_min_pct` | `30.0` | minimum prior uptrend before the base |
| `indicators.vcp_contraction_ratio` | `0.78` | recent ADR must be below this ratio of base ADR |
| `indicators.vcp_adr_ceiling` | `3.5` | absolute recent ADR ceiling |
| `indicators.vcp_range_ceiling` | `12.0` | recent high-low span ceiling |
| `indicators.vcp_vdu_ratio` | `0.75` | recent volume must be below this ratio of base volume |
| `indicators.vcp_proximity_band` | `0.08` | max decimal distance below pivot |

## Notes

- This scan is now a pre-breakout setup detector, not a breakout-day trigger.
- Same-day pivot breakout is still excluded from the scan condition.
- RS and industry leadership can still be applied through post-scan filters or watchlist presets.
