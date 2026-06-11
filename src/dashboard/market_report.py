from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class MarketReportConfig:
    """Configurable thresholds for AI-input market document generation."""

    write_json: bool = True
    write_markdown: bool = True
    score_improving_1w: float = 3.0
    score_deteriorating_1w: float = -3.0
    score_improving_1m: float = 5.0
    score_deteriorating_1m: float = -5.0
    neutral_score_floor: float = 40.0
    positive_score_floor: float = 60.0
    breadth_strong_level: float = 70.0
    breadth_weak_level: float = 50.0
    s2w_high_active_level: float = 30.0
    s2w_high_weak_level: float = 15.0
    vix_low_level: float = 12.0
    vix_neutral_level: float = 17.0
    vix_elevated_level: float = 25.0
    vix_stress_level: float = 30.0
    safe_haven_positive_threshold: float = 2.0
    safe_haven_negative_threshold: float = -2.0
    high_distance_warning_pct: float = -5.0
    minimum_required_metric_coverage: float = 0.8
    disagreement_penalty: float = 0.2

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "MarketReportConfig":
        if not isinstance(payload, dict):
            return cls()
        output = _mapping(payload.get("output"))
        regime = _mapping(payload.get("regime"))
        breadth = _mapping(payload.get("breadth"))
        volatility = _mapping(payload.get("volatility"))
        risk = _mapping(payload.get("risk"))
        confidence = _mapping(payload.get("confidence"))
        return cls(
            write_json=bool(output.get("write_json", True)),
            write_markdown=bool(output.get("write_markdown", True)),
            score_improving_1w=_float(regime.get("score_improving_1w"), 3.0),
            score_deteriorating_1w=_float(regime.get("score_deteriorating_1w"), -3.0),
            score_improving_1m=_float(regime.get("score_improving_1m"), 5.0),
            score_deteriorating_1m=_float(regime.get("score_deteriorating_1m"), -5.0),
            neutral_score_floor=_float(regime.get("neutral_score_floor"), 40.0),
            positive_score_floor=_float(regime.get("positive_score_floor"), 60.0),
            breadth_strong_level=_float(breadth.get("strong_level"), 70.0),
            breadth_weak_level=_float(breadth.get("weak_level"), 50.0),
            s2w_high_active_level=_float(breadth.get("s2w_high_active_level"), 30.0),
            s2w_high_weak_level=_float(breadth.get("s2w_high_weak_level"), 15.0),
            vix_low_level=_float(volatility.get("vix_low_level"), 12.0),
            vix_neutral_level=_float(volatility.get("vix_neutral_level"), 17.0),
            vix_elevated_level=_float(volatility.get("vix_elevated_level"), 25.0),
            vix_stress_level=_float(volatility.get("vix_stress_level"), 30.0),
            safe_haven_positive_threshold=_float(risk.get("safe_haven_positive_threshold"), 2.0),
            safe_haven_negative_threshold=_float(risk.get("safe_haven_negative_threshold"), -2.0),
            high_distance_warning_pct=_float(risk.get("high_distance_warning_pct"), -5.0),
            minimum_required_metric_coverage=_float(confidence.get("minimum_required_metric_coverage"), 0.8),
            disagreement_penalty=_float(confidence.get("disagreement_penalty"), 0.2),
        )


@dataclass(slots=True)
class MarketReportMetric:
    metric: str
    source_field: str
    value: float | str | None
    raw_value: float | None = None
    score_value: float | None = None
    delta_1d: float | None = None
    delta_1w: float | None = None
    delta_1m: float | None = None
    note: str | None = None


@dataclass(slots=True)
class MarketReportTrajectory:
    category: str
    pattern: str
    sample_count: int
    streak: int
    delta_1d: float | None
    delta_1w: float | None
    delta_1m: float | None
    delta_3m: float | None = None
    best_day_in_window: float | None = None
    worst_day_in_window: float | None = None
    explanation: str = ""


@dataclass(slots=True)
class MarketReportSignificance:
    level: str
    reason: str


@dataclass(slots=True)
class MarketReportSection:
    key: str
    title: str
    label: str
    direction: str | None
    significance: MarketReportSignificance
    summary: str
    metrics: list[MarketReportMetric] = field(default_factory=list)
    facts_for_ai: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trajectory: MarketReportTrajectory | None = None


@dataclass(slots=True)
class MarketReportTransition:
    date: str | None
    category: str
    event: str
    significance: str
    source_fields: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MarketReportWatchpoint:
    metric: str
    threshold: float
    direction: str
    narrative: str
    reason: str
    source_field: str


@dataclass(slots=True)
class MarketReportMissingInput:
    key: str
    reason: str
    phase: str = "v0"


@dataclass(slots=True)
class MarketReportResult:
    schema_version: str
    document_type: str
    trade_date: str | None
    generated_at: str
    source_summary_path: str | None
    executive_context: dict[str, object]
    sections: list[MarketReportSection]
    recent_transitions: list[MarketReportTransition]
    watchpoint_candidates: list[MarketReportWatchpoint]
    analysis_boundary: dict[str, object]
    missing_inputs: list[MarketReportMissingInput]
    data_appendix: list[MarketReportMetric]
    report_generation_contract: dict[str, object]

    @property
    def overall_label(self) -> str:
        return str(self.executive_context.get("market_label", "No Data"))

    @property
    def overall_direction(self) -> str:
        return str(self.executive_context.get("market_direction", "stable"))

    @property
    def confidence(self) -> str:
        return str(self.executive_context.get("confidence", "Low"))

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class MarketReportBuilder:
    """Build an AI-input market document from persisted market_summary JSON."""

    def __init__(self, config: MarketReportConfig | None = None) -> None:
        self.config = config or MarketReportConfig()

    def build(
        self,
        summary: dict[str, object],
        *,
        source_summary_path: str | None = None,
        data_health_summary: dict[str, object] | None = None,
        history_summaries: list[dict[str, object]] | None = None,
    ) -> MarketReportResult:
        history = self._normalized_history(summary, history_summaries)
        sections = [
            self._market_regime(summary, history),
            self._recommendation_inputs(summary),
            self._risk_on_ratio(summary, history),
            self._breadth_and_participation(summary, history),
            self._volatility_and_safe_haven(summary, history),
            self._term_credit_diagnostics(summary, history),
            self._index_state_diagnostics(summary),
            self._sector_rotation(summary, history),
            self._industry_leadership(summary),
            self._factor_and_style(summary),
        ]
        missing_inputs = self._missing_inputs(summary, data_health_summary)
        recent_transitions = self._recent_transitions(summary, history)
        watchpoints = self._watchpoint_candidates(summary)
        executive_context = self._executive_context(summary, sections, recent_transitions, missing_inputs)
        return MarketReportResult(
            schema_version="market_document.v1",
            document_type="ai_market_report_input",
            trade_date=_date_string(summary.get("trade_date")),
            generated_at=datetime.now().isoformat(timespec="seconds"),
            source_summary_path=source_summary_path,
            executive_context=executive_context,
            sections=sections,
            recent_transitions=recent_transitions,
            watchpoint_candidates=watchpoints,
            analysis_boundary=self._analysis_boundary(watchpoints),
            missing_inputs=missing_inputs,
            data_appendix=self._data_appendix(sections),
            report_generation_contract=self._report_generation_contract(),
        )

    def _market_regime(self, summary: dict[str, object], history: list[dict[str, object]]) -> MarketReportSection:
        score = _optional_float(summary.get("score"))
        label = str(summary.get("label", "No Data"))
        direction = self._overall_direction(summary)
        trajectory = self._trajectory(
            "regime",
            history,
            lambda item: _optional_float(item.get("score")),
            _score_delta(summary, "score_1d_ago"),
            _score_delta(summary, "score_1w_ago"),
            _score_delta(summary, "score_1m_ago"),
            _score_delta(summary, "score_3m_ago"),
        )
        significance = self._significance_from_trajectory(
            trajectory,
            high_threshold=3.0,
            medium_threshold=1.0,
            label_changed=self._previous_value(history, "label") not in {None, label},
            reason_source="Market Score / label",
        )
        facts = [
            f"Market Score={_format_number(score)}",
            f"label={label}",
            f"direction={direction}",
            f"trajectory={trajectory.pattern}",
        ]
        return MarketReportSection(
            key="market_regime",
            title="Market Regime",
            label=label,
            direction=direction,
            significance=significance,
            summary="Use this section as the top-level market regime input for the final report.",
            metrics=[
                self._evidence("Market Score", "score", summary.get("score"), delta_1d=trajectory.delta_1d, delta_1w=trajectory.delta_1w, delta_1m=trajectory.delta_1m),
                self._evidence("Score 1D Ago", "score_1d_ago", summary.get("score_1d_ago")),
                self._evidence("Score 1W Ago", "score_1w_ago", summary.get("score_1w_ago")),
                self._evidence("Score 1M Ago", "score_1m_ago", summary.get("score_1m_ago")),
                self._evidence("Score 3M Ago", "score_3m_ago", summary.get("score_3m_ago")),
            ],
            facts_for_ai=facts,
            warnings=self._regime_warnings(summary),
            trajectory=trajectory,
        )

    def _recommendation_inputs(self, summary: dict[str, object]) -> MarketReportSection:
        sector_rows = _records(summary.get("sector_relative_strength"))
        style_rows = _records(summary.get("style_pair_summary"))
        industry_rows = _sort_records(_records(summary.get("industry_leaders")), "RS", reverse=True)
        defensive_cyclical = _mapping(summary.get("defensive_cyclical_summary"))
        overweight = self._overweight_sectors(sector_rows)
        avoid = self._avoid_sectors(sector_rows)
        exit_watch = self._exit_watch_sectors(sector_rows)
        style_tilts = self._style_tilts(style_rows)
        priority_groups = self._priority_candidate_groups(industry_rows, overweight, avoid, exit_watch, style_tilts)
        defensive_spread_1m = _optional_float(defensive_cyclical.get("REL 1M %"))
        facts = []
        if overweight:
            facts.append("priority_sectors=" + ", ".join(overweight))
        if avoid:
            facts.append("lower_priority_new_entries=" + ", ".join(avoid))
        if exit_watch:
            facts.append("profit_taking_exit_watch=" + ", ".join(exit_watch))
        if style_tilts:
            facts.append("style_tilts=" + ", ".join(style_tilts))
        if defensive_spread_1m is not None:
            facts.append(f"cyclical_growth_minus_defensive_1m={_format_number(defensive_spread_1m)}")
        facts.extend(
            [
                "priority_candidate_high=" + _join_group(priority_groups["high"]),
                "priority_candidate_medium=" + _join_group(priority_groups["medium"]),
                "priority_candidate_low_watch=" + _join_group(priority_groups["low_watch"]),
            ]
        )
        significance = MarketReportSignificance(
            level="high" if overweight or avoid or exit_watch else "low",
            reason="Sector/style priority inputs are present." if sector_rows or style_rows else "Sector/style priority inputs are missing.",
        )
        return MarketReportSection(
            key="recommendation_inputs",
            title="Recommendation Inputs",
            label="actionable_inputs" if facts else "insufficient_data",
            direction=None,
            significance=significance,
            summary="System-generated inputs for the skill's investment-priority section. These are not final investment advice by themselves.",
            metrics=[
                *[
                    MarketReportMetric(
                        metric=str(row.get("TICKER", "")),
                        source_field="sector_relative_strength",
                        value=row.get("NAME"),
                        raw_value=_optional_float(row.get("REL 1M %")),
                        delta_1w=_optional_float(row.get("REL 1W %")),
                        delta_1m=_optional_float(row.get("REL 1M %")),
                        note=f"REL 3M={_format_number(_optional_float(row.get('REL 3M %')))}, RANK 1M={_format_number(_optional_float(row.get('RANK 1M')))}, RANK DELTA 1W={_format_number(_optional_float(row.get('RANK DELTA 1W')))}",
                    )
                    for row in sector_rows
                ],
                *[
                    MarketReportMetric(
                        metric=str(row.get("PAIR", "")),
                        source_field="style_pair_summary",
                        value=row.get("NAME"),
                        raw_value=_optional_float(row.get("REL 1M %")),
                        delta_1w=_optional_float(row.get("REL 1W %")),
                        delta_1m=_optional_float(row.get("REL 1M %")),
                        note=f"ABOVE MA COUNT={_format_number(_optional_float(row.get('ABOVE MA COUNT')))} / {_format_number(_optional_float(row.get('MA COUNT')))}",
                    )
                    for row in style_rows
                ],
            ],
            facts_for_ai=facts or ["No actionable sector/style priority input was produced."],
            warnings=[],
        )

    def _risk_on_ratio(self, summary: dict[str, object], history: list[dict[str, object]]) -> MarketReportSection:
        ratio = _mapping(summary.get("risk_on_ratio_summary"))
        rel_1w = _optional_float(ratio.get("REL 1W %"))
        rel_1m = _optional_float(ratio.get("REL 1M %"))
        rel_3m = _optional_float(ratio.get("REL 3M %"))
        high_dist = _optional_float(ratio.get("HIGH DIST %"))
        above_ma = _optional_float(ratio.get("ABOVE MA COUNT"))
        ma_count = _optional_float(ratio.get("MA COUNT"))
        label = self._risk_on_label(rel_1w, rel_1m, rel_3m, high_dist)
        trajectory = self._trajectory(
            "risk_on",
            history,
            lambda item: _optional_float(_mapping(item.get("risk_on_ratio_summary")).get("ABOVE MA COUNT")),
            _metric_delta(summary, "risk_on:ABOVE MA COUNT", "1D"),
            _metric_delta(summary, "risk_on:ABOVE MA COUNT", "1W"),
            _metric_delta(summary, "risk_on:ABOVE MA COUNT", "1M"),
            None,
        )
        significance = self._significance_from_trajectory(
            trajectory,
            high_threshold=1.0,
            medium_threshold=0.5,
            label_changed=self._previous_risk_label(history) not in {None, label},
            reason_source="Risk-On Ratio MA confirmation",
        )
        facts = [
            f"label={label}",
            f"REL 1W={_format_number(rel_1w)}",
            f"REL 1M={_format_number(rel_1m)}",
            f"HIGH DIST={_format_number(high_dist)}",
            f"ABOVE MA COUNT={_format_number(above_ma)} / {_format_number(ma_count)}",
            f"state={self._risk_on_state(above_ma, ma_count, high_dist, rel_1w, rel_1m)}",
        ]
        warnings = []
        if ma_count and above_ma is not None and above_ma < ma_count:
            warnings.append("Risk-On Ratio is not above every configured moving average.")
        if high_dist is not None and high_dist <= self.config.high_distance_warning_pct:
            warnings.append("Risk-On Ratio is below the configured high-distance warning threshold.")
        return MarketReportSection(
            key="risk_on_ratio",
            title="Risk-On Ratio",
            label=label,
            direction=_delta_direction([_metric_delta(summary, "risk_on:REL 1W %", "1W"), _metric_delta(summary, "risk_on:REL 1M %", "1W")]),
            significance=significance,
            summary="Small-growth risk appetite input. The skill may describe posture but must not infer external causes.",
            metrics=[
                self._metric_evidence(summary, "Risk-On Ratio", "risk_on_ratio_summary.RATIO", raw=True),
                self._metric_evidence(summary, "Risk-On REL 1W", "risk_on_ratio_summary.REL 1W %", raw=True),
                self._metric_evidence(summary, "Risk-On REL 1M", "risk_on_ratio_summary.REL 1M %", raw=True),
                self._metric_evidence(summary, "Risk-On REL 3M", "risk_on_ratio_summary.REL 3M %", raw=True),
                self._metric_evidence(summary, "Risk-On High Distance", "risk_on_ratio_summary.HIGH DIST %", raw=True),
                self._metric_evidence(summary, "Risk-On Above MA", "risk_on_ratio_summary.ABOVE MA COUNT", raw=True, note=f"MA COUNT={_format_number(ma_count)}"),
            ],
            facts_for_ai=facts,
            warnings=warnings,
            trajectory=trajectory,
        )

    def _breadth_and_participation(self, summary: dict[str, object], history: list[dict[str, object]]) -> MarketReportSection:
        breadth = _mapping(summary.get("breadth_summary"))
        participation = _mapping(summary.get("participation_summary"))
        high_vix = _mapping(summary.get("high_vix_summary"))
        sma20 = _optional_float(breadth.get("pct_above_sma20"))
        sma50 = _optional_float(breadth.get("pct_above_sma50"))
        positive_1w = _optional_float(participation.get("pct_positive_1w"))
        s2w_high = _optional_float(high_vix.get("S2W HIGH %"))
        label = "strong" if _both_at_or_above([sma20, sma50], self.config.breadth_strong_level) else "mixed"
        if _any_below([sma20, sma50], self.config.breadth_weak_level):
            label = "weak"
        trajectory = self._trajectory(
            "breadth",
            history,
            lambda item: _optional_float(_mapping(item.get("breadth_summary")).get("pct_above_sma20")),
            _metric_delta(summary, "pct_above_sma20", "1D"),
            _metric_delta(summary, "pct_above_sma20", "1W"),
            _metric_delta(summary, "pct_above_sma20", "1M"),
            None,
        )
        significance = self._significance_from_trajectory(
            trajectory,
            high_threshold=7.0,
            medium_threshold=3.0,
            label_changed=self._previous_breadth_label(history) not in {None, label},
            reason_source="SMA20 breadth",
        )
        warnings = []
        if s2w_high is not None and s2w_high < self.config.s2w_high_weak_level:
            warnings.append("S2W High participation is limited.")
        return MarketReportSection(
            key="breadth_participation",
            title="Breadth And Participation",
            label=label,
            direction=_delta_direction([trajectory.delta_1w, _metric_delta(summary, "pct_above_sma50", "1W"), _metric_delta(summary, "pct_positive_1w", "1W")]),
            significance=significance,
            summary="Participation and breadth inputs for determining whether screening standards should be tightened.",
            metrics=[
                self._metric_evidence(summary, "SMA20 Breadth", "breadth_summary.pct_above_sma20", raw=True),
                self._metric_evidence(summary, "SMA50 Breadth", "breadth_summary.pct_above_sma50", raw=True),
                self._metric_evidence(summary, "Positive 1W", "participation_summary.pct_positive_1w", raw=True),
                self._metric_evidence(summary, "Positive 1M", "participation_summary.pct_positive_1m", raw=True),
                self._metric_evidence(summary, "S2W High", "high_vix_summary.S2W HIGH %", raw=True),
            ],
            facts_for_ai=[
                f"SMA20 breadth={_format_number(sma20)}",
                f"SMA50 breadth={_format_number(sma50)}",
                f"Positive 1W={_format_number(positive_1w)}",
                f"S2W HIGH={_format_number(s2w_high)}",
                f"trajectory={trajectory.pattern}",
            ],
            warnings=warnings,
            trajectory=trajectory,
        )

    def _volatility_and_safe_haven(self, summary: dict[str, object], history: list[dict[str, object]]) -> MarketReportSection:
        vix = _optional_float(summary.get("vix_close"))
        high_vix = _mapping(summary.get("high_vix_summary"))
        safe_haven = _optional_float(high_vix.get("SAFE HAVEN %"))
        vix_percentile = _optional_float(high_vix.get("VIX 252D PCTL"))
        vix_peak_days = _optional_float(high_vix.get("VIX PEAK DAYS"))
        vix_peak_ratio = _optional_float(high_vix.get("VIX PEAK RATIO %"))
        vix_label = self._vix_label(vix)
        safe_haven_label = self._safe_haven_label(safe_haven)
        previous_vix_label = self._previous_vix_label(history)
        label_changed = previous_vix_label not in {None, vix_label}
        delta_1d = _metric_delta(summary, "VIX", "1D")
        significance = MarketReportSignificance(
            level="high" if label_changed else ("medium" if _abs_ge(delta_1d, 1.0) else "low"),
            reason="VIX label changed." if label_changed else "VIX/Safe Haven label is unchanged.",
        )
        warnings = []
        if vix is not None and safe_haven is not None and vix <= self.config.vix_neutral_level and safe_haven < self.config.safe_haven_negative_threshold:
            warnings.append("VIX is benign while Safe Haven is Risk-Off.")
        return MarketReportSection(
            key="volatility_safe_haven",
            title="Volatility And Safe Haven",
            label=f"{vix_label} / {safe_haven_label}",
            direction=_delta_direction([_negate_optional(_metric_delta(summary, "VIX", "1W")), _metric_delta(summary, "safe_haven_score", "1W")]),
            significance=significance,
            summary="Volatility and Safe Haven input. The skill must not infer macro causes from this section.",
            metrics=[
                self._evidence("VIX Close", "vix_close", summary.get("vix_close"), delta_1d=_metric_delta(summary, "VIX", "1D"), delta_1w=_metric_delta(summary, "VIX", "1W"), delta_1m=_metric_delta(summary, "VIX", "1M")),
                self._evidence("VIX 252D Percentile", "high_vix_summary.VIX 252D PCTL", vix_percentile, delta_1d=_metric_delta(summary, "VIX 252D PCTL", "1D"), delta_1w=_metric_delta(summary, "VIX 252D PCTL", "1W"), delta_1m=_metric_delta(summary, "VIX 252D PCTL", "1M")),
                self._evidence("VIX Peak Days", "high_vix_summary.VIX PEAK DAYS", vix_peak_days, delta_1d=_metric_delta(summary, "VIX PEAK DAYS", "1D"), delta_1w=_metric_delta(summary, "VIX PEAK DAYS", "1W"), delta_1m=_metric_delta(summary, "VIX PEAK DAYS", "1M")),
                self._evidence("VIX Peak Ratio", "high_vix_summary.VIX PEAK RATIO %", vix_peak_ratio, delta_1d=_metric_delta(summary, "VIX PEAK RATIO %", "1D"), delta_1w=_metric_delta(summary, "VIX PEAK RATIO %", "1W"), delta_1m=_metric_delta(summary, "VIX PEAK RATIO %", "1M")),
                self._metric_evidence(summary, "Safe Haven Spread", "high_vix_summary.SAFE HAVEN %", raw=True),
                self._metric_evidence(summary, "VIX Score", "component_scores.vix_score", score=True),
                self._metric_evidence(summary, "Safe Haven Score", "component_scores.safe_haven_score", score=True),
            ],
            facts_for_ai=[
                f"VIX={_format_number(vix)}",
                f"VIX label={vix_label}",
                f"VIX 252D PCTL={_format_number(vix_percentile)}",
                f"VIX PEAK DAYS={_format_number(vix_peak_days)}",
                f"VIX PEAK RATIO %={_format_number(vix_peak_ratio)}",
                f"Safe Haven={_format_number(safe_haven)}",
                f"Safe Haven label={safe_haven_label}",
            ],
            warnings=warnings,
        )

    def _term_credit_diagnostics(self, summary: dict[str, object], history: list[dict[str, object]]) -> MarketReportSection:
        term = _mapping(summary.get("volatility_term_structure"))
        credit = _mapping(summary.get("credit_risk_proxy"))
        vix_ratio = _optional_float(term.get("RATIO"))
        inversion_flag = _optional_float(term.get("INVERSION FLAG"))
        credit_flag = _optional_float(credit.get("CREDIT RISK-OFF FLAG"))
        hyg_lqd_1m = _optional_float(credit.get("HYG/LQD REL 1M %"))
        hyg_ief_1m = _optional_float(credit.get("HYG/IEF REL 1M %"))
        term_label = self._vix_term_label(vix_ratio, inversion_flag)
        credit_label = self._credit_proxy_label(hyg_lqd_1m, hyg_ief_1m, credit_flag)
        warnings = []
        if inversion_flag == 1.0:
            warnings.append("VIX term structure is inverted.")
        if credit_flag == 1.0:
            warnings.append("Credit proxy is weakening across both configured ratios.")
        significance = MarketReportSignificance(
            level="high" if warnings else ("medium" if term or credit else "low"),
            reason="Term/credit diagnostic warning is active." if warnings else "Term/credit diagnostics are available without an active warning.",
        )
        return MarketReportSection(
            key="term_credit_diagnostics",
            title="Term And Credit Diagnostics",
            label=f"{term_label} / {credit_label}",
            direction=_delta_direction(
                [
                    _negate_optional(_metric_delta(summary, "vix_term:RATIO", "1W")),
                    _metric_delta(summary, "credit:HYG/LQD REL 1W %", "1W"),
                    _metric_delta(summary, "credit:HYG/IEF REL 1W %", "1W"),
                ]
            ),
            significance=significance,
            summary="Volatility term structure and credit risk proxy diagnostics. These are context inputs, not direct scan or entry rules.",
            metrics=[
                self._evidence("VIX/VIX3M", "volatility_term_structure.RATIO", term.get("RATIO"), delta_1d=_metric_delta(summary, "vix_term:RATIO", "1D"), delta_1w=_metric_delta(summary, "vix_term:RATIO", "1W"), delta_1m=_metric_delta(summary, "vix_term:RATIO", "1M")),
                self._evidence("VIX3M", "volatility_term_structure.VIX3M", term.get("VIX3M"), delta_1d=_metric_delta(summary, "vix_term:VIX3M", "1D"), delta_1w=_metric_delta(summary, "vix_term:VIX3M", "1W"), delta_1m=_metric_delta(summary, "vix_term:VIX3M", "1M")),
                self._evidence("HYG/LQD", "credit_risk_proxy.HYG/LQD RATIO", credit.get("HYG/LQD RATIO"), delta_1d=_metric_delta(summary, "credit:HYG/LQD RATIO", "1D"), delta_1w=_metric_delta(summary, "credit:HYG/LQD RATIO", "1W"), delta_1m=_metric_delta(summary, "credit:HYG/LQD RATIO", "1M")),
                self._evidence("HYG/IEF", "credit_risk_proxy.HYG/IEF RATIO", credit.get("HYG/IEF RATIO"), delta_1d=_metric_delta(summary, "credit:HYG/IEF RATIO", "1D"), delta_1w=_metric_delta(summary, "credit:HYG/IEF RATIO", "1W"), delta_1m=_metric_delta(summary, "credit:HYG/IEF RATIO", "1M")),
            ],
            facts_for_ai=[
                f"VIX/VIX3M={_format_number(vix_ratio)}",
                f"term_label={term_label}",
                f"HYG/LQD REL 1M={_format_number(hyg_lqd_1m)}",
                f"HYG/IEF REL 1M={_format_number(hyg_ief_1m)}",
                f"credit_label={credit_label}",
            ],
            warnings=warnings,
        )

    def _index_state_diagnostics(self, summary: dict[str, object]) -> MarketReportSection:
        index_state = _mapping(summary.get("index_state_summary"))
        symbols = self._index_state_symbols(index_state)
        statuses = {symbol: self._index_state_status(index_state, symbol) for symbol in symbols}
        under_pressure = any(
            _optional_float(index_state.get(f"{symbol} UNDER PRESSURE FLAG")) == 1.0
            for symbol in symbols
        )
        ftd_confirmed = any(
            _optional_float(index_state.get(f"{symbol} FTD FLAG")) == 1.0
            for symbol in symbols
        )
        active_attempt = any(
            (_optional_float(index_state.get(f"{symbol} RALLY ATTEMPT DAY")) or 0.0) > 0.0
            for symbol in symbols
        )
        if ftd_confirmed and under_pressure:
            label = "confirmed_rally_under_pressure"
        elif ftd_confirmed:
            label = "confirmed_rally"
        elif active_attempt:
            label = "rally_attempt"
        elif symbols:
            label = "no_active_attempt"
        else:
            label = "no_data"
        warnings = []
        if under_pressure:
            warnings.append("Distribution day count is at or above the configured pressure threshold.")
        if active_attempt and not ftd_confirmed:
            warnings.append("Rally attempt exists but no follow-through day is confirmed.")
        significance = MarketReportSignificance(
            level="high" if warnings else ("medium" if ftd_confirmed else "low"),
            reason="Index state warning is active." if warnings else "Index state diagnostic is available.",
        )
        metrics: list[MarketReportMetric] = []
        facts: list[str] = []
        for symbol in symbols:
            rally_day = _optional_float(index_state.get(f"{symbol} RALLY ATTEMPT DAY"))
            ftd_flag = _optional_float(index_state.get(f"{symbol} FTD FLAG"))
            ftd_age = _optional_float(index_state.get(f"{symbol} FTD AGE DAYS"))
            ftd_gain = _optional_float(index_state.get(f"{symbol} FTD GAIN %"))
            ftd_volume_ratio = _optional_float(index_state.get(f"{symbol} FTD VOLUME RATIO"))
            ftd_advance_ratio = _optional_float(index_state.get(f"{symbol} FTD ADVANCE RATIO"))
            ftd_quality_score = _optional_float(index_state.get(f"{symbol} FTD QUALITY SCORE"))
            distribution_count = _optional_float(index_state.get(f"{symbol} DISTRIBUTION DAY COUNT"))
            pressure_flag = _optional_float(index_state.get(f"{symbol} UNDER PRESSURE FLAG"))
            metrics.extend(
                [
                    self._evidence(f"{symbol} Rally Attempt Day", f"index_state_summary.{symbol} RALLY ATTEMPT DAY", rally_day),
                    self._evidence(f"{symbol} FTD Flag", f"index_state_summary.{symbol} FTD FLAG", ftd_flag),
                    self._evidence(f"{symbol} FTD Age Days", f"index_state_summary.{symbol} FTD AGE DAYS", ftd_age),
                    self._evidence(f"{symbol} FTD Gain", f"index_state_summary.{symbol} FTD GAIN %", ftd_gain),
                    self._evidence(f"{symbol} FTD Volume Ratio", f"index_state_summary.{symbol} FTD VOLUME RATIO", ftd_volume_ratio),
                    self._evidence(f"{symbol} FTD Advance Ratio", f"index_state_summary.{symbol} FTD ADVANCE RATIO", ftd_advance_ratio),
                    self._evidence(f"{symbol} FTD Quality Score", f"index_state_summary.{symbol} FTD QUALITY SCORE", ftd_quality_score),
                    self._evidence(f"{symbol} Distribution Days", f"index_state_summary.{symbol} DISTRIBUTION DAY COUNT", distribution_count),
                    self._evidence(f"{symbol} Under Pressure", f"index_state_summary.{symbol} UNDER PRESSURE FLAG", pressure_flag),
                ]
            )
            facts.append(
                f"{symbol} status={statuses.get(symbol, 'no_data')}, rally_day={_format_number(rally_day)}, "
                f"ftd_flag={_format_number(ftd_flag)}, ftd_age={_format_number(ftd_age)}, "
                f"ftd_quality={_format_number(ftd_quality_score)}, distribution_days={_format_number(distribution_count)}"
            )
        direction = "weakening" if under_pressure else ("improving" if ftd_confirmed else "stable")
        return MarketReportSection(
            key="index_state_diagnostics",
            title="Index State Diagnostics",
            label=label,
            direction=direction,
            significance=significance,
            summary="SPY/QQQ follow-through day, rally-attempt, and distribution-day diagnostics. These are context inputs and do not change Market Score.",
            metrics=metrics,
            facts_for_ai=facts or ["Index state diagnostics are unavailable."],
            warnings=warnings,
        )

    def _sector_rotation(self, summary: dict[str, object], history: list[dict[str, object]]) -> MarketReportSection:
        sector_rows = _records(summary.get("sector_relative_strength"))
        market_records = _records(summary.get("market_snapshot"))
        counts = _position_counts(market_records)
        previous_counts = _position_counts(_records(_mapping(history[-2]).get("market_snapshot"))) if len(history) >= 2 else {}
        above = counts.get("above 21EMA High", 0)
        below = counts.get("below 21EMA Low", 0)
        label = "constructive" if above > below else "mixed"
        if below > above:
            label = "weakening"
        distribution_changed = counts != previous_counts if previous_counts else False
        significance = MarketReportSignificance(
            level="high" if distribution_changed and abs(above - previous_counts.get("above 21EMA High", above)) >= 2 else ("medium" if distribution_changed else "low"),
            reason=f"21EMA POS distribution: {counts}; previous={previous_counts or 'unavailable'}",
        )
        facts = [
            f"21EMA POS distribution={counts}",
            f"top_relative_1m={', '.join(_ticker_name(row) for row in sector_rows[:3])}" if sector_rows else "top_relative_1m=unavailable",
        ]
        return MarketReportSection(
            key="sector_rotation",
            title="Sector Rotation",
            label=label,
            direction=None,
            significance=significance,
            summary="Sector rotation inputs based on relative strength and 21EMA POS distribution.",
            metrics=[
                self._evidence("Core 21EMA Above Count", "market_snapshot.21EMA POS", above, raw_value=float(above), note=str(counts)),
                *[
                    MarketReportMetric(
                        metric=str(row.get("TICKER", "")),
                        source_field="sector_relative_strength",
                        value=row.get("NAME"),
                        raw_value=_optional_float(row.get("REL 1M %")),
                        delta_1w=_optional_float(row.get("REL 1W %")),
                        delta_1m=_optional_float(row.get("REL 1M %")),
                    )
                    for row in sector_rows[:5]
                ],
            ],
            facts_for_ai=facts,
            warnings=[],
        )

    def _industry_leadership(self, summary: dict[str, object]) -> MarketReportSection:
        industry_rows = _sort_records(_records(summary.get("industry_leaders")), "RS", reverse=True)
        if not industry_rows:
            return MarketReportSection(
                key="industry_leadership",
                title="Industry Leadership",
                label="no_data",
                direction=None,
                significance=MarketReportSignificance(level="low", reason="Industry leader rows are missing."),
                summary="Industry-level leadership inputs for final-report candidate-priority guidance.",
                facts_for_ai=["No industry leadership data is available."],
            )

        top_industries = industry_rows[:5]
        new_high_industries = [row for row in industry_rows if _is_52w_high(row.get("52W HIGH"))][:5]
        accelerating_industries = [row for row in industry_rows if _is_accelerating_industry(row)][:5]
        sustained_industries = [row for row in industry_rows if _is_sustained_industry(row)][:5]
        weak_industries = _weak_industries(industry_rows)[:5]
        facts = [
            "top_industries=" + _industry_list(top_industries),
            "new_high_industries=" + _industry_list(new_high_industries),
            "accelerating_industries=" + _industry_list(accelerating_industries),
            "sustained_leadership_industries=" + _industry_list(sustained_industries),
            "weak_industries=" + _industry_list(weak_industries),
        ]
        label = "confirmed_industry_leadership" if new_high_industries or sustained_industries else "mixed_industry_leadership"
        if not top_industries:
            label = "no_data"
        significance = MarketReportSignificance(
            level="high" if new_high_industries or sustained_industries else "medium",
            reason="Industry-level RS leaders and 52W HIGH context are available.",
        )
        evidence_rows = _unique_records([*top_industries, *new_high_industries, *accelerating_industries, *weak_industries])
        metrics = [_industry_metric(row) for row in evidence_rows[:12]]
        return MarketReportSection(
            key="industry_leadership",
            title="Industry Leadership",
            label=label,
            direction=None,
            significance=significance,
            summary="Industry-level leadership inputs for final-report candidate-priority guidance.",
            metrics=metrics,
            facts_for_ai=facts,
            warnings=[],
        )

    def _factor_and_style(self, summary: dict[str, object]) -> MarketReportSection:
        factors = _records(summary.get("factors_vs_sp500"))
        style_rows = _records(summary.get("style_pair_summary"))
        classifications = []
        metrics: list[MarketReportMetric] = []
        for record in factors:
            ticker = str(record.get("TICKER", "")).strip()
            rel_1w = _optional_float(record.get("REL 1W %"))
            rel_1m = _optional_float(record.get("REL 1M %"))
            classification = _factor_classification(rel_1w, rel_1m)
            classifications.append(f"{ticker}={classification}")
            metrics.append(
                MarketReportMetric(
                    metric=ticker,
                    source_field="factors_vs_sp500",
                    value=classification,
                    raw_value=rel_1m,
                    delta_1w=rel_1w,
                    delta_1m=rel_1m,
                )
            )
        for row in style_rows:
            metrics.append(
                MarketReportMetric(
                    metric=str(row.get("PAIR", "")),
                    source_field="style_pair_summary",
                    value=row.get("NAME"),
                    raw_value=_optional_float(row.get("REL 1M %")),
                    delta_1w=_optional_float(row.get("REL 1W %")),
                    delta_1m=_optional_float(row.get("REL 1M %")),
                )
            )
        label = "factor_leadership" if any("=accelerating" in item for item in classifications) else "no_clear_factor_leadership"
        if not factors and not style_rows:
            label = "no_data"
        return MarketReportSection(
            key="factor_style",
            title="Factor And Style",
            label=label,
            direction=None,
            significance=MarketReportSignificance(
                level="medium" if factors or style_rows else "low",
                reason="Factor/style rows are available." if factors or style_rows else "Factor/style rows are missing.",
            ),
            summary="Factor/style inputs. The final skill should summarize only material factor/style differences.",
            metrics=metrics,
            facts_for_ai=classifications or ["No factor/style data is available."],
            warnings=[],
        )

    def _executive_context(
        self,
        summary: dict[str, object],
        sections: list[MarketReportSection],
        transitions: list[MarketReportTransition],
        missing_inputs: list[MarketReportMissingInput],
    ) -> dict[str, object]:
        section_map = {section.key: section for section in sections}
        score = _optional_float(summary.get("score"))
        label = str(summary.get("label", "No Data"))
        direction = self._overall_direction(summary)
        risk = section_map.get("risk_on_ratio")
        breadth = section_map.get("breadth_participation")
        recommendation = section_map.get("recommendation_inputs")
        industry = section_map.get("industry_leadership")
        volatility = section_map.get("volatility_safe_haven")
        diagnostics = section_map.get("term_credit_diagnostics")
        index_state = section_map.get("index_state_diagnostics")
        sector = section_map.get("sector_rotation")
        required_missing = [item.key for item in missing_inputs if item.phase == "v0"]
        confidence = "Low" if required_missing else ("Medium" if transitions else "High")
        action_mode = self._market_action_mode(summary, section_map)
        confirmation_order = self._confirmation_order(action_mode, section_map)
        swing_market_posture = self._swing_market_posture(action_mode, summary, section_map)
        action_context = [
            f"Market Score { _format_number(score) } is {label} and direction is {direction}.",
            f"market_action_mode={action_mode['label']} ({action_mode['key']})",
            f"action_mode_reason={action_mode['reason']}",
            f"Risk-On Ratio posture is {risk.label if risk else 'unavailable'}.",
            f"Breadth posture is {breadth.label if breadth else 'unavailable'}.",
        ]
        if industry:
            action_context.append(f"Industry leadership posture is {industry.label}.")
        if sector:
            action_context.append(f"Sector rotation posture is {sector.label}.")
        if volatility:
            action_context.append(f"Volatility/Safe Haven posture is {volatility.label}.")
        if diagnostics:
            action_context.append(f"Term/Credit diagnostics posture is {diagnostics.label}.")
        if index_state:
            action_context.append(f"Index state diagnostics posture is {index_state.label}.")
        if recommendation and recommendation.facts_for_ai:
            action_context.append("Priority inputs: " + " / ".join(recommendation.facts_for_ai[:3]))
        return {
            "market_label": label,
            "market_score": score,
            "market_direction": direction,
            "market_action_mode": action_mode["label"],
            "market_action_mode_key": action_mode["key"],
            "market_action_mode_reason": action_mode["reason"],
            "swing_market_posture": swing_market_posture,
            "confirmation_order": confirmation_order,
            "confidence": confidence,
            "one_line_diagnosis": f"{action_mode['label']}: Market Score {_format_number(score)} ({label}, {direction})",
            "action_context_facts": action_context,
            "notable_changes": [item.event for item in transitions[:2]],
            "required_missing_inputs": required_missing,
        }

    def _recent_transitions(self, summary: dict[str, object], history: list[dict[str, object]]) -> list[MarketReportTransition]:
        if len(history) < 2:
            return []
        previous = history[-2]
        current_date = _date_string(summary.get("trade_date"))
        transitions: list[MarketReportTransition] = []
        previous_label = str(previous.get("label", "No Data"))
        current_label = str(summary.get("label", "No Data"))
        if previous_label != current_label:
            transitions.append(
                MarketReportTransition(
                    date=current_date,
                    category="regime",
                    event=f"Market label changed from {previous_label} to {current_label}.",
                    significance="high",
                    source_fields=["label", "score"],
                )
            )
        previous_risk = self._previous_risk_label(history)
        current_risk = self._risk_on_label_from_summary(summary)
        if previous_risk is not None and previous_risk != current_risk:
            transitions.append(
                MarketReportTransition(
                    date=current_date,
                    category="risk_on",
                    event=f"Risk-On Ratio state changed from {previous_risk} to {current_risk}.",
                    significance="high",
                    source_fields=["risk_on_ratio_summary.REL 1M %", "risk_on_ratio_summary.HIGH DIST %", "risk_on_ratio_summary.ABOVE MA COUNT"],
                )
            )
        previous_breadth = self._previous_breadth_label(history)
        current_breadth = self._breadth_label_from_summary(summary)
        if previous_breadth is not None and previous_breadth != current_breadth:
            transitions.append(
                MarketReportTransition(
                    date=current_date,
                    category="breadth",
                    event=f"Breadth state changed from {previous_breadth} to {current_breadth}.",
                    significance="medium",
                    source_fields=["breadth_summary.pct_above_sma20", "breadth_summary.pct_above_sma50"],
                )
            )
        return transitions[:5]

    def _watchpoint_candidates(self, summary: dict[str, object]) -> list[MarketReportWatchpoint]:
        breadth = _mapping(summary.get("breadth_summary"))
        ratio = _mapping(summary.get("risk_on_ratio_summary"))
        vix = _optional_float(summary.get("vix_close"))
        candidates: list[MarketReportWatchpoint] = []
        sma20 = _optional_float(breadth.get("pct_above_sma20"))
        if sma20 is not None:
            threshold = self.config.breadth_weak_level if sma20 < self.config.breadth_weak_level else self.config.breadth_strong_level
            direction = "above" if sma20 < self.config.breadth_weak_level else "below"
            narrative = "SMA20 breadth が50%を回復するか" if direction == "above" else "SMA20 breadth が70%を維持できるか"
            candidates.append(
                MarketReportWatchpoint(
                    metric="breadth_summary.pct_above_sma20",
                    threshold=threshold,
                    direction=direction,
                    narrative=narrative,
                    reason=f"current={_format_number(sma20)}",
                    source_field="breadth_summary.pct_above_sma20",
                )
            )
        rel_1w = _optional_float(ratio.get("REL 1W %"))
        if rel_1w is not None:
            candidates.append(
                MarketReportWatchpoint(
                    metric="risk_on_ratio_summary.REL 1W %",
                    threshold=0.0,
                    direction="above" if rel_1w <= 0 else "below",
                    narrative="Risk-On Ratio のREL 1Wが正に転じるか" if rel_1w <= 0 else "Risk-On Ratio のREL 1Wがプラスを維持できるか",
                    reason=f"current={_format_number(rel_1w)}",
                    source_field="risk_on_ratio_summary.REL 1W %",
                )
            )
        above_ma = _optional_float(ratio.get("ABOVE MA COUNT"))
        ma_count = _optional_float(ratio.get("MA COUNT"))
        if above_ma is not None and ma_count:
            target = min(ma_count, max(1.0, above_ma + 1.0))
            candidates.append(
                MarketReportWatchpoint(
                    metric="risk_on_ratio_summary.ABOVE MA COUNT",
                    threshold=target,
                    direction="above",
                    narrative="Risk-On Ratio が少なくとも追加のMAを回復するか",
                    reason=f"current={_format_number(above_ma)} / {_format_number(ma_count)}",
                    source_field="risk_on_ratio_summary.ABOVE MA COUNT",
                )
            )
        if vix is not None:
            threshold = self.config.vix_neutral_level if vix < self.config.vix_neutral_level else self.config.vix_elevated_level
            candidates.append(
                MarketReportWatchpoint(
                    metric="vix_close",
                    threshold=threshold,
                    direction="below" if vix >= self.config.vix_neutral_level else "above",
                    narrative="VIX が中立水準を回復/維持できるか",
                    reason=f"current={_format_number(vix)}",
                    source_field="vix_close",
                )
            )
        return candidates[:4]

    def _analysis_boundary(self, watchpoints: list[MarketReportWatchpoint]) -> dict[str, object]:
        return {
            "allowed_sources": [
                "本ドキュメント内の数値、ラベル、trajectory、significance",
                "本ドキュメント内の facts_for_ai",
                "本ドキュメント内の watchpoint_candidates",
            ],
            "prohibited_sources": [
                "経済指標の発表スケジュール",
                "個別企業の決算やニュース",
                "原油価格、金利、為替など本ドキュメントに存在しない外部市場要因",
                "地政学的イベント",
            ],
            "watchpoint_candidates_only": [item.metric for item in watchpoints],
            "sector_inference_limit": "セクター/業種の含意は 21EMA POS、DAY%、relative strength、52W HIGH、basket comparison の範囲に限定する。上昇/下落の外部理由は書かない。",
        }

    def _report_generation_contract(self) -> dict[str, object]:
        return {
            "final_report_owner": "skill",
            "system_output_role": "AIが品質を満たす日次マーケットレポートを書くための根拠付き入力を生成する。",
            "must_not_do": [
                "外部イベントやニュースを補完しない",
                "個別銘柄の売買実行指示を書かない",
                "ポジションサイズや損切り管理を書かない",
                "swing_market_posture を売買執行やポジション管理の指示に変換しない",
                "watchpoint_candidates にない次回注視点を作らない",
            ],
            "token_efficiency_rule": "significance=low の section は最終レポートで1文以内に圧縮してよい。",
        }

    def _missing_inputs(self, summary: dict[str, object], data_health_summary: dict[str, object] | None) -> list[MarketReportMissingInput]:
        missing: list[MarketReportMissingInput] = []
        required = [
            "score",
            "label",
            "breadth_summary",
            "participation_summary",
            "metric_deltas",
            "high_vix_summary",
            "risk_on_ratio_summary",
            "market_snapshot",
            "factors_vs_sp500",
        ]
        for key in required:
            if key not in summary or summary.get(key) in (None, {}, []):
                missing.append(MarketReportMissingInput(key=key, reason="Required market document input is unavailable."))
        enriched = {
            "sector_relative_strength": "Useful for sector rotation priority.",
            "style_pair_summary": "Useful for style rotation priority.",
            "defensive_cyclical_summary": "Useful for Defensive vs Cyclical/Growth spread.",
            "industry_leaders": "Useful for industry-level leadership priority.",
            "volatility_term_structure": "Useful for VIX term structure diagnostics.",
            "credit_risk_proxy": "Useful for credit risk proxy diagnostics.",
            "index_state_summary": "Useful for FTD, rally attempt, and distribution-day diagnostics.",
        }
        for key, reason in enriched.items():
            if key not in summary or summary.get(key) in (None, {}, []):
                missing.append(MarketReportMissingInput(key=key, reason=reason, phase="phase2"))
        if data_health_summary:
            for key in ["sample_count", "stale_cache_count", "missing_count"]:
                value = _optional_float(data_health_summary.get(key))
                if value and value > 0:
                    missing.append(MarketReportMissingInput(key=f"data_health_summary.{key}", reason=f"Data health warning count is {int(value)}."))
        return missing

    def _data_appendix(self, sections: list[MarketReportSection]) -> list[MarketReportMetric]:
        seen: set[tuple[str, str]] = set()
        appendix: list[MarketReportMetric] = []
        for metric in [item for section in sections for item in section.metrics]:
            key = (metric.metric, metric.source_field)
            if key in seen:
                continue
            seen.add(key)
            appendix.append(metric)
        return appendix

    def _normalized_history(self, summary: dict[str, object], history_summaries: list[dict[str, object]] | None) -> list[dict[str, object]]:
        history = [item for item in (history_summaries or []) if isinstance(item, dict)]
        current_date = _date_string(summary.get("trade_date"))
        if not history or _date_string(history[-1].get("trade_date")) != current_date:
            history.append(summary)
        return history[-10:]

    def _trajectory(
        self,
        category: str,
        history: list[dict[str, object]],
        value_getter,
        delta_1d: float | None,
        delta_1w: float | None,
        delta_1m: float | None,
        delta_3m: float | None,
    ) -> MarketReportTrajectory:
        values = [_optional_float(value_getter(item)) for item in history]
        values = [value for value in values if value is not None]
        deltas = [round(values[index] - values[index - 1], 3) for index in range(1, len(values))]
        recent_deltas = deltas[-5:]
        pattern = _trajectory_pattern(recent_deltas)
        streak = _signed_streak(recent_deltas)
        return MarketReportTrajectory(
            category=category,
            pattern=pattern,
            sample_count=len(values),
            streak=streak,
            delta_1d=delta_1d,
            delta_1w=delta_1w,
            delta_1m=delta_1m,
            delta_3m=delta_3m,
            best_day_in_window=max(recent_deltas) if recent_deltas else None,
            worst_day_in_window=min(recent_deltas) if recent_deltas else None,
            explanation=_trajectory_explanation(pattern, recent_deltas),
        )

    def _significance_from_trajectory(
        self,
        trajectory: MarketReportTrajectory,
        *,
        high_threshold: float,
        medium_threshold: float,
        label_changed: bool,
        reason_source: str,
    ) -> MarketReportSignificance:
        if label_changed:
            return MarketReportSignificance(level="high", reason=f"{reason_source} label changed.")
        change = max(abs(value) for value in [trajectory.delta_1d, trajectory.delta_1w] if value is not None) if any(value is not None for value in [trajectory.delta_1d, trajectory.delta_1w]) else 0.0
        if change >= high_threshold:
            return MarketReportSignificance(level="high", reason=f"{reason_source} changed materially.")
        if change >= medium_threshold:
            return MarketReportSignificance(level="medium", reason=f"{reason_source} moved but label did not change.")
        return MarketReportSignificance(level="low", reason=f"{reason_source} is broadly unchanged.")

    def _overall_direction(self, summary: dict[str, object]) -> str:
        delta_1w = _score_delta(summary, "score_1w_ago")
        delta_1m = _score_delta(summary, "score_1m_ago")
        if delta_1w is not None and delta_1w >= self.config.score_improving_1w:
            return "improving"
        if delta_1m is not None and delta_1m >= self.config.score_improving_1m:
            return "improving"
        if delta_1w is not None and delta_1w <= self.config.score_deteriorating_1w:
            return "deteriorating"
        if delta_1m is not None and delta_1m <= self.config.score_deteriorating_1m:
            return "deteriorating"
        return "stable"

    def _risk_on_label_from_summary(self, summary: dict[str, object]) -> str:
        ratio = _mapping(summary.get("risk_on_ratio_summary"))
        return self._risk_on_label(
            _optional_float(ratio.get("REL 1W %")),
            _optional_float(ratio.get("REL 1M %")),
            _optional_float(ratio.get("REL 3M %")),
            _optional_float(ratio.get("HIGH DIST %")),
        )

    def _risk_on_label(self, rel_1w: float | None, rel_1m: float | None, rel_3m: float | None, high_dist: float | None) -> str:
        positives = sum(1 for value in [rel_1w, rel_1m, rel_3m] if value is not None and value > 0)
        label = "risk_on" if positives >= 2 else "mixed"
        if positives == 0 or (high_dist is not None and high_dist <= self.config.high_distance_warning_pct):
            label = "risk_off_warning"
        return label

    def _risk_on_state(self, above_ma: float | None, ma_count: float | None, high_dist: float | None, rel_1w: float | None, rel_1m: float | None) -> str:
        if ma_count and above_ma == 0 and high_dist is not None and high_dist <= self.config.high_distance_warning_pct:
            return "structural_risk_off"
        if rel_1w is not None and rel_1w > 0 and rel_1m is not None and rel_1m <= 0:
            return "rebound_attempt_needs_confirmation"
        if ma_count and above_ma is not None and 0 < above_ma < ma_count:
            return "partial_recovery_or_early_risk_off"
        if ma_count and above_ma == ma_count:
            return "confirmed_risk_on"
        return "mixed"

    def _breadth_label_from_summary(self, summary: dict[str, object]) -> str:
        breadth = _mapping(summary.get("breadth_summary"))
        sma20 = _optional_float(breadth.get("pct_above_sma20"))
        sma50 = _optional_float(breadth.get("pct_above_sma50"))
        if _both_at_or_above([sma20, sma50], self.config.breadth_strong_level):
            return "strong"
        if _any_below([sma20, sma50], self.config.breadth_weak_level):
            return "weak"
        return "mixed"

    def _previous_value(self, history: list[dict[str, object]], key: str) -> object | None:
        return history[-2].get(key) if len(history) >= 2 else None

    def _previous_risk_label(self, history: list[dict[str, object]]) -> str | None:
        return self._risk_on_label_from_summary(history[-2]) if len(history) >= 2 else None

    def _previous_breadth_label(self, history: list[dict[str, object]]) -> str | None:
        return self._breadth_label_from_summary(history[-2]) if len(history) >= 2 else None

    def _previous_vix_label(self, history: list[dict[str, object]]) -> str | None:
        return self._vix_label(_optional_float(history[-2].get("vix_close"))) if len(history) >= 2 else None

    def _regime_warnings(self, summary: dict[str, object]) -> list[str]:
        label = str(summary.get("label", "No Data"))
        transitions = [
            str(old_label)
            for old_label in [summary.get("label_1d_ago"), summary.get("label_1w_ago"), summary.get("label_1m_ago"), summary.get("label_3m_ago")]
            if old_label and old_label != label
        ]
        return [f"Recent regime history differs from current label: {', '.join(transitions)}"] if transitions else []

    def _vix_label(self, vix: float | None) -> str:
        if vix is None:
            return "no_data"
        if vix < self.config.vix_low_level:
            return "low_volatility"
        if vix < self.config.vix_neutral_level:
            return "normal_volatility"
        if vix < self.config.vix_elevated_level:
            return "elevated_volatility"
        if vix < self.config.vix_stress_level:
            return "high_volatility"
        return "stress_volatility"

    def _safe_haven_label(self, safe_haven: float | None) -> str:
        if safe_haven is None:
            return "no_data"
        if safe_haven >= self.config.safe_haven_positive_threshold:
            return "risk_on"
        if safe_haven <= self.config.safe_haven_negative_threshold:
            return "risk_off"
        return "neutral"

    def _vix_term_label(self, ratio: float | None, inversion_flag: float | None) -> str:
        if ratio is None:
            return "no_data"
        if inversion_flag == 1.0 or ratio >= 1.0:
            return "inverted_term_structure"
        if ratio >= 0.95:
            return "flat_or_elevated_term_structure"
        return "normal_contango"

    def _credit_proxy_label(
        self,
        hyg_lqd_1m: float | None,
        hyg_ief_1m: float | None,
        risk_off_flag: float | None,
    ) -> str:
        values = [value for value in [hyg_lqd_1m, hyg_ief_1m] if value is not None]
        if not values:
            return "no_data"
        if risk_off_flag == 1.0 or all(value < 0.0 for value in values):
            return "credit_risk_off"
        if all(value > 0.0 for value in values):
            return "credit_risk_on"
        return "mixed_credit"

    def _index_state_symbols(self, index_state: dict[str, object]) -> list[str]:
        symbols: list[str] = []
        for key in index_state:
            text = str(key)
            if " " not in text:
                continue
            symbol = text.split(" ", 1)[0].strip()
            if symbol and symbol not in symbols:
                symbols.append(symbol)
        preferred = [symbol for symbol in ["SPY", "QQQ"] if symbol in symbols]
        return preferred + [symbol for symbol in symbols if symbol not in preferred]

    def _index_state_status(self, index_state: dict[str, object], symbol: str) -> str:
        ftd_flag = _optional_float(index_state.get(f"{symbol} FTD FLAG"))
        pressure_flag = _optional_float(index_state.get(f"{symbol} UNDER PRESSURE FLAG"))
        rally_day = _optional_float(index_state.get(f"{symbol} RALLY ATTEMPT DAY"))
        if ftd_flag == 1.0 and pressure_flag == 1.0:
            return "confirmed_under_pressure"
        if ftd_flag == 1.0:
            return "confirmed_rally"
        if rally_day is not None and rally_day > 0.0:
            return "rally_attempt"
        if rally_day is not None:
            return "no_active_attempt"
        return "no_data"

    def _overweight_sectors(self, rows: list[dict[str, object]]) -> list[str]:
        candidates = []
        for row in rows:
            rel_1w = _optional_float(row.get("REL 1W %"))
            rel_1m = _optional_float(row.get("REL 1M %"))
            rank = _optional_float(row.get("RANK 1M"))
            if rel_1w is not None and rel_1m is not None and rank is not None and rel_1w > 0 and rel_1m > 1.0 and rank <= 3:
                candidates.append(_ticker_name(row))
        return candidates[:3]

    def _avoid_sectors(self, rows: list[dict[str, object]]) -> list[str]:
        candidates = []
        for row in rows:
            rel_1m = _optional_float(row.get("REL 1M %"))
            rel_3m = _optional_float(row.get("REL 3M %"))
            if rel_1m is not None and rel_3m is not None and rel_1m < -1.0 and rel_3m < 0:
                candidates.append(_ticker_name(row))
        return candidates[:3]

    def _exit_watch_sectors(self, rows: list[dict[str, object]]) -> list[str]:
        candidates = []
        for row in rows:
            rel_1w = _optional_float(row.get("REL 1W %"))
            rel_1m = _optional_float(row.get("REL 1M %"))
            rank_delta = _optional_float(row.get("RANK DELTA 1W"))
            if rel_1w is not None and rel_1m is not None and rel_1m > 1.0 and rel_1w < 0:
                candidates.append(_ticker_name(row))
                continue
            if rank_delta is not None and rank_delta <= -3:
                candidates.append(_ticker_name(row))
        return list(dict.fromkeys(candidates))[:3]

    def _style_tilts(self, rows: list[dict[str, object]]) -> list[str]:
        tilts = []
        for row in rows:
            rel_1w = _optional_float(row.get("REL 1W %"))
            rel_1m = _optional_float(row.get("REL 1M %"))
            above_ma = _optional_float(row.get("ABOVE MA COUNT"))
            ma_count = _optional_float(row.get("MA COUNT"))
            if rel_1w is None or rel_1m is None:
                continue
            name = str(row.get("NAME", row.get("PAIR", "")))
            if rel_1w > 0 and rel_1m > 0 and (not ma_count or above_ma == ma_count):
                tilts.append(f"{name} 優位")
            elif rel_1w < 0 and rel_1m < 0:
                tilts.append(f"{name} 劣後")
        return tilts[:4]

    def _market_action_mode(self, summary: dict[str, object], section_map: dict[str, MarketReportSection]) -> dict[str, str]:
        score = _optional_float(summary.get("score"))
        label = str(summary.get("label", "")).lower()
        breadth_label = section_map.get("breadth_participation").label if section_map.get("breadth_participation") else "no_data"
        risk_label = section_map.get("risk_on_ratio").label if section_map.get("risk_on_ratio") else "no_data"
        sector_label = section_map.get("sector_rotation").label if section_map.get("sector_rotation") else "no_data"
        industry_label = section_map.get("industry_leadership").label if section_map.get("industry_leadership") else "no_data"
        vix_label = self._vix_label(_optional_float(summary.get("vix_close")))
        breadth = _mapping(summary.get("breadth_summary"))
        sma20 = _optional_float(breadth.get("pct_above_sma20"))
        sma50 = _optional_float(breadth.get("pct_above_sma50"))
        s2w_high = _optional_float(_mapping(summary.get("high_vix_summary")).get("S2W HIGH %"))
        vix_stressed = vix_label in {"high_volatility", "stress_volatility"}
        breadth_weak = breadth_label == "weak"
        risk_off = risk_label == "risk_off_warning"

        if (score is not None and score < self.config.neutral_score_floor) or (breadth_weak and risk_off) or vix_stressed:
            return {
                "key": "defense",
                "label": "防御",
                "reason": "Market score, breadth, Risk-On Ratio, or VIX indicates defensive candidate review.",
            }

        if (
            score is not None
            and score >= self.config.positive_score_floor
            and breadth_label != "strong"
            and (sma20 is not None and sma20 < self.config.breadth_strong_level)
            and (sma50 is not None and sma50 < self.config.breadth_strong_level)
        ):
            return {
                "key": "overheat_watch",
                "label": "過熱警戒",
                "reason": "Headline score is positive while breadth confirmation is not broad enough.",
            }

        positive_or_bullish = "positive" in label or "bullish" in label
        if (
            score is not None
            and score >= self.config.positive_score_floor
            and positive_or_bullish
            and breadth_label == "strong"
            and risk_label == "risk_on"
            and industry_label == "confirmed_industry_leadership"
        ):
            return {
                "key": "attack",
                "label": "攻める",
                "reason": "Trend, breadth, Risk-On Ratio, and industry leadership are aligned.",
            }

        if sector_label == "constructive" and industry_label == "confirmed_industry_leadership" and breadth_label in {"mixed", "strong"}:
            return {
                "key": "sector_rotation",
                "label": "セクター乗り換え",
                "reason": "Sector rotation and industry leadership are confirmed, so candidate review should start with leadership groups.",
            }

        if (
            (score is not None and score >= self.config.neutral_score_floor)
            and (breadth_label in {"mixed", "strong"} or industry_label == "confirmed_industry_leadership")
            and not risk_off
            and not vix_stressed
        ):
            return {
                "key": "selective_attack",
                "label": "厳選して攻める",
                "reason": "Some confirmation exists, but not enough for broad risk taking.",
            }

        if s2w_high is not None and s2w_high < self.config.s2w_high_weak_level:
            return {
                "key": "wait",
                "label": "様子見",
                "reason": "Short-term high participation is limited, so wait for clearer confirmation.",
            }
        return {
            "key": "wait",
            "label": "様子見",
            "reason": "Signals are mixed or insufficient for aggressive candidate review.",
        }

    def _swing_market_posture(
        self,
        action_mode: dict[str, str],
        summary: dict[str, object],
        section_map: dict[str, MarketReportSection],
    ) -> dict[str, object]:
        key = action_mode.get("key", "wait")
        score = _optional_float(summary.get("score"))
        label = str(summary.get("label", "No Data"))
        breadth = section_map.get("breadth_participation")
        risk = section_map.get("risk_on_ratio")
        volatility = section_map.get("volatility_safe_haven")
        industry = section_map.get("industry_leadership")
        sector = section_map.get("sector_rotation")
        base_facts = [
            f"Market Score={_format_number(score)} ({label})",
            f"Breadth={breadth.label if breadth else 'unavailable'}",
            f"Risk-On Ratio={risk.label if risk else 'unavailable'}",
            f"Volatility/Safe Haven={volatility.label if volatility else 'unavailable'}",
        ]
        if industry:
            base_facts.append(f"Industry leadership={industry.label}")
        if sector:
            base_facts.append(f"Sector rotation={sector.label}")

        posture_map: dict[str, dict[str, tuple[str, str, str]]] = {
            "attack": {
                "long_exposure": ("ロング許容", "ロング候補を通常通り確認しやすい市場認識です。", "Trend, Breadth, Risk-On Ratio, and leadership are aligned."),
                "new_entry": ("通常確認", "新規候補は通常のスクリーニング順で確認できます。", "Market score and leadership confirmation are constructive."),
                "profit_taking_watch": ("通常", "利確・警戒候補は通常の確認優先度で扱います。", "No broad overheat or defensive warning is dominant."),
                "risk_management": ("通常", "リスク管理ルールは通常運用とし、緩める必要はありません。", "Market context does not require defensive tightening."),
                "entry_signal": ("通常評価", "EntrySignal は市場逆風による割引を強めずに確認できます。", "Market context supports normal signal interpretation."),
            },
            "selective_attack": {
                "long_exposure": ("選別保有", "ロング候補は許容しつつ、強い業種・強い形状を優先する市場認識です。", "Some confirmation exists, but broad confirmation is incomplete."),
                "new_entry": ("厳選", "新規候補は Breadth、Risk-On Ratio、業種リーダーシップが一致するものに絞ります。", "Confirmation is partial rather than broad."),
                "profit_taking_watch": ("通常から警戒", "弱い業種や劣後スタイルは利確・警戒候補として優先確認します。", "Mixed confirmation raises selection risk."),
                "risk_management": ("やや厳格", "リスク管理ルールは緩めず、弱い候補を残しにくい前提で確認します。", "Selective environment requires tighter review standards."),
                "entry_signal": ("優先度差を付ける", "強い業種の EntrySignal を先に確認し、弱い業種の信号は割引して読みます。", "Leadership alignment matters in selective conditions."),
            },
            "sector_rotation": {
                "long_exposure": ("リーダー業種優先", "ロング候補はセクター・業種リーダーに寄せて確認する市場認識です。", "Sector rotation and industry leadership are confirmed."),
                "new_entry": ("セクター限定", "新規候補は資金流入が続くセクター・業種を優先します。", "Rotation quality is the main edge."),
                "profit_taking_watch": ("劣後確認", "順位低下セクターや弱い業種は利確・警戒候補として確認します。", "Rotation creates a stronger gap between leaders and laggards."),
                "risk_management": ("選別厳格", "リーダー外の候補はリスク管理ルールを緩めずに扱います。", "Non-leadership exposure has weaker confirmation."),
                "entry_signal": ("リーダー優先", "EntrySignal はリーダー業種内の候補を優先して解釈します。", "Industry leadership is the primary confirmation layer."),
            },
            "overheat_watch": {
                "long_exposure": ("選別保有", "ロング保有は許容しつつ、広がり不足に注意する市場認識です。", "Headline score is positive while breadth confirmation is not broad enough."),
                "new_entry": ("厳選", "新規候補は強い業種・強い出来高・明確な形状に限定して確認します。", "Breadth confirmation is not broad enough for loose screening."),
                "profit_taking_watch": ("優先確認", "伸び切った候補や弱い Breadth の候補は利確・警戒確認を優先します。", "Overheat risk increases when headline strength lacks breadth."),
                "risk_management": ("厳格", "リスク管理ルールは緩めず、遅れた候補を追いにくい前提で確認します。", "Late entries have weaker expectancy in overheat-watch conditions."),
                "entry_signal": ("追加確認要求", "EntrySignal は市場内部の確認不足を割り引いて読みます。", "Positive label conflicts with incomplete breadth confirmation."),
            },
            "wait": {
                "long_exposure": ("選別保有", "ロング候補は残せますが、積極的に広げるより改善確認を優先する市場認識です。", "Signals are mixed or short-term participation is limited."),
                "new_entry": ("控えめ", "新規候補は原則控えめにし、改善が確認できる候補だけを確認します。", "Market context is not strong enough for broad new-entry review."),
                "profit_taking_watch": ("警戒優先", "弱い候補や伸び切った候補は利確・警戒確認を優先します。", "Mixed conditions lower tolerance for weak candidates."),
                "risk_management": ("緩和禁止", "リスク管理ルールは緩めず、条件未達の候補を上げない前提で確認します。", "Wait mode requires discipline rather than looser criteria."),
                "entry_signal": ("厳しめ評価", "EntrySignal は通常より厳しめに読み、市場改善が伴うかを確認します。", "Signal quality needs market confirmation."),
            },
            "defense": {
                "long_exposure": ("防御寄り", "ロング候補は防御寄りに確認し、弱い候補を優先的に除外する市場認識です。", "Market score, breadth, Risk-On Ratio, or VIX indicates defensive review."),
                "new_entry": ("原則控えめ", "新規候補は原則控えめにし、明確な市場改善が出るまで確認優先度を下げます。", "Defensive conditions reduce broad long-only expectancy."),
                "profit_taking_watch": ("最優先確認", "利確・警戒候補の確認を新規候補より優先します。", "Defensive posture raises the importance of risk review."),
                "risk_management": ("厳格化", "リスク管理ルールは緩めず、弱い候補を残しにくい前提で確認します。", "Defensive context requires strict review standards."),
                "entry_signal": ("割引評価", "EntrySignal は市場逆風を強く割り引いて読みます。", "Signals need unusually strong confirmation under defensive conditions."),
            },
        }
        selected = posture_map.get(key, posture_map["wait"])
        return {
            "objective": "スイング投資における現在の市場認識",
            "mode_key": key,
            "mode_label": action_mode.get("label", "様子見"),
            "mode_reason": action_mode.get("reason", ""),
            "long_exposure_posture": _posture_item(*selected["long_exposure"]),
            "new_entry_posture": _posture_item(*selected["new_entry"]),
            "profit_taking_watch": _posture_item(*selected["profit_taking_watch"]),
            "risk_management_strictness": _posture_item(*selected["risk_management"]),
            "entry_signal_interpretation": _posture_item(*selected["entry_signal"]),
            "evidence_facts": base_facts,
            "boundary": "This is report-level market-context guidance only; it does not change EntrySignal, WatchList, scan logic, position sizing, execution, or exit management.",
        }

    def _confirmation_order(self, action_mode: dict[str, str], section_map: dict[str, MarketReportSection]) -> list[str]:
        order = []
        if section_map.get("industry_leadership") and section_map["industry_leadership"].label != "no_data":
            order.append("1. 業種リーダーシップ: 52W HIGH、accelerating、sustained leadership の業種を先に確認する。")
        if section_map.get("recommendation_inputs"):
            order.append("2. 優先候補グループ: High / Medium / Low-Watch の順に確認する。")
        if action_mode["key"] in {"selective_attack", "overheat_watch", "wait", "defense"}:
            order.append("3. Stage 2 Quality と Mature / Late Stage Risk Filter を通過する候補だけに絞る。")
        else:
            order.append("3. Stage 2 銘柄の中でブレイクアウトまたは初回押し目の候補を確認する。")
        order.append("4. Breadth、Risk-On Ratio、VIX の順に市場側の逆風がないか確認する。")
        if action_mode["key"] in {"defense", "wait"}:
            order.append("5. 新規候補より watchpoint_candidates の改善確認を優先する。")
        return order[:5]

    def _priority_candidate_groups(
        self,
        industry_rows: list[dict[str, object]],
        priority_sectors: list[str],
        avoid_sectors: list[str],
        exit_watch_sectors: list[str],
        style_tilts: list[str],
    ) -> dict[str, list[str]]:
        new_high = [row for row in industry_rows if _is_52w_high(row.get("52W HIGH"))]
        sustained = [row for row in industry_rows if _is_sustained_industry(row)]
        accelerating = [row for row in industry_rows if _is_accelerating_industry(row)]
        weak = _weak_industries(industry_rows)
        high = [_industry_descriptor(row) for row in _unique_records([*new_high, *sustained, *accelerating])[:5]]
        medium_rows = [row for row in industry_rows[:8] if _industry_descriptor(row) not in high and _industry_state(row) != "weak"]
        medium = [_industry_descriptor(row) for row in medium_rows[:5]]
        medium.extend(f"priority_sector={name}" for name in priority_sectors)
        medium.extend(f"style_tilt={name}" for name in style_tilts[:2])
        low_watch = [_industry_descriptor(row) for row in weak[:5]]
        low_watch.extend(f"lower_priority_sector={name}" for name in avoid_sectors)
        low_watch.extend(f"profit_taking_exit_watch={name}" for name in exit_watch_sectors)
        return {
            "high": list(dict.fromkeys(high))[:5],
            "medium": list(dict.fromkeys(medium))[:5],
            "low_watch": list(dict.fromkeys(low_watch))[:6],
        }

    def _metric_evidence(self, summary: dict[str, object], metric: str, source_field: str, *, raw: bool = False, score: bool = False, note: str | None = None) -> MarketReportMetric:
        value = _get_path(summary, source_field)
        metric_key = source_field.rsplit(".", 1)[-1]
        return MarketReportMetric(
            metric=metric,
            source_field=source_field,
            value=value if isinstance(value, str) else _optional_float(value),
            raw_value=_optional_float(value) if raw else None,
            score_value=_optional_float(value) if score else None,
            delta_1d=_metric_delta(summary, metric_key, "1D"),
            delta_1w=_metric_delta(summary, metric_key, "1W"),
            delta_1m=_metric_delta(summary, metric_key, "1M"),
            note=note,
        )

    def _evidence(
        self,
        metric: str,
        source_field: str,
        value: object,
        *,
        raw_value: float | None = None,
        score_value: float | None = None,
        delta_1d: float | None = None,
        delta_1w: float | None = None,
        delta_1m: float | None = None,
        note: str | None = None,
    ) -> MarketReportMetric:
        return MarketReportMetric(
            metric=metric,
            source_field=source_field,
            value=value if isinstance(value, str) else _optional_float(value),
            raw_value=raw_value,
            score_value=score_value,
            delta_1d=delta_1d,
            delta_1w=delta_1w,
            delta_1m=delta_1m,
            note=note,
        )


class MarketReportMarkdownRenderer:
    """Render an AI-input market document, not the final human-facing report."""

    def render(self, report: MarketReportResult) -> str:
        lines = [
            "# AI入力用マーケットドキュメント",
            "",
            f"- schema_version: `{report.schema_version}`",
            f"- document_type: `{report.document_type}`",
            f"- 対象日: {report.trade_date or '不明'}",
            f"- 生成時刻: {report.generated_at}",
            f"- 総合: {report.executive_context.get('one_line_diagnosis', '')}",
            f"- 行動モード: {report.executive_context.get('market_action_mode', '不明')}",
            "",
            "## executive_context",
            "",
        ]
        if report.executive_context.get("market_action_mode_reason"):
            lines.append(f"- market_action_mode_reason: {report.executive_context.get('market_action_mode_reason')}")
        swing_posture = _mapping(report.executive_context.get("swing_market_posture"))
        if swing_posture:
            lines.append("- swing_market_posture:")
            lines.append(f"  - objective: {swing_posture.get('objective', '')}")
            lines.append(f"  - mode: {swing_posture.get('mode_label', '')} ({swing_posture.get('mode_key', '')})")
            for key, label in (
                ("long_exposure_posture", "long_exposure"),
                ("new_entry_posture", "new_entry"),
                ("profit_taking_watch", "profit_taking_watch"),
                ("risk_management_strictness", "risk_management"),
                ("entry_signal_interpretation", "entry_signal"),
            ):
                item = _mapping(swing_posture.get(key))
                if item:
                    lines.append(f"  - {label}: {item.get('label', '')}; guidance={item.get('guidance', '')}; reason={item.get('reason', '')}")
            evidence = _as_list(swing_posture.get("evidence_facts"))
            if evidence:
                lines.append("  - evidence_facts:")
                lines.extend(f"    - {fact}" for fact in evidence)
            if swing_posture.get("boundary"):
                lines.append(f"  - boundary: {swing_posture.get('boundary')}")
        confirmation_order = _as_list(report.executive_context.get("confirmation_order"))
        if confirmation_order:
            lines.append("- confirmation_order:")
            lines.extend(f"  - {item}" for item in confirmation_order)
        for fact in _as_list(report.executive_context.get("action_context_facts")):
            lines.append(f"- {fact}")
        if report.executive_context.get("notable_changes"):
            lines.append("- notable_changes: " + " / ".join(str(item) for item in _as_list(report.executive_context.get("notable_changes"))))
        lines.append("")
        lines.extend(self._boundary_lines(report.analysis_boundary))
        lines.extend(self._watchpoint_lines(report.watchpoint_candidates))
        lines.extend(self._transition_lines(report.recent_transitions))
        lines.append("## sections")
        lines.append("")
        for section in report.sections:
            lines.extend(self._section_lines(section))
        lines.extend(self._missing_input_lines(report.missing_inputs))
        lines.extend(self._contract_lines(report.report_generation_contract))
        return "\n".join(lines).rstrip() + "\n"

    def _boundary_lines(self, boundary: dict[str, object]) -> list[str]:
        lines = ["## analysis_boundary", ""]
        lines.append("- allowed_sources: " + " / ".join(str(item) for item in _as_list(boundary.get("allowed_sources"))))
        lines.append("- prohibited_sources: " + " / ".join(str(item) for item in _as_list(boundary.get("prohibited_sources"))))
        lines.append(f"- sector_inference_limit: {boundary.get('sector_inference_limit', '')}")
        lines.append("")
        return lines

    def _watchpoint_lines(self, watchpoints: list[MarketReportWatchpoint]) -> list[str]:
        lines = ["## watchpoint_candidates", ""]
        if not watchpoints:
            lines.extend(["- none", ""])
            return lines
        for item in watchpoints:
            lines.append(f"- `{item.metric}` {item.direction} {item.threshold}: {item.narrative} ({item.reason})")
        lines.append("")
        return lines

    def _transition_lines(self, transitions: list[MarketReportTransition]) -> list[str]:
        lines = ["## recent_transitions", ""]
        if not transitions:
            lines.extend(["- none", ""])
            return lines
        for item in transitions:
            lines.append(f"- [{item.significance}] {item.category}: {item.event}")
        lines.append("")
        return lines

    def _section_lines(self, section: MarketReportSection) -> list[str]:
        lines = [
            f"### {section.key}: {section.title}",
            "",
            f"- label: `{section.label}`",
            f"- direction: `{section.direction or 'none'}`",
            f"- significance: `{section.significance.level}` ({section.significance.reason})",
            f"- summary_for_skill: {section.summary}",
        ]
        if section.trajectory:
            lines.append(
                f"- trajectory: `{section.trajectory.pattern}`, streak={section.trajectory.streak}, "
                f"delta_1d={_format_number(section.trajectory.delta_1d)}, "
                f"delta_1w={_format_number(section.trajectory.delta_1w)}, "
                f"delta_1m={_format_number(section.trajectory.delta_1m)}"
            )
        if section.facts_for_ai:
            lines.append("- facts_for_ai:")
            lines.extend(f"  - {fact}" for fact in section.facts_for_ai)
        if section.warnings:
            lines.append("- warnings:")
            lines.extend(f"  - {warning}" for warning in section.warnings)
        if section.metrics:
            lines.append("- evidence_metrics:")
            for metric in section.metrics[:12]:
                lines.append(f"  - {self._metric_line(metric)}")
        lines.append("")
        return lines

    def _metric_line(self, metric: MarketReportMetric) -> str:
        parts = [f"{metric.metric}", f"source={metric.source_field}", f"value={_format_value(metric.value)}"]
        if metric.raw_value is not None:
            parts.append(f"raw={_format_number(metric.raw_value)}")
        if metric.score_value is not None:
            parts.append(f"score={_format_number(metric.score_value)}")
        if metric.delta_1d is not None:
            parts.append(f"delta_1d={_format_signed(metric.delta_1d)}")
        if metric.delta_1w is not None:
            parts.append(f"delta_1w={_format_signed(metric.delta_1w)}")
        if metric.delta_1m is not None:
            parts.append(f"delta_1m={_format_signed(metric.delta_1m)}")
        if metric.note:
            parts.append(f"note={metric.note}")
        return "; ".join(parts)

    def _missing_input_lines(self, missing_inputs: list[MarketReportMissingInput]) -> list[str]:
        lines = ["## missing_inputs", ""]
        if not missing_inputs:
            lines.extend(["- none", ""])
            return lines
        for item in missing_inputs:
            lines.append(f"- {item.key} ({item.phase}): {item.reason}")
        lines.append("")
        return lines

    def _contract_lines(self, contract: dict[str, object]) -> list[str]:
        lines = ["## report_generation_contract", ""]
        lines.append(f"- final_report_owner: {contract.get('final_report_owner')}")
        lines.append(f"- system_output_role: {contract.get('system_output_role')}")
        lines.append("- must_not_do:")
        lines.extend(f"  - {item}" for item in _as_list(contract.get("must_not_do")))
        lines.append(f"- token_efficiency_rule: {contract.get('token_efficiency_rule')}")
        lines.append("")
        return lines


def _posture_item(label: str, guidance: str, reason: str) -> dict[str, str]:
    return {
        "label": label,
        "guidance": guidance,
        "reason": reason,
    }


def _mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _records(value: object) -> list[dict[str, object]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _sort_records(records: list[dict[str, object]], key: str, *, reverse: bool = False) -> list[dict[str, object]]:
    return sorted(records, key=lambda item: _optional_float(item.get(key)) if _optional_float(item.get(key)) is not None else float("-inf"), reverse=reverse)


def _unique_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    unique: list[dict[str, object]] = []
    for record in records:
        key = str(record.get("TICKER", "")).strip() or str(id(record))
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _date_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text[:10] if text else None


def _get_path(summary: dict[str, object], source_field: str) -> object:
    current: object = summary
    for part in source_field.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _score_delta(summary: dict[str, object], previous_key: str) -> float | None:
    score = _optional_float(summary.get("score"))
    previous = _optional_float(summary.get(previous_key))
    if score is None or previous is None:
        return None
    return round(score - previous, 3)


def _metric_delta(summary: dict[str, object], metric_key: str, period: str) -> float | None:
    deltas = _mapping(_mapping(summary.get("metric_deltas")).get(metric_key))
    return _optional_float(deltas.get(period))


def _delta_direction(values: list[float | None]) -> str:
    valid = [value for value in values if value is not None]
    if not valid:
        return "unknown"
    positive = sum(1 for value in valid if value > 0)
    negative = sum(1 for value in valid if value < 0)
    if positive > negative:
        return "improving"
    if negative > positive:
        return "deteriorating"
    return "stable"


def _trajectory_pattern(deltas: list[float]) -> str:
    if len(deltas) < 2:
        return "limited_history"
    positives = sum(1 for value in deltas if value > 0)
    negatives = sum(1 for value in deltas if value < 0)
    total = sum(deltas)
    if negatives >= max(2, len(deltas) - 1):
        return "sustained_decline"
    if positives >= max(2, len(deltas) - 1):
        return "sustained_improvement"
    if len(deltas) >= 3 and deltas[-1] > 0 and deltas[-2] > 0 and total < 0:
        return "reversal_attempt"
    if total < 0 and positives and negatives:
        return "volatile_decline"
    if total > 0 and positives and negatives:
        return "volatile_improvement"
    return "flat"


def _signed_streak(deltas: list[float]) -> int:
    if not deltas:
        return 0
    last_sign = 1 if deltas[-1] > 0 else -1 if deltas[-1] < 0 else 0
    if last_sign == 0:
        return 0
    count = 0
    for value in reversed(deltas):
        sign = 1 if value > 0 else -1 if value < 0 else 0
        if sign != last_sign:
            break
        count += 1
    return count * last_sign


def _trajectory_explanation(pattern: str, deltas: list[float]) -> str:
    if not deltas:
        return "No daily path is available."
    return f"{pattern}; path deltas={', '.join(_format_signed(value) for value in deltas)}"


def _abs_ge(value: float | None, threshold: float) -> bool:
    return value is not None and abs(value) >= threshold


def _negate_optional(value: float | None) -> float | None:
    return -value if value is not None else None


def _both_at_or_above(values: list[float | None], threshold: float) -> bool:
    valid = [value for value in values if value is not None]
    return bool(valid) and all(value >= threshold for value in valid)


def _any_below(values: list[float | None], threshold: float) -> bool:
    return any(value is not None and value < threshold for value in values)


def _position_counts(records: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        label = str(record.get("21EMA POS", "unknown"))
        counts[label] = counts.get(label, 0) + 1
    return counts


def _ticker_name(record: dict[str, object]) -> str:
    ticker = str(record.get("TICKER", "")).strip()
    name = str(record.get("NAME", ticker)).strip() or ticker
    return f"{ticker} {name}".strip()


def _industry_list(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "none"
    return ", ".join(_industry_descriptor(row) for row in rows)


def _join_group(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _industry_descriptor(row: dict[str, object]) -> str:
    return (
        f"{_ticker_name(row)} "
        f"(RS={_format_number(_optional_float(row.get('RS')))}, "
        f"1D={_format_number(_optional_float(row.get('1D')))}, "
        f"1W={_format_number(_optional_float(row.get('1W')))}, "
        f"1M={_format_number(_optional_float(row.get('1M')))}, "
        f"RS MTH%={_format_signed(_optional_float(row.get('RS MTH%')))}, "
        f"52W HIGH={_format_value(row.get('52W HIGH'))})"
    )


def _industry_metric(row: dict[str, object]) -> MarketReportMetric:
    state = _industry_state(row)
    note = (
        f"1D={_format_number(_optional_float(row.get('1D')))}, "
        f"1W={_format_number(_optional_float(row.get('1W')))}, "
        f"1M={_format_number(_optional_float(row.get('1M')))}, "
        f"52W HIGH={_format_value(row.get('52W HIGH'))}, "
        f"state={state}"
    )
    return MarketReportMetric(
        metric=str(row.get("TICKER", "")),
        source_field="industry_leaders",
        value=row.get("NAME"),
        raw_value=_optional_float(row.get("RS")),
        delta_1d=_optional_float(row.get("RS DAY%")),
        delta_1w=_optional_float(row.get("RS WK%")),
        delta_1m=_optional_float(row.get("RS MTH%")),
        note=note,
    )


def _is_52w_high(value: object) -> bool:
    return str(value).strip().lower() == "yes"


def _is_accelerating_industry(row: dict[str, object]) -> bool:
    one_day = _optional_float(row.get("1D"))
    one_week = _optional_float(row.get("1W"))
    one_month = _optional_float(row.get("1M"))
    rs_day = _optional_float(row.get("RS DAY%"))
    rs_week = _optional_float(row.get("RS WK%"))
    if None in {one_day, one_week, one_month, rs_day, rs_week}:
        return False
    return bool(one_day >= one_week >= one_month and one_day >= 70 and rs_day > 0 and rs_week > 0)


def _is_sustained_industry(row: dict[str, object]) -> bool:
    values = [_optional_float(row.get(key)) for key in ["1D", "1W", "1M"]]
    rs_month = _optional_float(row.get("RS MTH%"))
    return all(value is not None and value >= 80 for value in values) and rs_month is not None and rs_month > 0


def _weak_industries(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    weak = []
    for row in rows:
        rs = _optional_float(row.get("RS"))
        one_month = _optional_float(row.get("1M"))
        rs_month = _optional_float(row.get("RS MTH%"))
        if (rs is not None and rs <= 35) or (one_month is not None and one_month <= 35) or (rs_month is not None and rs_month <= -5):
            weak.append(row)
    return _sort_records(weak, "RS")


def _industry_state(row: dict[str, object]) -> str:
    if _is_accelerating_industry(row):
        return "accelerating"
    if _is_sustained_industry(row):
        return "sustained_leadership"
    rs = _optional_float(row.get("RS"))
    one_month = _optional_float(row.get("1M"))
    rs_month = _optional_float(row.get("RS MTH%"))
    if (rs is not None and rs <= 35) or (one_month is not None and one_month <= 35) or (rs_month is not None and rs_month <= -5):
        return "weak"
    one_day = _optional_float(row.get("1D"))
    if one_day is not None and one_month is not None and one_day >= 75 and one_month < 60:
        return "rebound_watch"
    return "mixed"


def _factor_classification(rel_1w: float | None, rel_1m: float | None) -> str:
    if rel_1w is None or rel_1m is None:
        return "unknown"
    if rel_1w > 0 and rel_1m > 0:
        return "accelerating"
    if rel_1w > 0 and rel_1m <= 0:
        return "rebound_watch"
    if rel_1w <= 0 and rel_1m > 0:
        return "decelerating"
    return "lagging"


def _format_number(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _format_signed(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.2f}".rstrip("0").rstrip(".")


def _format_value(value: object) -> str:
    if isinstance(value, float):
        return _format_number(value)
    if value is None:
        return "N/A"
    return str(value)


# Backward-compatible aliases for old test/import vocabulary.
MarketReportEvidence = MarketReportMetric
MarketDocumentResult = MarketReportResult
MarketDocumentBuilder = MarketReportBuilder
MarketDocumentMarkdownRenderer = MarketReportMarkdownRenderer
