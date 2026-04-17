from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pandas as pd


ENTRY_SIGNAL_STATUS_VALUES = ("enabled", "disabled")


@dataclass(frozen=True, slots=True)
class EntrySignalDefinition:
    signal_name: str
    display_name: str
    description: str
    evaluator: Callable[[pd.Series], bool]
    note_builder: Callable[[pd.Series], str]
    risk_builder: Callable[[pd.Series], str]


@dataclass(slots=True)
class EntrySignalConfig:
    status_map: dict[str, str] = field(default_factory=dict)
    default_selected_signal_names: tuple[str, ...] | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "EntrySignalConfig":
        data = payload if isinstance(payload, dict) else {}
        return cls(
            status_map=_normalize_signal_status_map(data.get("signal_status_map")),
            default_selected_signal_names=_normalize_signal_names(data.get("default_selected_signal_names"))
            if "default_selected_signal_names" in data
            else None,
        )

    def enabled_signal_names(self) -> tuple[str, ...]:
        return tuple(
            name
            for name in ENTRY_SIGNAL_REGISTRY
            if self.status_map.get(name, "enabled") == "enabled"
        )

    def startup_selected_signal_names(self) -> tuple[str, ...]:
        enabled = self.enabled_signal_names()
        if self.default_selected_signal_names is None:
            return enabled
        enabled_set = set(enabled)
        return tuple(name for name in self.default_selected_signal_names if name in enabled_set)


def _pocket_pivot_entry(row: pd.Series) -> bool:
    return _as_bool(row.get("pocket_pivot")) and _gt(row.get("close"), row.get("sma50"))


def _structure_pivot_breakout_entry(row: pd.Series) -> bool:
    return _as_bool(row.get("structure_pivot_long_breakout_first_day"))


def _pullback_low_risk_zone(row: pd.Series) -> bool:
    return (
        (_as_bool(row.get("atr_21ema_zone")) or _as_bool(row.get("atr_50sma_zone")))
        and _gt(row.get("rs21"), 50.0)
        and not _lt(row.get("dcr_percent"), 30.0)
    )


def _volume_reclaim_entry(row: pd.Series) -> bool:
    return _gt(row.get("close"), row.get("sma50")) and _gte(row.get("rel_volume"), 1.4) and _gt(row.get("daily_change_pct"), 0.0)


def _note(text: str) -> Callable[[pd.Series], str]:
    return lambda _row: text


def _risk_from_ema21_or_sma50(row: pd.Series) -> str:
    for column in ("ema21_low", "sma50", "structure_pivot_long_hl_price"):
        value = row.get(column)
        if _is_number(value):
            return f"{column}: {float(value):.2f}"
    return ""


ENTRY_SIGNAL_REGISTRY: dict[str, EntrySignalDefinition] = {
    "Pocket Pivot Entry": EntrySignalDefinition(
        signal_name="Pocket Pivot Entry",
        display_name="Pocket Pivot Entry",
        description="Pocket pivot day while price is above SMA50.",
        evaluator=_pocket_pivot_entry,
        note_builder=_note("Pocket pivot with close above SMA50."),
        risk_builder=_risk_from_ema21_or_sma50,
    ),
    "Structure Pivot Breakout Entry": EntrySignalDefinition(
        signal_name="Structure Pivot Breakout Entry",
        display_name="Structure Pivot Breakout",
        description="First close breakout above the active bullish structure pivot line.",
        evaluator=_structure_pivot_breakout_entry,
        note_builder=_note("First-day bullish structure pivot breakout."),
        risk_builder=_risk_from_ema21_or_sma50,
    ),
    "Pullback Low-Risk Zone": EntrySignalDefinition(
        signal_name="Pullback Low-Risk Zone",
        display_name="Pullback Low-Risk Zone",
        description="Price is near the 21EMA or 50SMA zone while RS remains constructive.",
        evaluator=_pullback_low_risk_zone,
        note_builder=_note("Near 21EMA/50SMA support zone with RS holding."),
        risk_builder=_risk_from_ema21_or_sma50,
    ),
    "Volume Reclaim Entry": EntrySignalDefinition(
        signal_name="Volume Reclaim Entry",
        display_name="Volume Reclaim Entry",
        description="Positive close above SMA50 with relative volume confirmation.",
        evaluator=_volume_reclaim_entry,
        note_builder=_note("Close above SMA50 with 1.4x+ relative volume."),
        risk_builder=_risk_from_ema21_or_sma50,
    ),
}


def _normalize_signal_status_map(raw_map: object) -> dict[str, str]:
    if raw_map is None:
        return {}
    if not isinstance(raw_map, dict):
        raise ValueError("entry signal_status_map must be a mapping of signal name to status")
    normalized: dict[str, str] = {}
    for raw_name, raw_status in raw_map.items():
        signal_name = str(raw_name).strip()
        if not signal_name:
            continue
        if signal_name not in ENTRY_SIGNAL_REGISTRY:
            raise ValueError(f"entry signal_status_map references unknown signal: {signal_name}")
        status = str(raw_status).strip().lower().replace("-", "_").replace(" ", "_")
        status = {"enabled": "enabled", "active": "enabled", "disabled": "disabled"}.get(status, status)
        if status not in ENTRY_SIGNAL_STATUS_VALUES:
            raise ValueError(f"entry signal_status_map status for '{signal_name}' must be one of: {', '.join(ENTRY_SIGNAL_STATUS_VALUES)}")
        normalized[signal_name] = status
    return normalized


def _normalize_signal_names(raw_names: object) -> tuple[str, ...]:
    if raw_names is None:
        return tuple()
    return tuple(
        dict.fromkeys(
            str(name).strip()
            for name in raw_names
            if str(name).strip() and str(name).strip() in ENTRY_SIGNAL_REGISTRY
        )
    )


def _as_bool(value: object) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except TypeError:
        pass
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _is_number(value: object) -> bool:
    try:
        if value is None or pd.isna(value):
            return False
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _gt(left: object, right: object) -> bool:
    return _is_number(left) and _is_number(right) and float(left) > float(right)


def _gte(left: object, right: object) -> bool:
    return _is_number(left) and _is_number(right) and float(left) >= float(right)


def _lt(left: object, right: object) -> bool:
    return _is_number(left) and _is_number(right) and float(left) < float(right)
