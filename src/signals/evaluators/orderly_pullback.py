from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.signals.pool import SignalPoolEntry
from src.signals.risk_reward import RiskRewardResult, evaluate_risk_reward
from src.signals.rules import EntrySignalDefinition
from src.signals.scoring import composite_score, piecewise_linear_score


@dataclass(frozen=True, slots=True)
class AxisResult:
    score: float
    detail: dict[str, float]


@dataclass(frozen=True, slots=True)
class OrderlyPullbackEvaluation:
    setup_maturity_score: float
    timing_score: float
    risk_reward_score: float
    entry_strength: float
    maturity_detail: dict[str, float]
    timing_detail: dict[str, float]
    risk_reward: RiskRewardResult


def evaluate_orderly_pullback(
    row: pd.Series | dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
    *,
    eval_date: pd.Timestamp,
) -> OrderlyPullbackEvaluation:
    current = _series_to_dict(row)
    setup = evaluate_setup_maturity(current, pool_entry, definition, eval_date=eval_date)
    timing = evaluate_timing(current, definition)
    risk_reward = evaluate_risk_reward(current, pool_entry, definition.risk_reward)
    entry_strength = calculate_entry_strength(
        setup.score,
        timing.score,
        risk_reward.score,
        definition,
    )
    return OrderlyPullbackEvaluation(
        setup_maturity_score=setup.score,
        timing_score=timing.score,
        risk_reward_score=risk_reward.score,
        entry_strength=entry_strength,
        maturity_detail=setup.detail,
        timing_detail=timing.detail,
        risk_reward=risk_reward,
    )


def evaluate_setup_maturity(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
    *,
    eval_date: pd.Timestamp,
) -> AxisResult:
    days_since_first_detected = _business_day_distance(pool_entry.first_detected_date, eval_date)
    rs21_at_detection = _to_float(pool_entry.snapshot_at_detection.get("rs21"))
    rs21_now = _to_float(row.get("rs21"))
    rs21_delta = None if rs21_at_detection is None or rs21_now is None else rs21_now - rs21_at_detection

    detail: dict[str, float] = {}
    weighted_scores: dict[str, tuple[float, float]] = {}
    for indicator_name, indicator in definition.setup_maturity.indicators.items():
        if indicator.composite:
            component_scores: dict[str, tuple[float, float]] = {}
            for component_name, component in indicator.components.items():
                component_value = _virtual_field_value(
                    row,
                    component.field,
                    days_since_first_detected=days_since_first_detected,
                    rs21_delta_from_detection=rs21_delta,
                )
                component_scores[component_name] = (
                    piecewise_linear_score(component_value, component.breakpoints),
                    component.weight,
                )
            indicator_score = composite_score(component_scores)
        else:
            indicator_value = _virtual_field_value(
                row,
                indicator.field,
                days_since_first_detected=days_since_first_detected,
                rs21_delta_from_detection=rs21_delta,
            )
            indicator_score = piecewise_linear_score(indicator_value, indicator.breakpoints)
        detail[indicator_name] = round(indicator_score, 2)
        weighted_scores[indicator_name] = (indicator_score, indicator.weight)
    return AxisResult(score=round(composite_score(weighted_scores), 2), detail=detail)


def evaluate_timing(
    row: dict[str, object],
    definition: EntrySignalDefinition,
) -> AxisResult:
    detail: dict[str, float] = {}
    weighted_scores: dict[str, tuple[float, float]] = {}
    for indicator_name, indicator in definition.timing.indicators.items():
        if indicator.composite:
            indicator_score = _timing_logic_score(indicator_name, row)
        elif indicator.field is None and not indicator.breakpoints:
            indicator_score = _timing_logic_score(indicator_name, row)
        else:
            indicator_score = piecewise_linear_score(
                _to_float(row.get(indicator.field)) if indicator.field else None,
                indicator.breakpoints,
            )
        detail[indicator_name] = round(indicator_score, 2)
        weighted_scores[indicator_name] = (indicator_score, indicator.weight)
    return AxisResult(score=round(composite_score(weighted_scores), 2), detail=detail)


def calculate_entry_strength(
    maturity: float,
    timing: float,
    risk_reward: float,
    definition: EntrySignalDefinition,
) -> float:
    weights = definition.entry_strength
    weighted_avg = (
        maturity * weights.setup_maturity_weight
        + timing * weights.timing_weight
        + risk_reward * weights.risk_reward_weight
    )
    if min(maturity, timing, risk_reward) < weights.min_axis_threshold:
        return round(min(weighted_avg, weights.capped_strength), 2)
    return round(max(0.0, min(100.0, weighted_avg)), 2)


def _timing_logic_score(indicator_name: str, row: dict[str, object]) -> float:
    close_crossed_above_ema21 = bool(row.get("close_crossed_above_ema21"))
    atr_21ema_zone = _to_float(row.get("atr_21ema_zone"))
    high = _to_float(row.get("high"))
    prev_high = _to_float(row.get("prev_high"))
    ud_volume_ratio = _to_float(row.get("ud_volume_ratio")) or 0.0
    if indicator_name == "ema_reclaim_event":
        if close_crossed_above_ema21:
            return 100.0
        if atr_21ema_zone is None:
            return 5.0
        if 0.0 <= atr_21ema_zone <= 0.5:
            return 70.0
        if -0.3 <= atr_21ema_zone < 0.0:
            return 40.0
        if -0.5 <= atr_21ema_zone < -0.3:
            return 20.0
        return 5.0
    if indicator_name == "micro_structure_breakout":
        base = 70.0 if high is not None and prev_high is not None and high > prev_high else 20.0
        bonus = 30.0 if close_crossed_above_ema21 else 0.0
        return min(base + bonus, 100.0)
    if indicator_name == "demand_footprint":
        if bool(row.get("pocket_pivot")):
            return 90.0
        if ud_volume_ratio >= 1.5:
            return 70.0
        if ud_volume_ratio >= 1.0:
            return 40.0
        return 15.0
    raise ValueError(f"unsupported timing indicator logic: {indicator_name}")


def _virtual_field_value(
    row: dict[str, object],
    field_name: str | None,
    *,
    days_since_first_detected: int,
    rs21_delta_from_detection: float | None,
) -> float | None:
    if field_name == "_days_since_first_detected":
        return float(days_since_first_detected)
    if field_name == "_rs21_delta_from_detection":
        return rs21_delta_from_detection
    return _to_float(row.get(field_name)) if field_name else None


def _series_to_dict(row: pd.Series | dict[str, object]) -> dict[str, object]:
    if isinstance(row, pd.Series):
        return row.to_dict()
    return dict(row)


def _business_day_distance(left: pd.Timestamp, right: pd.Timestamp) -> int:
    left_date = pd.Timestamp(left).normalize().date()
    right_date = pd.Timestamp(right).normalize().date()
    if right_date <= left_date:
        return 1 if right_date == left_date else 0
    return int(np.busday_count(left_date, right_date)) + 1


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
