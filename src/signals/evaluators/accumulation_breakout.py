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
class AccumulationBreakoutEvaluation:
    setup_maturity_score: float
    timing_score: float
    risk_reward_score: float
    entry_strength: float
    maturity_detail: dict[str, float]
    timing_detail: dict[str, float]
    risk_reward: RiskRewardResult


def evaluate_accumulation_breakout(
    row: pd.Series | dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
    *,
    eval_date: pd.Timestamp,
) -> AccumulationBreakoutEvaluation:
    current = _series_to_dict(row)
    setup = evaluate_setup_maturity(current, pool_entry, definition)
    timing = evaluate_timing(current, pool_entry, definition, eval_date=eval_date)
    risk_reward = evaluate_breakout_risk_reward(current, pool_entry, definition)

    if risk_reward.risk_in_atr is not None and risk_reward.risk_in_atr > 2.0:
        risk_reward = replace(risk_reward, score=min(risk_reward.score, 35.0))
    if risk_reward.reward_in_atr is not None and risk_reward.reward_in_atr < 1.5:
        risk_reward = replace(risk_reward, score=min(risk_reward.score, 25.0))

    entry_strength = calculate_entry_strength(
        setup.score,
        timing.score,
        risk_reward.score,
        definition,
    )
    timing_detail = dict(timing.detail)
    guard_reason = _guard_reason(current, pool_entry, risk_reward, eval_date)
    if guard_reason:
        timing_detail[guard_reason] = 100.0
        entry_strength = min(entry_strength, definition.display.signal_detected - 0.01)

    return AccumulationBreakoutEvaluation(
        setup_maturity_score=setup.score,
        timing_score=timing.score,
        risk_reward_score=risk_reward.score,
        entry_strength=round(entry_strength, 2),
        maturity_detail=setup.detail,
        timing_detail=timing_detail,
        risk_reward=risk_reward,
    )


def evaluate_setup_maturity(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> AxisResult:
    detail: dict[str, float] = {}
    weighted_scores: dict[str, tuple[float, float]] = {}
    for indicator_name, indicator in definition.setup_maturity.indicators.items():
        if indicator.field and indicator.breakpoints:
            indicator_score = piecewise_linear_score(_to_float(row.get(indicator.field)), indicator.breakpoints)
        else:
            indicator_score = _setup_logic_score(indicator_name, row, pool_entry)
        detail[indicator_name] = round(indicator_score, 2)
        weighted_scores[indicator_name] = (indicator_score, indicator.weight)
    return AxisResult(score=round(composite_score(weighted_scores), 2), detail=detail)


def evaluate_timing(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
    *,
    eval_date: pd.Timestamp,
) -> AxisResult:
    detail: dict[str, float] = {}
    weighted_scores: dict[str, tuple[float, float]] = {}
    for indicator_name, indicator in definition.timing.indicators.items():
        if indicator.field and indicator.breakpoints:
            indicator_score = piecewise_linear_score(_to_float(row.get(indicator.field)), indicator.breakpoints)
        else:
            indicator_score = _timing_logic_score(indicator_name, row, pool_entry, eval_date)
        detail[indicator_name] = round(indicator_score, 2)
        weighted_scores[indicator_name] = (indicator_score, indicator.weight)
    return AxisResult(score=round(composite_score(weighted_scores), 2), detail=detail)


def evaluate_breakout_risk_reward(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> RiskRewardResult:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    stop_price, risk_in_atr, stop_adjusted = _breakout_stop(row, pool_entry, definition)
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


def _setup_logic_score(
    indicator_name: str,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
) -> float:
    if indicator_name == "rs_leadership":
        rs21_score = piecewise_linear_score(_to_float(row.get("rs21")), [(45, 10), (60, 45), (75, 75), (90, 100)])
        weekly_score = piecewise_linear_score(_to_float(row.get("weekly_return_rank")), [(70, 10), (85, 55), (97, 100)])
        quarterly_score = piecewise_linear_score(_to_float(row.get("quarterly_return_rank")), [(60, 10), (80, 60), (95, 100)])
        return composite_score({"rs21": (rs21_score, 0.40), "weekly": (weekly_score, 0.35), "quarterly": (quarterly_score, 0.25)})
    if indicator_name == "accumulation_quality":
        hit_scans = _hit_scan_set(row)
        score = 0.0
        if bool(row.get("pocket_pivot")) or "Pocket Pivot" in hit_scans:
            score += 35.0
        pp_count = _to_float(row.get("pp_count_window")) or 0.0
        score += min(pp_count, 3.0) / 3.0 * 35.0
        if "Volume Accumulation" in hit_scans:
            score += 30.0
        return min(score, 100.0)
    if indicator_name == "base_tightness":
        vcs = _to_float(row.get("vcs"))
        drawdown = _to_float(row.get("drawdown_from_20d_high_pct"))
        cloud_width = _to_float(row.get("ema21_cloud_width"))
        tight_flag = 100.0 if bool(row.get("three_weeks_tight")) else 45.0
        vcs_score = piecewise_linear_score(vcs, [(40, 10), (55, 45), (70, 85), (80, 100)])
        drawdown_score = piecewise_linear_score(drawdown, [(0, 80), (5, 100), (10, 60), (15, 20)])
        cloud_score = piecewise_linear_score(cloud_width, [(0, 100), (2, 80), (5, 45), (8, 15)])
        return composite_score({"vcs": (vcs_score, 0.35), "drawdown": (drawdown_score, 0.30), "cloud": (cloud_score, 0.20), "tight": (tight_flag, 0.15)})
    if indicator_name == "resistance_context":
        close = _to_float(row.get("close"))
        resistance = _breakout_reference(row)
        resistance_tests = _to_float(row.get("resistance_test_count")) or 0.0
        body_ratio = _to_float(row.get("breakout_body_ratio"))
        close_score = 20.0
        if close is not None and resistance is not None:
            clearance_pct = (close - resistance) / resistance * 100.0
            close_score = piecewise_linear_score(clearance_pct, [(-2, 5), (-0.25, 35), (0, 70), (1.5, 100), (5, 70)])
        test_score = piecewise_linear_score(resistance_tests, [(0, 20), (1, 50), (2, 80), (3, 100)])
        body_score = piecewise_linear_score(body_ratio, [(0.10, 20), (0.35, 55), (0.60, 85), (0.80, 100)])
        return composite_score({"close": (close_score, 0.50), "tests": (test_score, 0.25), "body": (body_score, 0.25)})
    raise ValueError(f"unsupported accumulation breakout setup indicator: {indicator_name}")


def _timing_logic_score(
    indicator_name: str,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    eval_date: pd.Timestamp,
) -> float:
    if indicator_name == "breakout_event":
        return _breakout_event_score(row)
    if indicator_name == "follow_through":
        return _follow_through_score(row, pool_entry, eval_date)
    raise ValueError(f"unsupported accumulation breakout timing indicator: {indicator_name}")


def _breakout_event_score(row: dict[str, object]) -> float:
    close = _to_float(row.get("close"))
    reference = _breakout_reference(row)
    hit_scans = _hit_scan_set(row)
    if close is None or reference is None or reference <= 0.0:
        return 70.0 if {"RS New High", "VCS 52 High"} & hit_scans else 20.0
    clearance_pct = (close - reference) / reference * 100.0
    if 0.0 <= clearance_pct <= 3.0:
        return 100.0
    if 3.0 < clearance_pct <= 6.0:
        return 75.0
    if -1.0 <= clearance_pct < 0.0:
        return 55.0
    return 20.0


def _follow_through_score(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    eval_date: pd.Timestamp,
) -> float:
    days_in_pool = _business_day_distance(pool_entry.first_detected_date, eval_date)
    if days_in_pool <= 1:
        return 50.0
    close = _to_float(row.get("close"))
    snapshot_close = _to_float(pool_entry.snapshot_at_detection.get("close"))
    snapshot_high = _to_float(pool_entry.snapshot_at_detection.get("high"))
    daily_change_pct = _to_float(row.get("daily_change_pct")) or 0.0
    if close is not None and snapshot_close is not None and close > snapshot_close and daily_change_pct > 0.0:
        return 100.0
    if pool_entry.high_since_detection is not None and snapshot_high is not None and pool_entry.high_since_detection > snapshot_high:
        return 75.0
    return 30.0 if days_in_pool == 2 else 15.0


def _breakout_stop(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> tuple[float | None, float | None, bool]:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    snapshot_low = _to_float(pool_entry.snapshot_at_detection.get("low"))
    ema21_close = _to_float(row.get("ema21_close"))
    if ema21_close is None:
        ema21_close = _to_float(pool_entry.snapshot_at_detection.get("ema21_close"))
    if entry_price is None or atr is None or atr <= 0.0:
        return None, None, False

    candidates = []
    if snapshot_low is not None:
        candidates.append(snapshot_low - atr * 0.25)
    if ema21_close is not None:
        candidates.append(ema21_close - atr * 0.50)
    if pool_entry.low_since_detection is not None:
        candidates.append(pool_entry.low_since_detection - atr * 0.25)
    if not candidates:
        return None, None, False

    min_distance = atr * definition.risk_reward.stop.min_distance_atr
    valid_candidates = [candidate for candidate in candidates if candidate < entry_price]
    reference_stop = max(valid_candidates) if valid_candidates else entry_price - min_distance
    adjusted_stop = min(reference_stop, entry_price - min_distance)
    stop_adjusted = adjusted_stop != reference_stop
    return adjusted_stop, (entry_price - adjusted_stop) / atr, stop_adjusted


def _reward_target(row: dict[str, object], entry_price: float | None, stop_price: float | None) -> float | None:
    if entry_price is None or stop_price is None:
        return None
    risk = entry_price - stop_price
    if risk <= 0.0:
        return None
    rr_2x = entry_price + risk * 2.0
    high_52w = _to_float(row.get("high_52w"))
    if high_52w is not None and high_52w > entry_price and (high_52w - entry_price) >= risk * 1.5:
        return min(high_52w, rr_2x) if high_52w < rr_2x else rr_2x
    return rr_2x


def _guard_reason(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    risk_reward: RiskRewardResult,
    eval_date: pd.Timestamp,
) -> str:
    rel_volume = _to_float(row.get("rel_volume")) or 0.0
    daily_change_pct = _to_float(row.get("daily_change_pct")) or 0.0
    dist_from_52w_high = _to_float(row.get("dist_from_52w_high"))
    dcr_percent = _to_float(row.get("dcr_percent")) or 0.0
    close = _to_float(row.get("close"))
    snapshot_low = _to_float(pool_entry.snapshot_at_detection.get("low"))
    days_in_pool = _business_day_distance(pool_entry.first_detected_date, eval_date)
    if close is not None and snapshot_low is not None and close < snapshot_low:
        return "breakout_failure"
    if risk_reward.risk_in_atr is not None and risk_reward.risk_in_atr > 2.0:
        return "risk_cap_reason"
    if risk_reward.rr_ratio is not None and risk_reward.rr_ratio < 1.5:
        return "risk_cap_reason"
    if rel_volume >= 5.0 and daily_change_pct >= 6.0:
        return "climax_warning"
    if dist_from_52w_high is not None and dist_from_52w_high >= -1.0 and daily_change_pct >= 6.0:
        return "climax_warning"
    if dcr_percent < 50.0:
        return "low_dcr_warning"
    if days_in_pool >= 3 and pool_entry.high_since_detection is not None and snapshot_low is not None and close is not None and close <= snapshot_low:
        return "follow_through_failure"
    return ""


def _breakout_reference(row: dict[str, object]) -> float | None:
    resistance = _to_float(row.get("resistance_level_lookback"))
    rolling_high = _to_float(row.get("rolling_20d_close_high"))
    candidates = [value for value in (resistance, rolling_high) if value is not None and value > 0.0]
    return min(candidates) if candidates else None


def _business_day_distance(left: pd.Timestamp, right: pd.Timestamp) -> int:
    left_date = pd.Timestamp(left).normalize().date()
    right_date = pd.Timestamp(right).normalize().date()
    if right_date <= left_date:
        return 1 if right_date == left_date else 0
    return int(np.busday_count(left_date, right_date)) + 1


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
