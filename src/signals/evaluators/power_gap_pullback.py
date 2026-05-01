from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from src.signals.evaluators.orderly_pullback import AxisResult, calculate_entry_strength
from src.signals.pool import SignalPoolEntry
from src.signals.risk_reward import RiskRewardResult, calculate_buffered_stop, calculate_rr_ratio, score_rr
from src.signals.rules import EntrySignalDefinition
from src.signals.scoring import composite_score, piecewise_linear_score


@dataclass(frozen=True, slots=True)
class PowerGapPullbackEvaluation:
    setup_maturity_score: float
    timing_score: float
    risk_reward_score: float
    entry_strength: float
    maturity_detail: dict[str, float]
    timing_detail: dict[str, float]
    risk_reward: RiskRewardResult


def evaluate_power_gap_pullback(
    row: pd.Series | dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
    *,
    eval_date: pd.Timestamp,
) -> PowerGapPullbackEvaluation:
    current = _series_to_dict(row)
    setup = evaluate_setup_maturity(current, definition)
    timing = evaluate_timing(current, definition)
    risk_reward = evaluate_gap_pullback_risk_reward(current, pool_entry, definition)
    if risk_reward.risk_in_atr is not None and risk_reward.risk_in_atr > 2.0:
        risk_reward = replace(risk_reward, score=min(risk_reward.score, 30.0))

    entry_strength = calculate_entry_strength(setup.score, timing.score, risk_reward.score, definition)
    timing_detail = dict(timing.detail)
    guard_reason = _guard_reason(current, pool_entry, risk_reward)
    if guard_reason:
        timing_detail[guard_reason] = 100.0
        entry_strength = min(entry_strength, definition.display.signal_detected - 0.01)
    _ = eval_date
    return PowerGapPullbackEvaluation(
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


def evaluate_gap_pullback_risk_reward(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> RiskRewardResult:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    stop_price, risk_in_atr, stop_adjusted = _gap_pullback_stop(row, pool_entry, definition)
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
    if indicator_name == "gap_quality":
        gap_score = piecewise_linear_score(_to_float(row.get("power_gap_up_pct")), [(3, 10), (5, 60), (8, 100), (15, 75)])
        volume_score = piecewise_linear_score(_to_float(row.get("rel_volume")), [(1, 20), (1.5, 55), (2.5, 90), (5, 75)])
        dcr_score = piecewise_linear_score(_to_float(row.get("dcr_percent")), [(40, 10), (60, 55), (80, 100)])
        return composite_score({"gap": (gap_score, 0.40), "volume": (volume_score, 0.35), "dcr": (dcr_score, 0.25)})
    if indicator_name == "pullback_orderliness":
        volume_dry = piecewise_linear_score(_to_float(row.get("volume_ma5_to_ma20_ratio")), [(0.5, 100), (0.7, 80), (0.9, 35), (1.2, 10)])
        drawdown = piecewise_linear_score(_to_float(row.get("drawdown_from_20d_high_pct")), [(0, 40), (4, 100), (9, 75), (14, 35), (18, 10)])
        zone = piecewise_linear_score(_to_float(row.get("atr_21ema_zone")), [(-1, 15), (-0.25, 70), (0.5, 100), (1.5, 60), (3, 15)])
        return composite_score({"volume_dry": (volume_dry, 0.35), "drawdown": (drawdown, 0.35), "zone": (zone, 0.30)})
    if indicator_name == "support_proximity":
        high_zone = piecewise_linear_score(_to_float(row.get("atr_low_to_ema21_high")), [(-1, 15), (-0.25, 75), (0.5, 100), (1.5, 60), (3, 15)])
        low_zone = piecewise_linear_score(_to_float(row.get("atr_low_to_ema21_low")), [(-1, 15), (-0.25, 70), (0.5, 100), (1.5, 65), (3, 20)])
        ema_low = piecewise_linear_score(_to_float(row.get("ema21_low_pct")), [(-5, 10), (-2, 45), (0, 90), (2, 100), (6, 40)])
        return composite_score({"high_zone": (high_zone, 0.35), "low_zone": (low_zone, 0.35), "ema_low": (ema_low, 0.30)})
    if indicator_name == "rs_resilience":
        rs_score = piecewise_linear_score(_to_float(row.get("rs21")), [(45, 10), (60, 45), (75, 80), (90, 100)])
        weekly_rank = piecewise_linear_score(_to_float(row.get("weekly_return_rank")), [(50, 10), (70, 45), (90, 100)])
        return composite_score({"rs": (rs_score, 0.65), "weekly": (weekly_rank, 0.35)})
    if indicator_name == "accumulation_return":
        score = 0.0
        if bool(row.get("pocket_pivot")) or "Pocket Pivot" in hit_scans:
            score += 40.0
        if "Volume Accumulation" in hit_scans:
            score += 35.0
        score += min(_to_float(row.get("pp_count_window")) or 0.0, 3.0) / 3.0 * 25.0
        return min(score, 100.0)
    raise ValueError(f"unsupported power gap pullback setup indicator: {indicator_name}")


def _timing_logic_score(indicator_name: str, row: dict[str, object]) -> float:
    hit_scans = _hit_scan_set(row)
    if indicator_name == "reclaim_trigger":
        if "Reclaim scan" in hit_scans or bool(row.get("close_crossed_above_ema21")):
            return 100.0
        if {"21EMA Pattern H", "21EMA Pattern L"} & hit_scans:
            return 80.0
        close = _to_float(row.get("close"))
        ema21 = _to_float(row.get("ema21_close"))
        if close is not None and ema21 is not None and close >= ema21:
            return 65.0
        return 20.0
    if indicator_name == "volume_reentry":
        rel_volume = _to_float(row.get("rel_volume")) or 0.0
        volume_ratio = _to_float(row.get("volume_ratio_20d")) or 0.0
        score = max(
            piecewise_linear_score(rel_volume, [(0.8, 10), (1.0, 35), (1.3, 70), (2.0, 100), (5.0, 65)]),
            piecewise_linear_score(volume_ratio, [(0.8, 10), (1.0, 35), (1.2, 70), (1.8, 100), (4.0, 70)]),
        )
        if bool(row.get("pocket_pivot")) or "Pocket Pivot" in hit_scans:
            score = max(score, 90.0)
        return score
    if indicator_name == "pullback_age":
        return piecewise_linear_score(_to_float(row.get("days_since_power_gap")), [(0, 5), (1, 20), (3, 80), (5, 100), (12, 100), (16, 55), (20, 20)])
    raise ValueError(f"unsupported power gap pullback timing indicator: {indicator_name}")


def _gap_pullback_stop(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> tuple[float | None, float | None, bool]:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    if entry_price is None or atr is None or atr <= 0.0:
        return None, None, False
    candidates = []
    if pool_entry.low_since_detection is not None:
        candidates.append(pool_entry.low_since_detection)
    ema21_low = _to_float(row.get("ema21_low"))
    if ema21_low is not None:
        candidates.append(ema21_low)
    if not candidates:
        snapshot_low = _to_float(pool_entry.snapshot_at_detection.get("low"))
        if snapshot_low is not None:
            candidates.append(snapshot_low)
    if not candidates:
        return None, None, False
    reference = min(candidates)
    stop_result = calculate_buffered_stop(entry_price, atr, reference, definition.risk_reward)
    return stop_result.stop_price, stop_result.risk_in_atr, stop_result.stop_adjusted


def _reward_target(row: dict[str, object], entry_price: float | None, stop_price: float | None) -> float | None:
    if entry_price is None or stop_price is None:
        return None
    risk = entry_price - stop_price
    if risk <= 0.0:
        return None
    rr_2x = entry_price + risk * 2.0
    rolling_high = _to_float(row.get("rolling_20d_close_high"))
    if rolling_high is not None and rolling_high > entry_price and (rolling_high - entry_price) >= risk * 1.5:
        return rolling_high
    high_52w = _to_float(row.get("high_52w"))
    if high_52w is not None and high_52w > entry_price and (high_52w - entry_price) >= risk * 2.0:
        return min(high_52w, rr_2x)
    return rr_2x


def _guard_reason(row: dict[str, object], pool_entry: SignalPoolEntry, risk_reward: RiskRewardResult) -> str:
    close = _to_float(row.get("close"))
    days_since_gap = _to_float(row.get("days_since_power_gap"))
    rel_volume = _to_float(row.get("rel_volume")) or 0.0
    daily_change_pct = _to_float(row.get("daily_change_pct")) or 0.0
    drawdown = _to_float(row.get("drawdown_from_20d_high_pct")) or 0.0
    dcr_percent = _to_float(row.get("dcr_percent")) or 0.0
    if days_since_gap is not None and days_since_gap <= 1.0:
        return "gap_chase_warning"
    if close is not None and pool_entry.low_since_detection is not None and close < pool_entry.low_since_detection:
        return "gap_failure"
    if drawdown > 18.0:
        return "gap_failure"
    if risk_reward.risk_in_atr is not None and risk_reward.risk_in_atr > 2.0:
        return "risk_cap_reason"
    if risk_reward.rr_ratio is not None and risk_reward.rr_ratio < 1.5:
        return "risk_cap_reason"
    if rel_volume >= 5.0 and daily_change_pct >= 6.0:
        return "climax_warning"
    if dcr_percent < 50.0:
        return "low_dcr_warning"
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
