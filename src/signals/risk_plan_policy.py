from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.signals.pool import SignalPoolEntry
from src.signals.risk_reward import calculate_buffered_stop
from src.signals.rules import EntrySignalDefinition


MOMENTUM_MAX_RISK_ATR = 2.0
MOMENTUM_MIN_STRUCTURAL_TP_RR = 1.5
MOMENTUM_ENTRY_ZONE_DISTANCE_ATR = 0.5
BREAKOUT_MAX_RISK_ATR = 2.0
BREAKOUT_MIN_STRUCTURAL_TP_RR = 1.5
BREAKOUT_ENTRY_ZONE_DISTANCE_ATR = 0.5
ORDERLY_MAX_RISK_ATR = 1.8
ORDERLY_MIN_STRUCTURAL_TP_RR = 1.5
ORDERLY_ENTRY_ZONE_DISTANCE_ATR = 0.4
PULLBACK_MAX_RISK_ATR = 2.5
PULLBACK_MIN_STRUCTURAL_TP_RR = 1.5
PULLBACK_ENTRY_ZONE_DISTANCE_ATR = 0.5
POWER_GAP_MAX_RISK_ATR = 2.0
POWER_GAP_MIN_STRUCTURAL_TP_RR = 1.5
POWER_GAP_ENTRY_ZONE_DISTANCE_ATR = 0.5
PULLBACK_TRIGGER_PRESET = "Pullback Trigger"
RECLAIM_TRIGGER_PRESET = "Reclaim Trigger"
FIFTY_SMA_DEFENSE_PRESET = "50SMA Defense"


@dataclass(frozen=True, slots=True)
class RiskPlanPolicyResult:
    sl_candidates: list[dict[str, object]] = field(default_factory=list)
    selected_sl: dict[str, object] | None = None
    tp1_candidates: list[dict[str, object]] = field(default_factory=list)
    selected_tp1: dict[str, object] | None = None
    tp2_plan: str = "Future trailing stop"
    rr_current: float | None = None
    rr_ideal: float | None = None
    max_entry_price: float | None = None
    entry_zone_low: float | None = None
    entry_zone_high: float | None = None
    distance_to_entry_zone_pct: float | None = None
    risk_in_atr: float | None = None
    reward_in_atr: float | None = None
    stop_adjusted: bool = False
    sl_quality: str = "Invalid"
    reject_codes: tuple[str, ...] = ()


def build_accumulation_breakout_risk_plan(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> RiskPlanPolicyResult:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    if entry_price is None or atr is None or atr <= 0.0:
        return RiskPlanPolicyResult(reject_codes=("entry_or_atr_unavailable",))

    sl_candidates = _breakout_sl_candidates(entry_price, atr, row, pool_entry, definition)
    selected_sl = _select_breakout_sl(sl_candidates)
    reject_codes: list[str] = []
    if selected_sl is None:
        reject_codes.append("sl_unavailable")

    risk_in_atr = _to_float(selected_sl.get("risk_in_atr")) if selected_sl else None
    stop_adjusted = bool(selected_sl.get("adjusted")) if selected_sl else False
    sl_quality = _breakout_sl_quality(selected_sl, risk_in_atr, row)
    if risk_in_atr is not None and risk_in_atr > BREAKOUT_MAX_RISK_ATR:
        reject_codes.append("sl_too_wide")
    if sl_quality == "Weak":
        reject_codes.append("sl_quality_weak")

    tp1_candidates = _breakout_tp1_candidates(entry_price, row, pool_entry, selected_sl, definition)
    selected_tp1 = _select_breakout_tp1(tp1_candidates)
    if selected_tp1 is None:
        reject_codes.append("tp1_unavailable")

    rr_current = None
    rr_ideal = None
    max_entry_price = None
    entry_zone_low = None
    entry_zone_high = None
    distance_to_entry_zone_pct = None
    reward_in_atr = None
    if selected_sl is not None and selected_tp1 is not None:
        stop_price = _to_float(selected_sl.get("price"))
        tp1_price = _to_float(selected_tp1.get("price"))
        if stop_price is None:
            reject_codes.append("sl_unavailable")
        elif tp1_price is None:
            reject_codes.append("tp1_unavailable")
        else:
            rr_current = _rr_for_entry(entry_price, stop_price, tp1_price)
            if rr_current is None:
                if stop_price >= entry_price:
                    reject_codes.append("sl_not_below_entry")
                elif tp1_price <= entry_price:
                    reject_codes.append("tp1_not_above_entry")
            reward_in_atr = max(0.0, (tp1_price - entry_price) / atr) if tp1_price > entry_price else None
            if reward_in_atr is not None and reward_in_atr < 1.5:
                reject_codes.append("reward_too_small")
            max_entry_price = _max_entry_for_rr(
                stop_loss=stop_price,
                tp1=tp1_price,
                min_rr=definition.action.entry_ready_rr_ratio_min,
            )
            if max_entry_price is not None and max_entry_price > stop_price:
                entry_zone_high = min(max_entry_price, tp1_price)
                entry_zone_low = stop_price + atr * BREAKOUT_ENTRY_ZONE_DISTANCE_ATR
                if entry_zone_low > entry_zone_high:
                    reject_codes.append("entry_zone_invalid")
                else:
                    ideal_entry = entry_price if entry_zone_low <= entry_price <= entry_zone_high else entry_zone_high
                    rr_ideal = _rr_for_entry(ideal_entry, stop_price, tp1_price)
                    if entry_price > entry_zone_high:
                        distance_to_entry_zone_pct = (entry_price / entry_zone_high - 1.0) * 100.0
                    elif entry_price < entry_zone_low:
                        distance_to_entry_zone_pct = (entry_price / entry_zone_low - 1.0) * 100.0

    return RiskPlanPolicyResult(
        sl_candidates=sl_candidates,
        selected_sl=selected_sl,
        tp1_candidates=tp1_candidates,
        selected_tp1=selected_tp1,
        tp2_plan=_breakout_tp2_plan(selected_tp1),
        rr_current=rr_current,
        rr_ideal=rr_ideal,
        max_entry_price=max_entry_price,
        entry_zone_low=entry_zone_low,
        entry_zone_high=entry_zone_high,
        distance_to_entry_zone_pct=distance_to_entry_zone_pct,
        risk_in_atr=risk_in_atr,
        reward_in_atr=reward_in_atr,
        stop_adjusted=stop_adjusted,
        sl_quality=sl_quality,
        reject_codes=tuple(dict.fromkeys(reject_codes)),
    )


def build_orderly_pullback_risk_plan(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> RiskPlanPolicyResult:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    if entry_price is None or atr is None or atr <= 0.0:
        return RiskPlanPolicyResult(reject_codes=("entry_or_atr_unavailable",))

    sl_candidates = _orderly_sl_candidates(entry_price, atr, row, pool_entry, definition)
    selected_sl = _select_orderly_sl(sl_candidates)
    reject_codes: list[str] = []
    if selected_sl is None:
        reject_codes.append("sl_unavailable")

    risk_in_atr = _to_float(selected_sl.get("risk_in_atr")) if selected_sl else None
    stop_adjusted = bool(selected_sl.get("adjusted")) if selected_sl else False
    sl_quality = _orderly_sl_quality(selected_sl, risk_in_atr, row)
    if risk_in_atr is not None and risk_in_atr > ORDERLY_MAX_RISK_ATR:
        reject_codes.append("sl_too_wide")
    if sl_quality == "Weak":
        reject_codes.append("sl_quality_weak")

    tp1_candidates = _orderly_tp1_candidates(entry_price, row, pool_entry, selected_sl, definition)
    selected_tp1 = _select_orderly_tp1(tp1_candidates)
    if selected_tp1 is None:
        reject_codes.append("tp1_unavailable")

    rr_current = None
    rr_ideal = None
    max_entry_price = None
    entry_zone_low = None
    entry_zone_high = None
    distance_to_entry_zone_pct = None
    reward_in_atr = None
    if selected_sl is not None and selected_tp1 is not None:
        stop_price = _to_float(selected_sl.get("price"))
        tp1_price = _to_float(selected_tp1.get("price"))
        if stop_price is None:
            reject_codes.append("sl_unavailable")
        elif tp1_price is None:
            reject_codes.append("tp1_unavailable")
        else:
            rr_current = _rr_for_entry(entry_price, stop_price, tp1_price)
            if rr_current is None:
                if stop_price >= entry_price:
                    reject_codes.append("sl_not_below_entry")
                elif tp1_price <= entry_price:
                    reject_codes.append("tp1_not_above_entry")
            reward_in_atr = max(0.0, (tp1_price - entry_price) / atr) if tp1_price > entry_price else None
            max_entry_price = _max_entry_for_rr(
                stop_loss=stop_price,
                tp1=tp1_price,
                min_rr=definition.action.entry_ready_rr_ratio_min,
            )
            if max_entry_price is not None and max_entry_price > stop_price:
                entry_zone_high = min(max_entry_price, tp1_price)
                entry_zone_low = stop_price + atr * ORDERLY_ENTRY_ZONE_DISTANCE_ATR
                if entry_zone_low > entry_zone_high:
                    reject_codes.append("entry_zone_invalid")
                else:
                    ideal_entry = entry_price if entry_zone_low <= entry_price <= entry_zone_high else entry_zone_high
                    rr_ideal = _rr_for_entry(ideal_entry, stop_price, tp1_price)
                    if entry_price > entry_zone_high:
                        distance_to_entry_zone_pct = (entry_price / entry_zone_high - 1.0) * 100.0
                    elif entry_price < entry_zone_low:
                        distance_to_entry_zone_pct = (entry_price / entry_zone_low - 1.0) * 100.0

    return RiskPlanPolicyResult(
        sl_candidates=sl_candidates,
        selected_sl=selected_sl,
        tp1_candidates=tp1_candidates,
        selected_tp1=selected_tp1,
        tp2_plan=_orderly_tp2_plan(selected_tp1),
        rr_current=rr_current,
        rr_ideal=rr_ideal,
        max_entry_price=max_entry_price,
        entry_zone_low=entry_zone_low,
        entry_zone_high=entry_zone_high,
        distance_to_entry_zone_pct=distance_to_entry_zone_pct,
        risk_in_atr=risk_in_atr,
        reward_in_atr=reward_in_atr,
        stop_adjusted=stop_adjusted,
        sl_quality=sl_quality,
        reject_codes=tuple(dict.fromkeys(reject_codes)),
    )


def build_momentum_acceleration_risk_plan(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> RiskPlanPolicyResult:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    if entry_price is None or atr is None or atr <= 0.0:
        return RiskPlanPolicyResult(reject_codes=("entry_or_atr_unavailable",))

    sl_candidates = _momentum_sl_candidates(entry_price, atr, row, pool_entry, definition)
    selected_sl = _select_momentum_sl(sl_candidates)
    reject_codes: list[str] = []
    if selected_sl is None:
        reject_codes.append("sl_unavailable")

    risk_in_atr = _to_float(selected_sl.get("risk_in_atr")) if selected_sl else None
    stop_adjusted = bool(selected_sl.get("adjusted")) if selected_sl else False
    sl_quality = _momentum_sl_quality(selected_sl, risk_in_atr, row)
    if risk_in_atr is not None and risk_in_atr > MOMENTUM_MAX_RISK_ATR:
        reject_codes.append("sl_too_wide")
    if sl_quality == "Weak":
        reject_codes.append("sl_quality_weak")

    tp1_candidates = _momentum_tp1_candidates(entry_price, row, pool_entry, selected_sl, definition)
    selected_tp1 = _select_momentum_tp1(tp1_candidates)
    if selected_tp1 is None:
        reject_codes.append("tp1_unavailable")

    rr_current = None
    rr_ideal = None
    max_entry_price = None
    entry_zone_low = None
    entry_zone_high = None
    distance_to_entry_zone_pct = None
    reward_in_atr = None
    if selected_sl is not None and selected_tp1 is not None:
        stop_price = _to_float(selected_sl.get("price"))
        tp1_price = _to_float(selected_tp1.get("price"))
        if stop_price is None:
            reject_codes.append("sl_unavailable")
        elif tp1_price is None:
            reject_codes.append("tp1_unavailable")
        else:
            rr_current = _rr_for_entry(entry_price, stop_price, tp1_price)
            if rr_current is None:
                if stop_price >= entry_price:
                    reject_codes.append("sl_not_below_entry")
                elif tp1_price <= entry_price:
                    reject_codes.append("tp1_not_above_entry")
            reward_in_atr = max(0.0, (tp1_price - entry_price) / atr) if tp1_price > entry_price else None
            max_entry_price = _max_entry_for_rr(
                stop_loss=stop_price,
                tp1=tp1_price,
                min_rr=definition.action.entry_ready_rr_ratio_min,
            )
            if max_entry_price is not None and max_entry_price > stop_price:
                entry_zone_high = min(max_entry_price, tp1_price)
                entry_zone_low = stop_price + atr * MOMENTUM_ENTRY_ZONE_DISTANCE_ATR
                if entry_zone_low > entry_zone_high:
                    reject_codes.append("entry_zone_invalid")
                else:
                    ideal_entry = entry_price if entry_zone_low <= entry_price <= entry_zone_high else entry_zone_high
                    rr_ideal = _rr_for_entry(ideal_entry, stop_price, tp1_price)
                    if entry_price > entry_zone_high:
                        distance_to_entry_zone_pct = (entry_price / entry_zone_high - 1.0) * 100.0
                    elif entry_price < entry_zone_low:
                        distance_to_entry_zone_pct = (entry_price / entry_zone_low - 1.0) * 100.0

    return RiskPlanPolicyResult(
        sl_candidates=sl_candidates,
        selected_sl=selected_sl,
        tp1_candidates=tp1_candidates,
        selected_tp1=selected_tp1,
        tp2_plan=_momentum_tp2_plan(selected_tp1),
        rr_current=rr_current,
        rr_ideal=rr_ideal,
        max_entry_price=max_entry_price,
        entry_zone_low=entry_zone_low,
        entry_zone_high=entry_zone_high,
        distance_to_entry_zone_pct=distance_to_entry_zone_pct,
        risk_in_atr=risk_in_atr,
        reward_in_atr=reward_in_atr,
        stop_adjusted=stop_adjusted,
        sl_quality=sl_quality,
        reject_codes=tuple(dict.fromkeys(reject_codes)),
    )


def build_pullback_resumption_risk_plan(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> RiskPlanPolicyResult:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    if entry_price is None or atr is None or atr <= 0.0:
        return RiskPlanPolicyResult(reject_codes=("entry_or_atr_unavailable",))

    sl_candidates = _pullback_sl_candidates(entry_price, atr, row, pool_entry, definition)
    selected_sl = _select_pullback_sl(sl_candidates)
    reject_codes: list[str] = []
    if selected_sl is None:
        reject_codes.append("sl_unavailable")

    risk_in_atr = _to_float(selected_sl.get("risk_in_atr")) if selected_sl else None
    stop_adjusted = bool(selected_sl.get("adjusted")) if selected_sl else False
    sl_quality = _pullback_sl_quality(selected_sl, risk_in_atr, row, pool_entry)
    if risk_in_atr is not None and risk_in_atr > PULLBACK_MAX_RISK_ATR:
        reject_codes.append("sl_too_wide")
    if sl_quality == "Weak":
        reject_codes.append("sl_quality_weak")

    tp1_candidates = _pullback_tp1_candidates(entry_price, row, pool_entry, selected_sl, definition)
    selected_tp1 = _select_pullback_tp1(tp1_candidates)
    if selected_tp1 is None:
        reject_codes.append("tp1_unavailable")

    rr_current = None
    rr_ideal = None
    max_entry_price = None
    entry_zone_low = None
    entry_zone_high = None
    distance_to_entry_zone_pct = None
    reward_in_atr = None
    if selected_sl is not None and selected_tp1 is not None:
        stop_price = _to_float(selected_sl.get("price"))
        tp1_price = _to_float(selected_tp1.get("price"))
        if stop_price is None:
            reject_codes.append("sl_unavailable")
        elif tp1_price is None:
            reject_codes.append("tp1_unavailable")
        else:
            rr_current = _rr_for_entry(entry_price, stop_price, tp1_price)
            if rr_current is None:
                if stop_price >= entry_price:
                    reject_codes.append("sl_not_below_entry")
                elif tp1_price <= entry_price:
                    reject_codes.append("tp1_not_above_entry")
            reward_in_atr = max(0.0, (tp1_price - entry_price) / atr) if tp1_price > entry_price else None
            max_entry_price = _max_entry_for_rr(
                stop_loss=stop_price,
                tp1=tp1_price,
                min_rr=definition.action.entry_ready_rr_ratio_min,
            )
            if max_entry_price is not None and max_entry_price > stop_price:
                entry_zone_high = min(max_entry_price, tp1_price)
                entry_zone_low = stop_price + atr * PULLBACK_ENTRY_ZONE_DISTANCE_ATR
                if entry_zone_low > entry_zone_high:
                    reject_codes.append("entry_zone_invalid")
                else:
                    ideal_entry = entry_price if entry_zone_low <= entry_price <= entry_zone_high else entry_zone_high
                    rr_ideal = _rr_for_entry(ideal_entry, stop_price, tp1_price)
                    if entry_price > entry_zone_high:
                        distance_to_entry_zone_pct = (entry_price / entry_zone_high - 1.0) * 100.0
                    elif entry_price < entry_zone_low:
                        distance_to_entry_zone_pct = (entry_price / entry_zone_low - 1.0) * 100.0

    return RiskPlanPolicyResult(
        sl_candidates=sl_candidates,
        selected_sl=selected_sl,
        tp1_candidates=tp1_candidates,
        selected_tp1=selected_tp1,
        tp2_plan=_pullback_tp2_plan(selected_tp1),
        rr_current=rr_current,
        rr_ideal=rr_ideal,
        max_entry_price=max_entry_price,
        entry_zone_low=entry_zone_low,
        entry_zone_high=entry_zone_high,
        distance_to_entry_zone_pct=distance_to_entry_zone_pct,
        risk_in_atr=risk_in_atr,
        reward_in_atr=reward_in_atr,
        stop_adjusted=stop_adjusted,
        sl_quality=sl_quality,
        reject_codes=tuple(dict.fromkeys(reject_codes)),
    )


def build_power_gap_pullback_risk_plan(
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> RiskPlanPolicyResult:
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    if entry_price is None or atr is None or atr <= 0.0:
        return RiskPlanPolicyResult(reject_codes=("entry_or_atr_unavailable",))

    sl_candidates = _power_gap_sl_candidates(entry_price, atr, row, pool_entry, definition)
    selected_sl = _select_power_gap_sl(sl_candidates)
    reject_codes: list[str] = []
    if selected_sl is None:
        reject_codes.append("sl_unavailable")

    risk_in_atr = _to_float(selected_sl.get("risk_in_atr")) if selected_sl else None
    stop_adjusted = bool(selected_sl.get("adjusted")) if selected_sl else False
    sl_quality = _power_gap_sl_quality(selected_sl, risk_in_atr, row)
    if risk_in_atr is not None and risk_in_atr > POWER_GAP_MAX_RISK_ATR:
        reject_codes.append("sl_too_wide")
    if sl_quality == "Weak":
        reject_codes.append("sl_quality_weak")

    tp1_candidates = _power_gap_tp1_candidates(entry_price, row, pool_entry, selected_sl, definition)
    selected_tp1 = _select_power_gap_tp1(tp1_candidates)
    if selected_tp1 is None:
        reject_codes.append("tp1_unavailable")

    rr_current = None
    rr_ideal = None
    max_entry_price = None
    entry_zone_low = None
    entry_zone_high = None
    distance_to_entry_zone_pct = None
    reward_in_atr = None
    if selected_sl is not None and selected_tp1 is not None:
        stop_price = _to_float(selected_sl.get("price"))
        tp1_price = _to_float(selected_tp1.get("price"))
        if stop_price is None:
            reject_codes.append("sl_unavailable")
        elif tp1_price is None:
            reject_codes.append("tp1_unavailable")
        else:
            rr_current = _rr_for_entry(entry_price, stop_price, tp1_price)
            if rr_current is None:
                if stop_price >= entry_price:
                    reject_codes.append("sl_not_below_entry")
                elif tp1_price <= entry_price:
                    reject_codes.append("tp1_not_above_entry")
            reward_in_atr = max(0.0, (tp1_price - entry_price) / atr) if tp1_price > entry_price else None
            max_entry_price = _max_entry_for_rr(
                stop_loss=stop_price,
                tp1=tp1_price,
                min_rr=definition.action.entry_ready_rr_ratio_min,
            )
            if max_entry_price is not None and max_entry_price > stop_price:
                entry_zone_high = min(max_entry_price, tp1_price)
                entry_zone_low = stop_price + atr * POWER_GAP_ENTRY_ZONE_DISTANCE_ATR
                if entry_zone_low > entry_zone_high:
                    reject_codes.append("entry_zone_invalid")
                else:
                    ideal_entry = entry_price if entry_zone_low <= entry_price <= entry_zone_high else entry_zone_high
                    rr_ideal = _rr_for_entry(ideal_entry, stop_price, tp1_price)
                    if entry_price > entry_zone_high:
                        distance_to_entry_zone_pct = (entry_price / entry_zone_high - 1.0) * 100.0
                    elif entry_price < entry_zone_low:
                        distance_to_entry_zone_pct = (entry_price / entry_zone_low - 1.0) * 100.0

    return RiskPlanPolicyResult(
        sl_candidates=sl_candidates,
        selected_sl=selected_sl,
        tp1_candidates=tp1_candidates,
        selected_tp1=selected_tp1,
        tp2_plan=_power_gap_tp2_plan(selected_tp1),
        rr_current=rr_current,
        rr_ideal=rr_ideal,
        max_entry_price=max_entry_price,
        entry_zone_low=entry_zone_low,
        entry_zone_high=entry_zone_high,
        distance_to_entry_zone_pct=distance_to_entry_zone_pct,
        risk_in_atr=risk_in_atr,
        reward_in_atr=reward_in_atr,
        stop_adjusted=stop_adjusted,
        sl_quality=sl_quality,
        reject_codes=tuple(dict.fromkeys(reject_codes)),
    )


def _momentum_sl_candidates(
    entry_price: float,
    atr: float,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> list[dict[str, object]]:
    acceleration_low = _to_float(pool_entry.snapshot_at_detection.get("low"))
    if acceleration_low is None:
        acceleration_low = _to_float(row.get("low"))
    raw_candidates: list[tuple[str, float | None, float]] = [
        ("acceleration_day_low", acceleration_low, 0.25),
    ]

    low_since_detection = _to_float(pool_entry.low_since_detection)
    if low_since_detection is not None and acceleration_low is not None and low_since_detection > acceleration_low:
        raw_candidates.append(("higher_low_since_detection", low_since_detection, 0.15))

    current_low = _to_float(row.get("low"))
    if current_low is not None and acceleration_low is not None and current_low > acceleration_low:
        raw_candidates.append(("current_higher_low", current_low, 0.15))

    candidates: list[dict[str, object]] = []
    for source, reference, atr_buffer in raw_candidates:
        stop = calculate_buffered_stop(
            entry_price,
            atr,
            reference,
            definition.risk_reward,
            atr_buffer=atr_buffer,
        )
        if stop.stop_price is None or stop.stop_price >= entry_price:
            continue
        candidates.append(
            {
                "source": source,
                "reference": reference,
                "price": round(stop.stop_price, 4),
                "risk_in_atr": round(stop.risk_in_atr, 4) if stop.risk_in_atr is not None else None,
                "adjusted": stop.stop_adjusted,
                "atr_buffer": atr_buffer,
            }
        )
    return _dedupe_candidates(candidates)


def _pullback_sl_candidates(
    entry_price: float,
    atr: float,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> list[dict[str, object]]:
    source = _primary_pool_source(pool_entry)
    if source == FIFTY_SMA_DEFENSE_PRESET:
        raw_candidates = [
            ("sma50_defense", _to_float(row.get("sma50")), 0.50),
            ("pullback_low", _to_float(pool_entry.low_since_detection), 0.25),
        ]
    elif source == RECLAIM_TRIGGER_PRESET:
        raw_candidates = [
            ("reclaim_pullback_low", _to_float(pool_entry.low_since_detection), 0.35),
            ("ema21_reclaim", _to_float(row.get("ema21_close")), 0.35),
        ]
    else:
        raw_candidates = [
            ("pullback_low", _to_float(pool_entry.low_since_detection), 0.25),
            ("ema21_support", _to_float(row.get("ema21_close")), 0.50),
        ]

    candidates: list[dict[str, object]] = []
    for candidate_source, reference, atr_buffer in raw_candidates:
        stop = calculate_buffered_stop(
            entry_price,
            atr,
            reference,
            definition.risk_reward,
            atr_buffer=atr_buffer,
        )
        if stop.stop_price is None or stop.stop_price >= entry_price:
            continue
        candidates.append(
            {
                "source": candidate_source,
                "reference": reference,
                "price": round(stop.stop_price, 4),
                "risk_in_atr": round(stop.risk_in_atr, 4) if stop.risk_in_atr is not None else None,
                "adjusted": stop.stop_adjusted,
                "atr_buffer": atr_buffer,
            }
        )
    return _dedupe_candidates(candidates)


def _orderly_sl_candidates(
    entry_price: float,
    atr: float,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> list[dict[str, object]]:
    low_since_detection = _to_float(pool_entry.low_since_detection)
    ema21_low = _to_float(row.get("ema21_low"))
    ema21_close = _to_float(row.get("ema21_close"))
    raw_candidates = [
        ("low_since_detection", low_since_detection, 0.25),
        ("ema21_low", ema21_low, 0.25),
        ("ema21_close_proxy", ema21_close, 0.50),
    ]

    candidates: list[dict[str, object]] = []
    for candidate_source, reference, atr_buffer in raw_candidates:
        stop = calculate_buffered_stop(
            entry_price,
            atr,
            reference,
            definition.risk_reward,
            atr_buffer=atr_buffer,
        )
        if stop.stop_price is None or stop.stop_price >= entry_price:
            continue
        candidates.append(
            {
                "source": candidate_source,
                "reference": reference,
                "price": round(stop.stop_price, 4),
                "risk_in_atr": round(stop.risk_in_atr, 4) if stop.risk_in_atr is not None else None,
                "adjusted": stop.stop_adjusted,
                "atr_buffer": atr_buffer,
            }
        )
    return _dedupe_candidates(candidates)


def _breakout_sl_candidates(
    entry_price: float,
    atr: float,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> list[dict[str, object]]:
    snapshot_low = _to_float(pool_entry.snapshot_at_detection.get("low"))
    resistance = _to_float(pool_entry.snapshot_at_detection.get("resistance_level_lookback"))
    if resistance is None:
        resistance = _to_float(row.get("resistance_level_lookback"))
    breakout_support_values = [value for value in (snapshot_low, resistance) if value is not None]
    breakout_support = max(breakout_support_values) if breakout_support_values else None
    ema21_close = _to_float(row.get("ema21_close"))
    if ema21_close is None:
        ema21_close = _to_float(pool_entry.snapshot_at_detection.get("ema21_close"))
    low_since_detection = _to_float(pool_entry.low_since_detection)
    vcp_pivot = _to_float(row.get("vcp_pivot_price"))
    if vcp_pivot is None:
        vcp_pivot = _to_float(pool_entry.snapshot_at_detection.get("vcp_pivot_price"))

    raw_candidates = [
        ("breakout_support", breakout_support, 0.25),
        ("ema21_breakout_support", ema21_close, 0.25),
        ("low_since_detection", low_since_detection, 0.25),
        ("vcp_pivot_support", vcp_pivot, 0.25),
    ]

    candidates: list[dict[str, object]] = []
    for candidate_source, reference, atr_buffer in raw_candidates:
        stop = calculate_buffered_stop(
            entry_price,
            atr,
            reference,
            definition.risk_reward,
            atr_buffer=atr_buffer,
        )
        if stop.stop_price is None or stop.stop_price >= entry_price:
            continue
        raw_risk_in_atr = None
        if reference is not None:
            raw_risk_in_atr = (entry_price - (reference - atr * atr_buffer)) / atr
        candidates.append(
            {
                "source": candidate_source,
                "reference": reference,
                "price": round(stop.stop_price, 4),
                "risk_in_atr": round(stop.risk_in_atr, 4) if stop.risk_in_atr is not None else None,
                "raw_risk_in_atr": round(raw_risk_in_atr, 4) if raw_risk_in_atr is not None else None,
                "adjusted": stop.stop_adjusted,
                "atr_buffer": atr_buffer,
                "resistance_test_count": _to_float(row.get("resistance_test_count")),
            }
        )
    return _dedupe_candidates(candidates)


def _power_gap_sl_candidates(
    entry_price: float,
    atr: float,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> list[dict[str, object]]:
    low_since_detection = _to_float(pool_entry.low_since_detection)
    ema21_low = _to_float(row.get("ema21_low"))
    if ema21_low is None:
        ema21_low = _to_float(pool_entry.snapshot_at_detection.get("ema21_low"))
    support_values = [value for value in (low_since_detection, ema21_low) if value is not None]
    pullback_support = max(support_values) if support_values else None
    snapshot_low = _to_float(pool_entry.snapshot_at_detection.get("low"))
    if snapshot_low is None:
        snapshot_low = _to_float(row.get("low"))

    raw_candidates = [
        ("gap_pullback_support", pullback_support, 0.25),
        ("gap_day_low_proxy", snapshot_low, 0.15),
    ]

    candidates: list[dict[str, object]] = []
    for candidate_source, reference, atr_buffer in raw_candidates:
        stop = calculate_buffered_stop(
            entry_price,
            atr,
            reference,
            definition.risk_reward,
            atr_buffer=atr_buffer,
        )
        if stop.stop_price is None or stop.stop_price >= entry_price:
            continue
        candidates.append(
            {
                "source": candidate_source,
                "reference": reference,
                "price": round(stop.stop_price, 4),
                "risk_in_atr": round(stop.risk_in_atr, 4) if stop.risk_in_atr is not None else None,
                "adjusted": stop.stop_adjusted,
                "atr_buffer": atr_buffer,
            }
        )
    return _dedupe_candidates(candidates)


def _select_momentum_sl(candidates: list[dict[str, object]]) -> dict[str, object] | None:
    valid = [candidate for candidate in candidates if _to_float(candidate.get("price")) is not None]
    if not valid:
        return None
    higher_lows = [
        candidate
        for candidate in valid
        if str(candidate.get("source")) in {"higher_low_since_detection", "current_higher_low"}
    ]
    if higher_lows:
        return min(higher_lows, key=lambda candidate: float(candidate.get("risk_in_atr") or 99.0))
    return min(valid, key=lambda candidate: abs(float(candidate.get("risk_in_atr") or 99.0) - 1.2))


def _select_orderly_sl(candidates: list[dict[str, object]]) -> dict[str, object] | None:
    valid = [candidate for candidate in candidates if _to_float(candidate.get("price")) is not None]
    if not valid:
        return None
    primary = [
        candidate
        for candidate in valid
        if candidate.get("source") == "low_since_detection"
        and _to_float(candidate.get("risk_in_atr")) is not None
        and float(candidate["risk_in_atr"]) <= ORDERLY_MAX_RISK_ATR
    ]
    if primary:
        return primary[0]
    alternatives = [
        candidate
        for candidate in valid
        if candidate.get("source") == "ema21_low"
        and _to_float(candidate.get("risk_in_atr")) is not None
        and float(candidate["risk_in_atr"]) <= ORDERLY_MAX_RISK_ATR
    ]
    if alternatives:
        return alternatives[0]
    proxy = [
        candidate
        for candidate in valid
        if candidate.get("source") == "ema21_close_proxy"
        and _to_float(candidate.get("risk_in_atr")) is not None
        and float(candidate["risk_in_atr"]) <= ORDERLY_MAX_RISK_ATR
    ]
    if proxy:
        return proxy[0]
    return min(valid, key=lambda candidate: float(candidate.get("risk_in_atr") or 99.0))


def _select_breakout_sl(candidates: list[dict[str, object]]) -> dict[str, object] | None:
    valid = [candidate for candidate in candidates if _to_float(candidate.get("price")) is not None]
    if not valid:
        return None
    primary = [
        candidate
        for candidate in valid
        if candidate.get("source") == "breakout_support"
        and _to_float(candidate.get("risk_in_atr")) is not None
        and float(candidate["risk_in_atr"]) <= BREAKOUT_MAX_RISK_ATR
        and (_to_float(candidate.get("raw_risk_in_atr")) is None or float(candidate["raw_risk_in_atr"]) >= 0.5)
    ]
    if primary:
        return primary[0]
    alternatives = [
        candidate
        for candidate in valid
        if candidate.get("source") in {"ema21_breakout_support", "low_since_detection", "vcp_pivot_support"}
        and _to_float(candidate.get("risk_in_atr")) is not None
        and float(candidate["risk_in_atr"]) <= BREAKOUT_MAX_RISK_ATR
    ]
    if alternatives:
        return max(alternatives, key=lambda candidate: float(candidate.get("price") or -1.0))
    return min(valid, key=lambda candidate: float(candidate.get("risk_in_atr") or 99.0))


def _select_pullback_sl(candidates: list[dict[str, object]]) -> dict[str, object] | None:
    valid = [candidate for candidate in candidates if _to_float(candidate.get("price")) is not None]
    if not valid:
        return None
    structural = [
        candidate
        for candidate in valid
        if str(candidate.get("source")) in {"sma50_defense", "reclaim_pullback_low", "pullback_low"}
    ]
    if structural:
        return min(structural, key=lambda candidate: abs(float(candidate.get("risk_in_atr") or 99.0) - 1.4))
    return min(valid, key=lambda candidate: abs(float(candidate.get("risk_in_atr") or 99.0) - 1.2))


def _select_power_gap_sl(candidates: list[dict[str, object]]) -> dict[str, object] | None:
    valid = [candidate for candidate in candidates if _to_float(candidate.get("price")) is not None]
    if not valid:
        return None
    primary = [
        candidate
        for candidate in valid
        if candidate.get("source") == "gap_pullback_support"
        and _to_float(candidate.get("risk_in_atr")) is not None
        and float(candidate["risk_in_atr"]) <= POWER_GAP_MAX_RISK_ATR
    ]
    if primary:
        return primary[0]
    proxy = [
        candidate
        for candidate in valid
        if candidate.get("source") == "gap_day_low_proxy"
        and _to_float(candidate.get("risk_in_atr")) is not None
        and float(candidate["risk_in_atr"]) <= POWER_GAP_MAX_RISK_ATR
    ]
    if proxy:
        return proxy[0]
    return min(valid, key=lambda candidate: float(candidate.get("risk_in_atr") or 99.0))


def _momentum_tp1_candidates(
    entry_price: float,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    selected_sl: dict[str, object] | None,
    definition: EntrySignalDefinition,
) -> list[dict[str, object]]:
    structural_sources = [
        ("rolling_20d_close_high", _to_float(row.get("rolling_20d_close_high"))),
        ("high_since_detection", _to_float(pool_entry.high_since_detection)),
        ("high_52w", _to_float(row.get("high_52w"))),
    ]
    candidates: list[dict[str, object]] = []
    stop_price = _to_float(selected_sl.get("price")) if selected_sl else None
    for source, price in structural_sources:
        if price is None or price <= entry_price:
            continue
        rr = _rr_for_entry(entry_price, stop_price, price) if stop_price is not None else None
        candidates.append(
            {
                "source": source,
                "price": round(price, 4),
                "rr": round(rr, 4) if rr is not None else None,
                "target_type": "structural",
            }
        )

    validation_target = _rr_target(
        entry_price,
        selected_sl,
        definition.action.entry_ready_rr_ratio_min,
    )
    if validation_target is not None:
        candidates.append(
            {
                "source": "rr_validation_target",
                "price": round(validation_target, 4),
                "rr": definition.action.entry_ready_rr_ratio_min,
                "target_type": "validation",
            }
        )
    return _dedupe_candidates(candidates)


def _pullback_tp1_candidates(
    entry_price: float,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    selected_sl: dict[str, object] | None,
    definition: EntrySignalDefinition,
) -> list[dict[str, object]]:
    structural_sources = [
        ("snapshot_rolling_20d_close_high", _to_float(pool_entry.snapshot_at_detection.get("rolling_20d_close_high"))),
        ("rolling_20d_close_high", _to_float(row.get("rolling_20d_close_high"))),
        ("high_since_detection", _to_float(pool_entry.high_since_detection)),
        ("high_52w", _to_float(row.get("high_52w"))),
    ]
    candidates: list[dict[str, object]] = []
    stop_price = _to_float(selected_sl.get("price")) if selected_sl else None
    for source, price in structural_sources:
        if price is None or price <= entry_price:
            continue
        rr = _rr_for_entry(entry_price, stop_price, price) if stop_price is not None else None
        candidates.append(
            {
                "source": source,
                "price": round(price, 4),
                "rr": round(rr, 4) if rr is not None else None,
                "target_type": "structural",
            }
        )

    validation_target = _rr_target(
        entry_price,
        selected_sl,
        definition.action.entry_ready_rr_ratio_min,
    )
    if validation_target is not None:
        candidates.append(
            {
                "source": "rr_validation_target",
                "price": round(validation_target, 4),
                "rr": definition.action.entry_ready_rr_ratio_min,
                "target_type": "validation",
            }
        )
    return _dedupe_candidates(candidates)


def _orderly_tp1_candidates(
    entry_price: float,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    selected_sl: dict[str, object] | None,
    definition: EntrySignalDefinition,
) -> list[dict[str, object]]:
    structural_sources = [
        ("snapshot_rolling_20d_close_high", _to_float(pool_entry.snapshot_at_detection.get("rolling_20d_close_high"))),
        ("high_52w", _to_float(row.get("high_52w"))),
        ("rolling_20d_close_high", _to_float(row.get("rolling_20d_close_high"))),
        ("high_since_detection", _to_float(pool_entry.high_since_detection)),
    ]
    candidates: list[dict[str, object]] = []
    stop_price = _to_float(selected_sl.get("price")) if selected_sl else None
    for source, price in structural_sources:
        if price is None or price <= entry_price:
            continue
        rr = _rr_for_entry(entry_price, stop_price, price) if stop_price is not None else None
        candidates.append(
            {
                "source": source,
                "price": round(price, 4),
                "rr": round(rr, 4) if rr is not None else None,
                "target_type": "structural",
            }
        )

    validation_target = _rr_target(
        entry_price,
        selected_sl,
        definition.action.entry_ready_rr_ratio_min,
    )
    if validation_target is not None:
        candidates.append(
            {
                "source": "rr_validation_target",
                "price": round(validation_target, 4),
                "rr": definition.action.entry_ready_rr_ratio_min,
                "target_type": "validation",
            }
        )
    return _dedupe_candidates(candidates)


def _breakout_tp1_candidates(
    entry_price: float,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    selected_sl: dict[str, object] | None,
    definition: EntrySignalDefinition,
) -> list[dict[str, object]]:
    dist_from_52w_high = _to_float(row.get("dist_from_52w_high"))
    high_52w = _to_float(row.get("high_52w"))
    structural_sources: list[tuple[str, float | None]] = []
    if dist_from_52w_high is None or dist_from_52w_high <= -2.0:
        structural_sources.append(("high_52w", high_52w))
    structural_sources.extend(
        [
            ("measured_move", _breakout_measured_move_target(entry_price, row, pool_entry)),
            ("vcp_measured_move", _vcp_measured_move_target(entry_price, row, pool_entry)),
        ]
    )

    candidates: list[dict[str, object]] = []
    stop_price = _to_float(selected_sl.get("price")) if selected_sl else None
    for source, price in structural_sources:
        if price is None or price <= entry_price:
            continue
        rr = _rr_for_entry(entry_price, stop_price, price) if stop_price is not None else None
        candidates.append(
            {
                "source": source,
                "price": round(price, 4),
                "rr": round(rr, 4) if rr is not None else None,
                "target_type": "structural",
            }
        )

    validation_target = _rr_target(
        entry_price,
        selected_sl,
        definition.action.entry_ready_rr_ratio_min,
    )
    if validation_target is not None:
        candidates.append(
            {
                "source": "rr_validation_target",
                "price": round(validation_target, 4),
                "rr": definition.action.entry_ready_rr_ratio_min,
                "target_type": "validation",
            }
        )
    return _dedupe_candidates(candidates)


def _power_gap_tp1_candidates(
    entry_price: float,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    selected_sl: dict[str, object] | None,
    definition: EntrySignalDefinition,
) -> list[dict[str, object]]:
    proxy_targets = [
        ("rolling_20d_close_high", _to_float(row.get("rolling_20d_close_high"))),
        ("high_since_detection", _to_float(pool_entry.high_since_detection)),
        ("snapshot_high", _to_float(pool_entry.snapshot_at_detection.get("high"))),
    ]
    available_proxy_targets = [
        (source, price) for source, price in proxy_targets if price is not None and price > entry_price
    ]
    primary_proxy = max(available_proxy_targets, key=lambda item: item[1]) if available_proxy_targets else None
    structural_sources: list[tuple[str, float | None]] = []
    if primary_proxy is not None:
        structural_sources.append(primary_proxy)
    structural_sources.append(("high_52w", _to_float(row.get("high_52w"))))

    candidates: list[dict[str, object]] = []
    stop_price = _to_float(selected_sl.get("price")) if selected_sl else None
    for source, price in structural_sources:
        if price is None or price <= entry_price:
            continue
        rr = _rr_for_entry(entry_price, stop_price, price) if stop_price is not None else None
        candidates.append(
            {
                "source": source,
                "price": round(price, 4),
                "rr": round(rr, 4) if rr is not None else None,
                "target_type": "structural",
            }
        )

    validation_target = _rr_target(
        entry_price,
        selected_sl,
        definition.action.entry_ready_rr_ratio_min,
    )
    if validation_target is not None:
        candidates.append(
            {
                "source": "rr_validation_target",
                "price": round(validation_target, 4),
                "rr": definition.action.entry_ready_rr_ratio_min,
                "target_type": "validation",
            }
        )
    return _dedupe_candidates(candidates)


def _select_momentum_tp1(candidates: list[dict[str, object]]) -> dict[str, object] | None:
    structural = [
        candidate
        for candidate in candidates
        if candidate.get("target_type") == "structural"
        and _to_float(candidate.get("rr")) is not None
        and float(candidate["rr"]) >= MOMENTUM_MIN_STRUCTURAL_TP_RR
    ]
    if structural:
        return min(structural, key=lambda candidate: float(candidate["price"]))
    validation = [candidate for candidate in candidates if candidate.get("target_type") == "validation"]
    if validation:
        return validation[0]
    return None


def _select_orderly_tp1(candidates: list[dict[str, object]]) -> dict[str, object] | None:
    structural = [
        candidate
        for candidate in candidates
        if candidate.get("target_type") == "structural"
        and _to_float(candidate.get("rr")) is not None
        and float(candidate["rr"]) >= ORDERLY_MIN_STRUCTURAL_TP_RR
    ]
    if structural:
        return structural[0]
    validation = [candidate for candidate in candidates if candidate.get("target_type") == "validation"]
    if validation:
        return validation[0]
    return None


def _select_breakout_tp1(candidates: list[dict[str, object]]) -> dict[str, object] | None:
    structural = [
        candidate
        for candidate in candidates
        if candidate.get("target_type") == "structural"
        and _to_float(candidate.get("rr")) is not None
        and float(candidate["rr"]) >= BREAKOUT_MIN_STRUCTURAL_TP_RR
    ]
    if structural:
        return structural[0]
    validation = [candidate for candidate in candidates if candidate.get("target_type") == "validation"]
    if validation:
        return validation[0]
    return None


def _select_pullback_tp1(candidates: list[dict[str, object]]) -> dict[str, object] | None:
    structural = [
        candidate
        for candidate in candidates
        if candidate.get("target_type") == "structural"
        and _to_float(candidate.get("rr")) is not None
        and float(candidate["rr"]) >= PULLBACK_MIN_STRUCTURAL_TP_RR
    ]
    if structural:
        return min(structural, key=lambda candidate: float(candidate["price"]))
    validation = [candidate for candidate in candidates if candidate.get("target_type") == "validation"]
    if validation:
        return validation[0]
    return None


def _select_power_gap_tp1(candidates: list[dict[str, object]]) -> dict[str, object] | None:
    structural = [
        candidate
        for candidate in candidates
        if candidate.get("target_type") == "structural"
        and _to_float(candidate.get("rr")) is not None
        and float(candidate["rr"]) >= POWER_GAP_MIN_STRUCTURAL_TP_RR
    ]
    if structural:
        return structural[0]
    validation = [candidate for candidate in candidates if candidate.get("target_type") == "validation"]
    if validation:
        return validation[0]
    return None


def _momentum_sl_quality(
    selected_sl: dict[str, object] | None,
    risk_in_atr: float | None,
    row: dict[str, object],
) -> str:
    if selected_sl is None or risk_in_atr is None:
        return "Invalid"
    if risk_in_atr < 0.5:
        return "Invalid"
    if risk_in_atr > MOMENTUM_MAX_RISK_ATR:
        return "Weak"
    dcr_percent = _to_float(row.get("dcr_percent"))
    if dcr_percent is not None and dcr_percent < 50.0:
        return "Weak"
    source = str(selected_sl.get("source", ""))
    if source in {"acceleration_day_low", "higher_low_since_detection", "current_higher_low"}:
        if risk_in_atr <= 1.5 and (dcr_percent is None or dcr_percent >= 60.0):
            return "Strong"
        return "OK"
    return "Weak"


def _pullback_sl_quality(
    selected_sl: dict[str, object] | None,
    risk_in_atr: float | None,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
) -> str:
    if selected_sl is None or risk_in_atr is None:
        return "Invalid"
    if risk_in_atr < 0.5:
        return "Invalid"
    if risk_in_atr > PULLBACK_MAX_RISK_ATR:
        return "Weak"
    dcr_percent = _to_float(row.get("dcr_percent"))
    source = str(selected_sl.get("source", ""))
    primary_pool_source = _primary_pool_source(pool_entry)
    if source == "sma50_defense":
        sma50_slope = _to_float(row.get("sma50_slope_10d_pct")) or 0.0
        if sma50_slope > 0.0 and (dcr_percent is None or dcr_percent >= 60.0):
            return "Strong" if risk_in_atr <= 2.0 else "OK"
        return "Weak"
    if source in {"reclaim_pullback_low", "pullback_low"}:
        if dcr_percent is not None and dcr_percent < 45.0:
            return "Weak"
        return "Strong" if risk_in_atr <= 2.0 else "OK"
    if source in {"ema21_reclaim", "ema21_support"} and primary_pool_source != FIFTY_SMA_DEFENSE_PRESET:
        return "OK"
    return "Weak"


def _orderly_sl_quality(
    selected_sl: dict[str, object] | None,
    risk_in_atr: float | None,
    row: dict[str, object],
) -> str:
    if selected_sl is None or risk_in_atr is None:
        return "Invalid"
    if risk_in_atr < ORDERLY_ENTRY_ZONE_DISTANCE_ATR:
        return "Invalid"
    if risk_in_atr > ORDERLY_MAX_RISK_ATR:
        return "Weak"
    dcr_percent = _to_float(row.get("dcr_percent"))
    sma50_slope = _to_float(row.get("sma50_slope_10d_pct")) or 0.0
    source = str(selected_sl.get("source", ""))
    if sma50_slope <= 0.0:
        return "Weak"
    if dcr_percent is not None and dcr_percent < 45.0:
        return "Weak"
    if source == "low_since_detection":
        return "Strong" if risk_in_atr <= 1.5 and (dcr_percent is None or dcr_percent >= 60.0) else "OK"
    if source in {"ema21_low", "ema21_close_proxy"}:
        return "OK"
    return "Weak"


def _breakout_sl_quality(
    selected_sl: dict[str, object] | None,
    risk_in_atr: float | None,
    row: dict[str, object],
) -> str:
    if selected_sl is None or risk_in_atr is None:
        return "Invalid"
    if risk_in_atr < 0.5:
        return "Invalid"
    if risk_in_atr > BREAKOUT_MAX_RISK_ATR:
        return "Weak"
    dcr_percent = _to_float(row.get("dcr_percent"))
    if dcr_percent is not None and dcr_percent < 50.0:
        return "Weak"
    source = str(selected_sl.get("source", ""))
    if source == "breakout_support":
        resistance_tests = _to_float(row.get("resistance_test_count")) or 0.0
        return "Strong" if resistance_tests >= 2.0 and risk_in_atr <= 1.5 else "OK"
    if source in {"ema21_breakout_support", "low_since_detection", "vcp_pivot_support"}:
        return "OK"
    return "Weak"


def _power_gap_sl_quality(
    selected_sl: dict[str, object] | None,
    risk_in_atr: float | None,
    row: dict[str, object],
) -> str:
    if selected_sl is None or risk_in_atr is None:
        return "Invalid"
    if risk_in_atr < POWER_GAP_ENTRY_ZONE_DISTANCE_ATR:
        return "Invalid"
    if risk_in_atr > POWER_GAP_MAX_RISK_ATR:
        return "Weak"
    dcr_percent = _to_float(row.get("dcr_percent"))
    if dcr_percent is not None and dcr_percent < 50.0:
        return "Weak"
    source = str(selected_sl.get("source", ""))
    if source == "gap_pullback_support":
        return "Strong" if risk_in_atr <= 1.5 and (dcr_percent is None or dcr_percent >= 60.0) else "OK"
    if source == "gap_day_low_proxy":
        return "OK"
    return "Weak"


def _momentum_tp2_plan(selected_tp1: dict[str, object] | None) -> str:
    if selected_tp1 is not None and selected_tp1.get("target_type") == "validation":
        return "No structural TP1; manage with 10-day low trailing from pool day 3"
    return "After TP1 or pool day 3, trail with 10-day low"


def _breakout_tp2_plan(selected_tp1: dict[str, object] | None) -> str:
    if selected_tp1 is not None and selected_tp1.get("target_type") == "validation":
        return "No structural TP1; manage with 10-day low trailing from pool day 3"
    return "After TP1 or pool day 3, trail with 10-day low"


def _orderly_tp2_plan(selected_tp1: dict[str, object] | None) -> str:
    if selected_tp1 is not None and selected_tp1.get("target_type") == "validation":
        return "No structural TP1; manage with 21EMA close trailing from pool day 3"
    return "After TP1, trail with 21EMA close; exit on two consecutive closes below 21EMA"


def _pullback_tp2_plan(selected_tp1: dict[str, object] | None) -> str:
    if selected_tp1 is not None and selected_tp1.get("target_type") == "validation":
        return "No structural TP1; manage with 10-day low or 21EMA trailing after confirmation"
    return "After TP1, trail with 10-day low or 21EMA support"


def _power_gap_tp2_plan(selected_tp1: dict[str, object] | None) -> str:
    if selected_tp1 is not None and selected_tp1.get("target_type") == "validation":
        return "No structural TP1; manage with 21EMA close trailing from pool day 3"
    return "After TP1, trail with 21EMA close; exit on two consecutive closes below 21EMA"


def _primary_pool_source(pool_entry: SignalPoolEntry) -> str:
    sources = set(pool_entry.preset_sources)
    for source in (FIFTY_SMA_DEFENSE_PRESET, RECLAIM_TRIGGER_PRESET, PULLBACK_TRIGGER_PRESET):
        if source in sources:
            return source
    return pool_entry.preset_sources[0] if pool_entry.preset_sources else ""


def _rr_target(entry_price: float, selected_sl: dict[str, object] | None, rr: float) -> float | None:
    if selected_sl is None:
        return None
    stop = _to_float(selected_sl.get("price"))
    if stop is None:
        return None
    risk = entry_price - stop
    if risk <= 0.0:
        return None
    return entry_price + risk * rr


def _breakout_measured_move_target(
    entry_price: float,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
) -> float | None:
    resistance = _to_float(pool_entry.snapshot_at_detection.get("resistance_level_lookback"))
    if resistance is None:
        resistance = _to_float(row.get("resistance_level_lookback"))
    if resistance is None:
        resistance = _to_float(pool_entry.snapshot_at_detection.get("rolling_20d_close_high"))
    if resistance is None or resistance <= 0.0:
        return None
    base_low_candidates = [
        _to_float(pool_entry.snapshot_at_detection.get("low")),
        _to_float(pool_entry.low_since_detection),
        _to_float(row.get("sma50")),
    ]
    base_lows = [value for value in base_low_candidates if value is not None and 0.0 < value < resistance]
    if not base_lows:
        return None
    base_width = resistance - min(base_lows)
    if base_width <= 0.0:
        return None
    return max(entry_price, resistance) + base_width


def _vcp_measured_move_target(
    entry_price: float,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
) -> float | None:
    pivot = _to_float(row.get("vcp_pivot_price"))
    if pivot is None:
        pivot = _to_float(pool_entry.snapshot_at_detection.get("vcp_pivot_price"))
    depth_pct = _to_float(row.get("vcp_t1_depth_pct"))
    if depth_pct is None:
        depth_pct = _to_float(pool_entry.snapshot_at_detection.get("vcp_t1_depth_pct"))
    if pivot is None or depth_pct is None or pivot <= 0.0 or depth_pct <= 0.0:
        return None
    return max(entry_price, pivot) + pivot * depth_pct / 100.0


def _max_entry_for_rr(*, stop_loss: float, tp1: float, min_rr: float) -> float | None:
    if min_rr <= 0.0 or tp1 <= stop_loss:
        return None
    return (tp1 + min_rr * stop_loss) / (1.0 + min_rr)


def _rr_for_entry(entry_price: float, stop_loss: float | None, tp1: float) -> float | None:
    if stop_loss is None:
        return None
    risk = entry_price - stop_loss
    reward = tp1 - entry_price
    if risk <= 0.0 or reward <= 0.0:
        return None
    return reward / risk


def _dedupe_candidates(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    deduped: list[dict[str, object]] = []
    seen: set[tuple[str, float]] = set()
    for candidate in candidates:
        price = _to_float(candidate.get("price"))
        if price is None:
            continue
        key = (str(candidate.get("source", "")), round(price, 4))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


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
