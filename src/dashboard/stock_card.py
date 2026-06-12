from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pandas as pd

from src.dashboard.compressed_tape import CompressedTapeConfig, CompressedTapeError, CompressedTapeGenerator
from src.indicators.core import IndicatorCalculator, IndicatorConfig


SCHEMA_VERSION = "card-v1.0.2"


@dataclass(frozen=True, slots=True)
class StockCardConfig:
    output_dir: str = "data_runs/stock_cards"
    tape_config: CompressedTapeConfig = CompressedTapeConfig()

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "StockCardConfig":
        data = payload or {}
        tape_payload = data.get("compressed_tape", {})
        if not isinstance(tape_payload, dict):
            tape_payload = {}
        return cls(
            output_dir=str(data.get("output_dir", "data_runs/stock_cards")),
            tape_config=CompressedTapeConfig.from_dict(tape_payload),
        )


@dataclass(frozen=True, slots=True)
class StockCardMetadata:
    sector_etf: str = "NA"
    industry_etf: str = "NA"
    industry_rs_rank: int | None = None
    rs_pctl: float | None = None


@dataclass(frozen=True, slots=True)
class StockCardDocument:
    ticker: str
    text: str
    end_date: pd.Timestamp
    path: Path | None = None

    @property
    def filename(self) -> str:
        return f"card_{self.ticker}_{self.end_date.strftime('%Y%m%d')}.md"


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
        return StockCardDocument(ticker=symbol, text=text, end_date=pd.Timestamp(prepared.index[-1]))

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
            f"OVERALL={overall}",
        ]

    def _trend(self, ctx: "_CardContext") -> list[str]:
        tt_pass, tt_total, fail_items = self._trend_template(ctx)
        fail_text = "none" if not fail_items else ",".join(str(item) for item in fail_items)
        rs_text = self._rank(ctx.metadata.rs_pctl)
        stage_num = "2" if self._stage(ctx) == "Stage2" else "1-2" if self._stage(ctx) == "Stage1-2" else "NA"
        p_vs_150 = ctx.close / ctx.sma150 - 1.0 if self._is_num(ctx.sma150) else np.nan
        slope150 = self._slope150(ctx)
        sma200_up = "Y" if self._is_num(ctx.sma200_slope) and ctx.sma200_slope > 0.0 else "N" if self._is_num(ctx.sma200_slope) else "NA"
        return [
            f"TT={tt_pass}/{tt_total} FAIL_ITEMS={fail_text} RS_PCTL={rs_text}",
            f"STAGE={stage_num} P_VS_150SMA={self._fmt_pct(p_vs_150)} SLOPE150={self._fmt_percent_value(slope150, digits=3)}/d",
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
        ]

    def _setup(self, ctx: "_CardContext") -> list[str]:
        setup = self._setup_state(ctx)
        return [
            f"CANDIDATES={','.join(setup['candidates']) if setup['candidates'] else 'NONE'}",
            f"VCP={setup['vcp']} DEPTHS={setup['depths']} BASE: depth={self._fmt_abs_pct(setup['base_depth'])} len={setup['base_len']}d below_high={self._fmt_abs_pct(setup['below_high'])}",
            f"PULLBACK_REF={setup['pullback_ref']} UR_REF={setup['ur_ref']}",
        ]

    def _risk_plan(self, ctx: "_CardContext") -> list[str]:
        plan = self._risk_state(ctx)
        return [
            f"## RISK_PLAN (basis: {plan['basis_text']})",
            f"SL_CAND: struct={plan['struct']} atr2={self._price(plan['atr2'])}({self._fmt_pct(plan['atr2_pct'])}) cap8={self._price(plan['cap8'])}(-8.0%)",
            f"TP_CAND: 2R={self._price(plan['tp2'])} 3R={self._price(plan['tp3'])} oneil={self._price(plan['oneil_low'])}..{self._price(plan['oneil_high'])} measured={self._price(plan['measured'])}",
            f"TRAIL_REF: EMA21={self._price(ctx.ema21)} SMA50={self._price(ctx.sma50)}",
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
        pivot, _ = self._pivot(ctx)
        base_depth, base_len, below_high = self._base(ctx)
        depths = self._depths(ctx)
        candidates: list[str] = []
        basis: dict[str, float] = {}
        if base_len >= 25 and self._is_num(base_depth) and base_depth <= 35.0 and self._is_num(below_high) and below_high <= 5.0:
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
        if pullback is not None:
            candidates.append("PULLBACK")
            basis["PULLBACK"] = self._buy_price(pullback[1])
        candidates = [candidate for candidate in candidates if not self._is_expired_candidate(ctx, candidate, basis.get(candidate))]
        basis = {candidate: value for candidate, value in basis.items() if candidate in candidates}
        return {
            "candidates": candidates or ["NONE"],
            "basis": basis,
            "vcp": "Y" if len(depths) >= 2 and all(depths[i] > depths[i + 1] for i in range(len(depths) - 1)) else "N",
            "depths": "[" + ",".join(self._one(value) for value in depths) + "]",
            "base_depth": base_depth,
            "base_len": base_len,
            "below_high": below_high,
            "pullback_ref": "NA" if pullback is None else f"{pullback[0].strftime('%m%d')}({self._price(pullback[2])})",
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
        struct_price, struct_date = self._struct_stop(ctx, basis)
        atr = self._display_price_value(ctx.atr)
        atr2 = self._round(basis - 2.0 * atr, 2) if self._is_num(atr) else np.nan
        cap8 = self._round(basis * 0.92, 2)
        sl_first = struct_price if self._is_num(struct_price) else atr2
        risk = self._round(basis - sl_first, 2) if self._is_num(sl_first) else np.nan
        base_depth, _, _ = self._base(ctx)
        pivot_display = self._display_price_value(pivot)
        base_depth_display = self._round(base_depth, 1) if self._is_num(base_depth) else np.nan
        return {
            "basis_text": basis_text,
            "basis": basis,
            "struct_value": struct_price,
            "struct": "NA"
            if not self._is_num(struct_price)
            else f"{self._price(struct_price)}({struct_date.strftime('%m%d')}lo-,{self._fmt_pct(struct_price / basis - 1.0)})",
            "atr2": atr2,
            "atr2_pct": atr2 / basis - 1.0 if self._is_num(atr2) else np.nan,
            "cap8": cap8,
            "risk": risk,
            "tp2": self._round(basis + 2.0 * risk, 2) if self._is_num(risk) else np.nan,
            "tp3": self._round(basis + 3.0 * risk, 2) if self._is_num(risk) else np.nan,
            "oneil_low": self._round(basis * 1.20, 2),
            "oneil_high": self._round(basis * 1.25, 2),
            "measured": self._round(pivot_display * (1.0 + base_depth_display / 100.0), 2)
            if self._is_num(pivot_display) and self._is_num(base_depth_display)
            else np.nan,
        }

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
        struct_price, _ = self._struct_stop(ctx, float(risk_state["basis"]))
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

    def _pullback_ref(self, ctx: "_CardContext") -> tuple[pd.Timestamp, float, float] | None:
        if self._stage(ctx) != "Stage2":
            return None
        recent = ctx.source.tail(5)
        candidates: list[tuple[pd.Timestamp, float, float]] = []
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
                pullback_low = low if zone.empty else float(zone["low"].min())
                candidates.append((rev_idx, float(ctx.source.loc[rev_idx, "high"]), pullback_low))
        return candidates[-1] if candidates else None

    def _struct_stop(self, ctx: "_CardContext", basis: float) -> tuple[float, pd.Timestamp]:
        lows = ctx.source["low"].tail(65)
        min_distance = self._struct_stop_min_distance(ctx, basis)
        cap8 = self._round(basis * 0.92, 2)
        candidates: list[tuple[float, pd.Timestamp]] = []
        for idx, low in lows.items():
            display_low = self._display_price_value(low)
            if not self._is_num(display_low):
                continue
            stop = self._round(display_low * 0.999, 2)
            if stop <= basis - min_distance and stop >= cap8:
                candidates.append((stop, pd.Timestamp(idx)))
        if not candidates:
            return np.nan, ctx.end
        return max(candidates, key=lambda item: item[0])

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

    def _is_num(self, value: object) -> bool:
        return bool(pd.notna(value) and np.isfinite(float(value)))

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
