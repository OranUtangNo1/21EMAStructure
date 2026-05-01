from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from src.data.signal_tracking import ACTIVE_POOL_STATUS
from src.signals.pool import SignalPoolEntry
from src.signals.risk_reward import calculate_buffered_stop
from src.signals.rules import EntrySignalDefinition


TP2_TRAILING_PLACEHOLDER = "Future trailing stop"
DEFAULT_PULLBACK_DISTANCE_LIMIT_PCT = 7.5


@dataclass(frozen=True, slots=True)
class EntryPlanResult:
    plan_status: str
    plan_type: str
    entry_type: str
    entry_price: float | None
    current_price: float | None
    entry_zone_low: float | None
    entry_zone_high: float | None
    max_entry_price: float | None
    distance_to_entry_zone_pct: float | None
    stop_loss: float | None
    tp1: float | None
    tp2: str
    rr_tp1: float | None
    rr_current: float | None
    rr_ideal: float | None
    tp2_plan: str
    trigger_condition: str
    plan_verdict: str
    plan_reject_codes: tuple[str, ...]
    plan_reject_reason: str
    sl_quality: str
    sl_source: str
    sl_basis: str
    sl_safety: str
    tp1_source: str
    plan_invalidation: str
    plan_note: str
    plan_detail: dict[str, object]

    def to_row(self) -> dict[str, object]:
        return {
            "Plan Status": self.plan_status,
            "Plan Type": self.plan_type,
            "Entry Type": self.entry_type,
            "Entry Price": self.entry_price,
            "Current Price": self.current_price,
            "Entry Zone Low": self.entry_zone_low,
            "Entry Zone High": self.entry_zone_high,
            "Max Entry Price": self.max_entry_price,
            "Distance To Entry Zone %": self.distance_to_entry_zone_pct,
            "Stop Loss": self.stop_loss,
            "TP1": self.tp1,
            "TP2": self.tp2,
            "R/R TP1": self.rr_tp1,
            "R/R Current": self.rr_current,
            "R/R Ideal": self.rr_ideal,
            "TP2 Plan": self.tp2_plan,
            "Trigger Condition": self.trigger_condition,
            "Plan Verdict": self.plan_verdict,
            "Plan Reject Codes": ", ".join(self.plan_reject_codes),
            "Plan Reject Reason": self.plan_reject_reason,
            "SL Quality": self.sl_quality,
            "SL Source": self.sl_source,
            "SL Basis": self.sl_basis,
            "SL Safety": self.sl_safety,
            "TP1 Source": self.tp1_source,
            "Plan Invalidation": self.plan_invalidation,
            "Plan Note": self.plan_note,
            "Plan Detail": json.dumps(self.plan_detail, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
        }


def build_entry_plan(
    *,
    action_bucket: str,
    entry_ready_bucket: str,
    watch_setup_bucket: str,
    needs_review_bucket: str,
    definition: EntrySignalDefinition,
    pool_entry: SignalPoolEntry,
    current_row: pd.Series,
    pool_status: str,
    pool_transition: str,
) -> EntryPlanResult:
    if pool_status != ACTIVE_POOL_STATUS or pool_transition:
        reason = pool_transition or pool_status or "inactive_pool"
        return _empty_plan(
            plan_status="Inactive",
            verdict="Invalid",
            reject_codes=("inactive_pool",),
            reject_reason=reason,
            plan_invalidation=reason,
        )

    row = current_row.to_dict()
    entry_price = _to_float(row.get("close"))
    atr = _to_float(row.get("atr"))
    if entry_price is None or atr is None or atr <= 0.0:
        return _empty_plan(
            plan_status=_status_for_bucket(action_bucket, entry_ready_bucket, watch_setup_bucket, needs_review_bucket),
            verdict="Invalid",
            reject_codes=("entry_or_atr_unavailable",),
            reject_reason="entry price or ATR unavailable",
            plan_invalidation="entry price or ATR unavailable",
        )

    sl_candidates = _build_sl_candidates(
        entry_price=entry_price,
        atr=atr,
        row=row,
        pool_entry=pool_entry,
        definition=definition,
    )
    selected_sl = _select_stop(sl_candidates)
    tp1_candidates = _build_tp1_candidates(
        entry_price=entry_price,
        atr=atr,
        row=row,
        pool_entry=pool_entry,
        definition=definition,
        selected_sl=selected_sl,
    )
    selected_tp1 = _select_tp1(tp1_candidates)

    reject_codes: list[str] = []
    if selected_sl is None:
        reject_codes.append("sl_unavailable")
    if selected_tp1 is None:
        reject_codes.append("tp1_unavailable")

    rr_current = None
    rr_ideal = None
    max_entry_price = None
    entry_zone_low = None
    entry_zone_high = None
    distance_to_entry_zone_pct = None
    if selected_sl is not None and selected_tp1 is not None:
        risk = entry_price - selected_sl["price"]
        reward = selected_tp1["price"] - entry_price
        if risk <= 0.0:
            reject_codes.append("sl_not_below_entry")
        elif reward <= 0.0:
            reject_codes.append("tp1_not_above_entry")
        else:
            rr_current = reward / risk
            max_entry_price = _max_entry_for_rr(
                stop_loss=float(selected_sl["price"]),
                tp1=float(selected_tp1["price"]),
                min_rr=definition.action.entry_ready_rr_ratio_min,
            )
            if max_entry_price is not None and max_entry_price > float(selected_sl["price"]):
                entry_zone_high = min(max_entry_price, float(selected_tp1["price"]))
                entry_zone_low = max(float(selected_sl["price"]) + atr, entry_zone_high - atr * 0.75)
                if entry_zone_low > entry_zone_high:
                    entry_zone_low = entry_zone_high
                ideal_entry = entry_price if entry_price <= entry_zone_high else entry_zone_high
                rr_ideal = _rr_for_entry(ideal_entry, float(selected_sl["price"]), float(selected_tp1["price"]))
                if entry_price > entry_zone_high:
                    distance_to_entry_zone_pct = (entry_price / entry_zone_high - 1.0) * 100.0

    risk_in_atr = None
    if selected_sl is not None:
        risk_in_atr = (entry_price - selected_sl["price"]) / atr
        if risk_in_atr > 3.0:
            reject_codes.append("sl_too_wide")

    sl_quality = _sl_quality(selected_sl, risk_in_atr)
    if sl_quality == "Weak":
        reject_codes.append("sl_quality_weak")

    plan_type, plan_reject_codes = _classify_plan_type(
        action_bucket=action_bucket,
        entry_ready_bucket=entry_ready_bucket,
        watch_setup_bucket=watch_setup_bucket,
        needs_review_bucket=needs_review_bucket,
        current_rr=rr_current,
        ideal_rr=rr_ideal,
        max_entry_price=max_entry_price,
        entry_zone_high=entry_zone_high,
        distance_to_entry_zone_pct=distance_to_entry_zone_pct,
        structural_reject_codes=tuple(reject_codes),
        min_rr=definition.action.entry_ready_rr_ratio_min,
    )
    reject_codes.extend(plan_reject_codes)
    plan_status = _status_for_plan_type(
        plan_type=plan_type,
        action_bucket=action_bucket,
        entry_ready_bucket=entry_ready_bucket,
        watch_setup_bucket=watch_setup_bucket,
        needs_review_bucket=needs_review_bucket,
    )
    plan_verdict = "Invalid" if _has_hard_reject(reject_codes) else "Valid"
    if plan_status == "Ready" and plan_verdict != "Valid":
        plan_status = "Draft"
    reject_codes_tuple = tuple(dict.fromkeys(reject_codes))
    reject_reason = _reject_reason(reject_codes_tuple)
    sl_basis = selected_sl["source"] if selected_sl else definition.risk_reward.stop.reference
    sl_safety = (
        f"ATR buffer {definition.risk_reward.stop.atr_buffer:g}; "
        "minimum 1 ATR; round-number buffer"
    )
    plan_note = _plan_note(entry_price, selected_sl, selected_tp1, rr_current, rr_ideal, plan_type, reject_reason)
    detail = {
        "entry": entry_price,
        "plan_type": plan_type,
        "atr": atr,
        "sl_candidates": sl_candidates,
        "selected_sl": selected_sl,
        "tp1_candidates": tp1_candidates,
        "selected_tp1": selected_tp1,
        "rr_current": rr_current,
        "rr_ideal": rr_ideal,
        "max_entry_price": max_entry_price,
        "entry_zone_low": entry_zone_low,
        "entry_zone_high": entry_zone_high,
        "min_rr_tp1": definition.action.entry_ready_rr_ratio_min,
        "risk_in_atr": risk_in_atr,
        "reject_codes": list(reject_codes_tuple),
    }
    return EntryPlanResult(
        plan_status=plan_status,
        plan_type=plan_type,
        entry_type=_entry_type_for_plan(plan_type),
        entry_price=entry_price,
        current_price=entry_price,
        entry_zone_low=entry_zone_low,
        entry_zone_high=entry_zone_high,
        max_entry_price=max_entry_price,
        distance_to_entry_zone_pct=distance_to_entry_zone_pct,
        stop_loss=selected_sl["price"] if selected_sl else None,
        tp1=selected_tp1["price"] if selected_tp1 else None,
        tp2=TP2_TRAILING_PLACEHOLDER,
        rr_tp1=rr_current,
        rr_current=rr_current,
        rr_ideal=rr_ideal,
        tp2_plan="Trailing stop later",
        trigger_condition=_trigger_condition(definition.signal_key, plan_type),
        plan_verdict=plan_verdict,
        plan_reject_codes=reject_codes_tuple,
        plan_reject_reason=reject_reason,
        sl_quality=sl_quality,
        sl_source=selected_sl["source"] if selected_sl else "",
        sl_basis=sl_basis,
        sl_safety=sl_safety,
        tp1_source=selected_tp1["source"] if selected_tp1 else "",
        plan_invalidation="SL hit or setup invalidation" if selected_sl else "SL unavailable",
        plan_note=plan_note,
        plan_detail=detail,
    )


def _build_sl_candidates(
    *,
    entry_price: float,
    atr: float,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
) -> list[dict[str, object]]:
    raw_candidates = _sl_candidate_sources(definition.signal_key, row, pool_entry)
    candidates: list[dict[str, object]] = []
    for source, reference in raw_candidates:
        stop = calculate_buffered_stop(entry_price, atr, reference, definition.risk_reward)
        if stop.stop_price is None or stop.stop_price >= entry_price:
            continue
        candidates.append(
            {
                "source": source,
                "reference": reference,
                "price": round(stop.stop_price, 4),
                "risk_in_atr": round(stop.risk_in_atr, 4) if stop.risk_in_atr is not None else None,
                "adjusted": stop.stop_adjusted,
            }
        )

    atr_stop = calculate_buffered_stop(
        entry_price,
        atr,
        entry_price - atr,
        definition.risk_reward,
        atr_buffer=0.0,
    )
    if atr_stop.stop_price is not None:
        candidates.append(
            {
                "source": "atr_minimum",
                "reference": entry_price - atr,
                "price": round(atr_stop.stop_price, 4),
                "risk_in_atr": round(atr_stop.risk_in_atr, 4) if atr_stop.risk_in_atr is not None else None,
                "adjusted": atr_stop.stop_adjusted,
            }
        )
    return _dedupe_candidates(candidates)


def _select_stop(candidates: list[dict[str, object]]) -> dict[str, object] | None:
    valid = [candidate for candidate in candidates if _to_float(candidate.get("price")) is not None]
    if not valid:
        return None
    preferred = [candidate for candidate in valid if candidate.get("source") != "atr_minimum"]
    if preferred:
        return min(preferred, key=lambda candidate: abs(float(candidate["risk_in_atr"] or 99.0) - 1.2))
    return min(valid, key=lambda candidate: float(candidate["risk_in_atr"] or 99.0))


def _build_tp1_candidates(
    *,
    entry_price: float,
    atr: float,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    definition: EntrySignalDefinition,
    selected_sl: dict[str, object] | None,
) -> list[dict[str, object]]:
    raw_candidates = _tp1_candidate_sources(definition.signal_key, row, pool_entry, entry_price, selected_sl)
    candidates: list[dict[str, object]] = []
    for source, resistance, mode in raw_candidates:
        if resistance is None or resistance <= entry_price:
            continue
        target = resistance if mode == "target" else resistance - atr * 0.2
        if target <= entry_price:
            continue
        candidates.append(
            {
                "source": source,
                "resistance": resistance,
                "price": round(target, 4),
            }
        )
    return _dedupe_candidates(candidates)


def _select_tp1(candidates: list[dict[str, object]]) -> dict[str, object] | None:
    valid = [candidate for candidate in candidates if _to_float(candidate.get("price")) is not None]
    if not valid:
        return None
    return min(valid, key=lambda candidate: float(candidate["price"]))


def _sl_candidate_sources(
    signal_key: str,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
) -> list[tuple[str, float | None]]:
    common = [
        ("low_since_detection", pool_entry.low_since_detection),
        ("snapshot_low", _to_float(pool_entry.snapshot_at_detection.get("low"))),
        ("structure_pivot_long_hl_price", _to_float(row.get("structure_pivot_long_hl_price"))),
    ]
    moving_support = [
        ("ema21_close", _to_float(row.get("ema21_close"))),
        ("sma50", _to_float(row.get("sma50"))),
        ("sma75", _to_float(row.get("sma75"))),
    ]
    if signal_key in {"orderly_pullback_entry", "pullback_resumption_entry", "power_gap_pullback_entry"}:
        return common + moving_support
    if signal_key == "momentum_acceleration_entry":
        return [
            ("acceleration_day_low", _to_float(row.get("low"))),
            ("low_since_detection", pool_entry.low_since_detection),
            ("snapshot_low", _to_float(pool_entry.snapshot_at_detection.get("low"))),
            ("ema21_close", _to_float(row.get("ema21_close"))),
        ]
    if signal_key == "accumulation_breakout_entry":
        return [
            ("breakout_day_low", _to_float(row.get("low"))),
            ("resistance_retest", _to_float(row.get("resistance_level_lookback"))),
            ("low_since_detection", pool_entry.low_since_detection),
            ("snapshot_low", _to_float(pool_entry.snapshot_at_detection.get("low"))),
        ]
    if signal_key == "early_cycle_recovery_entry":
        return [
            ("recovery_pivot_low", pool_entry.low_since_detection),
            ("snapshot_low", _to_float(pool_entry.snapshot_at_detection.get("low"))),
            ("sma50", _to_float(row.get("sma50"))),
            ("sma200", _to_float(row.get("sma200"))),
        ]
    return common + moving_support


def _tp1_candidate_sources(
    signal_key: str,
    row: dict[str, object],
    pool_entry: SignalPoolEntry,
    entry_price: float,
    selected_sl: dict[str, object] | None,
) -> list[tuple[str, float | None, str]]:
    structural = [
        ("resistance_level_lookback", _to_float(row.get("resistance_level_lookback")), "resistance"),
        ("rolling_20d_close_high", _to_float(row.get("rolling_20d_close_high")), "resistance"),
        ("high_since_detection", pool_entry.high_since_detection, "resistance"),
        (
            "snapshot_rolling_20d_close_high",
            _to_float(pool_entry.snapshot_at_detection.get("rolling_20d_close_high")),
            "resistance",
        ),
        ("high_52w", _to_float(row.get("high_52w")), "resistance"),
    ]
    rr_2x = _rr_target(entry_price, selected_sl, 2.0)
    rr_25x = _rr_target(entry_price, selected_sl, 2.5)
    measured_move = _measured_move_target(entry_price, selected_sl, pool_entry)
    momentum_8pct = entry_price * 1.08
    if signal_key in {"momentum_acceleration_entry", "accumulation_breakout_entry"}:
        return [
            ("rr_2x", rr_2x, "target"),
            ("measured_move", measured_move, "target"),
            ("momentum_8pct", momentum_8pct, "target"),
            ("high_52w", _to_float(row.get("high_52w")), "resistance"),
            ("rolling_20d_close_high", _to_float(row.get("rolling_20d_close_high")), "resistance"),
        ]
    if signal_key == "early_cycle_recovery_entry":
        return [
            ("rr_2x", rr_2x, "target"),
            ("rolling_20d_close_high", _to_float(row.get("rolling_20d_close_high")), "resistance"),
            ("resistance_level_lookback", _to_float(row.get("resistance_level_lookback")), "resistance"),
            ("high_52w", _to_float(row.get("high_52w")), "resistance"),
        ]
    if signal_key == "pullback_resumption_entry":
        return structural + [("rr_2x", rr_2x, "target")]
    if signal_key == "power_gap_pullback_entry":
        return [
            ("high_since_detection", pool_entry.high_since_detection, "resistance"),
            ("rolling_20d_close_high", _to_float(row.get("rolling_20d_close_high")), "resistance"),
            ("rr_25x", rr_25x, "target"),
            ("high_52w", _to_float(row.get("high_52w")), "resistance"),
        ]
    return structural + [("rr_2x", rr_2x, "target")]


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


def _measured_move_target(
    entry_price: float,
    selected_sl: dict[str, object] | None,
    pool_entry: SignalPoolEntry,
) -> float | None:
    rr_2x = _rr_target(entry_price, selected_sl, 2.0)
    snapshot_high = _to_float(pool_entry.snapshot_at_detection.get("high"))
    if snapshot_high is None or snapshot_high <= entry_price:
        return rr_2x
    if rr_2x is None:
        return snapshot_high
    return max(snapshot_high, rr_2x)


def _sl_quality(selected_sl: dict[str, object] | None, risk_in_atr: float | None) -> str:
    if selected_sl is None or risk_in_atr is None:
        return "Invalid"
    source = str(selected_sl.get("source", ""))
    if risk_in_atr < 1.0:
        return "Invalid"
    if source in {"low_since_detection", "snapshot_low", "structure_pivot_long_hl_price"}:
        return "Strong" if risk_in_atr <= 2.0 else "OK"
    if source in {"ema21_close", "sma50", "sma75"}:
        return "OK"
    return "Weak"


def _status_for_bucket(action_bucket: str, entry_ready_bucket: str, watch_setup_bucket: str, needs_review_bucket: str) -> str:
    if action_bucket == entry_ready_bucket:
        return "Ready"
    if action_bucket == watch_setup_bucket:
        return "Draft"
    if action_bucket == needs_review_bucket:
        return "Review"
    return "No Plan"


def _status_for_plan_type(
    *,
    plan_type: str,
    action_bucket: str,
    entry_ready_bucket: str,
    watch_setup_bucket: str,
    needs_review_bucket: str,
) -> str:
    if plan_type == "Ready Now" and action_bucket == entry_ready_bucket:
        return "Ready"
    if plan_type in {"Ready Now", "Wait Pullback", "Wait Trigger"} and action_bucket in {
        entry_ready_bucket,
        watch_setup_bucket,
    }:
        return "Draft"
    if action_bucket == needs_review_bucket:
        return "Review"
    return _status_for_bucket(action_bucket, entry_ready_bucket, watch_setup_bucket, needs_review_bucket)


def _classify_plan_type(
    *,
    action_bucket: str,
    entry_ready_bucket: str,
    watch_setup_bucket: str,
    needs_review_bucket: str,
    current_rr: float | None,
    ideal_rr: float | None,
    max_entry_price: float | None,
    entry_zone_high: float | None,
    distance_to_entry_zone_pct: float | None,
    structural_reject_codes: tuple[str, ...],
    min_rr: float,
) -> tuple[str, list[str]]:
    if structural_reject_codes:
        return "Invalid", []
    if current_rr is not None and current_rr >= min_rr:
        if action_bucket == entry_ready_bucket:
            return "Ready Now", []
        if action_bucket in {watch_setup_bucket, needs_review_bucket}:
            return "Wait Trigger", []
    if (
        max_entry_price is not None
        and entry_zone_high is not None
        and ideal_rr is not None
        and ideal_rr >= min_rr
    ):
        distance = 0.0 if distance_to_entry_zone_pct is None else float(distance_to_entry_zone_pct)
        if distance <= DEFAULT_PULLBACK_DISTANCE_LIMIT_PCT:
            return "Wait Pullback", ["rr_current_below_min"]
        return "Poor R/R", ["entry_zone_too_far", "rr_current_below_min"]
    return "Poor R/R", ["rr_tp1_below_min"]


def _has_hard_reject(codes: list[str]) -> bool:
    hard_codes = {
        "entry_or_atr_unavailable",
        "inactive_pool",
        "sl_unavailable",
        "tp1_unavailable",
        "sl_not_below_entry",
        "tp1_not_above_entry",
        "sl_too_wide",
        "sl_quality_weak",
    }
    return any(code in hard_codes for code in codes)


def _max_entry_for_rr(*, stop_loss: float, tp1: float, min_rr: float) -> float | None:
    if min_rr <= 0.0 or tp1 <= stop_loss:
        return None
    return (tp1 + min_rr * stop_loss) / (1.0 + min_rr)


def _rr_for_entry(entry_price: float, stop_loss: float, tp1: float) -> float | None:
    risk = entry_price - stop_loss
    reward = tp1 - entry_price
    if risk <= 0.0 or reward <= 0.0:
        return None
    return reward / risk


def _entry_type_for_plan(plan_type: str) -> str:
    if plan_type == "Ready Now":
        return "Current Close"
    if plan_type == "Wait Pullback":
        return "Limit Pullback"
    if plan_type == "Wait Trigger":
        return "Trigger"
    return "No Entry"


def _trigger_condition(signal_key: str, plan_type: str) -> str:
    if plan_type == "Ready Now":
        return "Current daily setup confirms entry"
    if plan_type == "Wait Pullback":
        return "Wait for price to enter the entry zone, then confirm intraday reversal"
    if signal_key in {"accumulation_breakout_entry", "momentum_acceleration_entry"}:
        return "Wait for breakout/follow-through confirmation with volume"
    if signal_key in {"orderly_pullback_entry", "pullback_resumption_entry", "power_gap_pullback_entry"}:
        return "Wait for pullback reversal or reclaim confirmation"
    if signal_key == "early_cycle_recovery_entry":
        return "Wait for recovery reclaim to hold and reversal confirmation"
    return "Wait for signal-specific trigger confirmation"


def _reject_reason(codes: tuple[str, ...]) -> str:
    labels = {
        "entry_or_atr_unavailable": "entry price or ATR unavailable",
        "inactive_pool": "pool is inactive",
        "sl_unavailable": "SL candidate unavailable",
        "tp1_unavailable": "TP1 resistance unavailable",
        "sl_not_below_entry": "SL is not below entry",
        "tp1_not_above_entry": "TP1 is not above entry",
        "rr_tp1_below_min": "R/R to TP1 is below the signal threshold",
        "rr_current_below_min": "current price R/R is below the signal threshold",
        "entry_zone_too_far": "required entry zone is too far below current price",
        "sl_too_wide": "SL is too wide in ATR terms",
        "sl_quality_weak": "SL support quality is weak",
    }
    return "; ".join(labels.get(code, code) for code in codes)


def _plan_note(
    entry_price: float,
    selected_sl: dict[str, object] | None,
    selected_tp1: dict[str, object] | None,
    rr_current: float | None,
    rr_ideal: float | None,
    plan_type: str,
    reject_reason: str,
) -> str:
    if selected_sl is None or selected_tp1 is None or rr_current is None:
        return f"Review plan incomplete: {reject_reason}"
    return (
        f"{plan_type}: current {entry_price:.2f}, SL {float(selected_sl['price']):.2f}, "
        f"TP1 {float(selected_tp1['price']):.2f}, current R/R {rr_current:.2f}, "
        f"ideal R/R {_format_optional_rr(rr_ideal)}"
    )


def _format_optional_rr(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def _empty_plan(
    *,
    plan_status: str,
    verdict: str,
    reject_codes: tuple[str, ...],
    reject_reason: str,
    plan_invalidation: str,
) -> EntryPlanResult:
    detail = {"reject_codes": list(reject_codes)}
    return EntryPlanResult(
        plan_status=plan_status,
        plan_type="Invalid",
        entry_type="",
        entry_price=None,
        current_price=None,
        entry_zone_low=None,
        entry_zone_high=None,
        max_entry_price=None,
        distance_to_entry_zone_pct=None,
        stop_loss=None,
        tp1=None,
        tp2=TP2_TRAILING_PLACEHOLDER,
        rr_tp1=None,
        rr_current=None,
        rr_ideal=None,
        tp2_plan="Trailing stop later",
        trigger_condition="",
        plan_verdict=verdict,
        plan_reject_codes=reject_codes,
        plan_reject_reason=reject_reason,
        sl_quality="Invalid",
        sl_source="",
        sl_basis="",
        sl_safety="",
        tp1_source="",
        plan_invalidation=plan_invalidation,
        plan_note=f"Review plan incomplete: {reject_reason}",
        plan_detail=detail,
    )


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
