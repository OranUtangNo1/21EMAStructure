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
            self._sector_rotation(summary, history),
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
        defensive_cyclical = _mapping(summary.get("defensive_cyclical_summary"))
        overweight = self._overweight_sectors(sector_rows)
        avoid = self._avoid_sectors(sector_rows)
        exit_watch = self._exit_watch_sectors(sector_rows)
        style_tilts = self._style_tilts(style_rows)
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
        safe_haven = _optional_float(_mapping(summary.get("high_vix_summary")).get("SAFE HAVEN %"))
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
                self._metric_evidence(summary, "Safe Haven Spread", "high_vix_summary.SAFE HAVEN %", raw=True),
                self._metric_evidence(summary, "VIX Score", "component_scores.vix_score", score=True),
                self._metric_evidence(summary, "Safe Haven Score", "component_scores.safe_haven_score", score=True),
            ],
            facts_for_ai=[
                f"VIX={_format_number(vix)}",
                f"VIX label={vix_label}",
                f"Safe Haven={_format_number(safe_haven)}",
                f"Safe Haven label={safe_haven_label}",
            ],
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
        required_missing = [item.key for item in missing_inputs if item.phase == "v0"]
        confidence = "Low" if required_missing else ("Medium" if transitions else "High")
        action_context = [
            f"Market Score { _format_number(score) } is {label} and direction is {direction}.",
            f"Risk-On Ratio posture is {risk.label if risk else 'unavailable'}.",
            f"Breadth posture is {breadth.label if breadth else 'unavailable'}.",
        ]
        if recommendation and recommendation.facts_for_ai:
            action_context.append("Priority inputs: " + " / ".join(recommendation.facts_for_ai[:3]))
        return {
            "market_label": label,
            "market_score": score,
            "market_direction": direction,
            "confidence": confidence,
            "one_line_diagnosis": f"Market Score {_format_number(score)} ({label}, {direction})",
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
            "sector_inference_limit": "セクターの含意は 21EMA POS、DAY%、relative strength、basket comparison の範囲に限定する。上昇/下落の外部理由は書かない。",
        }

    def _report_generation_contract(self) -> dict[str, object]:
        return {
            "final_report_owner": "skill",
            "system_output_role": "AIが品質を満たす日次マーケットレポートを書くための根拠付き入力を生成する。",
            "must_not_do": [
                "外部イベントやニュースを補完しない",
                "個別銘柄の売買実行指示を書かない",
                "ポジションサイズや損切り管理を書かない",
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
            "credit_proxy": "Useful but not implemented.",
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
            "",
            "## executive_context",
            "",
        ]
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


def _mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _records(value: object) -> list[dict[str, object]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


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
