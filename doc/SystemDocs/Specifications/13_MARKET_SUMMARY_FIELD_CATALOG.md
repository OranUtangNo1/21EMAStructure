# Market Summary Field Catalog For AI

## 1. Purpose

This document is the machine-oriented field catalog for
`data_runs/service_outputs/market_report_input/market_summary_YYYYMMDD.json`.
It defines the emitted fields, units, formulas, conditional-output behavior, and current default parameters.

The sample used to confirm the emitted shape is `market_summary_20260618.json`.
Generated JSON is not the behavioral source of truth; formulas in this catalog come from the current implementation and assembled `config/default.yaml` configuration.

This artifact is an intermediate market-summary payload.
It is not the canonical `market_document.v1` report input and is not a trading instruction.

## 2. Notation And General Rules

| Symbol | Definition |
| --- | --- |
| `C_t`, `H_t`, `L_t`, `V_t` | Close, high, low, and volume at trading session `t`. |
| `SMA_k(t)` | Arithmetic mean of the latest `k` closes ending at `t`. |
| `EMA_k(t)` | Pandas exponential moving average with `span=k` and `adjust=False`. |
| `R_k(t)` | `100 * (C_t / C_(t-k) - 1)`. Trading-session return, not calendar-day return. |
| `I(condition)` | `1` when the condition is true, otherwise `0`. |
| `PR(x_i)` | Cross-sectional percentile rank: Pandas average rank divided by the non-null population count, multiplied by 100. The minimum is `100/N`, not zero. |
| `clip(x, a, b)` | `min(max(x, a), b)`. |
| `N` | Number of usable members in the selected calculation universe. |

Current horizon aliases are `1D=1`, `1W=5`, `2W=10`, `1M=21`, `3M=63`, `6M=126`, and `1Y=252` trading sessions.
JSON serialization converts Pandas/NumPy missing numeric values to `null`, timestamps to `YYYY-MM-DD`, and DataFrames to arrays of row objects.
Unavailable diagnostic groups may be `{}` or `[]`; unavailable conditional keys may be omitted.

Unless stated otherwise, summary maps are rounded to two decimals, while diagnostic maps are rounded to three decimals.
Raw row values may retain more precision when the row builder does not round them before serialization.

## 3. Calculation Universe And Market Score

The current default `market.calculation_mode` is `etf`.
Therefore breadth and participation use the 19 configured `market_condition_etf_universe` members.
The other supported modes are `active_symbols` and `blended`.

For a raw component `x`:

```text
x_etf    = component computed over usable configured market ETFs
x_active = component computed over usable active stock symbols
x_blend  = (w_etf * x_etf + w_active * x_active) / (w_etf + w_active)
```

The default blend weights are `0.5` and `0.5`, but they are inactive while mode is `etf`.

For breadth and participation percentages:

```text
pct(condition) = 100 / N * sum_i I(condition_i)
```

A member with a valid current close enters `N` even when a required long-window value is `NaN`.
The corresponding comparison then evaluates false, so short histories can depress a percentage rather than being excluded.

Most raw percentage components are transformed before scoring:

```text
g(x) = x                         when 0 <= x <= 50
g(x) = 50 + 0.6 * (x - 50)      when 50 < x <= 100
```

Thus a raw breadth value above 50 is deliberately compressed; for example, raw `70` becomes component score `62`.

The final score is:

```text
score = 0.12*g(pct_above_sma20)
      + 0.14*g(pct_above_sma50)
      + 0.14*g(pct_above_sma200)
      + 0.08*g(pct_sma50_gt_sma200)
      + 0.09*g(pct_positive_1m)
      + 0.08*g(pct_positive_3m)
      + 0.05*g(pct_2w_high)
      + 0.15*safe_haven_score
      + 0.15*vix_score
```

The configured weights sum to `1.0`.
Other entries in `component_scores` are diagnostics and currently have zero final-score weight.

| Score interval | `label` |
| --- | --- |
| `score >= 80` | `Bullish` |
| `60 <= score < 80` | `Positive` |
| `40 <= score < 60` | `Neutral` |
| `20 <= score < 40` | `Negative` |
| `score < 20` | `Bearish` |

## 4. Top-Level Scalar Fields

| JSON path | Type / unit | Definition |
| --- | --- | --- |
| `trade_date` | date | Latest date in benchmark history. |
| `score` | number, 0-100 | Current weighted Market Score, rounded to two decimals. |
| `label` | enum | Score label from the configured thresholds. |
| `score_1d_ago` | number or null | Market Score recomputed at offset 1. |
| `score_1w_ago` | number or null | Market Score recomputed at offset 5. |
| `score_1m_ago` | number or null | Market Score recomputed at offset 21. |
| `score_3m_ago` | number or null | Market Score recomputed at offset 63. |
| `label_1d_ago` | enum or null | Label derived from `score_1d_ago`. |
| `label_1w_ago` | enum or null | Label derived from `score_1w_ago`. |
| `label_1m_ago` | enum or null | Label derived from `score_1m_ago`. |
| `label_3m_ago` | enum or null | Label derived from `score_3m_ago`. |
| `vix_close` | index points or null | Latest `^VIX` close. |
| `update_time` | ISO local datetime | Market result construction time, with second precision and no explicit timezone offset. |

## 5. Component, Breadth, And Participation Maps

### 5.1 Raw Percentage Definitions

| Base key | Mathematical definition |
| --- | --- |
| `pct_above_sma10` | `100/N * sum I(C_t >= SMA_10(t))`. |
| `pct_above_sma20` | `100/N * sum I(C_t >= SMA_20(t))`. |
| `pct_above_sma50` | `100/N * sum I(C_t >= SMA_50(t))`. Uses stored `sma50` when present, otherwise rolling close mean. |
| `pct_above_sma200` | `100/N * sum I(C_t >= SMA_200(t))`. Uses stored `sma200` when present, otherwise rolling close mean. |
| `pct_sma20_gt_sma50` | `100/N * sum I(SMA_20(t) >= SMA_50(t))`. |
| `pct_sma50_gt_sma200` | `100/N * sum I(SMA_50(t) >= SMA_200(t))`. |
| `pct_positive_1w` | `100/N * sum I(R_5(t) > 0)`. |
| `pct_positive_1m` | `100/N * sum I(R_21(t) > 0)`. |
| `pct_positive_3m` | `100/N * sum I(R_63(t) > 0)`. |
| `pct_positive_1y` | `100/N * sum I(R_252(t) > 0)`. |
| `pct_positive_ytd` | `100/N * sum I(100*(C_t/C_first_session_of_year - 1) > 0)`. |
| `pct_2w_high` | `100/N * sum I(C_t >= max(C_(t-9)..C_t))`. Despite the label, this is a 10-session closing high. |

### 5.2 Output Maps

| JSON path | Emitted keys | Definition |
| --- | --- | --- |
| `breadth_summary` | Six `pct_above_*` / MA-order keys | Raw percentages from section 5.1. |
| `participation_summary` | Five `pct_positive_*` keys | Raw percentages from section 5.1. |
| `component_scores` | All 12 base keys plus `vix_score`, `safe_haven_score` | Base percentages transformed by `g(x)`; VIX and Safe Haven use their own formulas below. |

The `component_scores` base keys are `pct_above_sma10`, `pct_above_sma20`, `pct_above_sma50`, `pct_above_sma200`, `pct_sma20_gt_sma50`, `pct_sma50_gt_sma200`, `pct_positive_1w`, `pct_positive_1m`, `pct_positive_3m`, `pct_positive_1y`, `pct_positive_ytd`, and `pct_2w_high`.

```text
vix_score = clip(50 - (VIX_t - 17) * 5, 0, 100)
safe_haven_spread = R_20(SPY) - R_20(TLT)
safe_haven_score = clip(50 + 4 * safe_haven_spread, 0, 100)
```

When VIX is unavailable, `vix_score=50`.
When either Safe Haven leg is unavailable, the spread is zero and `safe_haven_score=50`.

## 6. Breadth Momentum And Internals

### 6.1 `breadth_momentum_summary`

| Key | Definition |
| --- | --- |
| `A20` | Current raw `pct_above_sma20`. |
| `A20 DELTA 1D` | `A20_t - A20_(t-1)`. |
| `A20 DELTA 5D` | `A20_t - A20_(t-5)`. |
| `A20 DELTA 10D` | `A20_t - A20_(t-10)`. |
| `A20 DELTA 21D` | `A20_t - A20_(t-21)`. |
| `A20 MOMENTUM FLAG` | `sign(delta10)` when `abs(delta10)>=15`; otherwise `sign(delta5)` when `abs(delta5)>=10`; otherwise `0`. |

### 6.2 `breadth_internal_summary`

This map is calculated from active stock histories and can be empty when no usable active-symbol histories are supplied.

| Key | Definition |
| --- | --- |
| `UNIVERSE COUNT` | Count with valid current and previous close. |
| `ADVANCERS` / `DECLINERS` | Counts where `C_t>C_(t-1)` / `C_t<C_(t-1)`. Unchanged issues belong to neither count. |
| `ADVANCE DECLINE NET` | `ADVANCERS - DECLINERS`. |
| `ADVANCE RATIO` | `ADVANCERS/(ADVANCERS+DECLINERS)`; defaults to `0.5` when the denominator is zero. |
| `AD LINE` | Cumulative sum through time of `ADVANCE DECLINE NET`. |
| `NEW HIGH 52W COUNT` | Count where `H_t >= stored high_52w`. |
| `NEW LOW 52W COUNT` | Count where `L_t <= stored low_52w`. |
| `NET NEW HIGH LOW` | New-high count minus new-low count. |
| `NET NEW HIGH LOW %` | `100 * NET NEW HIGH LOW / UNIVERSE COUNT`. |
| `STAGE2 %` | `100 * count(stage_label == "stage2_candidate" and valid) / UNIVERSE COUNT`. |
| `MCCLELLAN OSCILLATOR` | `EMA_19(z_t) - EMA_39(z_t)`, where `z_t=(ADVANCE RATIO_t-0.5)*200`. |
| `MCCLELLAN SUMMATION` | Cumulative sum of `MCCLELLAN OSCILLATOR`, with missing values filled by zero. |
| `ZWEIG BREADTH THRUST` | `EMA_10(ADVANCE RATIO)`. |
| `ZWEIG THRUST FLAG` | `1` when the minimum prior thrust over up to 10 sessions is below `0.4` and the current thrust is above `0.615`; otherwise `0`. |

## 7. Delta Map

`metric_deltas.<metric>.<horizon>` is always:

```text
current metric value - same metric recomputed at the horizon offset
```

Horizons are `1D`, `1W`, `2W`, and `1M`.
These are arithmetic changes, not percent changes of the metric.
For percentage metrics the unit is percentage points; for ratios it is ratio points; for flags it is state difference.

| Namespace | Source |
| --- | --- |
| no prefix | Raw breadth/participation keys, VIX diagnostics, `SAFE HAVEN %`, `vix_score`, and `safe_haven_score`. |
| `risk_on:` | `risk_on_ratio_summary`. |
| `vix_term:` | `volatility_term_structure`. |
| `credit:` | `credit_risk_proxy`. |
| `breadth_internal:` | `breadth_internal_summary`; absent in the sample because that map is empty. |
| `drawdown:` | `drawdown_summary`. |

Only metrics finite at both current and comparison offsets are emitted.
Date-like `VIX PEAK DATE` is not mathematically meaningful as a delta.
Because its `MMDD` string is numeric-coercible, the current implementation can nevertheless emit its arithmetic difference; AI consumers must ignore that delta.

## 8. Benchmark Performance And VIX Diagnostics

### 8.1 `performance_overview`

The benchmark is the pipeline benchmark, currently SPY.

| Key | Definition |
| --- | --- |
| `% YTD` | Return from the first benchmark session of the current year to `t`. |
| `% 1W` | `R_5(t)`. |
| `% 1M` | `R_21(t)`. |
| `% 1Y` | `R_252(t)`. |

Insufficient history produces `0.0` in this map.

### 8.2 `high_vix_summary`

| Key | Definition |
| --- | --- |
| `S2W HIGH %` | Raw `pct_2w_high`. |
| `VIX` | Latest `^VIX` close. |
| `SAFE HAVEN %` | `R_20(SPY)-R_20(TLT)`. Positive means the configured risk-on leg outperformed the risk-off leg. |
| `VIX 252D PCTL` | `100 * count(VIX_s <= VIX_t)/W` over the latest `W=min(252, available)` observations. |
| `VIX PEAK` | Maximum VIX close over the same window. |
| `VIX PEAK DATE` | `MMDD` of the last occurrence of that maximum. |
| `VIX PEAK DAYS` | Number of observations since the last peak. |
| `VIX PEAK RATIO %` | `100*(VIX_t/VIX_PEAK - 1)`. |

## 9. Ratio, Volatility, Credit, And Drawdown Maps

For any aligned numerator/denominator close series:

```text
Q_t = numerator_t / denominator_t
REL k % = 100 * (Q_t / Q_(t-k) - 1)
```

### 9.1 `risk_on_ratio_summary`

The configured ratio is `IWO/IWN`.

| Key | Definition |
| --- | --- |
| `RATIO` | Current `IWO/IWN`. |
| `REL 1W %`, `REL 1M %`, `REL 3M %` | Ratio returns for 5, 21, and 63 sessions. |
| `HIGH DIST %` | `100*(Q_t/max(Q over latest W)-1)`, `W=min(756, available)`. |
| `HIGH LOOKBACK DAYS` | Actual `W` used. |
| `ABOVE MA COUNT` | Number of available 20/50/200-session ratio SMAs with `Q_t >= SMA`. |
| `MA COUNT` | Number of those SMAs with sufficient data. |

### 9.2 `volatility_term_structure`

| Key | Definition |
| --- | --- |
| `RATIO` | `VIX/VIX3M`. |
| `REL 1W %`, `REL 1M %`, `REL 3M %` | Returns of the `VIX/VIX3M` ratio. |
| `VIX`, `VIX9D`, `VIX3M` | Latest closes of `^VIX`, `^VIX9D`, and `^VIX3M`. |
| `INVERSION FLAG` | `I(VIX/VIX3M >= 1)`. |
| `VIX9D/VIX RATIO` | `VIX9D/VIX`. |
| `FRONT INVERSION FLAG` | `I(VIX9D/VIX >= 1)`. |
| `FULL BACKWARDATION FLAG` | `I(VIX9D >= VIX >= VIX3M)`. |

### 9.3 `credit_risk_proxy`

| Key | Definition |
| --- | --- |
| `HYG/LQD RATIO` and three `REL` fields | Current HYG/LQD ratio and its 5/21/63-session returns. |
| `HYG/IEF RATIO` and three `REL` fields | Current HYG/IEF ratio and its 5/21/63-session returns. |
| `CREDIT RISK-OFF FLAG` | `1` only when both 1-week ratio returns are strictly negative; otherwise `0`. |
| `HY OAS` | Latest `BAMLH0A0HYM2` close, in percentage points. |
| `HY OAS DELTA 5D BPS` | `100*(OAS_t-OAS_(t-5))`. |
| `HY OAS WIDENING 5D FLAG` | `I(HY OAS DELTA 5D BPS >= 25)`. |
| `HY OAS DELTA 21D BPS` | `100*(OAS_t-OAS_(t-21))`. |

### 9.4 `drawdown_summary`

For each configured index, currently SPY and QQQ, let `W=min(drawdown_window, available)` and `P=max(C over latest W)`.
The default `drawdown_window` is 252.

| Suffix | Definition |
| --- | --- |
| `DD 252D %` | `100*(C_t/P-1)`. The key name remains `252D` even if configuration changes the window. |
| `T_DD` | Observations since the last occurrence of `P`. |
| `ROLLING HIGH` | `P`. |
| `DRAWDOWN WINDOW DAYS` | Actual `W` used. |

## 10. Index State And Context

### 10.1 Shared Index-State Rules

For each configured index, currently SPY and QQQ:

```text
daily_return_pct_t = 100 * (C_t/C_(t-1) - 1)
distribution_t = I(daily_return_pct_t <= -0.2 and V_t > V_(t-1))
distribution_count = sum(distribution over latest min(25, available) sessions)
```

The rally low is the minimum close in the latest `min(25, available)` sessions.
`RALLY ATTEMPT DAY` is the number of sessions since that low when the latest close is above the low, otherwise zero.

An FTD candidate must be at least four positions after the rally-low position and satisfy all of:

```text
daily_return_pct >= 1.7
current volume > previous volume
current close > rally-low close
```

When several sessions qualify, the latest qualifying session is used.

### 10.2 `index_state_summary`

Each key is prefixed by `SPY ` or `QQQ `.

| Suffix | Definition |
| --- | --- |
| `RALLY ATTEMPT DAY` | Sessions since the recent rally low, subject to the rule above. |
| `FTD FLAG` | `1` when an FTD candidate exists, otherwise `0`. |
| `FTD AGE DAYS` | Sessions since the latest FTD candidate; `-1` when none exists. |
| `DISTRIBUTION DAY COUNT` | Latest 25-session distribution count. The CLI enrichment pass overwrites this with the shared price-cache calculation. |
| `UNDER PRESSURE FLAG` | `I(distribution_count >= 5)` as computed before CLI enrichment. |
| `FTD GAIN %` | Conditional: FTD-day close return. |
| `FTD VOLUME RATIO` | Conditional: `V_FTD/V_previous`. |
| `FTD ADVANCE RATIO` | Conditional: active-universe `ADVANCE RATIO` on the FTD date. |
| `FTD QUALITY SCORE` | Conditional mean of available bounded gain, volume, and breadth subscores. |

```text
gain_subscore    = clip(FTD_GAIN/1.7*50, 0, 100)
volume_subscore  = clip((FTD_VOLUME_RATIO-1)*200, 0, 100)
breadth_subscore = clip(FTD_ADVANCE_RATIO*100, 0, 100)
FTD_QUALITY      = mean(available subscores)
```

### 10.3 `index_context_summary`

The base fields below are emitted per index with `SPY ` or `QQQ ` prefixes.

| Suffix | Definition |
| --- | --- |
| `CLOSE` | Latest close. |
| `DAY %` | Latest one-session close return. |
| `21EMA POSITION` | `above` when `C_t>EMA_21(high)`, `below` when `C_t<EMA_21(low)`, otherwise `inside`. |
| `50SMA %` | `100*(C_t/SMA_50(t)-1)`. |
| `BELOW 50SMA FLAG` | `I(50SMA % < 0)`. |
| `FTD DATE` | `MMDD` of the selected FTD, otherwise empty string. |
| `FTD VALID FLAG` | `1` when no post-FTD close is below the currently identified 25-session rally-low close; otherwise `0`. |
| Index-state suffixes | Same definitions as section 10.2, including conditional FTD quality fields. |

The CLI then enriches the same map from the shared price cache:

| Suffix | Definition |
| --- | --- |
| `PRICE DATE` | Last cached price date used by enrichment. This can differ between SPY and QQQ. |
| `HIGH`, `VOLUME`, `PREVIOUS VOLUME` | Latest high, latest volume, and prior-session volume. |
| `DISTRIBUTION DAY FLAG` | Latest-session distribution rule using fixed `-0.2%` and higher volume. |
| `ACC DAYS 10D` | Count in the latest 10 sessions where return is at least `+0.2%` and volume is higher than the previous session. |
| `DIST DAYS 10D` | Count in the latest 10 sessions satisfying the distribution rule. |
| `CLOSE ABOVE 21EMA FLAG` | `I(C_t > EMA_21(close)_t)`. This is not the high/low EMA cloud rule. |
| `HIGHER HIGH AFTER LAST DD FLAG` | `1` if any later high exceeds the high on the most recent distribution day, `0` if not, and `null` if no distribution day exists. |

## 11. Snapshot Arrays

### 11.1 `market_snapshot[]` And `external_snapshot[]`

`market_snapshot` uses configured market-condition ETFs; `external_snapshot` uses configured external ETFs.

| Row field | Definition |
| --- | --- |
| `TICKER`, `NAME` | Configured symbol and display name. |
| `PRICE` | Latest close. |
| `DAY %` | Latest `daily_change_pct` indicator. |
| `VOL vs 50D %` | `100*(rel_volume-1)`, where `rel_volume=V_t/average_volume_50d`. |
| `21EMA POS` | `below 21EMA Low` when close is below stored `ema21_low`; `above 21EMA High` when above stored `ema21_high`; otherwise `inside 21EMA Cloud`. |

`leadership_snapshot[]` is a retained payload field, but the current `MarketConditionScorer` initializes it as an empty DataFrame and does not populate it.

### 11.2 `factors_vs_sp500[]`

| Row field | Definition |
| --- | --- |
| `TICKER`, `NAME` | Configured factor ETF and name. |
| `REL 1W %` | `R_5(factor)-R_5(benchmark)`. |
| `REL 1M %` | `R_21(factor)-R_21(benchmark)`. |
| `REL 1Y %` | `R_252(factor)-R_252(benchmark)`. |

This is an arithmetic percentage-point return spread, not a price-ratio return.

### 11.3 `sector_relative_strength[]`

Only the 11 configured sector ETFs are included.

| Row field | Definition |
| --- | --- |
| `REL 1W %`, `REL 1M %`, `REL 3M %` | Sector return minus benchmark return at 5, 21, and 63 sessions. |
| `REL 1M 1W AGO %` | The 21-session relative return evaluated at offset 5. |
| `REL 1M 1M AGO %` | The 21-session relative return evaluated at offset 21. |
| `RANK 1M` | Cross-sectional descending rank of current `REL 1M %`, with minimum-rank tie handling. |
| `RANK DELTA 1W` | Prior 1-week-offset rank minus current rank. Positive means rank improved. |
| `RANK DELTA 1M` | Prior 1-month-offset rank minus current rank. Positive means rank improved. |

### 11.4 `style_pair_summary[]`

Configured pairs are `RSP/SPY`, `QQQ/SPY`, `VUG/VTV`, `MTUM/SPY`, `VB/MGC`, `VO/MGC`, and `VYM/SPY`.

| Row field | Definition |
| --- | --- |
| `PAIR`, `NAME` | Ratio identifier and configured name. |
| `REL 1W %`, `REL 1M %`, `REL 3M %` | 5/21/63-session return of the pair price ratio. |
| `ABOVE MA COUNT` | Count of available 20/50/200-session ratio SMAs at or below the current ratio. |
| `MA COUNT` | Count of those SMAs with sufficient data. |

### 11.5 `defensive_cyclical_summary`

For each horizon, calculate the mean ETF return of cyclical/growth sectors `(XLC, XLE, XLF, XLI, XLK, XLY)` and subtract the mean ETF return of defensive sectors `(XLP, XLU, XLV)`.

| Key | Definition |
| --- | --- |
| `REL 1W %` | Mean cyclical 5-session return minus mean defensive 5-session return. |
| `REL 1M %` | Same for 21 sessions. |
| `REL 3M %` | Same for 63 sessions. |

## 12. RS Radar Leadership Arrays

`sector_leaders[]` and `industry_leaders[]` are built from the combined configured Radar ETF universe, then filtered into their respective output tables.
Therefore percentile ranks are cross-sectional across the combined universe, not independently within the sector or industry table.

For ETF `i` and benchmark SPY:

```text
asset_return_i,k = 100*(C_i,t/C_i,t-k - 1)
benchmark_return_k = 100*(C_SPY,t/C_SPY,t-k - 1)
RS_RETURN_i,k = asset_return_i,k - benchmark_return_k
```

| Row field | Definition |
| --- | --- |
| `TICKER`, `NAME` | Configured ETF symbol and name. |
| `DAY %`, `WK %`, `MTH %`, `QTR %`, `HY %` | ETF returns for 1, 5, 21, 63, and 126 sessions. |
| `RS DAY%`, `RS WK%`, `RS MTH%`, `RS QTR%`, `RS HY%` | ETF return minus SPY return for the matching horizon. |
| `1D`, `1W`, `1M`, `3M`, `6M` | `PR` of the matching RS-return field across the combined Radar universe. |
| `RS` | Weighted mean of available tactical ranks using weights `(1D,1W,1M)=(1,2,2)`. With all values present: `(1D+2*1W+2*1M)/5`. |
| `STRUCT RS` | Weighted mean of available `(3M,6M)` ranks using weights `(1,1)`. With both present: `(3M+6M)/2`. |
| `52W HIGH` | `Yes` when close is at least `99.5%` of the latest 252-session rolling maximum high; otherwise formatted `100*(close/high_252-1)` such as `-13.2%`. Empty when unavailable. |
| `MAJOR STOCKS` | Industry-only comma-separated configured constituents; descriptive metadata, not a calculation. |

Rows are sorted by `STRUCT RS`, then `RS`, `1W`, and `1D`, all descending.

## 13. AI Consumption Rules

1. Treat `breadth_summary` and `participation_summary` as raw percentages, but treat `component_scores` as transformed 0-100 scores.
2. Treat every `metric_deltas` value as an arithmetic current-minus-prior change in the metric's native unit.
3. Do not infer causality, news, macro events, trade execution, sizing, stops, or exits from these fields.
4. Do not interpret an absent conditional key as zero. Use `unknown` unless the defining rule explicitly supplies a zero default.
5. Keep percentage-point spreads distinct from ratio returns: factor/sector RS uses return subtraction, while style/risk-on/credit/volatility ratio fields use returns of a quotient.
6. Prefer `PRICE DATE` for per-index freshness checks; the top-level `trade_date` does not guarantee every auxiliary series shares the same last observation date.
7. Use `market_document.v1` rather than this raw summary when generating the standard human-facing daily market report.

## 14. Implementation Sources

- Payload assembly: `src/cli/oratek.py::_market_summary_payload`
- Market calculations: `src/dashboard/market.py::MarketConditionScorer`
- Snapshot calculations: `src/dashboard/market.py::MarketSnapshotBuilder`
- Radar calculations: `src/dashboard/radar.py::RadarViewModelBuilder`
- Percentile rank: `src/utils.py::percent_rank`
- Default market parameters: `config/default/market.yaml`
- Default Radar parameters: `config/default/radar.yaml`
- Parent artifact contract: `doc/SystemDocs/Specifications/09_MARKET_DOCUMENT_AND_REPORT_SPEC.md`
