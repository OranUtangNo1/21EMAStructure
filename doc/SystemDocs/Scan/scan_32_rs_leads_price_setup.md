# Scan Spec: RS Leads Price Setup

## Canonical Metadata

| Item | Value |
| --- | --- |
| Canonical name | `RS Leads Price Setup` |
| UI display name | `RS Leads Price` |
| Implementation owner | `src/scan/rules.py::_scan_rs_leads_price_setup` |
| Runtime status | `enabled` |

## Purpose

Detects Stage 2 names where relative strength has already made a 52-week or 3-year high while price is still below its 52-week high. This is a pre-breakout leadership setup, not a price breakout by itself.

## Rule Logic

```python
matched = (
    Stage 2 Confirmed
    and Mature / Late Stage Risk Filter passes
    and raw_rs21 >= scan.rs_leads_price_rs_min
    and stage2_quality_score >= scan.rs_leads_price_quality_min
    and (rs_ratio_at_52w_high or rs_ratio_at_3y_high)
    and scan.rs_leads_price_dist_from_52w_high_min
        <= dist_from_52w_high
        <= scan.rs_leads_price_dist_from_52w_high_max
)
```

## Config Keys

| Key | Default | Role |
| --- | ---: | --- |
| `scan.rs_leads_price_rs_min` | `75.0` | minimum short-term RS |
| `scan.rs_leads_price_quality_min` | `70.0` | minimum Stage 2 quality score |
| `scan.rs_leads_price_dist_from_52w_high_max` | `-3.0` | avoids already-broken-out price |
| `scan.rs_leads_price_dist_from_52w_high_min` | `-30.0` | avoids prices too far from the prior high |

