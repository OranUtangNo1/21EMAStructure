from __future__ import annotations

from dataclasses import dataclass

from src.signals.pool import SignalPoolEntry
from src.signals.rules import RiskRewardConfig
from src.signals.scoring import piecewise_linear_score


@dataclass(frozen=True, slots=True)
class StopResult:
    stop_price: float | None
    risk_in_atr: float | None
    stop_adjusted: bool


@dataclass(frozen=True, slots=True)
class RiskRewardResult:
    score: float
    stop_price: float | None
    reward_target: float | None
    rr_ratio: float | None
    risk_in_atr: float | None
    reward_in_atr: float | None
    stop_adjusted: bool


def evaluate_risk_reward(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    config: RiskRewardConfig,
) -> RiskRewardResult:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    stop_result = calculate_stop_price(pool_entry, row, config)
    reward_target = calculate_reward_target(pool_entry, row, config, stop_result.stop_price)
    rr_ratio = calculate_rr_ratio(entry_price, stop_result.stop_price, reward_target)
    reward_in_atr = None
    if entry_price is not None and reward_target is not None and atr is not None and atr > 0.0:
        reward_in_atr = max(0.0, (reward_target - entry_price) / atr)
    score = score_rr(rr_ratio, stop_result.stop_adjusted, config)
    return RiskRewardResult(
        score=score,
        stop_price=stop_result.stop_price,
        reward_target=reward_target,
        rr_ratio=rr_ratio,
        risk_in_atr=stop_result.risk_in_atr,
        reward_in_atr=reward_in_atr,
        stop_adjusted=stop_result.stop_adjusted,
    )


def calculate_stop_price(
    pool_entry: SignalPoolEntry,
    row: dict[str, object],
    config: RiskRewardConfig,
) -> StopResult:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    reference_price = _resolve_stop_reference(pool_entry, row, config.stop.reference)
    if entry_price is None or atr is None or atr <= 0.0 or reference_price is None:
        return StopResult(stop_price=None, risk_in_atr=None, stop_adjusted=False)

    buffered_stop = reference_price - atr * config.stop.atr_buffer
    min_distance = atr * config.stop.min_distance_atr
    adjusted_stop = min(buffered_stop, entry_price - min_distance)
    stop_adjusted = adjusted_stop != buffered_stop
    if adjusted_stop >= entry_price:
        adjusted_stop = entry_price - min_distance
        stop_adjusted = True
    risk_in_atr = (entry_price - adjusted_stop) / atr if atr > 0.0 else None
    return StopResult(
        stop_price=adjusted_stop,
        risk_in_atr=risk_in_atr,
        stop_adjusted=stop_adjusted,
    )


def calculate_reward_target(
    pool_entry: SignalPoolEntry,
    row: dict[str, object],
    config: RiskRewardConfig,
    stop_price: float | None,
) -> float | None:
    entry_price = _to_float(row.get("close"))
    if entry_price is None:
        return None
    candidates = [
        _resolve_reward_reference(pool_entry, row, config.reward.primary),
        _resolve_reward_reference(pool_entry, row, config.reward.secondary),
        _resolve_reward_reference(pool_entry, row, config.reward.fallback, stop_price=stop_price),
    ]
    for candidate in candidates:
        if candidate is not None and candidate > entry_price:
            return candidate
    return None


def calculate_rr_ratio(
    entry_price: float | None,
    stop_price: float | None,
    reward_target: float | None,
) -> float | None:
    if entry_price is None or stop_price is None or reward_target is None:
        return None
    risk = entry_price - stop_price
    reward = reward_target - entry_price
    if risk <= 0.0 or reward <= 0.0:
        return None
    return reward / risk


def score_rr(
    rr_ratio: float | None,
    stop_adjusted: bool,
    config: RiskRewardConfig,
) -> float:
    if rr_ratio is None:
        return 0.0
    base_score = piecewise_linear_score(rr_ratio, config.scoring_breakpoints)
    if stop_adjusted:
        return max(0.0, min(100.0, base_score * config.stop.structural_penalty))
    return base_score


def _resolve_stop_reference(
    pool_entry: SignalPoolEntry,
    row: dict[str, object],
    reference_name: str,
) -> float | None:
    if reference_name == "low_since_detection":
        return pool_entry.low_since_detection
    return _to_float(row.get(reference_name))


def _resolve_reward_reference(
    pool_entry: SignalPoolEntry,
    row: dict[str, object],
    reference_name: str | None,
    *,
    stop_price: float | None = None,
) -> float | None:
    if not reference_name:
        return None
    if reference_name == "snapshot_rolling_20d_close_high":
        return _to_float(pool_entry.snapshot_at_detection.get("rolling_20d_close_high"))
    if reference_name == "measured_move":
        return _measured_move_target(pool_entry, row, stop_price)
    return _to_float(row.get(reference_name))


def _measured_move_target(
    pool_entry: SignalPoolEntry,
    row: dict[str, object],
    stop_price: float | None,
) -> float | None:
    entry_price = _to_float(row.get("close"))
    if entry_price is None or stop_price is None:
        return None
    risk = entry_price - stop_price
    if risk <= 0.0:
        return None
    snapshot_high = _to_float(pool_entry.snapshot_at_detection.get("high"))
    anchor = snapshot_high if snapshot_high is not None and snapshot_high > entry_price else entry_price
    return anchor + risk * 2.0


def _to_float(value: object) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None
