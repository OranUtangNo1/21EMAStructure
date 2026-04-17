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
selected_scan_names: [Sustained Leadership, Near 52W High]
selected_annotation_filters: [Trend Base, Fund Score > 70, RS 21 >= 63]
selected_duplicate_subfilters: []
duplicate_threshold: 2
duplicate_rule:
  mode: min_count
  min_count: 2
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

## Post-Scan And Duplicate Settings

- selected annotation filters: `Trend Base`, `Fund Score > 70`, `RS 21 >= 63`
- selected duplicate subfilters: none
- UI optional threshold after preset load: not used by `min_count`
- preset status: `enabled`
- duplicate rule: `min_count`; requires both selected scans because `min_count=2`

## Scan Role Mapping

| Role | Scan | Rationale |
|---|---|---|
| Core | `Sustained Leadership` | All-horizon RS (21/63/126) proves persistent institutional holding through market weakness |
| Core | `Near 52W High` | Maintaining 52-week high proximity under market pressure is direct evidence of resilience |
| Filter | `Trend Base`, `Fund Score > 70`, `RS 21 >= 63` | Preset-level annotation filters enforce trend, fundamental score, and RS quality gates |

## Logic Structure

```
duplicate_rule.mode: min_count
min_count: 2
→ ticker must hit both selected scans, then pass every selected annotation filter
```

Representative hit patterns:

- `Sustained Leadership` + `Near 52W High` + all selected annotation filters → near-high leader with fundamental backing and trend/RS quality

## Setup Interpretation

- **Target phase**: relative strength identification during market pressure; watchlist building for recovery
- **Why effective in Under Pressure**: most stocks break down under pressure; those maintaining high-zone RS plus fundamentals signal persistent institutional ownership and will be first to break out when the market environment improves
- **Not an immediate entry preset**: entry timing deferred to Base Breakout or Trend Pullback when market returns to Confirmed Uptrend

## Design Rationale

Sustained Leadership's multi-horizon RS requirement (21/63/126) is environment-independent and identifies stocks that outperform regardless of market state. Near 52W High becomes a much stronger filter under pressure because fewer stocks qualify. The selected annotation filters add trend, RS, and earnings-quality backing. The selected scans do not overlap with breakout triggers (Pocket Pivot, 3WT), pullback detectors (PB Quality, Reclaim), or reversal structure (Trend Reversal Setup, Structure Pivot).

## Scope Notes

- This preset changes watchlist page controls only.
- It does not override global scan thresholds.
