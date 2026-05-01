from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from src.signals.evaluators.orderly_pullback import AxisResult, calculate_entry_strength
from src.signals.pool import SignalPoolEntry
from src.signals.risk_reward import RiskRewardResult, calculate_buffered_stop, calculate_rr_ratio, score_rr
from src.signals.rules import EntrySignalDefinition
from src.signals.scoring import composite_score, piecewise_linear_score


@dataclass(frozen=True, slots=True)
class MomentumAccelerationEvaluation:
    setup_maturity_score: float
    timing_score: float
    risk_reward_score: float
    entry_strength: float
    maturity_detail: dict[str, float]
    timing_detail: dict[str, float]
    risk_reward: RiskRewardResult


def evaluate_momentum_acceleration(
    row: pd.Series | dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
    *,
    eval_date: pd.Timestamp,
) -> MomentumAccelerationEvaluation:
    current = _series_to_dict(row)
    setup = evaluate_setup_maturity(current, definition)
    timing = evaluate_timing(current, pool_entry, definition, eval_date=eval_date)
    risk_reward = evaluate_acceleration_day_risk_reward(current, pool_entry, definition)
    if risk_reward.risk_in_atr is not None and risk_reward.risk_in_atr > 2.0:
        risk_reward = replace(risk_reward, score=min(risk_reward.score, 35.0))

    entry_strength = calculate_entry_strength(
        setup.score,
        timing.score,
        risk_reward.score,
        definition,
    )
    timing_detail = dict(timing.detail)
    if _has_climax_warning(current, pool_entry, eval_date):
        timing_detail["climax_warning"] = 100.0
        entry_strength = min(entry_strength, definition.display.signal_detected - 0.01)

    return MomentumAccelerationEvaluation(
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
    definition: EntrySignalDefinition,
) -> AxisResult:
    detail: dict[str, float] = {}
    weighted_scores: dict[str, tuple[float, float]] = {}
    for indicator_name, indicator in definition.setup_maturity.indicators.items():
        indicator_score = piecewise_linear_score(
            _to_float(row.get(indicator.field)) if indicator.field else None,
            indicator.breakpoints,
        )
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
        if indicator.field is None and not indicator.breakpoints:
            indicator_score = _timing_logic_score(indicator_name, row, pool_entry, eval_date)
        else:
            indicator_score = piecewise_linear_score(
                _to_float(row.get(indicator.field)) if indicator.field else None,
                indicator.breakpoints,
            )
        detail[indicator_name] = round(indicator_score, 2)
        weighted_scores[indicator_name] = (indicator_score, indicator.weight)
    return AxisResult(score=round(composite_score(weighted_scores), 2), detail=detail)


def evaluate_acceleration_day_risk_reward(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> RiskRewardResult:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    stop_price, risk_in_atr, stop_adjusted = _acceleration_day_stop(row, pool_entry, definition)
    reward_target = _structural_target(row, entry_price, stop_price)
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


def _timing_logic_score(
    indicator_name: str,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    eval_date: pd.Timestamp,
) -> float:
    if indicator_name == "acceleration_event":
        return _acceleration_event_score(row)
    if indicator_name == "follow_through":
        return _follow_through_score(row, pool_entry, eval_date)
    raise ValueError(f"unsupported momentum acceleration timing indicator: {indicator_name}")


def _acceleration_event_score(row: dict[str, object]) -> float:
    daily_change_pct = _to_float(row.get("daily_change_pct")) or 0.0
    rel_volume = _to_float(row.get("rel_volume")) or 0.0
    pp_count_window = _to_float(row.get("pp_count_window")) or 0.0
    hit_scans = _hit_scan_set(row)
    if daily_change_pct >= 4.0 and rel_volume >= 1.0:
        return 100.0
    if daily_change_pct >= 4.0 or "4% bullish" in hit_scans:
        return 80.0
    if pp_count_window >= 3.0 or "PP Count" in hit_scans:
        return 75.0
    if "Momentum 97" in hit_scans:
        return 35.0
    return 15.0


def _follow_through_score(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    eval_date: pd.Timestamp,
) -> float:
    days_in_pool = _business_day_distance(pool_entry.first_detected_date, eval_date)
    if days_in_pool <= 1:
        return 50.0

    daily_change_pct = _to_float(row.get("daily_change_pct")) or 0.0
    close = _to_float(row.get("close"))
    snapshot_close = _to_float(pool_entry.snapshot_at_detection.get("close"))
    snapshot_high = _to_float(pool_entry.snapshot_at_detection.get("high"))
    if daily_change_pct > 1.0 and close is not None and snapshot_close is not None and close > snapshot_close:
        return 100.0
    if daily_change_pct > 0.0:
        return 80.0
    if (
        pool_entry.high_since_detection is not None
        and snapshot_high is not None
        and pool_entry.high_since_detection > snapshot_high
    ):
        return 70.0
    return 30.0 if days_in_pool == 2 else 15.0


def _acceleration_day_stop(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> tuple[float | None, float | None, bool]:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    reference_price = _to_float(pool_entry.snapshot_at_detection.get("low"))
    if reference_price is None:
        reference_price = pool_entry.low_since_detection
    if entry_price is None or atr is None or atr <= 0.0 or reference_price is None:
        return None, None, False

    stop_result = calculate_buffered_stop(entry_price, atr, reference_price, definition.risk_reward)
    return stop_result.stop_price, stop_result.risk_in_atr, stop_result.stop_adjusted


def _rr_2x_target(entry_price: float | None, stop_price: float | None) -> float | None:
    if entry_price is None or stop_price is None:
        return None
    risk = entry_price - stop_price
    if risk <= 0.0:
        return None
    return entry_price + risk * 2.0


def _structural_target(
    row: dict[str, object],
    entry_price: float | None,
    stop_price: float | None,
) -> float | None:
    if entry_price is None:
        return None
    rr_2x = _rr_2x_target(entry_price, stop_price)
    risk = None if stop_price is None else entry_price - stop_price
    candidates = [
        _to_float(row.get("rolling_20d_close_high")),
        _to_float(row.get("high_52w")),
        rr_2x,
    ]
    for candidate in candidates:
        if candidate is None or candidate <= entry_price:
            continue
        if risk is None or risk <= 0.0 or candidate == rr_2x or (candidate - entry_price) >= risk * 1.5:
            return candidate
    return rr_2x if rr_2x is not None else entry_price * 1.08


def _has_climax_warning(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    eval_date: pd.Timestamp,
) -> bool:
    rel_volume = _to_float(row.get("rel_volume")) or 0.0
    daily_change_pct = _to_float(row.get("daily_change_pct")) or 0.0
    dist_from_52w_high = _to_float(row.get("dist_from_52w_high"))
    dcr_percent = _to_float(row.get("dcr_percent")) or 0.0
    days_in_pool = _business_day_distance(pool_entry.first_detected_date, eval_date)
    return (
        rel_volume >= 5.0
        or (dist_from_52w_high is not None and dist_from_52w_high >= -1.0 and daily_change_pct >= 6.0)
        or (days_in_pool <= 1 and dcr_percent < 50.0)
    )


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
