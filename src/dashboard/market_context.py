from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

import pandas as pd


SCHEMA_VERSION = "v1.0.1"
SECTOR_TICKERS = frozenset({"XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"})


@dataclass(frozen=True, slots=True)
class MarketContextConfig:
    output_dir: str = "data_runs/service_outputs/market_context"
    write_markdown: bool = False
    write_json: bool = True
    output_mode: str = "daily_history"
    industry_top_n: int = 8
    industry_major_stocks: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "MarketContextConfig":
        data = payload or {}
        output = data.get("output", {})
        output_map = output if isinstance(output, dict) else {}
        return cls(
            output_dir=str(output_map.get("dir", data.get("output_dir", "data_runs/service_outputs/market_context"))),
            write_markdown=bool(output_map.get("write_markdown", data.get("write_markdown", False))),
            write_json=bool(output_map.get("write_json", data.get("write_json", True))),
            output_mode=cls._output_mode(output_map.get("mode", data.get("output_mode")), "daily_history"),
            industry_top_n=max(1, int(data.get("industry_top_n", 8))),
            industry_major_stocks=cls._major_map(data.get("industry_major_stocks")),
        )

    @staticmethod
    def _output_mode(value: object, default: str) -> str:
        mode = str(value or default).strip().lower()
        return mode if mode in {"daily_history", "latest_only", "on_demand", "disabled"} else default

    @staticmethod
    def _major_map(payload: object) -> dict[str, str]:
        if not isinstance(payload, dict):
            return {}
        result: dict[str, str] = {}
        for ticker, value in payload.items():
            key = str(ticker).strip().upper()
            if not key:
                continue
            if isinstance(value, (list, tuple)):
                text = ",".join(str(item).strip().upper() for item in value if str(item).strip())
            else:
                text = str(value).strip()
            if text:
                result[key] = text
        return result


@dataclass(frozen=True, slots=True)
class MarketContextResult:
    trade_date: str
    weekday: str
    schema_version: str
    sections: dict[str, list[str]] = field(default_factory=dict)
    structured_sections: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "document_type": "market_context",
            "schema_version": self.schema_version,
            "trade_date": self.trade_date,
            "weekday": self.weekday,
            "sections": self.sections,
            "structured_sections": self.structured_sections,
        }


class MarketContextBuilder:
    """Build fixed-schema market_context from saved market and radar summaries."""

    def __init__(self, config: MarketContextConfig | None = None) -> None:
        self.config = config or MarketContextConfig()

    def build(self, summary: dict[str, object], history_summaries: list[dict[str, object]] | None = None) -> MarketContextResult:
        history = history_summaries or []
        trade_date = self._trade_date(summary)
        previous = self._previous_summary(summary, history)
        sections = {
            "M_GATE": self._m_gate(summary, history),
            "INDEX": self._index(summary),
            "BREADTH": self._breadth(summary, previous),
            "SENTIMENT": self._sentiment(summary),
            "STYLE": self._style(summary),
            "SECTOR_RS": self._sector_rs(summary),
            "INDUSTRY_RS": self._industry_rs(summary, previous),
            "CHANGES_1W": self._changes_1w(summary, previous),
        }
        return MarketContextResult(
            trade_date=trade_date,
            weekday=pd.Timestamp(trade_date).strftime("%a") if trade_date != "NA" else "NA",
            schema_version=SCHEMA_VERSION,
            sections=sections,
            structured_sections=self._structured_sections(summary, previous, history, sections),
        )

    def _structured_sections(
        self,
        summary: dict[str, object],
        previous: dict[str, object] | None,
        history: list[dict[str, object]],
        sections: dict[str, list[str]],
    ) -> dict[str, object]:
        index_context = self._map(summary.get("index_context_summary"))
        index_state = self._map(summary.get("index_state_summary"))
        component_scores = self._map(summary.get("component_scores"))
        timeline = self._timeline(summary, history)
        metric_deltas = self._metric_deltas_from_timeline(timeline, self._map(summary.get("metric_deltas")))
        distribution_pressure = self._distribution_pressure(summary, timeline)
        payload = {
            "m_gate": {
                "verdict": self._verdict_from_lines(sections.get("M_GATE", [])),
                "market_score": self._json_number(summary.get("score")),
                "market_label": self._text(summary.get("label")),
                "market_score_history": self._market_score_history(timeline),
                "market_label_history": self._market_label_history(timeline),
                "component_scores": self._json_map(component_scores),
                "component_groups": self._component_groups(component_scores, summary),
                "distribution_pressure": distribution_pressure,
                "source_fields": [
                    "score",
                    "label",
                    "history_summaries.score",
                    "history_summaries.label",
                    "component_scores",
                ],
            },
            "deltas": {
                "metric_deltas": self._json_map(metric_deltas),
                "reference_audit": {"source": "history_summaries", "status": "PASS"},
                "source_fields": ["history_summaries", "metric_deltas(keys)"],
            },
            "regime": {
                "index_state": {
                    "SPY": self._index_state_for_symbol("SPY", index_context, index_state),
                    "QQQ": self._index_state_for_symbol("QQQ", index_context, index_state),
                },
                "transitions": self._detect_transitions(summary, history),
                "source_fields": ["score", "index_context_summary", "index_state_summary", "breadth_*", "volatility_term_structure", "credit_risk_proxy", "risk_on_ratio_summary", "industry_leaders", "style_pair_summary"],
            },
            "market_inputs": {
                "breadth_summary": self._json_map(self._map(summary.get("breadth_summary"))),
                "breadth_momentum_summary": self._json_map(self._map(summary.get("breadth_momentum_summary"))),
                "breadth_internal_summary": self._json_map(self._map(summary.get("breadth_internal_summary"))),
                "volatility_term_structure": self._json_map(self._map(summary.get("volatility_term_structure"))),
                "credit_risk_proxy": self._json_map(self._map(summary.get("credit_risk_proxy"))),
                "risk_on_ratio_summary": self._json_map(self._map(summary.get("risk_on_ratio_summary"))),
            },
            "leadership": {
                "sector_leaders": self._records(summary.get("sector_leaders")),
                "sector_relative_strength": self._records(summary.get("sector_relative_strength")),
                "industry_leaders": self._records(summary.get("industry_leaders")),
                "previous_trade_date": self._trade_date(previous) if previous else None,
            },
        }
        self._assert_reference_consistency(payload, timeline)
        return payload

    def _market_score_history(self, timeline: list[dict[str, object]]) -> dict[str, float | None]:
        return {
            "1d": self._score_at_timeline_offset(timeline, 1),
            "1w": self._score_at_timeline_offset(timeline, 5),
            "1m": self._score_at_timeline_offset(timeline, 21),
            "3m": self._score_at_timeline_offset(timeline, 63),
        }

    def _score_at_timeline_offset(self, timeline: list[dict[str, object]], offset: int) -> float | None:
        if len(timeline) <= offset:
            return None
        return self._json_number(timeline[-1 - offset].get("score"))

    def _market_label_history(self, timeline: list[dict[str, object]]) -> dict[str, str | None]:
        return {
            "1d": self._label_at_timeline_offset(timeline, 1),
            "1w": self._label_at_timeline_offset(timeline, 5),
            "1m": self._label_at_timeline_offset(timeline, 21),
            "3m": self._label_at_timeline_offset(timeline, 63),
        }

    def _label_at_timeline_offset(self, timeline: list[dict[str, object]], offset: int) -> str | None:
        if len(timeline) <= offset:
            return None
        label = self._text(timeline[-1 - offset].get("label"))
        return None if label == "NA" else label

    def _metric_deltas_from_timeline(
        self,
        timeline: list[dict[str, object]],
        source_metric_deltas: dict[str, object],
    ) -> dict[str, dict[str, float]]:
        if not timeline:
            return {}
        offsets = {"1D": 1, "1W": 5, "2W": 10, "1M": 21}
        keys = list(source_metric_deltas.keys())
        output: dict[str, dict[str, float]] = {}
        current = timeline[-1]
        for key in keys:
            current_value = self._metric_current_value(current, str(key))
            if not self._is_num(current_value):
                continue
            for label, offset in offsets.items():
                if len(timeline) <= offset:
                    continue
                previous_value = self._metric_current_value(timeline[-1 - offset], str(key))
                if not self._is_num(previous_value):
                    continue
                output.setdefault(str(key), {})[label] = round(float(current_value) - float(previous_value), 3)
        return output

    def _metric_current_value(self, summary: dict[str, object], key: str) -> object | None:
        direct_sources = (
            "breadth_summary",
            "participation_summary",
            "breadth_momentum_summary",
            "breadth_internal_summary",
            "high_vix_summary",
            "component_scores",
        )
        for source in direct_sources:
            values = self._map(summary.get(source))
            if key in values:
                return values.get(key)
        if key == "VIX":
            high_vix = self._map(summary.get("high_vix_summary"))
            return high_vix.get("VIX", summary.get("vix_close"))
        prefixed_sources = {
            "risk_on:": "risk_on_ratio_summary",
            "vix_term:": "volatility_term_structure",
            "credit:": "credit_risk_proxy",
        }
        for prefix, source in prefixed_sources.items():
            if key.startswith(prefix):
                return self._map(summary.get(source)).get(key.removeprefix(prefix))
        return None

    def _assert_reference_consistency(self, payload: dict[str, object], timeline: list[dict[str, object]]) -> None:
        m_gate = self._map(payload.get("m_gate"))
        assert m_gate.get("market_score_history") == self._market_score_history(timeline)
        assert m_gate.get("market_label_history") == self._market_label_history(timeline)
        deltas = self._map(payload.get("deltas"))
        expected = self._json_map(self._metric_deltas_from_timeline(timeline, self._map(timeline[-1].get("metric_deltas")) if timeline else {}))
        assert deltas.get("metric_deltas") == expected

    def _verdict_from_lines(self, lines: list[str]) -> str:
        for line in lines:
            if line.startswith("VERDICT:"):
                return line.split(":", 1)[1].strip()
        return "NA"

    def _component_groups(self, components: dict[str, object], summary: dict[str, object]) -> dict[str, object]:
        groups: dict[str, dict[str, object]] = {"trend": {}, "breadth": {}, "volatility": {}, "credit": {}, "lead": {}}
        for key, value in components.items():
            lowered = str(key).lower()
            if "vix" in lowered or "vol" in lowered:
                groups["volatility"][key] = value
            elif "credit" in lowered or "oas" in lowered or "hyg" in lowered or "lqd" in lowered:
                groups["credit"][key] = value
            elif "leader" in lowered or "lead" in lowered or "rs" in lowered or "safe_haven" in lowered or "risk" in lowered:
                groups["lead"][key] = value
            elif "breadth" in lowered or "pct_above" in lowered or "pct_positive" in lowered or "pct_2w" in lowered:
                groups["breadth"][key] = value
            elif "sma" in lowered or "trend" in lowered:
                groups["trend"][key] = value
            else:
                groups["breadth"][key] = value
        credit = self._map(summary.get("credit_risk_proxy"))
        for key in ("HY OAS", "HY OAS DELTA 5D BPS", "HY OAS DELTA 21D BPS", "HY OAS WIDENING 5D FLAG", "HYG/LQD REL 1W %", "CREDIT RISK-OFF FLAG"):
            if key in credit:
                groups["credit"][key] = credit[key]
        groups["lead"].update(self._lead_component_payload(summary))
        return {
            "trend": self._json_map(groups["trend"]),
            "breadth": self._json_map(groups["breadth"]),
            "volatility": self._json_map(groups["volatility"]),
            "credit": self._json_map(groups["credit"]),
            "lead": self._json_map(groups["lead"]),
        }

    def _lead_component_payload(self, summary: dict[str, object]) -> dict[str, object]:
        industry_rows = self._records(summary.get("industry_leaders"))
        sector_rows = self._records(summary.get("sector_leaders"))
        return {
            "industry_top8": [row.get("TICKER") for row in industry_rows[:8]],
            "sector_top5": [row.get("TICKER") for row in sector_rows[:5]],
            "lead_state": self._lead_axis_state(summary)["state"],
        }

    def _index_state_for_symbol(
        self,
        symbol: str,
        index_context: dict[str, object],
        index_state: dict[str, object],
    ) -> dict[str, object]:
        prefix = f"{symbol} "
        keys = {
            "close": "CLOSE",
            "day_pct": "DAY %",
            "ema21_position": "21EMA POSITION",
            "sma50_pct": "50SMA %",
            "rally_attempt_day": "RALLY ATTEMPT DAY",
            "ftd_flag": "FTD FLAG",
            "ftd_valid_flag": "FTD VALID FLAG",
            "ftd_date": "FTD DATE",
            "ftd_age_days": "FTD AGE DAYS",
            "distribution_day_count": "DISTRIBUTION DAY COUNT",
            "below_50sma_flag": "BELOW 50SMA FLAG",
            "under_pressure_flag": "UNDER PRESSURE FLAG",
        }
        result: dict[str, object] = {}
        for output_key, source_key in keys.items():
            value = index_context.get(prefix + source_key, index_state.get(prefix + source_key))
            result[output_key] = self._json_value(value)
        return result

    def _m_gate(self, summary: dict[str, object], history: list[dict[str, object]] | None = None) -> list[str]:
        score = self._num(summary.get("score"))
        index = self._map(summary.get("index_context_summary"))
        state = self._map(summary.get("index_state_summary"))
        breadth = self._map(summary.get("breadth_momentum_summary"))
        vol = self._map(summary.get("volatility_term_structure"))
        credit = self._map(summary.get("credit_risk_proxy"))
        distribution_pressure = self._distribution_pressure(summary, self._timeline(summary, history or []))

        spy_dd = self._num(index.get("SPY DISTRIBUTION DAY COUNT", state.get("SPY DISTRIBUTION DAY COUNT")))
        qqq_dd = self._num(index.get("QQQ DISTRIBUTION DAY COUNT", state.get("QQQ DISTRIBUTION DAY COUNT")))
        spy_dd_decayed = self._num(distribution_pressure.get("SPY", {}).get("dd_decayed"))
        qqq_dd_decayed = self._num(distribution_pressure.get("QQQ", {}).get("dd_decayed"))
        heavy_decayed_dd = any(self._is_num(value) and value >= 4.0 for value in (spy_dd_decayed, qqq_dd_decayed))
        valid_ftd = any(self._flag(index.get(f"{symbol} FTD VALID FLAG")) for symbol in ("SPY", "QQQ"))
        min_ftd_age = self._min_valid([index.get("SPY FTD AGE DAYS"), index.get("QQQ FTD AGE DAYS")])
        both_below_50 = all(self._flag(index.get(f"{symbol} BELOW 50SMA FLAG")) for symbol in ("SPY", "QQQ"))
        full_backwardation = self._flag(vol.get("FULL BACKWARDATION FLAG"))
        term_inversion = self._flag(vol.get("INVERSION FLAG"))
        credit_riskoff = self._flag(credit.get("CREDIT RISK-OFF FLAG"))
        oas_widening = self._flag(credit.get("HY OAS WIDENING 5D FLAG"))
        breadth_mom = self._num(breadth.get("A20 MOMENTUM FLAG"))

        no_go = (
            heavy_decayed_dd
            or full_backwardation
            or (credit_riskoff and oas_widening)
            or (self._is_num(score) and score < 40.0 and self._is_num(breadth_mom) and breadth_mom <= -1.0)
            or ((not valid_ftd) and both_below_50)
        )
        go = (
            valid_ftd
            and self._is_num(score)
            and score >= 60.0
            and self._is_num(spy_dd)
            and self._is_num(qqq_dd)
            and spy_dd <= 3.0
            and qqq_dd <= 3.0
            and not term_inversion
            and not credit_riskoff
        )
        verdict = "NO_GO" if no_go else "GO" if go else "CAUTION"
        reasons = [
            f"SPY_DD_RAW={self._int_or_na(distribution_pressure.get('SPY', {}).get('dd_raw'))}/25D",
            f"SPY_DD_DECAYED={self._one(distribution_pressure.get('SPY', {}).get('dd_decayed'))}",
            f"SPY_DD_ABSORB={self._yn_text(distribution_pressure.get('SPY', {}).get('dd_absorb'))}",
            f"QQQ_DD_RAW={self._int_or_na(distribution_pressure.get('QQQ', {}).get('dd_raw'))}/25D",
            f"QQQ_DD_DECAYED={self._one(distribution_pressure.get('QQQ', {}).get('dd_decayed'))}",
            f"QQQ_DD_ABSORB={self._yn_text(distribution_pressure.get('QQQ', {}).get('dd_absorb'))}",
            f"FTD_AGE={self._days_or_na(min_ftd_age)}({'valid' if valid_ftd else 'invalid_or_none'})",
            f"VIX_TERM={'INV' if term_inversion else 'NORMAL'}",
            f"BREADTH_MOM={self._int_or_na(breadth_mom)}",
            f"CREDIT={'RISKOFF' if credit_riskoff else 'OK'}",
            f"SCORE={self._one(score)}",
        ]
        return [f"VERDICT: {verdict}", f"REASONS: {'; '.join(reasons)}"]

    def _index(self, summary: dict[str, object]) -> list[str]:
        index = self._map(summary.get("index_context_summary"))
        drawdown = self._map(summary.get("drawdown_summary"))
        lines = []
        for symbol in ("SPY", "QQQ"):
            ftd = "N"
            if self._flag(index.get(f"{symbol} FTD FLAG")):
                date = str(index.get(f"{symbol} FTD DATE") or "NA")
                gain = self._pct(index.get(f"{symbol} FTD GAIN %"))
                adv = self._num(index.get(f"{symbol} FTD ADVANCE RATIO"))
                adv_text = "NA" if not self._is_num(adv) else f"ADV{adv * 100:.0f}%"
                ftd = f"Y({date},{gain},{adv_text})"
            lines.append(
                f"{symbol}: C={self._price(index.get(f'{symbol} CLOSE'))} "
                f"D%={self._pct(index.get(f'{symbol} DAY %'))} "
                f"21EMA={self._text(index.get(f'{symbol} 21EMA POSITION'))} "
                f"50SMA%={self._pct(index.get(f'{symbol} 50SMA %'))} "
                f"DD252={self._pct(drawdown.get(f'{symbol} DD 252D %'))}/T={self._int_or_na(drawdown.get(f'{symbol} T_DD'))}D "
                f"RALLY={self._int_or_na(index.get(f'{symbol} RALLY ATTEMPT DAY'))}D "
                f"FTD={ftd} "
                f"DD25={self._int_or_na(index.get(f'{symbol} DISTRIBUTION DAY COUNT'))}"
            )
        return lines

    def _breadth(self, summary: dict[str, object], previous: dict[str, object] | None) -> list[str]:
        breadth = self._map(summary.get("breadth_summary"))
        momentum = self._map(summary.get("breadth_momentum_summary"))
        internal = self._map(summary.get("breadth_internal_summary"))
        previous_internal = self._map(previous.get("breadth_internal_summary")) if previous else {}
        summ_direction = self._direction(internal.get("MCCLELLAN SUMMATION"), previous_internal.get("MCCLELLAN SUMMATION"))
        ad_direction = self._direction(internal.get("AD LINE"), previous_internal.get("AD LINE"))
        return [
            f"A20={self._one(momentum.get('A20', breadth.get('pct_above_sma20')))}"
            f"(D5:{self._signed_num(momentum.get('A20 DELTA 5D'), 0)} D10:{self._signed_num(momentum.get('A20 DELTA 10D'), 0)} MOM:{self._signed_num(momentum.get('A20 MOMENTUM FLAG'), 0)}) "
            f"A50={self._one(breadth.get('pct_above_sma50'))} A200={self._one(breadth.get('pct_above_sma200'))} "
            f"NH-NL={self._signed_num(internal.get('NET NEW HIGH LOW'), 0)}({self._pct(internal.get('NET NEW HIGH LOW %'))}) "
            f"STAGE2%={self._one(internal.get('STAGE2 %'))}",
            f"MCCL_OSC={self._signed_num(internal.get('MCCLELLAN OSCILLATOR'), 0)} "
            f"SUMM={self._signed_num(internal.get('MCCLELLAN SUMMATION'), 0)}({summ_direction}) "
            f"ZWEIG={self._one(internal.get('ZWEIG BREADTH THRUST'))}(FLAG:{self._yn(internal.get('ZWEIG THRUST FLAG'))}) "
            f"ADLINE={ad_direction}",
        ]

    def _sentiment(self, summary: dict[str, object]) -> list[str]:
        high_vix = self._map(summary.get("high_vix_summary"))
        vol = self._map(summary.get("volatility_term_structure"))
        risk = self._map(summary.get("risk_on_ratio_summary"))
        credit = self._map(summary.get("credit_risk_proxy"))
        components = self._map(summary.get("component_scores"))
        deltas = self._map(summary.get("metric_deltas"))
        vix_deltas = self._map(deltas.get("VIX"))
        peak_value = high_vix.get("VIX PEAK", self._peak_value(high_vix))
        peak_date = self._text(high_vix.get("VIX PEAK DATE"))
        return [
            f"VIX={self._one(high_vix.get('VIX', vol.get('VIX')))}(PCTL252={self._one(high_vix.get('VIX 252D PCTL'))}%) "
            f"D5={self._signed_num(vix_deltas.get('1W'), 1)} "
            f"TERM: 9D/VIX={self._one(vol.get('VIX9D/VIX RATIO'), 2)} VIX/3M={self._one(vol.get('RATIO'), 2)} "
            f"INV={self._yn(vol.get('INVERSION FLAG'))} BWD={self._yn(vol.get('FULL BACKWARDATION FLAG'))}",
            f"PEAK: {self._one(peak_value)}@{peak_date} OFF={self._pct(high_vix.get('VIX PEAK RATIO %'))} DAYS={self._int_or_na(high_vix.get('VIX PEAK DAYS'))}",
            f"SAFEHVN={self._pct(high_vix.get('SAFE HAVEN %'))}(SC={self._one(components.get('safe_haven_score'), 0)}) "
            f"RISKON: ABOVE_MA={self._int_or_na(risk.get('ABOVE MA COUNT'))}/{self._int_or_na(risk.get('MA COUNT'))} REL1M={self._pct(risk.get('REL 1M %'))}",
            f"CREDIT: OAS={self._oas_bps(credit.get('HY OAS'))} D5={self._signed_num(credit.get('HY OAS DELTA 5D BPS'), 0)} "
            f"D21={self._signed_num(credit.get('HY OAS DELTA 21D BPS'), 0)} WIDEN={self._yn(credit.get('HY OAS WIDENING 5D FLAG'))} "
            f"HYGLQD_1W={self._pct(credit.get('HYG/LQD REL 1W %'))} RISKOFF={self._yn(credit.get('CREDIT RISK-OFF FLAG'))}",
        ]

    def _style(self, summary: dict[str, object]) -> list[str]:
        rows = self._records(summary.get("style_pair_summary"))
        lookup = {str(row.get("PAIR", "")): row for row in rows}
        pairs = ["RSP/SPY", "QQQ/SPY", "MTUM/SPY", "VUG/VTV"]
        values = [f"{pair}_1M={self._pct(lookup.get(pair, {}).get('REL 1M %'))}" for pair in pairs]
        defensive = self._map(summary.get("defensive_cyclical_summary"))
        values.append(f"CYCDEF_1M={self._pct(defensive.get('REL 1M %'))}")
        return [" ".join(values)]

    def _sector_rs(self, summary: dict[str, object]) -> list[str]:
        rows = [row for row in self._records(summary.get("sector_leaders")) if str(row.get("TICKER", "")).upper() in SECTOR_TICKERS]
        rank_delta = {str(row.get("TICKER", "")): row.get("RANK DELTA 1W") for row in self._records(summary.get("sector_relative_strength"))}
        if not rows:
            return ["NA"]
        parts = ["## SECTOR_RS (tactRS|structRS63|dRank1W)"]
        ranked = sorted(rows, key=lambda row: self._num(row.get("STRUCT RS")), reverse=True)
        line = "  ".join(
            f"{index}.{row.get('TICKER', 'NA')} {self._rank(row.get('RS'))}|{self._rank(row.get('STRUCT RS'))}|{self._signed_num(rank_delta.get(str(row.get('TICKER', ''))), 0)}"
            for index, row in enumerate(ranked, start=1)
        )
        return [parts[0], line]

    def _industry_rs(self, summary: dict[str, object], previous: dict[str, object] | None) -> list[str]:
        all_rows = self._records(summary.get("industry_leaders"))
        rows = all_rows[: self.config.industry_top_n]
        previous_rows = self._records(previous.get("industry_leaders")) if previous else []
        previous_full_rank = self._struct_rank(previous_rows)
        current_full_rank = self._struct_rank(all_rows)
        previous_top_rank = {
            str(row.get("TICKER", "")): index
            for index, row in enumerate(previous_rows[: self.config.industry_top_n], start=1)
        }
        current_top_rank = {str(row.get("TICKER", "")): index for index, row in enumerate(rows, start=1)}
        if not rows:
            return ["NA", "NEW_IN_TOP8: NA  OUT: NA"]
        has_struct_history = bool(previous_full_rank) and bool(current_full_rank)
        lines = []
        for index, row in enumerate(rows, start=1):
            ticker = str(row.get("TICKER", "NA"))
            prior = previous_full_rank.get(ticker)
            current = current_full_rank.get(ticker)
            delta = "NA" if not has_struct_history or prior is None or current is None else self._signed_num(prior - current, 0)
            lines.append(
                f"{index}.{ticker} {self._rank(row.get('RS'))}|{self._rank(row.get('STRUCT RS'))}|{delta}|{self._major_stocks(ticker, row)}"
            )
        if not previous_rows:
            lines.append("NEW_IN_TOP8: NA(no_history)  OUT: NA(no_history)")
            return lines
        if not has_struct_history:
            lines.append("NEW_IN_TOP8: NA(no_struct_history)  OUT: NA(no_struct_history)")
            return lines
        new = [
            f"{ticker}({self._signed_num(previous_full_rank[ticker] - current_full_rank[ticker], 0) if ticker in previous_full_rank else 'NA'})"
            for ticker in current_top_rank
            if ticker not in previous_top_rank
        ]
        out = [
            f"{ticker}({self._signed_num(previous_top_rank[ticker] - current_full_rank[ticker], 0) if ticker in current_full_rank else 'NA'})"
            for ticker in previous_top_rank
            if ticker not in current_top_rank
        ]
        lines.append(f"NEW_IN_TOP8: {', '.join(new) if new else 'NA'}  OUT: {', '.join(out) if out else 'NA'}")
        return lines

    def _struct_rank(self, rows: list[dict[str, object]]) -> dict[str, int]:
        scored = [
            (str(row.get("TICKER", "")), self._num(row.get("STRUCT RS")))
            for row in rows
            if str(row.get("TICKER", "")).strip() and self._is_num(row.get("STRUCT RS"))
        ]
        if not scored:
            return {}
        ranked = sorted(scored, key=lambda item: item[1], reverse=True)
        return {ticker: index for index, (ticker, _) in enumerate(ranked, start=1)}

    def _major_stocks(self, ticker: str, row: dict[str, object]) -> str:
        value = self._text(row.get("MAJOR STOCKS"))
        if value != "NA":
            return value
        return self.config.industry_major_stocks.get(ticker.upper(), "NA")

    def _changes_1w(self, summary: dict[str, object], previous: dict[str, object] | None) -> list[str]:
        positives: list[tuple[float, str]] = []
        negatives: list[tuple[float, str]] = []
        momentum = self._map(summary.get("breadth_momentum_summary"))
        self._add_change(positives, negatives, momentum.get("A20 DELTA 5D"), f"A20 {self._signed_num(momentum.get('A20 DELTA 5D'), 0)}pt")
        for row in self._records(summary.get("sector_relative_strength")):
            ticker = str(row.get("TICKER", ""))
            delta = self._num(row.get("RANK DELTA 1W"))
            self._add_change(positives, negatives, delta, f"{ticker} rank {self._signed_num(delta, 0)}")
        credit = self._map(summary.get("credit_risk_proxy"))
        oas_delta = self._num(credit.get("HY OAS DELTA 5D BPS"))
        if self._is_num(oas_delta):
            self._add_change(positives, negatives, -oas_delta, f"OAS {self._signed_num(oas_delta, 0)}bps")
        if previous:
            state = self._map(summary.get("index_state_summary"))
            prev_state = self._map(previous.get("index_state_summary"))
            for symbol in ("SPY", "QQQ"):
                current = self._num(state.get(f"{symbol} DISTRIBUTION DAY COUNT"))
                prior = self._num(prev_state.get(f"{symbol} DISTRIBUTION DAY COUNT"))
                if self._is_num(current) and self._is_num(prior):
                    self._add_change(positives, negatives, prior - current, f"{symbol} DD25 {self._int_or_na(prior)}->{self._int_or_na(current)}")
        positives = sorted(positives, key=lambda item: abs(item[0]), reverse=True)[:3]
        negatives = sorted(negatives, key=lambda item: abs(item[0]), reverse=True)[:3]
        return [
            "+ " + ("; ".join(item[1] for item in positives) if positives else "NA"),
            "- " + ("; ".join(item[1] for item in negatives) if negatives else "NA"),
        ]

    def _detect_transitions(self, summary: dict[str, object], history: list[dict[str, object]]) -> list[dict[str, object]]:
        timeline = self._timeline(summary, history)
        if len(timeline) < 2:
            return []
        transitions: list[dict[str, object]] = []
        axes = ["GATE", "BREADTH", "VOL", "CREDIT", "LEAD"]
        for axis in axes:
            self._append_axis_transitions(transitions, timeline, axis, None)
        for symbol in ("SPY", "QQQ"):
            self._append_axis_transitions(transitions, timeline, "REGIME", symbol)
        current_date = self._trade_date(summary)
        transitions = [
            item
            for item in transitions
            if item["date"] <= current_date and self._is_num(item.get("age_days")) and float(item.get("age_days", 0)) <= 10.0
        ]
        return sorted(transitions, key=lambda item: (item["date"], str(item["axis"])), reverse=True)[:6]

    def _append_axis_transitions(
        self,
        transitions: list[dict[str, object]],
        timeline: list[dict[str, object]],
        axis: str,
        symbol: str | None,
    ) -> None:
        previous_state = self._axis_state(timeline[0], axis, symbol)
        for index, item in enumerate(timeline[1:], start=1):
            current_state = self._axis_state(item, axis, symbol)
            if previous_state["state"] is None or current_state["state"] is None:
                previous_state = current_state
                continue
            if current_state["state"] == previous_state["state"]:
                previous_state = current_state
                continue
            next_state = self._axis_state(timeline[index + 1], axis, symbol)["state"] if index + 1 < len(timeline) else None
            event: dict[str, object] = {
                "date": self._trade_date(item),
                "axis": axis if symbol is None else f"{symbol}_{axis}",
                "from": previous_state["state"],
                "to": current_state["state"],
                "trigger": current_state["trigger"],
                "confirmed": bool(next_state == current_state["state"]),
                "age_days": max(0, len(timeline) - 1 - index),
            }
            if symbol is not None:
                event["symbol"] = symbol
            transitions.append(event)
            previous_state = current_state

    def _axis_state(self, summary: dict[str, object], axis: str, symbol: str | None) -> dict[str, object]:
        if axis == "GATE":
            score = self._num(summary.get("score"))
            if not self._is_num(score):
                return {"state": None, "trigger": {"metric": "score", "value": None, "threshold": "GO>=60;NO_GO<40"}}
            state = "GO" if score >= 60.0 else "NO_GO" if score < 40.0 else "CAUTION"
            return {"state": state, "trigger": {"metric": "score", "value": score, "threshold": "GO>=60;NO_GO<40"}}
        if axis == "REGIME":
            return self._regime_axis_state(summary, symbol or "SPY")
        if axis == "BREADTH":
            return self._breadth_axis_state(summary)
        if axis == "VOL":
            return self._vol_axis_state(summary)
        if axis == "CREDIT":
            credit = self._map(summary.get("credit_risk_proxy"))
            riskoff = self._flag(credit.get("CREDIT RISK-OFF FLAG"))
            return {"state": "RISKOFF" if riskoff else "OK", "trigger": {"metric": "CREDIT RISK-OFF FLAG", "value": float(riskoff), "threshold": ">=1"}}
        if axis == "LEAD":
            return self._lead_axis_state(summary)
        return {"state": None, "trigger": {"metric": axis, "value": None, "threshold": None}}

    def _regime_axis_state(self, summary: dict[str, object], symbol: str) -> dict[str, object]:
        index = self._map(summary.get("index_context_summary"))
        state = self._map(summary.get("index_state_summary"))
        prefix = f"{symbol} "
        below_50 = self._flag(index.get(prefix + "BELOW 50SMA FLAG", state.get(prefix + "BELOW 50SMA FLAG")))
        sma50_pct = self._num(index.get(prefix + "50SMA %", state.get(prefix + "50SMA %")))
        ema21 = self._text(index.get(prefix + "21EMA POSITION", state.get(prefix + "21EMA POSITION"))).lower()
        rally = self._num(index.get(prefix + "RALLY ATTEMPT DAY", state.get(prefix + "RALLY ATTEMPT DAY")))
        ftd_valid = self._flag(index.get(prefix + "FTD VALID FLAG", state.get(prefix + "FTD VALID FLAG")))
        ftd_age = self._num(index.get(prefix + "FTD AGE DAYS", state.get(prefix + "FTD AGE DAYS")))
        under_pressure = self._flag(index.get(prefix + "UNDER PRESSURE FLAG", state.get(prefix + "UNDER PRESSURE FLAG")))
        dd_count = self._num(index.get(prefix + "DISTRIBUTION DAY COUNT", state.get(prefix + "DISTRIBUTION DAY COUNT")))
        if ftd_valid and self._is_num(ftd_age) and ftd_age <= 1.0:
            regime = "FTD_CONFIRMED"
        elif below_50 or (self._is_num(sma50_pct) and sma50_pct < 0.0):
            regime = "DOWNTREND"
        elif under_pressure or "below" in ema21 or (self._is_num(dd_count) and dd_count >= 5.0):
            regime = "UNDER_PRESSURE"
        elif self._is_num(rally) and rally > 0.0 and not ftd_valid:
            regime = "RALLY_ATTEMPT"
        elif ftd_valid or (self._is_num(sma50_pct) and sma50_pct >= 0.0):
            regime = "UPTREND"
        else:
            regime = None
        return {"state": regime, "trigger": {"metric": f"{symbol} regime inputs", "value": regime, "threshold": "FSM"}}

    def _breadth_axis_state(self, summary: dict[str, object]) -> dict[str, object]:
        breadth = self._map(summary.get("breadth_summary"))
        momentum = self._map(summary.get("breadth_momentum_summary"))
        internal = self._map(summary.get("breadth_internal_summary"))
        a20_delta10 = self._num(momentum.get("A20 DELTA 10D"))
        a50 = self._num(breadth.get("pct_above_sma50"))
        a200 = self._num(breadth.get("pct_above_sma200"))
        nhnl = self._num(internal.get("NET NEW HIGH LOW"))
        zweig = self._flag(internal.get("ZWEIG THRUST FLAG"))
        if zweig or (self._is_num(a20_delta10) and a20_delta10 >= 10.0):
            state = "THRUST_ON"
        elif (self._is_num(a20_delta10) and a20_delta10 <= -10.0) or (self._is_num(a50) and a50 < 40.0) or (self._is_num(a200) and a200 < 40.0) or (self._is_num(nhnl) and nhnl < 0.0):
            state = "DETERIORATING"
        else:
            state = "NEUTRAL"
        return {"state": state, "trigger": {"metric": "A20 DELTA 10D", "value": self._json_number(a20_delta10), "threshold": "THRUST>=10;DETERIORATING<=-10"}}

    def _vol_axis_state(self, summary: dict[str, object]) -> dict[str, object]:
        high_vix = self._map(summary.get("high_vix_summary"))
        vol = self._map(summary.get("volatility_term_structure"))
        vix_pctl = self._num(high_vix.get("VIX 252D PCTL"))
        inversion = self._flag(vol.get("INVERSION FLAG"))
        backwardation = self._flag(vol.get("FULL BACKWARDATION FLAG"))
        peak_off = self._num(high_vix.get("VIX PEAK RATIO %"))
        if inversion or backwardation or (self._is_num(vix_pctl) and vix_pctl >= 80.0):
            state = "STRESS_ON"
        elif self._is_num(peak_off) and peak_off <= -30.0:
            state = "STRESS_OFF"
        else:
            state = "NORMAL"
        return {"state": state, "trigger": {"metric": "VIX/term", "value": self._json_number(vix_pctl), "threshold": "stress pctl>=80 or term inversion"}}

    def _lead_axis_state(self, summary: dict[str, object]) -> dict[str, object]:
        risk_on = {"SMH", "QQQ", "XLK", "XLY", "IWM", "RSP"}
        defensive = {"XLP", "XLU", "XLV"}
        top = [str(row.get("TICKER", "")).upper() for row in self._records(summary.get("industry_leaders"))[:8]]
        sectors = [str(row.get("TICKER", "")).upper() for row in self._records(summary.get("sector_leaders"))[:5]]
        style_lookup = {str(row.get("PAIR", "")): row for row in self._records(summary.get("style_pair_summary"))}
        rsp_spy = self._num(style_lookup.get("RSP/SPY", {}).get("REL 1M %"))
        if any(ticker in risk_on for ticker in [*top, *sectors]) or (self._is_num(rsp_spy) and rsp_spy > 0.0):
            state = "RISKON_LED"
        elif any(ticker in defensive for ticker in sectors):
            state = "DEFENSIVE_LED"
        else:
            state = "MIXED"
        return {"state": state, "trigger": {"metric": "leadership", "value": ",".join(top[:3]), "threshold": "risk-on top8 or RSP/SPY>0"}}

    def _distribution_pressure(self, summary: dict[str, object], timeline: list[dict[str, object]]) -> dict[str, object]:
        return {symbol: self._distribution_pressure_for_symbol(symbol, summary, timeline) for symbol in ("SPY", "QQQ")}

    def _distribution_pressure_for_symbol(self, symbol: str, summary: dict[str, object], timeline: list[dict[str, object]]) -> dict[str, object]:
        events = self._distribution_events_for_symbol(symbol, timeline)
        decayed = sum(float(event["weight"]) for event in events) if events else None
        absorb_inputs = self._distribution_absorb_inputs(symbol, summary)
        absorb = self._distribution_absorb_flag(absorb_inputs)
        has_event_coverage = self._has_distribution_event_coverage(symbol, timeline)
        return {
            "dd_raw": float(len(events)) if events or has_event_coverage else None,
            "dd_decayed": round(decayed, 3) if decayed is not None else None,
            "dd_absorb": absorb,
            "absorb_inputs": absorb_inputs,
            "events": events,
        }

    def _has_distribution_event_coverage(self, symbol: str, timeline: list[dict[str, object]]) -> bool:
        recent = timeline[-25:]
        return bool(recent) and all(self._distribution_event_flag(symbol, item) is not None for item in recent)

    def _distribution_events_for_symbol(self, symbol: str, timeline: list[dict[str, object]]) -> list[dict[str, object]]:
        recent = timeline[-25:]
        flags = [self._distribution_event_flag(symbol, item) for item in recent]
        has_full_flag_coverage = bool(recent) and all(flag is not None for flag in flags)
        events: list[dict[str, object]] = []
        if has_full_flag_coverage:
            seen_event_dates: set[str] = set()
            for index, (item, flag) in enumerate(zip(recent, flags, strict=False)):
                if not flag:
                    continue
                event_date = self._distribution_event_date(symbol, item)
                if event_date in seen_event_dates:
                    continue
                seen_event_dates.add(event_date)
                age = len(recent) - 1 - index
                if age > 24:
                    continue
                credit = self._distribution_absorb_credit(symbol, recent, index)
                weight = math.exp(-math.log(2.0) * age / 10.0) * (1.0 - credit)
                events.append(self._distribution_event_record(item, age, credit, weight, event_date))
            return events
        if len(recent) < 2:
            return events
        previous_count = self._dd_count(symbol, recent[0])
        for index, item in enumerate(recent[1:], start=1):
            current_count = self._dd_count(symbol, item)
            if self._is_num(previous_count) and self._is_num(current_count) and current_count > previous_count:
                increment = max(1, int(round(current_count - previous_count)))
                for _ in range(increment):
                    age = len(recent) - 1 - index
                    if age <= 24:
                        credit = self._distribution_absorb_credit(symbol, recent, index)
                        weight = math.exp(-math.log(2.0) * age / 10.0) * (1.0 - credit)
                        events.append(self._distribution_event_record(item, age, credit, weight, self._distribution_event_date(symbol, item)))
            previous_count = current_count
        return events

    def _distribution_event_date(self, symbol: str, item: dict[str, object]) -> str:
        values = self._index_values(symbol, item)
        price_date = self._text(values.get("price_date"))
        return price_date if price_date != "NA" else self._trade_date(item)

    def _distribution_event_record(self, item: dict[str, object], age: int, credit: float, weight: float, event_date: str | None = None) -> dict[str, object]:
        return {
            "date": event_date or self._trade_date(item),
            "age_days": age,
            "severity": 1.0,
            "absorb_credit": round(credit, 3),
            "weight": round(weight, 3),
        }

    def _distribution_event_flag(self, symbol: str, summary: dict[str, object]) -> bool | None:
        values = self._index_values(symbol, summary)
        explicit = self._json_bool(values.get("distribution_day_flag"))
        if explicit is not None:
            return explicit
        day_pct = self._num(values.get("day_pct"))
        volume = self._num(values.get("volume"))
        previous_volume = self._num(values.get("previous_volume"))
        if not self._is_num(day_pct) or not self._is_num(volume) or not self._is_num(previous_volume):
            return None
        return bool(day_pct <= -0.2 and volume > previous_volume)

    def _distribution_absorb_credit(self, symbol: str, timeline: list[dict[str, object]], event_index: int) -> float:
        event_values = self._index_values(symbol, timeline[event_index])
        event_high = self._num(event_values.get("high"))
        event_volume = self._num(event_values.get("volume"))
        best_partial = 0.0
        for future in timeline[event_index + 1 : min(len(timeline), event_index + 4)]:
            values = self._index_values(symbol, future)
            close = self._num(values.get("close"))
            volume = self._num(values.get("volume"))
            if self._is_num(close) and self._is_num(event_high) and close >= event_high:
                if self._is_num(volume) and self._is_num(event_volume) and volume >= event_volume:
                    return 0.9
                best_partial = max(best_partial, 0.4)
        return best_partial

    def _distribution_absorb_inputs(self, symbol: str, summary: dict[str, object]) -> dict[str, object]:
        values = self._index_values(symbol, summary)
        return {
            "acc_days_10d": self._json_number(values.get("acc_days_10d")),
            "dist_days_10d": self._json_number(values.get("dist_days_10d")),
            "close_above_21ema": self._json_bool(values.get("close_above_21ema")),
            "higher_high_after_last_dd": self._json_bool(values.get("higher_high_after_last_dd")),
        }

    def _distribution_absorb_flag(self, inputs: dict[str, object]) -> bool | None:
        acc = self._num(inputs.get("acc_days_10d"))
        dist = self._num(inputs.get("dist_days_10d"))
        above = inputs.get("close_above_21ema")
        higher_high = inputs.get("higher_high_after_last_dd")
        if not self._is_num(acc) or not self._is_num(dist) or above is None or higher_high is None:
            return None
        return bool(acc >= dist and above and higher_high)

    def _dd_count(self, symbol: str, summary: dict[str, object]) -> float:
        context = self._map(summary.get("index_context_summary"))
        state = self._map(summary.get("index_state_summary"))
        return self._num(context.get(f"{symbol} DISTRIBUTION DAY COUNT", state.get(f"{symbol} DISTRIBUTION DAY COUNT")))

    def _index_values(self, symbol: str, summary: dict[str, object]) -> dict[str, object]:
        context = self._map(summary.get("index_context_summary"))
        state = self._map(summary.get("index_state_summary"))
        prefix = f"{symbol} "
        ema_position = self._text(context.get(prefix + "21EMA POSITION", state.get(prefix + "21EMA POSITION"))).lower()
        return {
            "price_date": context.get(prefix + "PRICE DATE", state.get(prefix + "PRICE DATE")),
            "close": context.get(prefix + "CLOSE", state.get(prefix + "CLOSE")),
            "day_pct": context.get(prefix + "DAY %", state.get(prefix + "DAY %")),
            "high": context.get(prefix + "HIGH", state.get(prefix + "HIGH")),
            "volume": context.get(prefix + "VOLUME", state.get(prefix + "VOLUME")),
            "previous_volume": context.get(prefix + "PREVIOUS VOLUME", state.get(prefix + "PREVIOUS VOLUME")),
            "distribution_day_flag": context.get(prefix + "DISTRIBUTION DAY FLAG", state.get(prefix + "DISTRIBUTION DAY FLAG")),
            "acc_days_10d": context.get(prefix + "ACC DAYS 10D", state.get(prefix + "ACC DAYS 10D")),
            "dist_days_10d": context.get(prefix + "DIST DAYS 10D", state.get(prefix + "DIST DAYS 10D")),
            "close_above_21ema": context.get(prefix + "CLOSE ABOVE 21EMA FLAG", 1.0 if "above" in ema_position else 0.0 if "below" in ema_position else None),
            "higher_high_after_last_dd": context.get(prefix + "HIGHER HIGH AFTER LAST DD FLAG", state.get(prefix + "HIGHER HIGH AFTER LAST DD FLAG")),
        }

    def _timeline(self, summary: dict[str, object], history: list[dict[str, object]]) -> list[dict[str, object]]:
        items = [item for item in history if self._trade_date(item) != "NA"]
        current_date = self._trade_date(summary)
        items = [item for item in items if self._trade_date(item) < current_date]
        items.append(summary)
        return sorted(items, key=self._trade_date)[-26:]

    def _add_change(self, positives: list[tuple[float, str]], negatives: list[tuple[float, str]], value: object, label: str) -> None:
        number = self._num(value)
        if not self._is_num(number) or number == 0.0:
            return
        if number > 0:
            positives.append((number, label))
        else:
            negatives.append((number, label))

    def _trade_date(self, summary: dict[str, object]) -> str:
        raw = summary.get("trade_date")
        parsed = pd.to_datetime(raw, errors="coerce")
        return pd.Timestamp(parsed).strftime("%Y-%m-%d") if pd.notna(parsed) else "NA"

    def _previous_summary(self, summary: dict[str, object], history: list[dict[str, object]]) -> dict[str, object] | None:
        current = self._trade_date(summary)
        prior = [item for item in history if self._trade_date(item) < current]
        return prior[-1] if prior else None

    def _records(self, value: object) -> list[dict[str, object]]:
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    def _map(self, value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    def _json_map(self, value: dict[str, object]) -> dict[str, object]:
        return {str(key): self._json_value(item) for key, item in value.items()}

    def _json_value(self, value: object) -> object:
        if isinstance(value, dict):
            return self._json_map(value)
        if isinstance(value, list):
            return [self._json_value(item) for item in value]
        if isinstance(value, pd.Timestamp):
            return value.strftime("%Y-%m-%d")
        number = pd.to_numeric(value, errors="coerce")
        if pd.notna(number):
            return float(number)
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in {"nan", "none", "nat"}:
            return None
        return text

    def _json_number(self, value: object) -> float | None:
        number = pd.to_numeric(value, errors="coerce")
        return float(number) if pd.notna(number) else None

    def _json_bool(self, value: object) -> bool | None:
        if value is None:
            return None
        text = str(value).strip().lower()
        if text in {"", "nan", "none", "na", "null"}:
            return None
        if text in {"y", "yes", "true"}:
            return True
        if text in {"n", "no", "false"}:
            return False
        number = pd.to_numeric(value, errors="coerce")
        return bool(number >= 0.5) if pd.notna(number) else None

    def _num(self, value: object) -> float:
        number = pd.to_numeric(value, errors="coerce")
        return float(number) if pd.notna(number) else float("nan")

    def _is_num(self, value: object) -> bool:
        return pd.notna(self._num(value))

    def _flag(self, value: object) -> bool:
        number = self._num(value)
        return bool(pd.notna(number) and number >= 0.5)

    def _min_valid(self, values: list[object]) -> float:
        numbers = [self._num(value) for value in values]
        valid = [value for value in numbers if pd.notna(value) and value >= 0.0]
        return min(valid) if valid else float("nan")

    def _direction(self, current: object, previous: object) -> str:
        current_num = self._num(current)
        previous_num = self._num(previous)
        if not self._is_num(current_num) or not self._is_num(previous_num):
            return "NA"
        delta = current_num - previous_num
        if abs(delta) < 0.1:
            return "flat"
        return "rising" if delta > 0 else "falling"

    def _peak_value(self, high_vix: dict[str, object]) -> float:
        current = self._num(high_vix.get("VIX"))
        ratio = self._num(high_vix.get("VIX PEAK RATIO %"))
        if self._is_num(current) and self._is_num(ratio) and ratio > -100.0:
            return current / (1.0 + ratio / 100.0)
        return float("nan")

    def _text(self, value: object) -> str:
        if value is None:
            return "NA"
        text = str(value).strip()
        return text if text and text.lower() not in {"nan", "none"} else "NA"

    def _one(self, value: object, digits: int = 1) -> str:
        number = self._num(value)
        return "NA" if not self._is_num(number) else f"{number:.{digits}f}"

    def _price(self, value: object) -> str:
        number = self._num(value)
        return "NA" if not self._is_num(number) else f"{number:.2f}"

    def _pct(self, value: object) -> str:
        number = self._num(value)
        return "NA" if not self._is_num(number) else f"{number:+.1f}%"

    def _signed_num(self, value: object, digits: int) -> str:
        number = self._num(value)
        return "NA" if not self._is_num(number) else f"{number:+.{digits}f}"

    def _int_or_na(self, value: object) -> str:
        number = self._num(value)
        return "NA" if not self._is_num(number) else str(int(round(number)))

    def _days_or_na(self, value: object) -> str:
        number = self._num(value)
        return "NA" if not self._is_num(number) else f"{int(round(number))}D"

    def _rank(self, value: object) -> str:
        number = self._num(value)
        return "NA" if not self._is_num(number) else str(int(round(number)))

    def _oas_bps(self, value: object) -> str:
        number = self._num(value)
        if not self._is_num(number):
            return "NA"
        bps = number * 100.0 if abs(number) < 100.0 else number
        return str(int(round(bps)))

    def _yn(self, value: object) -> str:
        return "Y" if self._flag(value) else "N"

    def _yn_text(self, value: object) -> str:
        parsed = self._json_bool(value)
        return "NA" if parsed is None else "Y" if parsed else "N"


class MarketContextMarkdownRenderer:
    def render(self, context: MarketContextResult) -> str:
        lines = [f"# MARKET_CONTEXT | {context.trade_date} ({context.weekday}) | schema {context.schema_version}", ""]
        for section in ["M_GATE", "INDEX", "BREADTH", "SENTIMENT", "STYLE", "SECTOR_RS", "INDUSTRY_RS", "CHANGES_1W"]:
            section_lines = context.sections.get(section, ["NA"])
            if section == "SECTOR_RS" and section_lines and section_lines[0].startswith("## SECTOR_RS"):
                lines.extend(section_lines)
            elif section == "INDUSTRY_RS":
                lines.append("## INDUSTRY_RS top8 (tactRS|structRS63|dRank1W|majors)")
                lines.extend(section_lines)
            else:
                lines.append(f"## {section}")
                lines.extend(section_lines or ["NA"])
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def render_json(self, context: MarketContextResult) -> str:
        return json.dumps(context.to_dict(), ensure_ascii=False, indent=2) + "\n"
