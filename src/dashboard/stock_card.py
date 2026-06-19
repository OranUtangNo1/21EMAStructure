from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pandas as pd

from src.dashboard.compressed_tape import CompressedTapeConfig, CompressedTapeError, CompressedTapeGenerator
from src.indicators.core import IndicatorCalculator, IndicatorConfig


SCHEMA_VERSION = "card-v1.0.2"


@dataclass(frozen=True, slots=True)
class StockCardConfig:
    output_dir: str = "data_runs/documents/stock_cards"
    write_markdown: bool = True
    write_json: bool = True
    tape_config: CompressedTapeConfig = CompressedTapeConfig()

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "StockCardConfig":
        data = payload or {}
        tape_payload = data.get("compressed_tape", {})
        if not isinstance(tape_payload, dict):
            tape_payload = {}
        return cls(
            output_dir=str(data.get("output_dir", "data_runs/documents/stock_cards")),
            write_markdown=bool(data.get("write_markdown", True)),
            write_json=bool(data.get("write_json", True)),
            tape_config=CompressedTapeConfig.from_dict(tape_payload),
        )


@dataclass(frozen=True, slots=True)
class StockCardMetadata:
    sector_etf: str = "NA"
    industry_etf: str = "NA"
    industry_rs_rank: int | None = None
    rs_pctl: float | None = None
    rs21: float | None = None
    rs63: float | None = None
    rs126: float | None = None
    rs_hi52: bool | None = None
    rs_hi3y: bool | None = None
    vcs: float | None = None
    stage2_quality_score: float | None = None
    mature_late_stage_risk: bool | None = None


@dataclass(frozen=True, slots=True)
class StockCardDocument:
    ticker: str
    text: str
    end_date: pd.Timestamp
    path: Path | None = None
    payload: dict[str, object] = field(default_factory=dict)
    json_path: Path | None = None

    @property
    def filename(self) -> str:
        return f"card_{self.ticker}_{self.end_date.strftime('%Y%m%d')}.md"

    @property
    def json_filename(self) -> str:
        return f"card_{self.ticker}_{self.end_date.strftime('%Y%m%d')}.json"


@dataclass(frozen=True, slots=True)
class StockCardExportResult:
    output_dir: Path
    documents: list[StockCardDocument]
    missing: dict[str, str]
    manifest_path: Path


class StockCardError(ValueError):
    """Raised when source data cannot produce a schema-compliant stock card."""


class StockCardGenerator:
    """Generate stock_card v1.0 markdown from one adjusted OHLCV pipeline."""

    def __init__(self, config: StockCardConfig | None = None, indicator_config: IndicatorConfig | None = None) -> None:
        self.config = config or StockCardConfig()
        self.tape_generator = CompressedTapeGenerator(self.config.tape_config)
        self.indicator_calculator = IndicatorCalculator(indicator_config or IndicatorConfig())

    def build(
        self,
        ticker: str,
        history: pd.DataFrame,
        *,
        metadata: StockCardMetadata | None = None,
        last_close: float | None = None,
    ) -> StockCardDocument:
        symbol = str(ticker).strip().upper()
        if not symbol:
            raise StockCardError("ticker is required")
        metadata = metadata or StockCardMetadata()

        try:
            prepared, adjusted = self.tape_generator._prepare_history(history)
            metrics = self.tape_generator._add_metrics(prepared)
            tape = self.tape_generator.build_t0(symbol, history, last_close=last_close)
        except CompressedTapeError as exc:
            raise StockCardError(str(exc)) from exc

        if prepared.empty:
            raise StockCardError(f"{symbol}: price history is empty")
        indicators = self.indicator_calculator.calculate(prepared)
        if indicators.empty:
            raise StockCardError(f"{symbol}: indicators are unavailable")

        context = _CardContext(
            ticker=symbol,
            source=prepared,
            metrics=metrics,
            indicators=indicators,
            adjusted=adjusted,
            metadata=metadata,
            tape_text=tape.text,
        )
        text = self._render(context)
        self._validate(context, text)
        return StockCardDocument(
            ticker=symbol,
            text=text,
            end_date=pd.Timestamp(prepared.index[-1]),
            payload=self._payload(context),
        )

    def _render(self, ctx: "_CardContext") -> str:
        lines: list[str] = [
            f"# STOCK_CARD {ctx.ticker} | {ctx.end.strftime('%Y-%m-%d')} ({ctx.end.strftime('%a')}) | schema {SCHEMA_VERSION}",
            "",
            "## META",
            self._meta_line_1(ctx),
            self._meta_line_2(ctx),
            "",
        ]
        lines.extend(["## GATES", *self._gates(ctx), ""])
        lines.extend(["## TREND", *self._trend(ctx), ""])
        lines.extend(["## MOMO_VOL", *self._momo_vol(ctx), ""])
        lines.extend(["## VOLUME", *self._volume(ctx), ""])
        lines.extend(["## LEVELS", *self._levels(ctx), ""])
        lines.extend(["## SETUP", *self._setup(ctx), ""])
        lines.extend(self._risk_plan(ctx))
        lines.append("")
        lines.extend(ctx.tape_text.rstrip().splitlines())
        return "\n".join(lines).rstrip() + "\n"

    def _meta_line_1(self, ctx: "_CardContext") -> str:
        suffix = " SHORT!" if len(ctx.source) < 200 else ""
        return (
            f"TICKER={ctx.ticker} DATA={len(ctx.source)}d({ctx.start.strftime('%Y-%m-%d')}..{ctx.end.strftime('%Y-%m-%d')}){suffix} "
            f"ADJ={'Y' if ctx.adjusted else 'N'}"
        )

    def _meta_line_2(self, ctx: "_CardContext") -> str:
        rank = "NA" if ctx.metadata.industry_rs_rank is None else str(int(ctx.metadata.industry_rs_rank))
        return f"INDUSTRY_ETF={self._text(ctx.metadata.industry_etf)} IND_RS_RANK={rank} SECTOR={self._text(ctx.metadata.sector_etf)}"

    def _gates(self, ctx: "_CardContext") -> list[str]:
        short = len(ctx.source) < 200
        stage = self._stage(ctx)
        tt_pass, tt_total, fail_items = self._trend_template(ctx)
        hi_dist = self._dist_from_high(ctx)
        lo_dist = self._dist_from_low(ctx)
        ext = ctx.close / ctx.sma50 - 1.0 if self._is_num(ctx.sma50) else np.nan
        ud25 = self._ud_ratio(ctx, 25)
        acc50, dist50 = self._acc_dist(ctx)

        g1 = "NA(SHORT)" if short else ("PASS" if stage == "Stage2" else "COND" if stage == "Stage1-2" else "FAIL")
        g2 = "NA(SHORT)" if short else ("PASS" if tt_pass >= 6 else "COND" if tt_pass == 5 else "FAIL")
        g3 = "PASS" if self._is_num(hi_dist) and self._is_num(lo_dist) and hi_dist >= -0.25 and lo_dist >= 0.30 else "FAIL"
        g4 = "PASS" if self._is_num(ext) and ext < 0.25 else "FAIL"
        g5 = "PASS" if (self._is_num(ud25) and ud25 >= 0.8) or acc50 >= dist50 else "COND"
        if short:
            overall = "FAIL(SHORT)"
        elif "FAIL" in (g1, g2, g3, g4, g5):
            overall = "FAIL"
        elif "COND" in (g1, g2, g3, g4, g5):
            overall = "COND"
        else:
            overall = "PASS"

        return [
            f"G1_STAGE={g1}({stage})  G2_TT={g2}({tt_pass}/{tt_total})  G3_POS={g3}(hi{self._fmt_pct(hi_dist)}/lo{self._fmt_pct(lo_dist)})",
            f"G4_EXT={g4}({self._fmt_pct(ext)})  G5_VOLQ={g5}(UD{self._ratio(ud25)},A{acc50}/D{dist50})",
            f"EXT_ATR50={self._one(ctx.latest.get('atr_50sma_zone'))} EXT_ATR50_MIN5={self._one(ctx.latest.get('min_atr_50sma_zone_5d'))}",
            f"OVERALL={overall}",
        ]

    def _trend(self, ctx: "_CardContext") -> list[str]:
        tt_pass, tt_total, fail_items = self._trend_template(ctx)
        fail_text = "none" if not fail_items else ",".join(str(item) for item in fail_items)
        rs_text = self._rank(ctx.metadata.rs_pctl)
        rs_hi52 = self._yn(ctx.metadata.rs_hi52)
        rs_hi3y = self._yn(ctx.metadata.rs_hi3y)
        stage_num = "2" if self._stage(ctx) == "Stage2" else "1-2" if self._stage(ctx) == "Stage1-2" else "NA"
        p_vs_150 = ctx.close / ctx.sma150 - 1.0 if self._is_num(ctx.sma150) else np.nan
        slope150 = self._slope150(ctx)
        sma200_up = "Y" if self._is_num(ctx.sma200_slope) and ctx.sma200_slope > 0.0 else "N" if self._is_num(ctx.sma200_slope) else "NA"
        return [
            f"TT={tt_pass}/{tt_total} FAIL_ITEMS={fail_text} RS_PCTL={rs_text} RS21={self._rank(ctx.metadata.rs21)} RS63={self._rank(ctx.metadata.rs63)} RS126={self._rank(ctx.metadata.rs126)} RS_HI52={rs_hi52} RS_HI3Y={rs_hi3y}",
            f"STAGE={stage_num} P_VS_150SMA={self._fmt_pct(p_vs_150)} SLOPE150={self._fmt_percent_value(slope150, digits=3)}/d",
            f"LATE_STAGE={self._yn(ctx.metadata.mature_late_stage_risk)} STAGE2_Q={self._one(ctx.metadata.stage2_quality_score)} STAGE2_AGE={self._int(ctx.latest.get('days_since_stage2_start'))} BASE_DAYS_3M={self._int(ctx.latest.get('stage_base_days_3m'))}",
            f"SMA50={self._price(ctx.sma50)} SMA150={self._price(ctx.sma150)} SMA200={self._price(ctx.sma200)} 200SMA_UP_1M={sma200_up}",
        ]

    def _momo_vol(self, ctx: "_CardContext") -> list[str]:
        atr_pct = ctx.atr / ctx.close * 100.0 if self._is_num(ctx.atr) and ctx.close else np.nan
        return [
            " ".join(
                [
                    f"M12_1={self._fmt_pct(self._momentum_12_1(ctx))}",
                    f"R1M={self._fmt_pct(self._return(ctx, 21))}",
                    f"R3M={self._fmt_pct(self._return(ctx, 63))}",
                    f"R6M={self._fmt_pct(self._return(ctx, 126))}",
                    f"R12M={self._fmt_pct(self._return(ctx, 252))}",
                ]
            ),
            f"ATR14={self._price(ctx.atr)}({self._fmt_unsigned_percent_value(atr_pct)}) RV20={self._fmt_unsigned_pct(self._realized_vol(ctx))}",
        ]

    def _volume(self, ctx: "_CardContext") -> list[str]:
        acc50, dist50 = self._acc_dist(ctx)
        return [
            f"V50={self._int(ctx.v50)} VLAST={self._int(ctx.vlast)}% DRYUP5/50={self._ratio(self._dryup(ctx))}",
            f"ACC50={acc50} DIST50={dist50} UD25={self._ratio(self._ud_ratio(ctx, 25))}",
        ]

    def _levels(self, ctx: "_CardContext") -> list[str]:
        pivot, pivot_date = self._pivot(ctx)
        buy = self._buy_price(pivot)
        return [
            f"C={self._price(ctx.close)} PIVOT={self._price(pivot)}({self._pivot_date_text(ctx, pivot_date)}) BUY={self._price(buy)} HI52={self._price(ctx.hi52)} LO52={self._price(ctx.lo52)}",
            f"SWLO10={self._price(self._swlo(ctx, 10))} SWLO20={self._price(self._swlo(ctx, 20))} EMA21={self._price(ctx.ema21)} SMA50={self._price(ctx.sma50)}",
            f"STRUCT_ANCHORS={self._struct_anchors_text(ctx, buy)} BODY_RATIO={self._one(ctx.latest.get('breakout_body_ratio'))} DCR={self._one(ctx.latest.get('dcr_percent'))} RES_TESTS={self._int(ctx.latest.get('resistance_test_count'))}",
        ]

    def _setup(self, ctx: "_CardContext") -> list[str]:
        setup = self._setup_state(ctx)
        return [
            f"CANDIDATES={','.join(setup['candidates']) if setup['candidates'] else 'NONE'}",
            f"VCP={setup['vcp']} DEPTHS={setup['depths']} BASE: depth={self._fmt_abs_pct(setup['base_depth'])} len={setup['base_len']}d below_high={self._fmt_abs_pct(setup['below_high'])}",
            f"PP={self._yn(ctx.latest.get('pocket_pivot'))} PP_CNT={self._int(ctx.latest.get('pp_count_window'))} 3WT={self._yn(ctx.latest.get('three_weeks_tight'))} PGAP={self._pct_value(ctx.latest.get('power_gap_up_pct'))} PGAP_AGE={self._days(ctx.latest.get('days_since_power_gap'))}",
            f"PB_ATR21={self._one(ctx.latest.get('atr_21ema_zone'))} PB_ATR21L={self._one(ctx.latest.get('atr_21emaL_zone'))} XABOVE_EMA21={self._yn(ctx.latest.get('close_crossed_above_ema21'))} XABOVE_SMA50={self._yn(ctx.latest.get('close_crossed_above_sma50'))}",
            f"ADR_RECENT={self._one(ctx.latest.get('vcp_adr_recent_pct'))} ADR_BASE={self._one(ctx.latest.get('vcp_adr_base_pct'))} ADR_CONTRACT={self._yn(ctx.latest.get('vcp_is_contracting'))} VCS={self._one(ctx.metadata.vcs)} TIGHT_DAYS={self._int(ctx.latest.get('vcp_tight_days'))} PRIOR_UP%={self._one(ctx.latest.get('vcp_prior_uptrend_pct'))}",
            f"PULLBACK_REF={setup['pullback_ref']} UR_REF={setup['ur_ref']}",
        ]

    def _risk_plan(self, ctx: "_CardContext") -> list[str]:
        plan = self._risk_state(ctx)
        tp2 = plan["tp2"] if plan["sl_valid"] else np.nan
        tp3 = plan["tp3"] if plan["sl_valid"] else np.nan
        oneil_low = plan["oneil_low"] if plan["sl_valid"] else np.nan
        oneil_high = plan["oneil_high"] if plan["sl_valid"] else np.nan
        measured = plan["measured"] if plan["sl_valid"] else np.nan
        return [
            f"## RISK_PLAN (basis: {plan['basis_text']})",
            f"SL_VALID={self._yn(plan['sl_valid'])} SIZE_BUCKET={self._text(ctx.latest.get('ema21_low_size_bucket'))} ATR_LO_EMA21L={self._one(ctx.latest.get('atr_low_to_ema21_low'))} ATR_LO_EMA21H={self._one(ctx.latest.get('atr_low_to_ema21_high'))}",
            f"SL_CAND: struct={plan['struct']} atr2={self._price(plan['atr2'])}({self._fmt_pct(plan['atr2_pct'])}) cap8={self._price(plan['cap8'])}(-8.0%)",
            f"TP_CAND: 2R={self._price(tp2)} 3R={self._price(tp3)} oneil={self._price(oneil_low)}..{self._price(oneil_high)} measured={self._price(measured)}",
            f"TRAIL_REF: EMA21={self._price(ctx.ema21)} SMA50={self._price(ctx.sma50)}",
            f"CHECKS=C_MATCH:OK;VLAST_OK:OK;SL_VALID:{self._yn(plan['sl_valid'])};DATE_MATCH:Y",
        ]

    def _trend_template(self, ctx: "_CardContext") -> tuple[int, int, list[int]]:
        checks = [
            self._is_num(ctx.sma150) and self._is_num(ctx.sma200) and ctx.close > ctx.sma150 and ctx.close > ctx.sma200,
            self._is_num(ctx.sma150) and self._is_num(ctx.sma200) and ctx.sma150 > ctx.sma200,
            self._is_num(ctx.sma200_slope) and ctx.sma200_slope > 0.0,
            self._is_num(ctx.sma50) and self._is_num(ctx.sma150) and self._is_num(ctx.sma200) and ctx.sma50 > ctx.sma150 and ctx.sma50 > ctx.sma200,
            self._is_num(ctx.sma50) and ctx.close > ctx.sma50,
            self._is_num(self._dist_from_low(ctx)) and self._dist_from_low(ctx) >= 0.30,
            self._is_num(self._dist_from_high(ctx)) and self._dist_from_high(ctx) >= -0.25,
        ]
        if ctx.metadata.rs_pctl is not None and self._is_num(ctx.metadata.rs_pctl):
            checks.append(float(ctx.metadata.rs_pctl) >= 70.0)
        fail = [idx for idx, ok in enumerate(checks, start=1) if not ok]
        return len(checks) - len(fail), len(checks), fail

    def _setup_state(self, ctx: "_CardContext") -> dict[str, object]:
        pivot, pivot_date = self._pivot(ctx)
        base_depth, base_len, below_high = self._base(ctx)
        depths = self._depths(ctx)
        depth_contraction = len(depths) >= 2 and all(depths[i] > depths[i + 1] for i in range(len(depths) - 1))
        strict_vcp = bool(ctx.latest.get("vcp_tightening", False)) if pd.notna(ctx.latest.get("vcp_tightening", pd.NA)) else False
        candidates: list[str] = []
        basis: dict[str, float] = {}
        pivot_breakout = self._is_pivot_breakout_setup(ctx, pivot_date, base_len, base_depth, below_high)
        if pivot_breakout:
            candidates.append("PIVOT_BREAKOUT")
            basis["PIVOT_BREAKOUT"] = self._buy_price(pivot)
        reclaim = self._reclaim_ref(ctx, pivot)
        if reclaim is not None:
            candidates.append("RECLAIM")
            basis["RECLAIM"] = self._buy_price(reclaim[1])
        ur = self._ur_ref(ctx)
        if ur is not None:
            candidates.append("UR")
            basis["UR"] = self._buy_price(ur[1])
        pullback = self._pullback_ref(ctx)
        if pullback is not None and not pivot_breakout:
            candidates.append("PULLBACK")
            basis["PULLBACK"] = self._buy_price(pullback[1])
        candidates = [candidate for candidate in candidates if not self._is_expired_candidate(ctx, candidate, basis.get(candidate))]
        basis = {candidate: value for candidate, value in basis.items() if candidate in candidates}
        return {
            "candidates": candidates or ["NONE"],
            "basis": basis,
            "vcp": "Y" if strict_vcp else "N",
            "vcp_depth_contraction": depth_contraction,
            "depths": "[" + ",".join(self._one(value) for value in depths) + "]",
            "depth_values": depths,
            "base_depth": base_depth,
            "base_len": base_len,
            "below_high": below_high,
            "pullback_ref": "NA" if pullback is None else f"{pullback[3].strftime('%m%d')}({self._price(pullback[2])})",
            "ur_ref": "NA" if ur is None else f"{ur[0].strftime('%m%d')}({self._price(ur[2])})",
        }

    def _risk_state(self, ctx: "_CardContext") -> dict[str, object]:
        setup = self._setup_state(ctx)
        pivot, _ = self._pivot(ctx)
        first = next((candidate for candidate in setup["candidates"] if candidate != "NONE"), "NONE")
        basis_map = setup["basis"]
        buy = self._buy_price(pivot)
        basis = float(basis_map.get(first, buy if self._is_num(buy) else self._display_price_value(ctx.close)))
        basis_text = f"BUY={self._price(basis)}(ref)" if first == "NONE" else f"{'BUY' if first == 'PIVOT_BREAKOUT' else first}={self._price(basis)}"
        struct_price, struct_date, struct_source_low = self._struct_stop(ctx, basis)
        atr = self._display_price_value(ctx.atr)
        atr2 = self._round(basis - 2.0 * atr, 2) if self._is_num(atr) else np.nan
        cap8 = self._round(basis * 0.92, 2)
        sl_first = struct_price if self._is_num(struct_price) else atr2
        risk = self._round(basis - sl_first, 2) if self._is_num(sl_first) else np.nan
        min_distance = self._struct_stop_min_distance(ctx, basis)
        base_depth, _, _ = self._base(ctx)
        pivot_display = self._display_price_value(pivot)
        base_depth_display = self._round(base_depth, 1) if self._is_num(base_depth) else np.nan
        return {
            "basis_text": basis_text,
            "basis": basis,
            "struct_value": struct_price,
            "struct_date": struct_date,
            "struct_source_low": struct_source_low,
            "struct_min_distance": min_distance,
            "struct_min_distance_atr_floor": atr if self._is_num(atr) else np.nan,
            "struct_min_distance_pct_floor": basis * 0.025,
            "struct": "NA"
            if not self._is_num(struct_price)
            else f"{self._price(struct_price)}({struct_date.strftime('%m%d')}lo-,{self._fmt_pct(struct_price / basis - 1.0)})",
            "atr2": atr2,
            "atr2_pct": atr2 / basis - 1.0 if self._is_num(atr2) else np.nan,
            "cap8": cap8,
            "risk": risk,
            "sl_valid": self._is_num(sl_first) and self._is_num(risk) and risk > 0.0 and sl_first >= cap8 and sl_first < basis,
            "tp2": self._round(basis + 2.0 * risk, 2) if self._is_num(risk) else np.nan,
            "tp3": self._round(basis + 3.0 * risk, 2) if self._is_num(risk) else np.nan,
            "oneil_low": self._round(basis * 1.20, 2),
            "oneil_high": self._round(basis * 1.25, 2),
            "measured": self._round(pivot_display * (1.0 + base_depth_display / 100.0), 2)
            if self._is_num(pivot_display) and self._is_num(base_depth_display)
            else np.nan,
        }

    def _payload(self, ctx: "_CardContext") -> dict[str, object]:
        setup = self._setup_state(ctx)
        risk = self._risk_state(ctx)
        tt_pass, tt_total, fail_items = self._trend_template(ctx)
        pivot, pivot_date = self._pivot(ctx)
        buy = self._buy_price(pivot)
        acc50, dist50 = self._acc_dist(ctx)
        pullback = self._pullback_ref(ctx)
        ur = self._ur_ref(ctx)
        atr_pct = ctx.atr / ctx.close * 100.0 if self._is_num(ctx.atr) and ctx.close else np.nan
        p_vs_150 = ctx.close / ctx.sma150 - 1.0 if self._is_num(ctx.sma150) else np.nan
        slope150 = self._slope150(ctx)
        payload = {
            "document_type": "stock_card",
            "schema_version": "stock_card_json.v1",
            "markdown_schema_version": SCHEMA_VERSION,
            "ticker": ctx.ticker,
            "trade_date": ctx.end.strftime("%Y-%m-%d"),
            "data": {
                "start_date": ctx.start.strftime("%Y-%m-%d"),
                "end_date": ctx.end.strftime("%Y-%m-%d"),
                "row_count": int(len(ctx.source)),
                "adjusted": bool(ctx.adjusted),
            },
            "meta": {
                "sector_etf": self._json_text(ctx.metadata.sector_etf),
                "industry_etf": self._json_text(ctx.metadata.industry_etf),
                "industry_rs_rank": self._json_number(ctx.metadata.industry_rs_rank),
                "rs_pctl": self._json_number(ctx.metadata.rs_pctl),
            },
            "decision_core": {
                "overall_gate": self._overall_gate(ctx),
                "ext_atr50": self._json_number(ctx.latest.get("atr_50sma_zone")),
                "ext_atr50_min5": self._json_number(ctx.latest.get("min_atr_50sma_zone_5d")),
                "sl_valid": bool(risk["sl_valid"]),
                "setup_candidates": setup["candidates"],
                "rs_hi52": self._json_bool(ctx.metadata.rs_hi52),
                "rs_hi3y": self._json_bool(ctx.metadata.rs_hi3y),
                "size_bucket": self._json_text(ctx.latest.get("ema21_low_size_bucket")),
            },
            "gates": {
                "trend_template_pass_count": tt_pass,
                "trend_template_total_count": tt_total,
                "trend_template_fail_items": fail_items,
                "ext_pct_vs_sma50": self._json_number(ctx.close / ctx.sma50 - 1.0 if self._is_num(ctx.sma50) else np.nan),
                "ext_atr50": self._json_number(ctx.latest.get("atr_50sma_zone")),
                "ext_atr50_min5": self._json_number(ctx.latest.get("min_atr_50sma_zone_5d")),
                "volume_quality": {
                    "ud25": self._json_number(self._ud_ratio(ctx, 25)),
                    "acc50": acc50,
                    "dist50": dist50,
                },
            },
            "trend": {
                "stage": self._stage(ctx),
                "stage_label": self._json_text(ctx.latest.get("stage_label")),
                "stage2_quality_score": self._json_number(ctx.metadata.stage2_quality_score),
                "late_stage": self._json_bool(ctx.metadata.mature_late_stage_risk),
                "stage2_age": self._json_number(ctx.latest.get("days_since_stage2_start")),
                "base_days_3m": self._json_number(ctx.latest.get("stage_base_days_3m")),
                "sma50": self._json_number(ctx.sma50),
                "sma150": self._json_number(ctx.sma150),
                "sma200": self._json_number(ctx.sma200),
                "p_vs_150sma": self._json_number(p_vs_150),
                "slope150_pct_per_day": self._json_number(slope150),
                "sma200_slope_1m_pct": self._json_number(ctx.sma200_slope),
            },
            "relative_strength": {
                "rs_pctl": self._json_number(ctx.metadata.rs_pctl),
                "rs21": self._json_number(ctx.metadata.rs21),
                "rs63": self._json_number(ctx.metadata.rs63),
                "rs126": self._json_number(ctx.metadata.rs126),
                "rs_hi52": self._json_bool(ctx.metadata.rs_hi52),
                "rs_hi3y": self._json_bool(ctx.metadata.rs_hi3y),
            },
            "momo_vol": {
                "m12_1": self._json_number(self._momentum_12_1(ctx)),
                "returns": {
                    "1m": self._json_number(self._return(ctx, 21)),
                    "3m": self._json_number(self._return(ctx, 63)),
                    "6m": self._json_number(self._return(ctx, 126)),
                    "12m": self._json_number(self._return(ctx, 252)),
                },
                "atr14": self._json_number(ctx.atr),
                "atr14_pct": self._json_number(atr_pct),
                "rv20": self._json_number(self._realized_vol(ctx)),
            },
            "volume": {
                "v50": self._json_number(ctx.v50),
                "vlast": self._json_number(ctx.vlast),
                "dryup5_50": self._json_number(self._dryup(ctx)),
                "acc50": acc50,
                "dist50": dist50,
                "ud25": self._json_number(self._ud_ratio(ctx, 25)),
            },
            "setup": {
                "candidates": setup["candidates"],
                "vcp": setup["vcp"] == "Y",
                "vcp_definition": "vcp_tightening",
                "vcp_depth_contraction": bool(setup["vcp_depth_contraction"]),
                "depths": [self._json_number(value) for value in setup["depth_values"]],
                "base_depth_pct": self._json_number(setup["base_depth"]),
                "base_length_days": setup["base_len"],
                "below_high_pct": self._json_number(setup["below_high"]),
                "pocket_pivot": self._json_bool(ctx.latest.get("pocket_pivot")),
                "pp_count": self._json_number(ctx.latest.get("pp_count_window")),
                "three_weeks_tight": self._json_bool(ctx.latest.get("three_weeks_tight")),
                "power_gap_pct": self._json_number(ctx.latest.get("power_gap_up_pct")),
                "power_gap_age_days": self._json_number(ctx.latest.get("days_since_power_gap")),
                "pb_atr21": self._json_number(ctx.latest.get("atr_21ema_zone")),
                "pb_atr21l": self._json_number(ctx.latest.get("atr_21emaL_zone")),
                "crossed_above_ema21": self._json_bool(ctx.latest.get("close_crossed_above_ema21")),
                "crossed_above_sma50": self._json_bool(ctx.latest.get("close_crossed_above_sma50")),
                "adr_recent_pct": self._json_number(ctx.latest.get("vcp_adr_recent_pct")),
                "adr_base_pct": self._json_number(ctx.latest.get("vcp_adr_base_pct")),
                "adr_contract": self._json_bool(ctx.latest.get("vcp_is_contracting")),
                "vcs": self._json_number(ctx.metadata.vcs),
                "tight_days": self._json_number(ctx.latest.get("vcp_tight_days")),
                "prior_up_pct": self._json_number(ctx.latest.get("vcp_prior_uptrend_pct")),
                "pullback_ref": self._pullback_payload(pullback),
                "ur_ref": self._ur_payload(ur),
            },
            "levels": {
                "close": self._json_number(ctx.close),
                "pivot": self._json_number(pivot),
                "pivot_date": pivot_date.strftime("%Y-%m-%d"),
                "buy": self._json_number(buy),
                "high_52w": self._json_number(ctx.hi52),
                "low_52w": self._json_number(ctx.lo52),
                "swlo10": self._json_number(self._swlo(ctx, 10)),
                "swlo20": self._json_number(self._swlo(ctx, 20)),
                "ema21": self._json_number(ctx.ema21),
                "sma50": self._json_number(ctx.sma50),
                "structure_anchors": self._struct_anchors(ctx, buy),
                "body_ratio": self._json_number(ctx.latest.get("breakout_body_ratio")),
                "dcr_percent": self._json_number(ctx.latest.get("dcr_percent")),
                "resistance_test_count": self._json_number(ctx.latest.get("resistance_test_count")),
            },
            "risk_plan": {
                "basis": self._json_number(risk["basis"]),
                "basis_text": str(risk["basis_text"]),
                "sl_valid": bool(risk["sl_valid"]),
                "struct_stop": self._json_number(risk["struct_value"]),
                "struct_stop_date": risk["struct_date"].strftime("%Y-%m-%d") if isinstance(risk["struct_date"], pd.Timestamp) and self._is_num(risk["struct_value"]) else None,
                "struct_stop_source": {
                    "kind": "swing_low_65d",
                    "source_low": self._json_number(risk["struct_source_low"]),
                    "stop_multiplier": 0.999,
                    "min_distance": self._json_number(risk["struct_min_distance"]),
                    "min_distance_atr_floor": self._json_number(risk["struct_min_distance_atr_floor"]),
                    "min_distance_pct_floor": self._json_number(risk["struct_min_distance_pct_floor"]),
                },
                "atr2_stop": self._json_number(risk["atr2"]),
                "cap8_stop": self._json_number(risk["cap8"]),
                "targets": {
                    "tp2": self._json_number(risk["tp2"]) if risk["sl_valid"] else None,
                    "tp3": self._json_number(risk["tp3"]) if risk["sl_valid"] else None,
                    "oneil_low": self._json_number(risk["oneil_low"]) if risk["sl_valid"] else None,
                    "oneil_high": self._json_number(risk["oneil_high"]) if risk["sl_valid"] else None,
                    "measured": self._json_number(risk["measured"]) if risk["sl_valid"] else None,
                },
                "size_bucket": self._json_text(ctx.latest.get("ema21_low_size_bucket")),
                "atr_low_to_ema21_low": self._json_number(ctx.latest.get("atr_low_to_ema21_low")),
                "atr_low_to_ema21_high": self._json_number(ctx.latest.get("atr_low_to_ema21_high")),
            },
            "checks": {
                "c_match": "OK",
                "vlast_ok": "OK",
                "sl_valid": "Y" if risk["sl_valid"] else "N",
                "date_match": "Y",
            },
            "compressed_tape": self._tape_payload(ctx),
        }
        return payload

    def _validate(self, ctx: "_CardContext", text: str) -> None:
        sections = ["## META", "## GATES", "## TREND", "## MOMO_VOL", "## VOLUME", "## LEVELS", "## SETUP", "## RISK_PLAN", "## TAPE"]
        positions = [text.find(section) for section in sections]
        if any(position < 0 for position in positions) or positions != sorted(positions):
            raise StockCardError(f"{ctx.ticker}: stock card section order is invalid")
        tape_last = [line for line in ctx.tape_text.splitlines() if "|" in line and not line.startswith("MMDD|")][-1].split("|")
        if self._price(ctx.close) != tape_last[4]:
            raise StockCardError(f"{ctx.ticker}: LEVELS.C does not match TAPE last close")
        if self._int(ctx.v50) not in ctx.tape_text.splitlines()[1]:
            raise StockCardError(f"{ctx.ticker}: VOLUME.V50 does not match TAPE header")
        if self._int(ctx.vlast) != tape_last[7]:
            raise StockCardError(f"{ctx.ticker}: VOLUME.VLAST does not match TAPE last v")
        pivot, _ = self._pivot(ctx)
        buy_text = f"BUY={self._price(self._buy_price(pivot))}"
        if buy_text not in text:
            raise StockCardError(f"{ctx.ticker}: BUY does not match display pivot x 1.001")
        risk_state = self._risk_state(ctx)
        basis = float(risk_state["basis"])
        atr = self._display_price_value(ctx.atr)
        expected_atr2 = self._round(basis - 2.0 * atr, 2) if self._is_num(atr) else np.nan
        expected_cap8 = self._round(basis * 0.92, 2)
        if self._price(risk_state["atr2"]) != self._price(expected_atr2) or self._price(risk_state["cap8"]) != self._price(expected_cap8):
            raise StockCardError(f"{ctx.ticker}: risk plan SL candidates do not match display-value inputs")
        sl_first = float(risk_state["struct_value"]) if self._is_num(risk_state["struct_value"]) else expected_atr2
        expected_risk = self._round(basis - sl_first, 2) if self._is_num(sl_first) else np.nan
        expected_tp2 = self._round(basis + 2.0 * expected_risk, 2) if self._is_num(expected_risk) else np.nan
        expected_tp3 = self._round(basis + 3.0 * expected_risk, 2) if self._is_num(expected_risk) else np.nan
        if self._price(risk_state["tp2"]) != self._price(expected_tp2) or self._price(risk_state["tp3"]) != self._price(expected_tp3):
            raise StockCardError(f"{ctx.ticker}: risk plan TP candidates do not match display-value inputs")
        expected_oneil_low = self._round(basis * 1.20, 2)
        expected_oneil_high = self._round(basis * 1.25, 2)
        pivot_display = self._display_price_value(pivot)
        base_depth, _, _ = self._base(ctx)
        base_depth_display = self._round(base_depth, 1) if self._is_num(base_depth) else np.nan
        expected_measured = (
            self._round(pivot_display * (1.0 + base_depth_display / 100.0), 2)
            if self._is_num(pivot_display) and self._is_num(base_depth_display)
            else np.nan
        )
        if (
            self._price(risk_state["oneil_low"]) != self._price(expected_oneil_low)
            or self._price(risk_state["oneil_high"]) != self._price(expected_oneil_high)
            or self._price(risk_state["measured"]) != self._price(expected_measured)
        ):
            raise StockCardError(f"{ctx.ticker}: risk plan target candidates do not match display-value inputs")
        expected_atr2_pct = self._fmt_pct(expected_atr2 / basis - 1.0) if self._is_num(expected_atr2) else "NA"
        if f"atr2={self._price(expected_atr2)}({expected_atr2_pct})" not in text:
            raise StockCardError(f"{ctx.ticker}: risk plan deviation percent does not match display-value inputs")
        if self._is_num(risk_state["struct_value"]):
            expected_struct_pct = self._fmt_pct(float(risk_state["struct_value"]) / basis - 1.0)
            if expected_struct_pct not in str(risk_state["struct"]):
                raise StockCardError(f"{ctx.ticker}: struct deviation percent does not match display-value inputs")
        setup = self._setup_state(ctx)
        expired = [
            candidate
            for candidate, basis in setup["basis"].items()
            if self._is_expired_candidate(ctx, candidate, basis)
        ]
        if expired:
            raise StockCardError(f"{ctx.ticker}: expired setup candidates were rendered")
        struct_price, _, _ = self._struct_stop(ctx, float(risk_state["basis"]))
        if self._is_num(struct_price):
            distance = basis - struct_price
            min_distance = self._struct_stop_min_distance(ctx, basis)
            if distance < min_distance or struct_price < self._round(basis * 0.92, 2):
                raise StockCardError(f"{ctx.ticker}: struct stop violates distance floor")

    def _stage(self, ctx: "_CardContext") -> str:
        label = str(ctx.latest.get("stage_label", "")).lower()
        if label == "stage2_candidate":
            return "Stage2"
        if label == "stage_base_or_transition":
            return "Stage1-2"
        if label == "stage4_avoid":
            return "Stage4"
        return "NA"

    def _pivot(self, ctx: "_CardContext") -> tuple[float, pd.Timestamp]:
        window = ctx.source.tail(min(65, len(ctx.source)))
        idx = window["high"].idxmax()
        return float(window.loc[idx, "high"]), pd.Timestamp(idx)

    def _base(self, ctx: "_CardContext") -> tuple[float, int, float]:
        window = ctx.source.tail(min(65, len(ctx.source)))
        high = float(window["high"].max())
        low = float(window["low"].min())
        depth = (high - low) / high * 100.0 if high else np.nan
        below = (high - ctx.close) / high * 100.0 if high else np.nan
        return depth, len(window), below

    def _depths(self, ctx: "_CardContext") -> list[float]:
        windows = [30, 20, 10, 5]
        depths: list[float] = []
        for length in windows:
            if len(ctx.source) < length:
                continue
            window = ctx.source.tail(length)
            high = float(window["high"].max())
            low = float(window["low"].min())
            if high:
                depths.append((high - low) / high * 100.0)
        return depths[-4:]

    def _reclaim_ref(self, ctx: "_CardContext", pivot: float) -> tuple[pd.Timestamp, float] | None:
        candidates: list[tuple[pd.Timestamp, float]] = []
        daily_pivot = ctx.source["high"].shift(1).rolling(65, min_periods=1).max()
        for level_series in [daily_pivot, ctx.indicators["sma50"]]:
            closes = ctx.source["close"]
            crossed = (closes > level_series) & (closes.shift(1) <= level_series.shift(1))
            for idx in crossed.tail(10).loc[lambda value: value].index:
                pos = ctx.source.index.get_loc(idx)
                if pos + 1 < len(ctx.source) and bool((closes.iloc[pos + 1 :] > level_series.iloc[pos + 1 :]).all()):
                    candidates.append((pd.Timestamp(idx), float(ctx.source.loc[idx, "high"])))
        return candidates[-1] if candidates else None

    def _ur_ref(self, ctx: "_CardContext") -> tuple[pd.Timestamp, float, float] | None:
        recent = ctx.metrics.tail(5)
        rows = [(pd.Timestamp(idx), float(row["high"]), float(row["low"])) for idx, row in recent.iterrows() if "U" in str(row["flags"])]
        return rows[-1] if rows else None

    def _pullback_ref(self, ctx: "_CardContext") -> tuple[pd.Timestamp, float, float, pd.Timestamp] | None:
        if self._stage(ctx) != "Stage2":
            return None
        recent = ctx.source.tail(5)
        candidates: list[tuple[pd.Timestamp, float, float, pd.Timestamp]] = []
        for idx, row in recent.iterrows():
            ema = float(ctx.indicators.loc[idx, "ema21_close"])
            sma = float(ctx.indicators.loc[idx, "sma50"])
            low = float(row["low"])
            touched = (self._is_num(ema) and abs(low / ema - 1.0) <= 0.02) or (self._is_num(sma) and abs(low / sma - 1.0) <= 0.02)
            if not touched:
                continue
            tail = ctx.metrics.loc[idx:]
            reversal = tail[(tail["close"] > tail["open"]) & (tail["pos"] >= 50)]
            if not reversal.empty:
                rev_idx = pd.Timestamp(reversal.index[-1])
                zone = ctx.source.loc[idx:rev_idx].iloc[:-1]
                if zone.empty:
                    pullback_low = low
                    pullback_low_date = pd.Timestamp(idx)
                else:
                    pullback_low_date = pd.Timestamp(zone["low"].idxmin())
                    pullback_low = float(zone.loc[pullback_low_date, "low"])
                candidates.append((rev_idx, float(ctx.source.loc[rev_idx, "high"]), pullback_low, pullback_low_date))
        return candidates[-1] if candidates else None

    def _is_pivot_breakout_setup(
        self,
        ctx: "_CardContext",
        pivot_date: pd.Timestamp,
        base_len: int,
        base_depth: float,
        below_high: float,
    ) -> bool:
        classic_base = (
            base_len >= 25
            and self._is_num(base_depth)
            and base_depth <= 35.0
            and self._is_num(below_high)
            and below_high <= 5.0
        )
        if classic_base:
            return True
        if pd.Timestamp(pivot_date).normalize() != ctx.end.normalize() or len(ctx.source) < 2:
            return False
        prior_window = ctx.source.iloc[:-1].tail(min(65, len(ctx.source) - 1))
        if prior_window.empty:
            return False
        prior_high = float(prior_window["high"].max())
        current_close = self._display_price_value(ctx.close)
        return bool(self._is_num(current_close) and current_close > self._display_price_value(prior_high))

    def _struct_stop(self, ctx: "_CardContext", basis: float) -> tuple[float, pd.Timestamp, float]:
        lows = ctx.source["low"].tail(65).dropna()
        min_distance = self._struct_stop_min_distance(ctx, basis)
        cap8 = self._round(basis * 0.92, 2)
        candidates: list[tuple[float, pd.Timestamp, float]] = []
        for pos, (idx, low) in enumerate(lows.items()):
            display_low = self._display_price_value(low)
            if not self._is_num(display_low):
                continue
            if not self._is_surviving_swing_low(lows, pos, display_low):
                continue
            stop = self._round(display_low * 0.999, 2)
            if stop <= basis - min_distance and stop >= cap8:
                candidates.append((stop, pd.Timestamp(idx), display_low))
        if not candidates:
            return np.nan, ctx.end, np.nan
        return max(candidates, key=lambda item: item[0])

    def _is_surviving_swing_low(self, lows: pd.Series, pos: int, display_low: float, *, k: int = 2) -> bool:
        if not self._is_swing_low(lows, pos, display_low, k=k):
            return False
        future = [self._display_price_value(value) for value in lows.iloc[pos + 1 :]]
        return all(not self._is_num(value) or value >= display_low for value in future)

    def _is_swing_low(self, lows: pd.Series, pos: int, display_low: float, *, k: int = 2) -> bool:
        if pos <= 0 or pos >= len(lows) - 1:
            return False
        left = [self._display_price_value(value) for value in lows.iloc[max(0, pos - k) : pos]]
        right = [self._display_price_value(value) for value in lows.iloc[pos + 1 : min(len(lows), pos + k + 1)]]
        left = [value for value in left if self._is_num(value)]
        right = [value for value in right if self._is_num(value)]
        if not left or not right:
            return False
        full_fractal = len(left) >= k and len(right) >= k and display_low < min(left) and display_low <= min(right)
        recent_reversal = pos + k >= len(lows) and display_low < left[-1] and display_low <= min(right)
        return bool(full_fractal or recent_reversal)

    def _struct_stop_min_distance(self, ctx: "_CardContext", basis: float) -> float:
        atr = self._display_price_value(ctx.atr)
        atr_floor = atr if self._is_num(atr) else 0.0
        pct_floor = basis * 0.025
        return max(atr_floor, pct_floor)

    def _is_expired_candidate(self, ctx: "_CardContext", candidate: str, basis: object) -> bool:
        if candidate == "PIVOT_BREAKOUT" or not self._is_num(basis):
            return False
        close = self._display_price_value(ctx.close)
        return bool(self._is_num(close) and close > float(basis) * 1.02)

    def _dist_from_high(self, ctx: "_CardContext") -> float:
        return ctx.close / ctx.hi52 - 1.0 if self._is_num(ctx.hi52) and ctx.hi52 else np.nan

    def _dist_from_low(self, ctx: "_CardContext") -> float:
        return ctx.close / ctx.lo52 - 1.0 if self._is_num(ctx.lo52) and ctx.lo52 else np.nan

    def _slope150(self, ctx: "_CardContext") -> float:
        series = ctx.indicators["sma150"].dropna().tail(30)
        if len(series) < 2:
            return np.nan
        x = np.arange(len(series), dtype=float)
        slope = float(np.polyfit(x, series.to_numpy(dtype=float), 1)[0])
        base = float(series.iloc[-1])
        return slope / base * 100.0 if base else np.nan

    def _return(self, ctx: "_CardContext", periods: int) -> float:
        close = ctx.source["close"]
        if len(close) <= periods:
            return np.nan
        return float(close.iloc[-1] / close.iloc[-periods - 1] - 1.0)

    def _momentum_12_1(self, ctx: "_CardContext") -> float:
        close = ctx.source["close"]
        if len(close) <= 252:
            return np.nan
        return float(close.iloc[-22] / close.iloc[-253] - 1.0)

    def _realized_vol(self, ctx: "_CardContext") -> float:
        returns = ctx.source["close"].pct_change(fill_method=None).dropna().tail(20)
        return float(returns.std(ddof=0) * np.sqrt(252.0)) if len(returns) >= 2 else np.nan

    def _dryup(self, ctx: "_CardContext") -> float:
        return float(ctx.source["volume"].tail(5).mean() / ctx.v50) if self._is_num(ctx.v50) and ctx.v50 else np.nan

    def _acc_dist(self, ctx: "_CardContext") -> tuple[int, int]:
        recent = ctx.metrics.tail(50)
        volume_ratio = pd.to_numeric(recent["v"], errors="coerce").fillna(0.0)
        acc = int(((recent["pos"] >= 80) & (volume_ratio > 140.0)).sum())
        dist = int(((recent["pos"] <= 20) & (volume_ratio > 140.0)).sum())
        return acc, dist

    def _ud_ratio(self, ctx: "_CardContext", periods: int) -> float:
        recent = ctx.source.tail(periods + 1)
        previous = recent["close"].shift(1)
        up = recent["volume"].where(recent["close"] >= previous, 0.0).iloc[1:].sum()
        down = recent["volume"].where(recent["close"] < previous, 0.0).iloc[1:].sum()
        return float(up / max(down, 1.0))

    def _swlo(self, ctx: "_CardContext", periods: int) -> float:
        return float(ctx.source["low"].tail(periods).min()) if len(ctx.source) >= periods else np.nan

    def _pullback_payload(self, value: tuple[pd.Timestamp, float, float, pd.Timestamp] | None) -> dict[str, object] | None:
        if value is None:
            return None
        trigger_date, trigger_high, pullback_low, pullback_low_date = value
        return {
            "trigger_date": pd.Timestamp(trigger_date).strftime("%Y-%m-%d"),
            "trigger_high": self._json_number(trigger_high),
            "pullback_low": self._json_number(pullback_low),
            "pullback_low_date": pd.Timestamp(pullback_low_date).strftime("%Y-%m-%d"),
        }

    def _ur_payload(self, value: tuple[pd.Timestamp, float, float] | None) -> dict[str, object] | None:
        if value is None:
            return None
        date, high, low = value
        return {
            "date": pd.Timestamp(date).strftime("%Y-%m-%d"),
            "high": self._json_number(high),
            "low": self._json_number(low),
        }

    def _tape_payload(self, ctx: "_CardContext") -> dict[str, object]:
        lines = ctx.tape_text.rstrip().splitlines()
        period_line = next((line for line in lines if line.startswith("PERIOD:")), "")
        rows: list[dict[str, object]] = []
        events: list[str] = []
        in_rows = False
        in_events = False
        for line in lines:
            if line.startswith("MMDD|"):
                in_rows = True
                in_events = False
                continue
            if line.startswith("## EVENTS_50D"):
                in_rows = False
                in_events = True
                continue
            if in_rows and "|" in line:
                parts = line.split("|")
                if len(parts) != 9:
                    continue
                rows.append(
                    {
                        "date": self._tape_row_date(parts[0], ctx.end),
                        "open": self._json_number(parts[1]),
                        "high": self._json_number(parts[2]),
                        "low": self._json_number(parts[3]),
                        "close": self._json_number(parts[4]),
                        "cc_pct": self._json_number(parts[5]),
                        "pos": self._json_number(parts[6]),
                        "volume_ratio_pct": self._json_number(parts[7]),
                        "flags": parts[8],
                    }
                )
            elif in_events and line:
                events.append(line)
        return {
            "schema_version": "tape-v1.0.1",
            "period": period_line.removeprefix("PERIOD:").strip() if period_line else None,
            "rows": rows,
            "events_50d": events,
        }

    def _tape_row_date(self, value: str, end: pd.Timestamp) -> str:
        text = str(value).strip()
        if "-" in text:
            parsed = pd.to_datetime(text, errors="coerce")
            return text if pd.isna(parsed) else pd.Timestamp(parsed).strftime("%Y-%m-%d")
        if len(text) == 4 and text.isdigit():
            month = int(text[:2])
            day = int(text[2:])
            year = pd.Timestamp(end).year
            candidate = pd.Timestamp(year=year, month=month, day=day)
            if candidate > pd.Timestamp(end).normalize():
                candidate = pd.Timestamp(year=year - 1, month=month, day=day)
            return candidate.strftime("%Y-%m-%d")
        return text

    def _overall_gate(self, ctx: "_CardContext") -> str:
        short = len(ctx.source) < 200
        if short:
            return "FAIL_SHORT"
        stage = self._stage(ctx)
        tt_pass, _, _ = self._trend_template(ctx)
        hi_dist = self._dist_from_high(ctx)
        lo_dist = self._dist_from_low(ctx)
        ext = ctx.close / ctx.sma50 - 1.0 if self._is_num(ctx.sma50) else np.nan
        ud25 = self._ud_ratio(ctx, 25)
        acc50, dist50 = self._acc_dist(ctx)
        gates = [
            "PASS" if stage == "Stage2" else "COND" if stage == "Stage1-2" else "FAIL",
            "PASS" if tt_pass >= 6 else "COND" if tt_pass == 5 else "FAIL",
            "PASS" if self._is_num(hi_dist) and self._is_num(lo_dist) and hi_dist >= -0.25 and lo_dist >= 0.30 else "FAIL",
            "PASS" if self._is_num(ext) and ext < 0.25 else "FAIL",
            "PASS" if (self._is_num(ud25) and ud25 >= 0.8) or acc50 >= dist50 else "COND",
        ]
        if "FAIL" in gates:
            return "FAIL"
        if "COND" in gates:
            return "COND"
        return "PASS"

    def _struct_anchors_text(self, ctx: "_CardContext", basis: object) -> str:
        anchors = self._struct_anchors(ctx, basis)
        parts = []
        for key in ("HL", "LL", "P1", "P2"):
            item = anchors[key]
            price = item["price"]
            pct = item["pct_from_basis"]
            parts.append(f"{key}={self._price(price)}({self._fmt_pct(pct)})")
        return ",".join(parts)

    def _struct_anchors(self, ctx: "_CardContext", basis: object) -> dict[str, dict[str, float | None]]:
        basis_value = self._display_price_value(basis)
        sources = {
            "HL": ctx.latest.get("structure_pivot_long_hl_price", np.nan),
            "LL": ctx.latest.get("structure_pivot_long_ll_price", np.nan),
            "P1": ctx.latest.get("structure_pivot_1st_pivot", np.nan),
            "P2": ctx.latest.get("structure_pivot_2nd_pivot", np.nan),
        }
        result: dict[str, dict[str, float | None]] = {}
        for key, value in sources.items():
            price = self._json_number(value)
            pct = None
            if price is not None and self._is_num(basis_value) and basis_value != 0.0:
                pct = float(price) / float(basis_value) - 1.0
            result[key] = {"price": price, "pct_from_basis": pct}
        return result

    def _price(self, value: object) -> str:
        return "NA" if not self._is_num(value) else f"{self._round(float(value), 2):.2f}"

    def _one(self, value: object) -> str:
        return "NA" if not self._is_num(value) else f"{self._round(float(value), 1):.1f}"

    def _fmt_pct(self, value: object, *, digits: int = 1) -> str:
        if not self._is_num(value):
            return "NA"
        return f"{self._round(float(value) * 100.0, digits):+.{digits}f}%"

    def _fmt_abs_pct(self, value: object) -> str:
        return "NA" if not self._is_num(value) else f"{self._round(float(value), 1):.1f}%"

    def _fmt_percent_value(self, value: object, *, digits: int = 1) -> str:
        if not self._is_num(value):
            return "NA"
        return f"{self._round(float(value), digits):+.{digits}f}%"

    def _fmt_unsigned_percent_value(self, value: object, *, digits: int = 1) -> str:
        if not self._is_num(value):
            return "NA"
        return f"{abs(self._round(float(value), digits)):.{digits}f}%"

    def _fmt_unsigned_pct(self, value: object, *, digits: int = 1) -> str:
        if not self._is_num(value):
            return "NA"
        return f"{abs(self._round(float(value) * 100.0, digits)):.{digits}f}%"

    def _rank(self, value: object) -> str:
        return "NA" if not self._is_num(value) else str(int(self._round(float(value), 0)))

    def _int(self, value: object) -> str:
        return "NA" if not self._is_num(value) else str(int(self._round(float(value), 0)))

    def _ratio(self, value: object) -> str:
        return "NA" if not self._is_num(value) else f"{self._round(float(value), 2):.2f}"

    def _pct_value(self, value: object) -> str:
        return "NA" if not self._is_num(value) else f"{self._round(float(value), 1):+.1f}%"

    def _days(self, value: object) -> str:
        return "NA" if not self._is_num(value) else f"{int(self._round(float(value), 0))}d"

    def _yn(self, value: object) -> str:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return "NA"
        return "Y" if bool(value) else "N"

    def _mmdd(self, value: pd.Timestamp | None) -> str:
        return "NA" if value is None else pd.Timestamp(value).strftime("%m%d")

    def _pivot_date_text(self, ctx: "_CardContext", value: pd.Timestamp | None) -> str:
        if value is None:
            return "NA"
        stamp = pd.Timestamp(value)
        suffix = "*" if stamp.normalize() == ctx.end.normalize() else ""
        return f"{stamp.strftime('%m%d')}{suffix}"

    def _buy_price(self, pivot: object) -> float:
        display_pivot = self._display_price_value(pivot)
        return np.nan if not self._is_num(display_pivot) else self._round(display_pivot * 1.001, 2)

    def _display_price_value(self, value: object) -> float:
        return np.nan if not self._is_num(value) else self._round(float(value), 2)

    def _text(self, value: object) -> str:
        if value is None:
            return "NA"
        text = str(value).strip().upper()
        return text if text and text not in {"NAN", "NONE"} else "NA"

    def _json_text(self, value: object) -> str | None:
        text = self._text(value)
        return None if text == "NA" else text

    def _json_number(self, value: object) -> float | None:
        if not self._is_num(value):
            return None
        return float(value)

    def _json_bool(self, value: object) -> bool | None:
        if value is None:
            return None
        if isinstance(value, float) and pd.isna(value):
            return None
        if isinstance(value, (np.bool_, bool)):
            return bool(value)
        if self._is_num(value):
            return bool(float(value) >= 0.5)
        text = str(value).strip().lower()
        if text in {"y", "yes", "true", "1"}:
            return True
        if text in {"n", "no", "false", "0"}:
            return False
        return None

    def _is_num(self, value: object) -> bool:
        try:
            return bool(pd.notna(value) and np.isfinite(float(value)))
        except (TypeError, ValueError):
            return False

    def _round(self, value: float, digits: int) -> float:
        quantizer = Decimal("1") if digits == 0 else Decimal("1").scaleb(-digits)
        return float(Decimal(str(value)).quantize(quantizer, rounding=ROUND_HALF_UP))


@dataclass(frozen=True, slots=True)
class _CardContext:
    ticker: str
    source: pd.DataFrame
    metrics: pd.DataFrame
    indicators: pd.DataFrame
    adjusted: bool
    metadata: StockCardMetadata
    tape_text: str

    @property
    def start(self) -> pd.Timestamp:
        return pd.Timestamp(self.source.index[0])

    @property
    def end(self) -> pd.Timestamp:
        return pd.Timestamp(self.source.index[-1])

    @property
    def latest(self) -> pd.Series:
        return self.indicators.iloc[-1]

    @property
    def close(self) -> float:
        return float(self.source["close"].iloc[-1])

    @property
    def sma50(self) -> float:
        return float(self.latest.get("sma50", np.nan))

    @property
    def sma150(self) -> float:
        return float(self.latest.get("sma150", np.nan))

    @property
    def sma200(self) -> float:
        return float(self.latest.get("sma200", np.nan))

    @property
    def sma200_slope(self) -> float:
        return float(self.latest.get("sma200_slope_1m_pct", np.nan))

    @property
    def ema21(self) -> float:
        return float(self.latest.get("ema21_close", np.nan))

    @property
    def atr(self) -> float:
        return float(self.latest.get("atr", np.nan))

    @property
    def hi52(self) -> float:
        return float(self.latest.get("high_52w", np.nan))

    @property
    def lo52(self) -> float:
        return float(self.latest.get("low_52w", np.nan))

    @property
    def v50(self) -> float:
        value = self.metrics["volume_sma"].iloc[-1]
        return float(value) if pd.notna(value) else np.nan

    @property
    def vlast(self) -> float:
        value = self.metrics["v"].iloc[-1]
        return float(value) if pd.notna(value) else np.nan
