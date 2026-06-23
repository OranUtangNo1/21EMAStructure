from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Mapping, Sequence


DEFAULT_COMPONENT_WEIGHTS = {
    "pct_above_sma20": 0.12,
    "pct_above_sma50": 0.14,
    "pct_above_sma200": 0.14,
    "pct_sma50_gt_sma200": 0.08,
    "pct_positive_1m": 0.09,
    "pct_positive_3m": 0.08,
    "pct_2w_high": 0.05,
    "safe_haven_score": 0.15,
    "vix_score": 0.15,
}


@dataclass(frozen=True, slots=True)
class MarketBriefConfig:
    component_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_COMPONENT_WEIGHTS))
    positive_score_floor: float = 60.0
    neutral_score_floor: float = 40.0
    strong_layer_floor: float = 60.0
    weak_layer_floor: float = 40.0
    converging_down_ceiling: float = 45.0
    vix_neutral_level: float = 17.0
    vix_score_slope: float = 5.0
    distribution_pressure_count: int = 5
    ftd_min_gain_pct: float = 1.7
    ftd_min_rally_day: int = 4

    @classmethod
    def from_market_settings(cls, payload: Mapping[str, object] | None) -> "MarketBriefConfig":
        settings = payload if isinstance(payload, Mapping) else {}
        weights = dict(DEFAULT_COMPONENT_WEIGHTS)
        raw_weights = settings.get("component_weights", {})
        if isinstance(raw_weights, Mapping):
            weights.update({str(key): float(value) for key, value in raw_weights.items()})
        index_state = settings.get("index_state", {})
        index_config = index_state if isinstance(index_state, Mapping) else {}
        brief = settings.get("market_brief", {})
        brief_config = brief if isinstance(brief, Mapping) else {}
        return cls(
            component_weights=weights,
            positive_score_floor=float(settings.get("positive_threshold", 60.0)),
            neutral_score_floor=float(settings.get("neutral_threshold", 40.0)),
            strong_layer_floor=float(brief_config.get("strong_layer_floor", 60.0)),
            weak_layer_floor=float(brief_config.get("weak_layer_floor", 40.0)),
            converging_down_ceiling=float(brief_config.get("converging_down_ceiling", 45.0)),
            vix_neutral_level=float(settings.get("vix_neutral_level", 17.0)),
            vix_score_slope=float(settings.get("vix_score_slope", 5.0)),
            distribution_pressure_count=int(index_config.get("distribution_pressure_count", 5)),
            ftd_min_gain_pct=float(index_config.get("ftd_min_gain_pct", 1.7)),
            ftd_min_rally_day=int(index_config.get("ftd_min_rally_day", 4)),
        )


@dataclass(frozen=True, slots=True)
class MarketBriefResult:
    payload: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return deepcopy(self.payload)


class MarketBriefBuilder:
    """Build the deterministic market_brief.v1 summary contract."""

    def __init__(self, config: MarketBriefConfig | None = None) -> None:
        self.config = config or MarketBriefConfig()

    def build(
        self,
        summary: Mapping[str, object],
        *,
        history_summaries: Sequence[Mapping[str, object]] | None = None,
    ) -> MarketBriefResult:
        raw = deepcopy(dict(summary))
        layers = self._regime_layers(raw)
        cycle_state = self._index_cycle_state(raw)
        verdict = self._regime_verdict(raw, layers, cycle_state)
        attribution = self._score_attribution(raw)
        distance = self._score_distance(raw)
        data_quality = self._data_quality(raw, layers)
        percentile, percentile_n = self._score_percentile(raw, history_summaries or [])

        payload = {
            "schema_version": "market_brief.v1",
            "document_type": "market_summary",
            "headline": self._headline(raw, verdict, percentile, percentile_n),
            "regime_layers": layers,
            "regime_verdict": verdict,
            "score_attribution": attribution,
            "score_distance": distance,
            "index_cycle_state": cycle_state,
            "divergence_flags": self._divergence_flags(raw, layers),
            "trigger_watch": self._trigger_watch(raw, distance, cycle_state),
            "leadership_map": self._leadership_map(raw),
            "data_quality": data_quality,
            "field_semantics": self._field_semantics(),
            "ignore_deltas": ["metric_deltas.VIX PEAK DATE"],
        }
        payload.update(deepcopy(raw))
        if not _mapping(raw.get("breadth_internal_summary")):
            payload["breadth_internal_summary"] = None
        payload["raw_reference"] = raw
        return MarketBriefResult(payload=payload)

    def _headline(
        self,
        summary: Mapping[str, object],
        verdict: Mapping[str, object],
        percentile: float | None,
        percentile_n: int,
    ) -> dict[str, object]:
        return {
            "trade_date": _date_text(summary.get("trade_date")),
            "market_score": _number(summary.get("score")),
            "market_label": summary.get("label"),
            "score_trajectory": {
                "current": _number(summary.get("score")),
                "1d_ago": _number(summary.get("score_1d_ago")),
                "1w_ago": _number(summary.get("score_1w_ago")),
                "1m_ago": _number(summary.get("score_1m_ago")),
                "3m_ago": _number(summary.get("score_3m_ago")),
            },
            "score_percentile_252d": percentile,
            "score_percentile_sample_n": percentile_n,
            "posture": verdict["posture"],
            "posture_guidance": verdict["posture_guidance"],
        }

    def _regime_layers(self, summary: Mapping[str, object]) -> dict[str, object]:
        breadth = _mapping(summary.get("breadth_summary"))
        participation = _mapping(summary.get("participation_summary"))
        momentum = _mapping(summary.get("breadth_momentum_summary"))
        internals_health = self._internals_health(summary)
        components = _mapping(summary.get("component_scores"))
        term = _mapping(summary.get("volatility_term_structure"))
        credit = _mapping(summary.get("credit_risk_proxy"))
        drawdown = _mapping(summary.get("drawdown_summary"))
        rotation = _mapping(summary.get("defensive_cyclical_summary"))
        sectors = _rows(summary.get("sector_relative_strength"))

        trend_values = [
            _number(breadth.get("pct_above_sma200")),
            _number(breadth.get("pct_sma50_gt_sma200")),
            _number(participation.get("pct_positive_3m")),
            _clip_optional(_add_scaled(100.0, _number(drawdown.get("SPY DD 252D %")), 4.0)),
        ]
        momentum_values = [
            _number(momentum.get("A20")),
            _number(breadth.get("pct_above_sma50")),
            _number(participation.get("pct_positive_1m")),
            _number(participation.get("pct_positive_1w")),
        ]
        legacy_momentum_score = _mean(momentum_values)
        internals_health_score = _number(internals_health.get("score"))
        momentum_score = (
            _mean([legacy_momentum_score, internals_health_score])
            if internals_health_score is not None
            else legacy_momentum_score
        )
        term_ratio = _number(term.get("RATIO"))
        if term_ratio is None:
            vix = _number(term.get("VIX"))
            vix3m = _number(term.get("VIX3M"))
            if vix is not None and vix3m not in {None, 0.0}:
                term_ratio = vix / vix3m
        term_health = None
        if term_ratio is not None:
            term_health = _clip(50.0 + (1.0 - term_ratio) * 200.0)
            if (_number(term.get("FRONT INVERSION FLAG")) or 0.0) >= 1.0:
                term_health = _clip(term_health - 15.0)
        volatility_values = [
            _number(components.get("vix_score")),
            term_health,
            _number(components.get("safe_haven_score")),
        ]
        oas_delta = _number(credit.get("HY OAS DELTA 21D BPS"))
        hyg_lqd = _number(credit.get("HYG/LQD REL 1M %"))
        hyg_ief = _number(credit.get("HYG/IEF REL 1M %"))
        credit_score = None
        if None not in {oas_delta, hyg_lqd, hyg_ief}:
            credit_score = _clip(60.0 - 0.8 * oas_delta + 5.0 * (hyg_lqd + hyg_ief))
        positive_sector_count = sum(1 for row in sectors if (_number(row.get("REL 1M %")) or 0.0) > 0.0)
        positive_sector_ratio = positive_sector_count / len(sectors) if sectors else None
        cyclical_3m = _number(rotation.get("REL 3M %"))
        leadership_score = None
        if cyclical_3m is not None and positive_sector_ratio is not None:
            leadership_score = _clip(50.0 + 2.0 * cyclical_3m + (positive_sector_ratio - 0.5) * 40.0)

        momentum_layer = self._layer(
            momentum_score,
            [
                _driver("breadth_momentum_summary.A20", momentum_values[0], "raw_pct"),
                _driver("breadth_summary.pct_above_sma50", momentum_values[1], "raw_pct"),
                _driver("participation_summary.pct_positive_1m", momentum_values[2], "raw_pct"),
                _driver("participation_summary.pct_positive_1w", momentum_values[3], "raw_pct"),
                _driver("derived.internals_health", internals_health_score, "score_0_100"),
            ],
        )
        momentum_layer["legacy_proxy_score"] = _round(legacy_momentum_score)
        momentum_layer["internals_health"] = internals_health if internals_health_score is not None else None

        return {
            "trend_structure": self._layer(
                _mean(trend_values),
                [
                    _driver("breadth_summary.pct_above_sma200", trend_values[0], "raw_pct"),
                    _driver("breadth_summary.pct_sma50_gt_sma200", trend_values[1], "raw_pct"),
                    _driver("participation_summary.pct_positive_3m", trend_values[2], "raw_pct"),
                    _driver("drawdown_summary.SPY DD 252D %", _number(drawdown.get("SPY DD 252D %")), "raw_pct"),
                ],
            ),
            "momentum_participation": momentum_layer,
            "volatility_stress": self._layer(
                _mean(volatility_values),
                [
                    _driver("component_scores.vix_score", volatility_values[0], "score_0_100"),
                    _driver("derived.term_health", term_health, "score_0_100"),
                    _driver("component_scores.safe_haven_score", volatility_values[2], "score_0_100"),
                ],
            ),
            "credit": self._layer(
                credit_score,
                [
                    _driver("credit_risk_proxy.HY OAS DELTA 21D BPS", oas_delta, "bps"),
                    _driver("credit_risk_proxy.HYG/LQD REL 1M %", hyg_lqd, "ratio_pt"),
                    _driver("credit_risk_proxy.HYG/IEF REL 1M %", hyg_ief, "ratio_pt"),
                ],
            ),
            "leadership": self._layer(
                leadership_score,
                [
                    _driver("defensive_cyclical_summary.REL 3M %", cyclical_3m, "pp_spread"),
                    _driver("derived.sector_rel_1m_positive_ratio", positive_sector_ratio, "ratio"),
                ],
            ),
        }

    def _layer(self, score: float | None, drivers: list[dict[str, object]]) -> dict[str, object]:
        state = "unknown"
        if score is not None:
            if score >= self.config.strong_layer_floor:
                state = "strong"
            elif score < self.config.weak_layer_floor:
                state = "weak"
            else:
                state = "neutral"
        return {"score": _round(score), "state": state, "drivers": drivers}

    def _internals_health(self, summary: Mapping[str, object]) -> dict[str, object]:
        internals = _mapping(summary.get("breadth_internal_summary"))
        advance_ratio = _number(internals.get("ADVANCE RATIO"))
        net_new_high_low_pct = _number(internals.get("NET NEW HIGH LOW %"))
        zweig_thrust = _number(internals.get("ZWEIG BREADTH THRUST"))
        mcclellan = _number(internals.get("MCCLELLAN OSCILLATOR"))
        stage2_pct = _number(internals.get("STAGE2 %"))
        components = {
            "advance_ratio": _clip_optional(_add_scaled(50.0, None if advance_ratio is None else advance_ratio - 0.5, 200.0)),
            "net_new_high_low": _clip_optional(_add_scaled(50.0, net_new_high_low_pct, 5.0)),
            "zweig": _clip_optional(_add_scaled(50.0, None if zweig_thrust is None else zweig_thrust - 0.5, 250.0)),
            "mcclellan": _clip_optional(_add_scaled(50.0, mcclellan, 0.5)),
            "stage2": _clip_optional(stage2_pct),
        }
        score = _mean(list(components.values()))
        if score is None:
            state = "unavailable"
        elif score < 45.0:
            state = "weak"
        elif score >= 60.0:
            state = "strong"
        else:
            state = "neutral"
        return {
            "score": _round(score),
            "state": state,
            "components": {key: _round(value) for key, value in components.items()},
            "source": "breadth_internal_summary",
        }

    def _regime_verdict(
        self,
        summary: Mapping[str, object],
        layers: Mapping[str, object],
        cycle_state: Mapping[str, object],
    ) -> dict[str, object]:
        scores = [
            _number(_mapping(layer).get("score"))
            for layer in layers.values()
            if _number(_mapping(layer).get("score")) is not None
        ]
        trend = _number(_mapping(layers.get("trend_structure")).get("score"))
        volatility = _number(_mapping(layers.get("volatility_stress")).get("score"))
        momentum = _mapping(summary.get("breadth_momentum_summary"))
        internals_health = _number(
            _mapping(_mapping(layers.get("momentum_participation")).get("internals_health")).get("score")
        )
        short_term_deterioration = (
            internals_health < 45.0
            if internals_health is not None
            else (
                (_number(momentum.get("A20 DELTA 1D")) or 0.0) <= -15.0
                or (_number(momentum.get("A20 MOMENTUM FLAG")) or 0.0) < 0.0
            )
        )
        if len(scores) == len(layers) and all(score >= self.config.strong_layer_floor for score in scores):
            alignment = "converging_up"
        elif len(scores) == len(layers) and all(score < self.config.converging_down_ceiling for score in scores):
            alignment = "converging_down"
        else:
            alignment = "diverging"
        if trend is not None and trend >= self.config.strong_layer_floor and (
            (volatility is not None and volatility < 50.0) or short_term_deterioration
        ):
            alignment = "diverging"

        stages = [
            _mapping(cycle_state.get(symbol)).get("stage")
            for symbol in ("SPY", "QQQ")
        ]
        under_pressure = "under_pressure" in stages
        if alignment == "converging_up":
            posture = "aggressive" if scores and min(scores) >= 70.0 and stages == ["confirmed_uptrend", "confirmed_uptrend"] else "trend_following"
        elif alignment == "converging_down":
            posture = "risk_off" if scores and max(scores) < self.config.weak_layer_floor else "defensive"
        elif under_pressure:
            posture = "cautious_hold"
        elif trend is not None and trend >= self.config.strong_layer_floor:
            posture = "trend_following"
        else:
            posture = "cautious_hold"

        guidance = {
            "aggressive": "主導群の新規候補確認を積極化し、ロング・エクスポージャー拡大を許容。",
            "trend_following": "主導群の順張りを優先し、選別的なロング・エクスポージャーを維持。",
            "cautious_hold": "新規上乗せを抑制し、主導群に限定してリスク資金を温存。",
            "defensive": "新規ロングを絞り、防御的なエクスポージャーを優先。",
            "risk_off": "新規ロングを見送り、リスク・エクスポージャーを最小化。",
        }
        dominant_story = self._dominant_story(layers)
        return {
            "alignment": alignment,
            "dominant_story": dominant_story,
            "posture": posture,
            "posture_guidance": guidance[posture],
        }

    def _dominant_story(self, layers: Mapping[str, object]) -> str:
        scored = [
            (key, _number(_mapping(value).get("score")))
            for key, value in layers.items()
        ]
        available = [(key, score) for key, score in scored if score is not None]
        if not available:
            return "insufficient_data"
        strongest = max(available, key=lambda item: item[1])
        weakest = min(available, key=lambda item: item[1])
        return f"{strongest[0]}_strongest__{weakest[0]}_weakest"

    def _score_attribution(self, summary: Mapping[str, object]) -> dict[str, object]:
        components = _mapping(summary.get("component_scores"))
        deltas = _mapping(summary.get("metric_deltas"))
        level = {
            key: _round(weight * value)
            for key, weight in self.config.component_weights.items()
            if (value := _number(components.get(key))) is not None
        }
        result: dict[str, object] = {
            "units": "market_score_points",
            "level_contribution": level,
            "level_total": _round(sum(level.values())),
        }
        raw_values = self._raw_component_values(summary)
        for horizon, prior_key, output_key in (
            ("1D", "score_1d_ago", "delta_contribution_1d"),
            ("1W", "score_1w_ago", "delta_contribution_1w"),
        ):
            contributions: dict[str, float] = {}
            for key, weight in self.config.component_weights.items():
                metric_delta = _number(_mapping(deltas.get(key)).get(horizon))
                if metric_delta is None:
                    continue
                if key in {"vix_score", "safe_haven_score"}:
                    contributions[key] = _round(weight * metric_delta)
                    continue
                current_raw = raw_values.get(key)
                if current_raw is None:
                    continue
                current_score = _ratio_component_score(current_raw)
                prior_score = _ratio_component_score(current_raw - metric_delta)
                contributions[key] = _round(weight * (current_score - prior_score))
            total = _round(sum(contributions.values()))
            expected = _difference(summary.get("score"), summary.get(prior_key))
            result[output_key] = contributions
            result[f"{output_key}_total"] = total
            result[f"{output_key}_expected"] = _round(expected)
            result[f"{output_key}_reconciliation_error"] = _round(None if expected is None else total - expected)
        return result

    def _raw_component_values(self, summary: Mapping[str, object]) -> dict[str, float | None]:
        breadth = _mapping(summary.get("breadth_summary"))
        participation = _mapping(summary.get("participation_summary"))
        high_vix = _mapping(summary.get("high_vix_summary"))
        return {
            **{key: _number(value) for key, value in breadth.items()},
            **{key: _number(value) for key, value in participation.items()},
            "pct_2w_high": _number(high_vix.get("S2W HIGH %")),
        }

    def _score_distance(self, summary: Mapping[str, object]) -> dict[str, object]:
        score = _number(summary.get("score"))
        return {
            "current_band": summary.get("label"),
            "to_positive": _round(None if score is None else self.config.positive_score_floor - score),
            "to_negative": _round(None if score is None else self.config.neutral_score_floor - score),
            "positive_boundary": self.config.positive_score_floor,
            "negative_boundary": self.config.neutral_score_floor,
            "units": "market_score_points",
        }

    def _index_cycle_state(self, summary: Mapping[str, object]) -> dict[str, object]:
        state = _mapping(summary.get("index_state_summary"))
        context = _mapping(summary.get("index_context_summary"))
        result: dict[str, object] = {}
        stages: list[str] = []
        for symbol in ("SPY", "QQQ"):
            prefix = f"{symbol} "
            rally_day = _number(state.get(prefix + "RALLY ATTEMPT DAY"))
            ftd_flag = _number(state.get(prefix + "FTD FLAG"))
            distribution_count = _number(state.get(prefix + "DISTRIBUTION DAY COUNT"))
            under_pressure = (
                (_number(state.get(prefix + "UNDER PRESSURE FLAG")) or 0.0) >= 1.0
                or (distribution_count is not None and distribution_count >= self.config.distribution_pressure_count)
            )
            sma50 = _number(context.get(prefix + "50SMA %"))
            if under_pressure:
                stage = "under_pressure"
            elif (ftd_flag or 0.0) >= 1.0:
                stage = "confirmed_uptrend"
            elif (rally_day or 0.0) >= 1.0:
                stage = "rally_attempt_awaiting_ftd"
            elif sma50 is not None and sma50 < 0.0:
                stage = "correction"
            elif distribution_count is not None and distribution_count >= self.config.distribution_pressure_count:
                stage = "distribution"
            else:
                stage = "neutral"
            stages.append(stage)
            result[symbol] = {
                "stage": stage,
                "rally_attempt_day": rally_day,
                "ftd_flag": ftd_flag,
                "distribution_count_25d": distribution_count,
                "under_pressure": under_pressure,
                "sma50_pct": sma50,
                "acc_days_10d": _number(context.get(prefix + "ACC DAYS 10D")),
                "dist_days_10d": _number(context.get(prefix + "DIST DAYS 10D")),
                "price_date": _date_text(context.get(prefix + "PRICE DATE")),
            }
        if stages == ["under_pressure", "under_pressure"]:
            rollup = "uptrend_under_distribution_pressure"
        elif all(stage == "confirmed_uptrend" for stage in stages):
            rollup = "confirmed_uptrend"
        elif any(stage == "correction" for stage in stages):
            rollup = "correction"
        elif any(stage == "under_pressure" for stage in stages):
            rollup = "mixed_under_pressure"
        elif any(stage == "rally_attempt_awaiting_ftd" for stage in stages):
            rollup = "rally_attempt_awaiting_ftd"
        else:
            rollup = "neutral"
        result["market_rollup"] = rollup
        return result

    def _divergence_flags(
        self,
        summary: Mapping[str, object],
        layers: Mapping[str, object],
    ) -> list[dict[str, str]]:
        flags: list[dict[str, str]] = []
        credit = _mapping(summary.get("credit_risk_proxy"))
        if (_number(credit.get("CREDIT RISK-OFF FLAG")) or 0.0) >= 1.0 and (_number(credit.get("HY OAS DELTA 21D BPS")) or 0.0) < 0.0:
            flags.append({"id": "credit_flag_vs_oas_trend", "severity": "medium", "note": "Credit proxy flag is risk-off while HY OAS is narrowing."})
        trend = _number(_mapping(layers.get("trend_structure")).get("score"))
        momentum = _mapping(summary.get("breadth_momentum_summary"))
        internals = _mapping(summary.get("breadth_internal_summary"))
        internals_health = _number(
            _mapping(_mapping(layers.get("momentum_participation")).get("internals_health")).get("score")
        )
        if trend is not None and trend >= self.config.strong_layer_floor and internals_health is not None and internals_health < 45.0:
            severity = "high" if internals_health < 35.0 else "medium"
            flags.append(
                {
                    "id": "structure_vs_internals",
                    "severity": severity,
                    "note": (
                        f"structure strong (trend={trend:.1f}) but internals weak "
                        f"(ADV RATIO={_display_number(internals.get('ADVANCE RATIO'))}, "
                        f"NET NEW H/L={_display_number(internals.get('NET NEW HIGH LOW'))}, "
                        f"Zweig={_display_number(internals.get('ZWEIG BREADTH THRUST'))})"
                    ),
                }
            )
        a20_delta_1d = _number(momentum.get("A20 DELTA 1D"))
        if a20_delta_1d is not None and a20_delta_1d <= -15.0 and internals_health is not None and internals_health >= 55.0:
            flags.append(
                {
                    "id": "etf_proxy_vs_broad_internals",
                    "severity": "info",
                    "note": f"ETF A20 proxy fell {a20_delta_1d:.1f}pp while broad internals remained healthy ({internals_health:.1f}).",
                }
            )
        context = _mapping(summary.get("index_context_summary"))
        spy_day = _number(context.get("SPY DAY %"))
        qqq_day = _number(context.get("QQQ DAY %"))
        if spy_day is not None and qqq_day is not None and spy_day > 0.0 > qqq_day:
            flags.append({"id": "spy_vs_qqq_temp", "severity": "medium", "note": "SPY is positive while QQQ is negative, indicating isolated technology weakness."})
        rotation = _mapping(summary.get("defensive_cyclical_summary"))
        if (_number(rotation.get("REL 3M %")) or 0.0) > 0.0 and (_number(rotation.get("REL 1M %")) or 0.0) < 0.0:
            flags.append({"id": "early_defensive_rotation", "severity": "medium", "note": "Three-month cyclical leadership remains positive while the one-month spread has turned defensive."})
        return flags

    def _trigger_watch(
        self,
        summary: Mapping[str, object],
        distance: Mapping[str, object],
        cycle_state: Mapping[str, object],
    ) -> dict[str, object]:
        high_vix = _mapping(summary.get("high_vix_summary"))
        credit = _mapping(summary.get("credit_risk_proxy"))
        momentum = _mapping(summary.get("breadth_momentum_summary"))
        vix = _number(high_vix.get("VIX"))
        vix_distance = None if vix is None else self.config.vix_neutral_level - vix
        delta10 = _number(momentum.get("A20 DELTA 10D"))
        delta5 = _number(momentum.get("A20 DELTA 5D"))
        a20_distance = None
        if (_number(momentum.get("A20 MOMENTUM FLAG")) or 0.0) < 0.0:
            candidates = []
            if delta10 is not None and delta10 <= -15.0:
                candidates.append(-15.0 - delta10)
            if delta5 is not None and delta5 <= -10.0:
                candidates.append(-10.0 - delta5)
            a20_distance = max(candidates) if candidates else 0.0
        ftd_watch = {}
        for symbol in ("SPY", "QQQ"):
            cycle = _mapping(cycle_state.get(symbol))
            ftd_watch[symbol] = {
                "rally_attempt_day": cycle.get("rally_attempt_day"),
                "minimum_rally_day": self.config.ftd_min_rally_day,
                "minimum_return_pct": self.config.ftd_min_gain_pct,
                "requires_volume_increase": True,
                "requires_close_above_rally_low": True,
            }
        return {
            "score_label": {
                "to_positive": distance.get("to_positive"),
                "to_negative": distance.get("to_negative"),
                "units": "market_score_points",
            },
            "vix_score_neutral_at_vix17": {
                "current_vix": vix,
                "target_vix": self.config.vix_neutral_level,
                "vix_points_to_target": _round(vix_distance),
                "component_score_points_per_vix_point": -self.config.vix_score_slope,
            },
            "under_pressure_clear": {
                symbol: {
                    "current_distribution_count": _mapping(cycle_state.get(symbol)).get("distribution_count_25d"),
                    "maximum_count_to_clear": self.config.distribution_pressure_count - 1,
                    "required_count_reduction": _round(
                        max(
                            0.0,
                            (_number(_mapping(cycle_state.get(symbol)).get("distribution_count_25d")) or 0.0)
                            - (self.config.distribution_pressure_count - 1),
                        )
                    ),
                }
                for symbol in ("SPY", "QQQ")
            },
            "credit_widening_flag": {
                "current_oas_delta_5d_bps": _number(credit.get("HY OAS DELTA 5D BPS")),
                "trigger_bps": 25.0,
                "distance_bps": _round(_nonnegative_distance_to(25.0, _number(credit.get("HY OAS DELTA 5D BPS")))),
            },
            "a20_momentum_flip": {
                "current_flag": _number(momentum.get("A20 MOMENTUM FLAG")),
                "delta10": delta10,
                "delta5": delta5,
                "minimum_improvement_to_neutral_pp": _round(a20_distance),
            },
            "ftd_watch": ftd_watch,
        }

    def _leadership_map(self, summary: Mapping[str, object]) -> dict[str, object]:
        sectors = []
        for row in _rows(summary.get("sector_relative_strength")):
            rel_1m = _number(row.get("REL 1M %"))
            rank_delta = _number(row.get("RANK DELTA 1W"))
            if rel_1m is not None and rel_1m > 0.0:
                tier = "leading_accelerating" if (rank_delta or 0.0) > 0.0 else "leading"
            elif (rank_delta or 0.0) > 0.0:
                tier = "improving_from_lag"
            else:
                tier = "lagging"
            sectors.append(
                {
                    "ticker": row.get("TICKER"),
                    "name": row.get("NAME"),
                    "rel_1m": rel_1m,
                    "rank_1m": _number(row.get("RANK 1M")),
                    "rank_delta_1w": rank_delta,
                    "tier": tier,
                }
            )
        industries = sorted(
            _rows(summary.get("industry_leaders")),
            key=lambda row: (_number(row.get("STRUCT RS")) or float("-inf"), _number(row.get("RS")) or float("-inf")),
            reverse=True,
        )[:5]
        return {
            "sectors": sectors,
            "cyclical_minus_defensive": {
                "1w": _number(_mapping(summary.get("defensive_cyclical_summary")).get("REL 1W %")),
                "1m": _number(_mapping(summary.get("defensive_cyclical_summary")).get("REL 1M %")),
                "3m": _number(_mapping(summary.get("defensive_cyclical_summary")).get("REL 3M %")),
                "units": "pp_spread",
            },
            "industry_top5": [
                {
                    "ticker": row.get("TICKER"),
                    "name": row.get("NAME"),
                    "struct_rs": _number(row.get("STRUCT RS")),
                    "rs": _number(row.get("RS")),
                    "52w_high": row.get("52W HIGH"),
                }
                for row in industries
            ],
        }

    def _data_quality(
        self,
        summary: Mapping[str, object],
        layers: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        series_as_of = {
            str(key): _date_text(value)
            for key, value in _mapping(summary.get("series_as_of")).items()
            if _date_text(value) is not None
        }
        dates = [_parse_date(value) for value in series_as_of.values()]
        valid_dates = [value for value in dates if value is not None]
        max_staleness = (max(valid_dates) - min(valid_dates)).days if valid_dates else None
        internals = _mapping(summary.get("breadth_internal_summary"))
        breadth_available = bool(internals)
        market_rows = _rows(summary.get("market_snapshot"))
        universe_n = _number(internals.get("UNIVERSE COUNT"))
        if universe_n is None:
            universe_n = float(len(market_rows)) if market_rows else None
        missing_blocks: list[dict[str, str]] = []
        if not breadth_available:
            missing_blocks.append({"block": "breadth_internal_summary", "reason": "active-symbol histories were unavailable"})
        for key in (
            "breadth_summary",
            "participation_summary",
            "volatility_term_structure",
            "credit_risk_proxy",
            "index_state_summary",
            "sector_relative_strength",
        ):
            value = summary.get(key)
            if not _mapping(value) and not _rows(value):
                missing_blocks.append({"block": key, "reason": "source data unavailable"})
        if not series_as_of:
            missing_blocks.append({"block": "series_as_of", "reason": "per-series observation dates unavailable"})
        for name, layer in _mapping(layers).items():
            if _number(_mapping(layer).get("score")) is None:
                missing_blocks.append(
                    {
                        "block": f"regime_layers.{name}",
                        "reason": "one or more required derived inputs were unavailable",
                    }
                )

        reasons: list[str] = []
        if not breadth_available:
            reasons.append("breadth internals unavailable")
        if max_staleness is not None and max_staleness > 1:
            reasons.append(f"maximum series staleness is {max_staleness} days")
        core_missing = [item for item in missing_blocks if item["block"] != "breadth_internal_summary"]
        if len(core_missing) >= 2 or (max_staleness is not None and max_staleness > 3):
            confidence = "low"
        elif missing_blocks or (max_staleness is not None and max_staleness > 1):
            confidence = "medium"
        else:
            confidence = "high"
        if core_missing:
            reasons.append("one or more required source blocks are missing")
        if not reasons:
            reasons.append("required blocks and freshness checks passed")
        return {
            "as_of": series_as_of,
            "max_staleness_days": max_staleness,
            "breadth_internal_available": breadth_available,
            "breadth_universe_n": int(universe_n) if universe_n is not None else None,
            "missing_blocks": missing_blocks,
            "overall_confidence": confidence,
            "confidence_reasons": reasons,
        }

    def _score_percentile(
        self,
        summary: Mapping[str, object],
        history: Sequence[Mapping[str, object]],
    ) -> tuple[float | None, int]:
        observations = [_number(item.get("score")) for item in history[-251:]]
        current = _number(summary.get("score"))
        values = [value for value in [*observations, current] if value is not None]
        if current is None or len(values) < 2:
            return None, len(values)
        percentile = 100.0 * sum(value <= current for value in values) / len(values)
        return _round(percentile), len(values)

    @staticmethod
    def _field_semantics() -> dict[str, object]:
        return {
            "component_scores": {"unit": "score_0_100", "transform": "g(x): x<=50; 50+0.6*(x-50) when x>50"},
            "breadth_summary": {"unit": "raw_pct"},
            "participation_summary": {"unit": "raw_pct"},
            "score_attribution": {"unit": "market_score_points"},
            "credit_risk_proxy.HY OAS DELTA * BPS": {"unit": "bps"},
            "ratio_relative_returns": {"unit": "ratio_pt"},
            "sector_and_factor_relative_strength": {"unit": "pp_spread"},
            "pct_2w_high": {"unit": "raw_pct", "actual_semantics": "10_session_closing_high_percentage"},
        }


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and number not in {float("inf"), float("-inf")} else None


def _round(value: float | None, digits: int = 3) -> float | None:
    return None if value is None else round(float(value), digits)


def _clip(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return min(upper, max(lower, value))


def _clip_optional(value: float | None) -> float | None:
    return None if value is None else _clip(value)


def _add_scaled(base: float, value: float | None, scale: float) -> float | None:
    return None if value is None else base + value * scale


def _mean(values: Sequence[float | None]) -> float | None:
    available = [value for value in values if value is not None]
    return sum(available) / len(available) if len(available) == len(values) and available else None


def _driver(field: str, value: float | None, unit: str) -> dict[str, object]:
    return {"field": field, "value": _round(value), "unit": unit}


def _display_number(value: object) -> str:
    number = _number(value)
    return "NA" if number is None else f"{number:.3f}".rstrip("0").rstrip(".")


def _ratio_component_score(raw_value: float) -> float:
    return raw_value if raw_value <= 50.0 else 50.0 + 0.6 * (raw_value - 50.0)


def _difference(current: object, prior: object) -> float | None:
    current_number = _number(current)
    prior_number = _number(prior)
    return None if current_number is None or prior_number is None else current_number - prior_number


def _distance_to(target: float, current: float | None) -> float | None:
    return None if current is None else target - current


def _nonnegative_distance_to(target: float, current: float | None) -> float | None:
    distance = _distance_to(target, current)
    return None if distance is None else max(0.0, distance)


def _date_text(value: object) -> str | None:
    parsed = _parse_date(value)
    return parsed.isoformat() if parsed is not None else None


def _parse_date(value: object) -> date | None:
    if value in {None, ""}:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None
