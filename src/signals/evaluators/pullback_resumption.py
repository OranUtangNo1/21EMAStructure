from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from src.signals.evaluators.orderly_pullback import AxisResult, calculate_entry_strength
from src.signals.pool import SignalPoolEntry
from src.signals.risk_plan_policy import build_pullback_resumption_risk_plan
from src.signals.risk_reward import RiskRewardResult, score_rr
from src.signals.rules import EntrySignalDefinition
from src.signals.scoring import composite_score, piecewise_linear_score


PULLBACK_TRIGGER_PRESET = "Pullback Trigger"
RECLAIM_TRIGGER_PRESET = "Reclaim Trigger"
FIFTY_SMA_DEFENSE_PRESET = "50SMA Defense"


@dataclass(frozen=True, slots=True)
class PullbackResumptionEvaluation:
    setup_maturity_score: float
    timing_score: float
    risk_reward_score: float
    entry_strength: float
    maturity_detail: dict[str, float]
    timing_detail: dict[str, float]
    risk_reward: RiskRewardResult


def evaluate_pullback_resumption(
    row: pd.Series | dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
    *,
    eval_date: pd.Timestamp,
) -> PullbackResumptionEvaluation:
    current = _series_to_dict(row)
    setup = evaluate_setup_maturity(current, pool_entry, definition)
    timing = evaluate_timing(current, pool_entry, definition)
    risk_reward = evaluate_depth_adaptive_risk_reward(current, pool_entry, definition)
    if risk_reward.reward_in_atr is not None and risk_reward.reward_in_atr < 1.5:
        risk_reward = replace(risk_reward, score=min(risk_reward.score, 10.0))
    entry_strength = calculate_entry_strength(
        setup.score,
        timing.score,
        risk_reward.score,
        definition,
    )
    _ = eval_date
    return PullbackResumptionEvaluation(
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
) -> AxisResult:
    detail: dict[str, float] = {}
    weighted_scores: dict[str, tuple[float, float]] = {}
    for indicator_name, indicator in definition.setup_maturity.indicators.items():
        if indicator_name == "pullback_depth_rr_quality":
            indicator_score = _score_pullback_depth(row, pool_entry)
        else:
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
) -> AxisResult:
    detail: dict[str, float] = {}
    weighted_scores: dict[str, tuple[float, float]] = {}
    for indicator_name, indicator in definition.timing.indicators.items():
        if indicator.field is None and not indicator.breakpoints:
            indicator_score = _timing_logic_score(indicator_name, row, pool_entry)
        else:
            indicator_score = piecewise_linear_score(
                _to_float(row.get(indicator.field)) if indicator.field else None,
                indicator.breakpoints,
            )
        detail[indicator_name] = round(indicator_score, 2)
        weighted_scores[indicator_name] = (indicator_score, indicator.weight)
    return AxisResult(score=round(composite_score(weighted_scores), 2), detail=detail)


def evaluate_depth_adaptive_risk_reward(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> RiskRewardResult:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    risk_plan = build_pullback_resumption_risk_plan(row, pool_entry, definition)
    stop_price = _to_float(risk_plan.selected_sl.get("price")) if risk_plan.selected_sl else None
    reward_target = _to_float(risk_plan.selected_tp1.get("price")) if risk_plan.selected_tp1 else None
    rr_ratio = risk_plan.rr_current
    reward_in_atr = risk_plan.reward_in_atr
    _ = entry_price, atr
    return RiskRewardResult(
        score=score_rr(rr_ratio, risk_plan.stop_adjusted, definition.risk_reward),
        stop_price=stop_price,
        reward_target=reward_target,
        rr_ratio=rr_ratio,
        risk_in_atr=risk_plan.risk_in_atr,
        reward_in_atr=reward_in_atr,
        stop_adjusted=risk_plan.stop_adjusted,
    )


def _score_pullback_depth(row: dict[str, object], pool_entry: SignalPoolEntry) -> float:
    source = _primary_source(pool_entry)
    atr_50sma_zone = _to_float(row.get("atr_50sma_zone"))
    atr_21ema_zone = _to_float(row.get("atr_21ema_zone"))
    dcr_percent = _to_float(row.get("dcr_percent")) or 0.0
    sma50_slope = _to_float(row.get("sma50_slope_10d_pct")) or 0.0
    close = _to_float(row.get("close"))
    sma50 = _to_float(row.get("sma50"))

    if source == FIFTY_SMA_DEFENSE_PRESET:
        if (
            sma50_slope > 0.0
            and bool(row.get("close_crossed_above_sma50"))
            and dcr_percent >= 60.0
            and atr_50sma_zone is not None
            and 0.0 <= atr_50sma_zone <= 1.0
        ):
            return 100.0
        if close is not None and sma50 is not None and close >= sma50 and sma50_slope > 0.0:
            return 80.0
        return 45.0
    if source == RECLAIM_TRIGGER_PRESET:
        if bool(row.get("close_crossed_above_ema21")):
            return 80.0
        if atr_21ema_zone is not None and 0.0 <= atr_21ema_zone <= 1.0:
            return 70.0
        return 60.0
    if source == PULLBACK_TRIGGER_PRESET:
        if atr_21ema_zone is not None and -0.25 <= atr_21ema_zone <= 0.75:
            return 60.0
        return 55.0
    return 50.0


def _timing_logic_score(
    indicator_name: str,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
) -> float:
    hit_scans = _hit_scan_set(row)
    if indicator_name == "pattern_trigger":
        if {"21EMA Pattern H", "21EMA Pattern L"} & hit_scans:
            return 100.0
        atr_21ema_zone = _to_float(row.get("atr_21ema_zone"))
        if atr_21ema_zone is not None and -0.5 <= atr_21ema_zone <= 1.0:
            return 55.0
        return 15.0
    if indicator_name == "ma_reclaim_event":
        if {"50SMA Reclaim", "Reclaim scan"} & hit_scans:
            return 100.0
        if bool(row.get("close_crossed_above_sma50")):
            return 85.0
        if bool(row.get("close_crossed_above_ema21")):
            return 75.0
        return 20.0
    if indicator_name == "demand_footprint":
        if "Pocket Pivot" in hit_scans or bool(row.get("pocket_pivot")):
            return 90.0
        ud_volume_ratio = _to_float(row.get("ud_volume_ratio")) or 0.0
        if ud_volume_ratio >= 1.5:
            return 70.0
        if _to_float(row.get("volume_ratio_20d")) is not None and float(row.get("volume_ratio_20d")) >= 1.1:
            return 55.0
        return 20.0
    raise ValueError(f"unsupported pullback resumption timing indicator: {indicator_name}")


def _primary_source(pool_entry: SignalPoolEntry) -> str:
    sources = set(pool_entry.preset_sources)
    for source in (FIFTY_SMA_DEFENSE_PRESET, RECLAIM_TRIGGER_PRESET, PULLBACK_TRIGGER_PRESET):
        if source in sources:
            return source
    return pool_entry.preset_sources[0] if pool_entry.preset_sources else ""


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
