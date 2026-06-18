from __future__ import annotations

import json
from dataclasses import dataclass, field

import pandas as pd


SCHEMA_VERSION = "v1.0.1"
SECTOR_TICKERS = frozenset({"XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"})


@dataclass(frozen=True, slots=True)
class MarketContextConfig:
    output_dir: str = "data_runs/market_context"
    write_markdown: bool = True
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
            output_dir=str(output_map.get("dir", data.get("output_dir", "data_runs/market_context"))),
            write_markdown=bool(output_map.get("write_markdown", data.get("write_markdown", True))),
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

    def to_dict(self) -> dict[str, object]:
        return {
            "document_type": "market_context",
            "schema_version": self.schema_version,
            "trade_date": self.trade_date,
            "weekday": self.weekday,
            "sections": self.sections,
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
            "M_GATE": self._m_gate(summary),
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
        )

    def _m_gate(self, summary: dict[str, object]) -> list[str]:
        score = self._num(summary.get("score"))
        index = self._map(summary.get("index_context_summary"))
        state = self._map(summary.get("index_state_summary"))
        breadth = self._map(summary.get("breadth_momentum_summary"))
        vol = self._map(summary.get("volatility_term_structure"))
        credit = self._map(summary.get("credit_risk_proxy"))

        spy_dd = self._num(index.get("SPY DISTRIBUTION DAY COUNT", state.get("SPY DISTRIBUTION DAY COUNT")))
        qqq_dd = self._num(index.get("QQQ DISTRIBUTION DAY COUNT", state.get("QQQ DISTRIBUTION DAY COUNT")))
        valid_ftd = any(self._flag(index.get(f"{symbol} FTD VALID FLAG")) for symbol in ("SPY", "QQQ"))
        min_ftd_age = self._min_valid([index.get("SPY FTD AGE DAYS"), index.get("QQQ FTD AGE DAYS")])
        both_below_50 = all(self._flag(index.get(f"{symbol} BELOW 50SMA FLAG")) for symbol in ("SPY", "QQQ"))
        full_backwardation = self._flag(vol.get("FULL BACKWARDATION FLAG"))
        term_inversion = self._flag(vol.get("INVERSION FLAG"))
        credit_riskoff = self._flag(credit.get("CREDIT RISK-OFF FLAG"))
        oas_widening = self._flag(credit.get("HY OAS WIDENING 5D FLAG"))
        breadth_mom = self._num(breadth.get("A20 MOMENTUM FLAG"))

        no_go = (
            (self._is_num(spy_dd) and spy_dd >= 6.0)
            or (self._is_num(qqq_dd) and qqq_dd >= 6.0)
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
            f"DD_COUNT_SPY={self._int_or_na(spy_dd)}/25D",
            f"DD_COUNT_QQQ={self._int_or_na(qqq_dd)}/25D",
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
