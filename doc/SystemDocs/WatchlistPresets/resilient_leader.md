# Watchlist Preset Spec: Resilient Leader

## Canonical Metadata

| Item | Value |
|---|---|
| Preset name | `Resilient Leader` |
| Preset type | built-in watchlist preset |
| Runtime source | `config/default/scan.yaml` |
| UI target | `Today's Watchlist` |
| Market environment | `Under Pressure` |

## Current Config Payload

```yaml
preset_name: Resilient Leader
selected_scan_names: [Sustained Leadership, Near 52W High, VCS, Fundamental Demand]
selected_annotation_filters: []
selected_duplicate_subfilters: []
duplicate_threshold: 1
duplicate_rule:
  mode: required_plus_optional_min
  required_scans: [Sustained Leadership, Near 52W High]
  optional_scans: [VCS, Fundamental Demand]
  optional_min_hits: 1
preset_status: enabled
```

## Pre-Scan Context

- preset-specific pre-scan filters: none
- shared pre-scan universe filter: active global `UniverseBuilder.filter()` rules only
- shared scan-context enrichment: `weekly_return_rank`, `quarterly_return_rank`, `eps_growth_rank`

## Selected Scans

| Scan name | Card display | Scan reference | Direct threshold summary |
|---|---|---|---|
| `Sustained Leadership` | `RS Leader` | [../Scan/scan_19_sustained_leadership.md](../Scan/scan_19_sustained_leadership.md) | `sustained_rs21_min=80.0`, `sustained_rs63_min=70.0`, `sustained_rs126_min=60.0` |
| `Near 52W High` | `Near 52W High` | [../Scan/scan_10_near_52w_high.md](../Scan/scan_10_near_52w_high.md) | `near_52w_high_threshold_pct=5.0`, `near_52w_high_hybrid_min=70.0` |
| `VCS` | `VCS` | [../Scan/scan_06_vcs.md](../Scan/scan_06_vcs.md) | `vcs_min_threshold=60.0`, plus hard-coded `raw_rs21 > 60.0` |
| `Fundamental Demand` | `Fund Demand` | [../Scan/scan_18_fundamental_demand.md](../Scan/scan_18_fundamental_demand.md) | `fund_demand_fundamental_min=70.0`, `fund_demand_rs21_min=60.0`, `fund_demand_rel_vol_min=1.0` |

## Post-Scan And Duplicate Settings

- selected annotation filters: none
- selected duplicate subfilters: none
- UI duplicate threshold after preset load: `1`
- preset status: `enabled`
- duplicate rule: `required_plus_optional_min`; requires every scan in `Sustained Leadership, Near 52W High` plus at least `1` hit from optional scans `VCS, Fundamental Demand`

## Scan Role Mapping

| Role | Scan | Rationale |
|---|---|---|
| Core | `Sustained Leadership` | All-horizon RS (21/63/126) proves persistent institutional holding through market weakness |
| Core | `Near 52W High` | Maintaining 52-week high proximity under market pressure is direct evidence of resilience |
| Confirmation | `VCS` | Volatility contraction score ≥ 60 shows selling pressure is contained, not expanding |
| Confirmation | `Fundamental Demand` | Fundamental score ≥ 70 + RS + volume provides earnings-quality backing |

## Logic Structure

```
duplicate_rule.mode: required_plus_optional_min
required_scans: [Sustained Leadership, Near 52W High]
optional_scans: [VCS, Fundamental Demand]
optional_min_hits: 1
→ ticker must hit every required scan and 1+ optional scan
```

Representative hit patterns:

- `Sustained Leadership` + `Near 52W High` + `VCS` → all-horizon RS leader near highs with contraction
- `Sustained Leadership` + `Near 52W High` + `Fundamental Demand` → near-high leader with fundamental backing and demand

## Setup Interpretation

- **Target phase**: relative strength identification during market pressure; watchlist building for recovery
- **Why effective in Under Pressure**: most stocks break down under pressure; those maintaining high-zone RS + contraction + fundamentals signal persistent institutional ownership and will be first to break out when the market environment improves
- **Not an immediate entry preset**: entry timing deferred to Base Breakout or Trend Pullback when market returns to Confirmed Uptrend

## Design Rationale

Sustained Leadership's multi-horizon RS requirement (21/63/126) is environment-independent and identifies stocks that outperform regardless of market state. Near 52W High becomes a much stronger filter under pressure because fewer stocks qualify. VCS confirms quiet institutional holding. Fundamental Demand adds earnings-quality backing. None of these scans overlap with breakout triggers (Pocket Pivot, 3WT), pullback detectors (PB Quality, Reclaim), or reversal structure (Trend Reversal Setup, Structure Pivot).

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
