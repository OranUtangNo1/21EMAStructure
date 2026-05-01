from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from src.signals.evaluators.orderly_pullback import AxisResult, calculate_entry_strength
from src.signals.pool import SignalPoolEntry
from src.signals.risk_reward import RiskRewardResult, calculate_rr_ratio, score_rr
from src.signals.rules import EntrySignalDefinition
from src.signals.scoring import composite_score, piecewise_linear_score


@dataclass(frozen=True, slots=True)
class EarlyCycleRecoveryEvaluation:
    setup_maturity_score: float
    timing_score: float
    risk_reward_score: float
    entry_strength: float
    maturity_detail: dict[str, float]
    timing_detail: dict[str, float]
    risk_reward: RiskRewardResult


def evaluate_early_cycle_recovery(
    row: pd.Series | dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
    *,
    eval_date: pd.Timestamp,
) -> EarlyCycleRecoveryEvaluation:
    current = _series_to_dict(row)
    setup = evaluate_setup_maturity(current, definition)
    timing = evaluate_timing(current, definition)
    risk_reward = evaluate_recovery_risk_reward(current, pool_entry, definition)
    if risk_reward.risk_in_atr is not None and risk_reward.risk_in_atr > 2.25:
        risk_reward = replace(risk_reward, score=min(risk_reward.score, 30.0))

    entry_strength = calculate_entry_strength(setup.score, timing.score, risk_reward.score, definition)
    timing_detail = dict(timing.detail)
    guard_reason = _guard_reason(current, pool_entry, risk_reward)
    if guard_reason:
        timing_detail[guard_reason] = 100.0
        entry_strength = min(entry_strength, definition.display.signal_detected - 0.01)
    _ = eval_date
    return EarlyCycleRecoveryEvaluation(
        setup_maturity_score=setup.score,
        timing_score=timing.score,
        risk_reward_score=risk_reward.score,
        entry_strength=round(entry_strength, 2),
        maturity_detail=setup.detail,
        timing_detail=timing_detail,
        risk_reward=risk_reward,
    )


def evaluate_setup_maturity(row: dict[str, object], definition: EntrySignalDefinition) -> AxisResult:
    detail: dict[str, float] = {}
    weighted_scores: dict[str, tuple[float, float]] = {}
    for indicator_name, indicator in definition.setup_maturity.indicators.items():
        score = _setup_logic_score(indicator_name, row)
        detail[indicator_name] = round(score, 2)
        weighted_scores[indicator_name] = (score, indicator.weight)
    return AxisResult(score=round(composite_score(weighted_scores), 2), detail=detail)


def evaluate_timing(row: dict[str, object], definition: EntrySignalDefinition) -> AxisResult:
    detail: dict[str, float] = {}
    weighted_scores: dict[str, tuple[float, float]] = {}
    for indicator_name, indicator in definition.timing.indicators.items():
        if indicator.field and indicator.breakpoints:
            score = piecewise_linear_score(_to_float(row.get(indicator.field)), indicator.breakpoints)
        else:
            score = _timing_logic_score(indicator_name, row)
        detail[indicator_name] = round(score, 2)
        weighted_scores[indicator_name] = (score, indicator.weight)
    return AxisResult(score=round(composite_score(weighted_scores), 2), detail=detail)


def evaluate_recovery_risk_reward(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> RiskRewardResult:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    stop_price, risk_in_atr, stop_adjusted = _recovery_stop(row, pool_entry, definition)
    reward_target = _reward_target(row, entry_price, stop_price)
    rr_ratio = calculate_rr_ratio(entry_price, stop_price, reward_target)
    reward_in_atr = None
    if entry_price is not None and reward_target is not None and atr is not None and atr > 0.0:
        reward_in_atr = max(0.0, (reward_target - entry_price) / atr)
    return RiskRewardResult(
        score=score_rr(rr_ratio, stop_adjusted, definition.risk_reward),
        stop_price=stop_price,
        reward_target=reward_target,
        rr_ratio=rr_ratio,
        risk_in_atr=risk_in_atr,
        reward_in_atr=reward_in_atr,
        stop_adjusted=stop_adjusted,
    )


def _setup_logic_score(indicator_name: str, row: dict[str, object]) -> float:
    hit_scans = _hit_scan_set(row)
    if indicator_name == "structure_reversal_quality":
        score = 0.0
        if bool(row.get("structure_pivot_long_active")):
            score += 25.0
        if bool(row.get("structure_pivot_1st_break")) or "LL-HL Structure 1st Pivot" in hit_scans:
            score += 25.0
        if bool(row.get("structure_pivot_2nd_break")) or "LL-HL Structure 2nd Pivot" in hit_scans:
            score += 25.0
        if bool(row.get("ct_trendline_break")) or "LL-HL Structure Trend Line Break" in hit_scans:
            score += 25.0
        return min(score, 100.0)
    if indicator_name == "low_to_recovery_position":
        low_score = piecewise_linear_score(_to_float(row.get("dist_from_52w_low")), [(0, 10), (10, 45), (25, 100), (60, 70), (100, 30)])
        high_score = piecewise_linear_score(_to_float(row.get("dist_from_52w_high")), [(-80, 15), (-50, 55), (-25, 100), (-5, 55), (0, 25)])
        return composite_score({"low": (low_score, 0.55), "high": (high_score, 0.45)})
    if indicator_name == "accumulation_evidence":
        score = 0.0
        if "Volume Accumulation" in hit_scans:
            score += 35.0
        if bool(row.get("pocket_pivot")) or "Pocket Pivot" in hit_scans:
            score += 35.0
        score += min(_to_float(row.get("pp_count_window")) or 0.0, 3.0) / 3.0 * 30.0
        return min(score, 100.0)
    if indicator_name == "trend_repair":
        ema_reclaim = 100.0 if bool(row.get("close_crossed_above_ema21")) else 45.0
        sma_reclaim = 100.0 if bool(row.get("close_crossed_above_sma50")) else 35.0
        zone21 = piecewise_linear_score(_to_float(row.get("atr_21ema_zone")), [(-2, 10), (-0.5, 45), (0, 80), (1, 100), (3, 55)])
        zone50 = piecewise_linear_score(_to_float(row.get("atr_50sma_zone")), [(-3, 20), (-1, 50), (0, 80), (1, 100), (3, 50)])
        return composite_score({"ema": (ema_reclaim, 0.35), "sma": (sma_reclaim, 0.25), "zone21": (zone21, 0.25), "zone50": (zone50, 0.15)})
    if indicator_name == "rs_recovery":
        rs_score = piecewise_linear_score(_to_float(row.get("rs21")), [(35, 10), (50, 40), (65, 75), (80, 100)])
        weekly_score = piecewise_linear_score(_to_float(row.get("weekly_return_rank")), [(50, 10), (70, 50), (90, 100)])
        quarterly_score = piecewise_linear_score(_to_float(row.get("quarterly_return_rank")), [(40, 10), (70, 60), (90, 100)])
        return composite_score({"rs": (rs_score, 0.45), "weekly": (weekly_score, 0.35), "quarterly": (quarterly_score, 0.20)})
    raise ValueError(f"unsupported early cycle recovery setup indicator: {indicator_name}")


def _timing_logic_score(indicator_name: str, row: dict[str, object]) -> float:
    hit_scans = _hit_scan_set(row)
    if indicator_name == "pivot_trigger":
        hl_price = _to_float(row.get("structure_pivot_long_hl_price"))
        close = _to_float(row.get("close"))
        if bool(row.get("structure_pivot_long_breakout_first_day")):
            return 100.0
        if bool(row.get("ct_trendline_break")) or "LL-HL Structure Trend Line Break" in hit_scans:
            return 90.0
        if close is not None and hl_price is not None and close > hl_price:
            return 75.0
        return 25.0
    if indicator_name == "ma_reclaim":
        if bool(row.get("close_crossed_above_ema21")):
            return 100.0
        if bool(row.get("close_crossed_above_sma50")):
            return 85.0
        close = _to_float(row.get("close"))
        ema21 = _to_float(row.get("ema21_close"))
        if close is not None and ema21 is not None and close >= ema21:
            return 65.0
        return 20.0
    raise ValueError(f"unsupported early cycle recovery timing indicator: {indicator_name}")


def _recovery_stop(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> tuple[float | None, float | None, bool]:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    if entry_price is None or atr is None or atr <= 0.0:
        return None, None, False
    reference = _to_float(row.get("structure_pivot_long_hl_price"))
    if reference is None:
        reference = pool_entry.low_since_detection
    if reference is None:
        reference = _to_float(pool_entry.snapshot_at_detection.get("low"))
    if reference is None:
        return None, None, False
    raw_stop = reference - atr * definition.risk_reward.stop.atr_buffer
    min_distance = atr * definition.risk_reward.stop.min_distance_atr
    adjusted_stop = min(raw_stop, entry_price - min_distance)
    stop_adjusted = adjusted_stop != raw_stop
    return adjusted_stop, (entry_price - adjusted_stop) / atr, stop_adjusted


def _reward_target(row: dict[str, object], entry_price: float | None, stop_price: float | None) -> float | None:
    if entry_price is None or stop_price is None:
        return None
    risk = entry_price - stop_price
    if risk <= 0.0:
        return None
    rr_2x = entry_price + risk * 2.0
    rolling_high = _to_float(row.get("rolling_20d_close_high"))
    if rolling_high is not None and rolling_high > entry_price and (rolling_high - entry_price) >= risk * 1.5:
        return min(rolling_high, rr_2x)
    return rr_2x


def _guard_reason(row: dict[str, object], pool_entry: SignalPoolEntry, risk_reward: RiskRewardResult) -> str:
    close = _to_float(row.get("close"))
    snapshot_low = _to_float(pool_entry.snapshot_at_detection.get("low"))
    pivot_low = _to_float(row.get("structure_pivot_long_hl_price"))
    dcr_percent = _to_float(row.get("dcr_percent")) or 0.0
    rel_volume = _to_float(row.get("rel_volume")) or 0.0
    daily_change_pct = _to_float(row.get("daily_change_pct")) or 0.0
    weekly_rank = _to_float(row.get("weekly_return_rank")) or 0.0
    rs21 = _to_float(row.get("rs21")) or 0.0
    if close is not None and snapshot_low is not None and close < snapshot_low:
        return "recovery_failure"
    if close is not None and pivot_low is not None and close < pivot_low:
        return "pivot_failure"
    if risk_reward.risk_in_atr is not None and risk_reward.risk_in_atr > 2.25:
        return "risk_cap_reason"
    if risk_reward.rr_ratio is not None and risk_reward.rr_ratio < 1.5:
        return "risk_cap_reason"
    if rel_volume >= 5.0 and daily_change_pct >= 6.0:
        return "climax_warning"
    if dcr_percent < 50.0:
        return "low_dcr_warning"
    if rs21 < 35.0 or weekly_rank < 50.0:
        return "rs_weakness"
    return ""


def _hit_scan_set(row: dict[str, object]) -> set[str]:
    raw_value = str(row.get("hit_scans", "") or "")
    return {value.strip() for value in raw_value.split(",") if value.strip()}


def _series_to_dict(row: pd.Series | dict[str, object]) -> dict[str, object]:
    if isinstance(row, pd.Series):
        return row.to_dict()
    return dict(row)


def _to_float(value: object) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
    except TypeError:
        if value is None:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
