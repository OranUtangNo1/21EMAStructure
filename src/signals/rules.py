from __future__ import annotations

from dataclasses import dataclass, field as dc_field


ENTRY_SIGNAL_STATUS_VALUES = ("enabled", "disabled")
ENTRY_SIGNAL_REGISTRY: dict[str, "EntrySignalDefinition"] = {}


@dataclass(frozen=True, slots=True)
class InvalidationRule:
    field: str
    condition: str
    reference: str | None = None
    reference_multiplier: float = 1.0
    threshold: float | None = None


@dataclass(frozen=True, slots=True)
class EntrySignalPoolConfig:
    preset_sources: tuple[str, ...]
    detection_window_days: int
    invalidation: tuple[InvalidationRule, ...]
    snapshot_fields: tuple[str, ...]
    pool_tracking: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AxisComponentConfig:
    field: str
    weight: float
    breakpoints: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class AxisIndicatorConfig:
    weight: float
    field: str | None = None
    breakpoints: tuple[tuple[float, float], ...] = ()
    components: dict[str, AxisComponentConfig] = dc_field(default_factory=dict)
    note: str = ""

    @property
    def composite(self) -> bool:
        return bool(self.components)


@dataclass(frozen=True, slots=True)
class AxisConfig:
    indicators: dict[str, AxisIndicatorConfig]


@dataclass(frozen=True, slots=True)
class RiskRewardStopConfig:
    reference: str
    atr_buffer: float
    min_distance_atr: float
    structural_penalty: float


@dataclass(frozen=True, slots=True)
class RiskRewardTargetConfig:
    primary: str
    secondary: str | None = None
    fallback: str | None = None


@dataclass(frozen=True, slots=True)
class RiskRewardConfig:
    stop: RiskRewardStopConfig
    reward: RiskRewardTargetConfig
    scoring_breakpoints: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class EntryStrengthConfig:
    setup_maturity_weight: float
    timing_weight: float
    risk_reward_weight: float
    min_axis_threshold: float
    capped_strength: float


@dataclass(frozen=True, slots=True)
class DisplayThresholdConfig:
    signal_detected: float
    approaching: float
    tracking: float

    def classify(self, entry_strength: float) -> str:
        strength = float(entry_strength)
        if strength >= self.signal_detected:
            return "Signal Detected"
        if strength >= self.approaching:
            return "Approaching"
        return "Tracking"


@dataclass(frozen=True, slots=True)
class EntryActionConfig:
    entry_ready_entry_strength_min: float = 50.0
    entry_ready_timing_min: float = 50.0
    entry_ready_risk_reward_min: float = 50.0
    entry_ready_rr_ratio_min: float = 2.0
    entry_ready_setup_maturity_min: float = 40.0
    watch_setup_setup_maturity_min: float = 45.0
    watch_setup_risk_reward_min: float = 30.0


@dataclass(frozen=True, slots=True)
class EntrySignalContextGuardConfig:
    enabled: bool
    weak_market_score_threshold: float | None
    cap_below_signal_detected: bool
    earnings_warning_field: str | None
    earnings_today_field: str | None
    signal_market_score_thresholds: dict[str, float | None] = dc_field(default_factory=dict)

    def weak_market_threshold_for(self, signal_name: str) -> float | None:
        return self.signal_market_score_thresholds.get(signal_name, self.weak_market_score_threshold)


@dataclass(frozen=True, slots=True)
class EntrySignalDefinition:
    signal_key: str
    display_name: str
    signal_version: str
    description: str
    pool: EntrySignalPoolConfig
    setup_maturity: AxisConfig
    timing: AxisConfig
    risk_reward: RiskRewardConfig
    entry_strength: EntryStrengthConfig
    display: DisplayThresholdConfig
    action: EntryActionConfig = dc_field(default_factory=EntryActionConfig)


@dataclass(slots=True)
class EntrySignalConfig:
    definitions: dict[str, EntrySignalDefinition] = dc_field(default_factory=dict)
    status_map: dict[str, str] = dc_field(default_factory=dict)
    default_selected_signal_names: tuple[str, ...] | None = None
    context_guard: EntrySignalContextGuardConfig = dc_field(
        default_factory=lambda: EntrySignalContextGuardConfig(
            enabled=False,
            weak_market_score_threshold=None,
            cap_below_signal_detected=True,
            earnings_warning_field=None,
            earnings_today_field=None,
            signal_market_score_thresholds={},
        )
    )

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "EntrySignalConfig":
        data = payload if isinstance(payload, dict) else {}
        definitions = _normalize_definitions(data.get("definitions"))
        status_map = _normalize_signal_status_map(data.get("signal_status_map"), definitions)
        return cls(
            definitions=definitions,
            status_map=status_map,
            default_selected_signal_names=_normalize_signal_names(
                data.get("default_selected_signal_names"),
                valid_names=set(definitions),
            )
            if "default_selected_signal_names" in data
            else None,
            context_guard=_normalize_context_guard_config(data.get("context_guard")),
        )

    def enabled_signal_names(self) -> tuple[str, ...]:
        return tuple(
            name
            for name in self.definitions
            if self.status_map.get(name, "enabled") == "enabled"
        )

    def startup_selected_signal_names(self) -> tuple[str, ...]:
        enabled = self.enabled_signal_names()
        if self.default_selected_signal_names is None:
            return enabled
        enabled_set = set(enabled)
        return tuple(name for name in self.default_selected_signal_names if name in enabled_set)

    def definition_for(self, signal_name: str) -> EntrySignalDefinition:
        return self.definitions[signal_name]

    def resolved_definitions(self) -> dict[str, EntrySignalDefinition]:
        return dict(self.definitions)


def evaluate_invalidation(definition: EntrySignalDefinition, row: dict[str, object]) -> str | None:
    for rule in definition.pool.invalidation:
        if _rule_matches(rule, row):
            return _rule_reason(rule)
    return None


def _normalize_definitions(raw_payload: object) -> dict[str, EntrySignalDefinition]:
    if raw_payload is None:
        return {}
    if not isinstance(raw_payload, dict):
        raise ValueError("entry_signals.definitions must be a mapping of signal key to definition")
    definitions: dict[str, EntrySignalDefinition] = {}
    for raw_name, raw_value in raw_payload.items():
        signal_key = str(raw_name).strip()
        if not signal_key:
            continue
        if not isinstance(raw_value, dict):
            raise ValueError(f"entry_signals.definitions.{signal_key} must be a mapping")
        definitions[signal_key] = EntrySignalDefinition(
            signal_key=signal_key,
            display_name=_required_text(raw_value, "display_name", signal_key),
            signal_version=_required_text(raw_value, "signal_version", signal_key),
            description=str(raw_value.get("description", "")).strip(),
            pool=_normalize_pool_config(signal_key, raw_value.get("pool")),
            setup_maturity=_normalize_axis_config(signal_key, "setup_maturity", raw_value.get("setup_maturity")),
            timing=_normalize_axis_config(signal_key, "timing", raw_value.get("timing")),
            risk_reward=_normalize_risk_reward_config(signal_key, raw_value.get("risk_reward")),
            entry_strength=_normalize_entry_strength_config(signal_key, raw_value.get("entry_strength")),
            display=_normalize_display_config(signal_key, raw_value.get("display")),
            action=_normalize_action_config(signal_key, raw_value.get("action")),
        )
    return definitions


def _normalize_pool_config(signal_key: str, raw_value: object) -> EntrySignalPoolConfig:
    if not isinstance(raw_value, dict):
        raise ValueError(f"entry_signals.definitions.{signal_key}.pool must be a mapping")
    return EntrySignalPoolConfig(
        preset_sources=_normalize_name_list(raw_value.get("preset_sources"), f"{signal_key}.pool.preset_sources"),
        detection_window_days=_normalize_positive_int(
            raw_value.get("detection_window_days"),
            field_name=f"{signal_key}.pool.detection_window_days",
        ),
        invalidation=_normalize_invalidation_rules(signal_key, raw_value.get("invalidation")),
        snapshot_fields=_normalize_name_list(raw_value.get("snapshot_fields"), f"{signal_key}.pool.snapshot_fields"),
        pool_tracking=_normalize_name_list(raw_value.get("pool_tracking"), f"{signal_key}.pool.pool_tracking"),
    )


def _normalize_invalidation_rules(signal_key: str, raw_value: object) -> tuple[InvalidationRule, ...]:
    if raw_value is None:
        return tuple()
    if not isinstance(raw_value, list):
        raise ValueError(f"entry_signals.definitions.{signal_key}.pool.invalidation must be a list")
    rules: list[InvalidationRule] = []
    for index, item in enumerate(raw_value):
        if not isinstance(item, dict):
            raise ValueError(f"{signal_key}.pool.invalidation[{index}] must be a mapping")
        field_name = str(item.get("field", "")).strip()
        condition = str(item.get("condition", "")).strip()
        reference = str(item.get("reference", "")).strip() or None
        reference_multiplier = _normalize_optional_float(item.get("reference_multiplier"))
        threshold = _normalize_optional_float(item.get("threshold"))
        if not field_name or not condition:
            raise ValueError(f"{signal_key}.pool.invalidation[{index}] requires field and condition")
        rules.append(
            InvalidationRule(
                field=field_name,
                condition=condition,
                reference=reference,
                reference_multiplier=reference_multiplier if reference_multiplier is not None else 1.0,
                threshold=threshold,
            )
        )
    return tuple(rules)


def _normalize_axis_config(signal_key: str, axis_name: str, raw_value: object) -> AxisConfig:
    if not isinstance(raw_value, dict):
        raise ValueError(f"entry_signals.definitions.{signal_key}.{axis_name} must be a mapping")
    indicators_raw = raw_value.get("indicators")
    if not isinstance(indicators_raw, dict) or not indicators_raw:
        raise ValueError(f"entry_signals.definitions.{signal_key}.{axis_name}.indicators must be a mapping")
    indicators: dict[str, AxisIndicatorConfig] = {}
    for indicator_name, indicator_value in indicators_raw.items():
        if not isinstance(indicator_value, dict):
            raise ValueError(f"{signal_key}.{axis_name}.indicators.{indicator_name} must be a mapping")
        weight = _normalize_float(
            indicator_value.get("weight"),
            field_name=f"{signal_key}.{axis_name}.indicators.{indicator_name}.weight",
        )
        components_raw = indicator_value.get("components")
        if components_raw is not None:
            if not isinstance(components_raw, dict) or not components_raw:
                raise ValueError(f"{signal_key}.{axis_name}.indicators.{indicator_name}.components must be a mapping")
            components: dict[str, AxisComponentConfig] = {}
            for component_name, component_value in components_raw.items():
                if not isinstance(component_value, dict):
                    raise ValueError(
                        f"{signal_key}.{axis_name}.indicators.{indicator_name}.components.{component_name} must be a mapping"
                    )
                components[component_name] = AxisComponentConfig(
                    field=_required_text(component_value, "field", f"{signal_key}.{axis_name}.{indicator_name}.{component_name}"),
                    weight=_normalize_float(
                        component_value.get("weight"),
                        field_name=f"{signal_key}.{axis_name}.indicators.{indicator_name}.components.{component_name}.weight",
                    ),
                    breakpoints=_normalize_breakpoints(
                        component_value.get("breakpoints"),
                        field_name=f"{signal_key}.{axis_name}.indicators.{indicator_name}.components.{component_name}.breakpoints",
                    ),
                )
            indicators[str(indicator_name)] = AxisIndicatorConfig(
                weight=weight,
                components=components,
                note=str(indicator_value.get("note", "")).strip(),
            )
            continue
        field = str(indicator_value.get("field", "")).strip() or None
        breakpoints = _normalize_breakpoints(
            indicator_value.get("breakpoints"),
            field_name=f"{signal_key}.{axis_name}.indicators.{indicator_name}.breakpoints",
            required=field is not None,
        )
        indicators[str(indicator_name)] = AxisIndicatorConfig(
            weight=weight,
            field=field,
            breakpoints=breakpoints,
            note=str(indicator_value.get("note", "")).strip(),
        )
    return AxisConfig(indicators=indicators)


def _normalize_risk_reward_config(signal_key: str, raw_value: object) -> RiskRewardConfig:
    if not isinstance(raw_value, dict):
        raise ValueError(f"entry_signals.definitions.{signal_key}.risk_reward must be a mapping")
    stop_raw = raw_value.get("stop")
    reward_raw = raw_value.get("reward")
    scoring_raw = raw_value.get("scoring")
    if not isinstance(stop_raw, dict) or not isinstance(reward_raw, dict) or not isinstance(scoring_raw, dict):
        raise ValueError(f"entry_signals.definitions.{signal_key}.risk_reward must include stop/reward/scoring mappings")
    return RiskRewardConfig(
        stop=RiskRewardStopConfig(
            reference=_required_text(stop_raw, "reference", f"{signal_key}.risk_reward.stop"),
            atr_buffer=_normalize_float(stop_raw.get("atr_buffer"), field_name=f"{signal_key}.risk_reward.stop.atr_buffer"),
            min_distance_atr=_normalize_float(
                stop_raw.get("min_distance_atr"),
                field_name=f"{signal_key}.risk_reward.stop.min_distance_atr",
            ),
            structural_penalty=_normalize_float(
                stop_raw.get("structural_penalty"),
                field_name=f"{signal_key}.risk_reward.stop.structural_penalty",
            ),
        ),
        reward=RiskRewardTargetConfig(
            primary=_required_text(reward_raw, "primary", f"{signal_key}.risk_reward.reward"),
            secondary=str(reward_raw.get("secondary", "")).strip() or None,
            fallback=str(reward_raw.get("fallback", "")).strip() or None,
        ),
        scoring_breakpoints=_normalize_breakpoints(
            scoring_raw.get("breakpoints"),
            field_name=f"{signal_key}.risk_reward.scoring.breakpoints",
        ),
    )


def _normalize_entry_strength_config(signal_key: str, raw_value: object) -> EntryStrengthConfig:
    if not isinstance(raw_value, dict):
        raise ValueError(f"entry_signals.definitions.{signal_key}.entry_strength must be a mapping")
    weights_raw = raw_value.get("weights")
    floor_gate_raw = raw_value.get("floor_gate")
    if not isinstance(weights_raw, dict) or not isinstance(floor_gate_raw, dict):
        raise ValueError(f"entry_signals.definitions.{signal_key}.entry_strength must include weights and floor_gate")
    return EntryStrengthConfig(
        setup_maturity_weight=_normalize_float(
            weights_raw.get("setup_maturity"),
            field_name=f"{signal_key}.entry_strength.weights.setup_maturity",
        ),
        timing_weight=_normalize_float(
            weights_raw.get("timing"),
            field_name=f"{signal_key}.entry_strength.weights.timing",
        ),
        risk_reward_weight=_normalize_float(
            weights_raw.get("risk_reward"),
            field_name=f"{signal_key}.entry_strength.weights.risk_reward",
        ),
        min_axis_threshold=_normalize_float(
            floor_gate_raw.get("min_axis_threshold"),
            field_name=f"{signal_key}.entry_strength.floor_gate.min_axis_threshold",
        ),
        capped_strength=_normalize_float(
            floor_gate_raw.get("capped_strength"),
            field_name=f"{signal_key}.entry_strength.floor_gate.capped_strength",
        ),
    )


def _normalize_display_config(signal_key: str, raw_value: object) -> DisplayThresholdConfig:
    if not isinstance(raw_value, dict):
        raise ValueError(f"entry_signals.definitions.{signal_key}.display must be a mapping")
    thresholds_raw = raw_value.get("thresholds")
    if not isinstance(thresholds_raw, dict):
        raise ValueError(f"entry_signals.definitions.{signal_key}.display.thresholds must be a mapping")
    return DisplayThresholdConfig(
        signal_detected=_normalize_float(
            thresholds_raw.get("signal_detected"),
            field_name=f"{signal_key}.display.thresholds.signal_detected",
        ),
        approaching=_normalize_float(
            thresholds_raw.get("approaching"),
            field_name=f"{signal_key}.display.thresholds.approaching",
        ),
        tracking=_normalize_float(
            thresholds_raw.get("tracking"),
            field_name=f"{signal_key}.display.thresholds.tracking",
        ),
    )


def _normalize_action_config(signal_key: str, raw_value: object) -> EntryActionConfig:
    if raw_value is None:
        return EntryActionConfig()
    if not isinstance(raw_value, dict):
        raise ValueError(f"entry_signals.definitions.{signal_key}.action must be a mapping")
    entry_ready_raw = raw_value.get("entry_ready", {})
    watch_setup_raw = raw_value.get("watch_setup", {})
    if not isinstance(entry_ready_raw, dict) or not isinstance(watch_setup_raw, dict):
        raise ValueError(f"entry_signals.definitions.{signal_key}.action entry_ready/watch_setup must be mappings")
    defaults = EntryActionConfig()
    return EntryActionConfig(
        entry_ready_entry_strength_min=_normalize_float_with_default(
            entry_ready_raw.get("entry_strength_min"),
            defaults.entry_ready_entry_strength_min,
            field_name=f"{signal_key}.action.entry_ready.entry_strength_min",
        ),
        entry_ready_timing_min=_normalize_float_with_default(
            entry_ready_raw.get("timing_min"),
            defaults.entry_ready_timing_min,
            field_name=f"{signal_key}.action.entry_ready.timing_min",
        ),
        entry_ready_risk_reward_min=_normalize_float_with_default(
            entry_ready_raw.get("risk_reward_min"),
            defaults.entry_ready_risk_reward_min,
            field_name=f"{signal_key}.action.entry_ready.risk_reward_min",
        ),
        entry_ready_rr_ratio_min=_normalize_float_with_default(
            entry_ready_raw.get("rr_ratio_min"),
            defaults.entry_ready_rr_ratio_min,
            field_name=f"{signal_key}.action.entry_ready.rr_ratio_min",
        ),
        entry_ready_setup_maturity_min=_normalize_float_with_default(
            entry_ready_raw.get("setup_maturity_min"),
            defaults.entry_ready_setup_maturity_min,
            field_name=f"{signal_key}.action.entry_ready.setup_maturity_min",
        ),
        watch_setup_setup_maturity_min=_normalize_float_with_default(
            watch_setup_raw.get("setup_maturity_min"),
            defaults.watch_setup_setup_maturity_min,
            field_name=f"{signal_key}.action.watch_setup.setup_maturity_min",
        ),
        watch_setup_risk_reward_min=_normalize_float_with_default(
            watch_setup_raw.get("risk_reward_min"),
            defaults.watch_setup_risk_reward_min,
            field_name=f"{signal_key}.action.watch_setup.risk_reward_min",
        ),
    )


def _normalize_context_guard_config(raw_value: object) -> EntrySignalContextGuardConfig:
    if raw_value is None:
        return EntrySignalContextGuardConfig(
            enabled=False,
            weak_market_score_threshold=None,
            cap_below_signal_detected=True,
            earnings_warning_field=None,
            earnings_today_field=None,
            signal_market_score_thresholds={},
        )
    if not isinstance(raw_value, dict):
        raise ValueError("entry_signals.context_guard must be a mapping")
    earnings_raw = raw_value.get("earnings")
    earnings_data = earnings_raw if isinstance(earnings_raw, dict) else {}
    signal_market_score_thresholds: dict[str, float | None] = {}
    overrides_raw = raw_value.get("signal_overrides")
    if overrides_raw is not None:
        if not isinstance(overrides_raw, dict):
            raise ValueError("entry_signals.context_guard.signal_overrides must be a mapping")
        for raw_signal_name, raw_override in overrides_raw.items():
            signal_name = str(raw_signal_name).strip()
            if not signal_name:
                continue
            if not isinstance(raw_override, dict):
                raise ValueError(f"entry_signals.context_guard.signal_overrides.{signal_name} must be a mapping")
            signal_market_score_thresholds[signal_name] = _normalize_optional_float(
                raw_override.get("weak_market_score_threshold")
            )
    return EntrySignalContextGuardConfig(
        enabled=bool(raw_value.get("enabled", False)),
        weak_market_score_threshold=_normalize_optional_float(raw_value.get("weak_market_score_threshold")),
        cap_below_signal_detected=bool(raw_value.get("cap_below_signal_detected", True)),
        earnings_warning_field=str(earnings_data.get("warning_field", "")).strip() or None,
        earnings_today_field=str(earnings_data.get("today_field", "")).strip() or None,
        signal_market_score_thresholds=signal_market_score_thresholds,
    )


def _normalize_signal_status_map(
    raw_map: object,
    definitions: dict[str, EntrySignalDefinition],
) -> dict[str, str]:
    if raw_map is None:
        return {}
    if not isinstance(raw_map, dict):
        raise ValueError("entry_signals.signal_status_map must be a mapping of signal key to status")
    normalized: dict[str, str] = {}
    valid_names = set(definitions)
    for raw_name, raw_status in raw_map.items():
        signal_name = str(raw_name).strip()
        if not signal_name:
            continue
        if signal_name not in valid_names:
            raise ValueError(f"entry_signals.signal_status_map references unknown signal: {signal_name}")
        status = str(raw_status).strip().lower().replace("-", "_").replace(" ", "_")
        status = {"enabled": "enabled", "active": "enabled", "disabled": "disabled"}.get(status, status)
        if status not in ENTRY_SIGNAL_STATUS_VALUES:
            raise ValueError(
                f"entry_signals.signal_status_map status for '{signal_name}' must be one of: {', '.join(ENTRY_SIGNAL_STATUS_VALUES)}"
            )
        normalized[signal_name] = status
    return normalized


def _normalize_signal_names(raw_names: object, *, valid_names: set[str]) -> tuple[str, ...]:
    if raw_names is None:
        return tuple()
    if not isinstance(raw_names, (list, tuple, set)):
        raise ValueError("entry_signals.default_selected_signal_names must be a list")
    return tuple(
        dict.fromkeys(
            str(name).strip()
            for name in raw_names
            if str(name).strip() and str(name).strip() in valid_names
        )
    )


def _normalize_name_list(raw_value: object, field_name: str) -> tuple[str, ...]:
    if raw_value is None:
        return tuple()
    if not isinstance(raw_value, (list, tuple, set)):
        raise ValueError(f"{field_name} must be a list")
    return tuple(dict.fromkeys(str(value).strip() for value in raw_value if str(value).strip()))


def _normalize_breakpoints(
    raw_value: object,
    *,
    field_name: str,
    required: bool = True,
) -> tuple[tuple[float, float], ...]:
    if raw_value is None:
        if required:
            raise ValueError(f"{field_name} must be provided")
        return tuple()
    if not isinstance(raw_value, list) or not raw_value:
        raise ValueError(f"{field_name} must be a non-empty list")
    breakpoints: list[tuple[float, float]] = []
    for index, item in enumerate(raw_value):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError(f"{field_name}[{index}] must be a [x, y] pair")
        breakpoints.append(
            (
                _normalize_float(item[0], field_name=f"{field_name}[{index}][0]"),
                _normalize_float(item[1], field_name=f"{field_name}[{index}][1]"),
            )
        )
    breakpoints.sort(key=lambda pair: pair[0])
    return tuple(breakpoints)


def _normalize_positive_int(value: object, *, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if parsed < 1:
        raise ValueError(f"{field_name} must be >= 1")
    return parsed


def _normalize_float(value: object, *, field_name: str) -> float:
    parsed = _normalize_optional_float(value)
    if parsed is None:
        raise ValueError(f"{field_name} must be numeric")
    return parsed


def _normalize_float_with_default(value: object, default: float, *, field_name: str) -> float:
    if value is None:
        return float(default)
    return _normalize_float(value, field_name=field_name)


def _normalize_optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _required_text(payload: dict[str, object], key: str, field_name: str) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise ValueError(f"{field_name}.{key} must be a non-empty string")
    return value


def _rule_matches(rule: InvalidationRule, row: dict[str, object]) -> bool:
    left = _normalize_optional_float(row.get(rule.field))
    right = _normalize_optional_float(row.get(rule.reference)) if rule.reference else rule.threshold
    if left is None or right is None:
        return False
    if rule.reference:
        right = right * rule.reference_multiplier
    if rule.condition == "below":
        return left < right
    if rule.condition == "above":
        return left > right
    if rule.condition == "at_or_below":
        return left <= right
    if rule.condition == "at_or_above":
        return left >= right
    raise ValueError(f"unsupported invalidation condition: {rule.condition}")


def _rule_reason(rule: InvalidationRule) -> str:
    if rule.reference:
        if rule.reference_multiplier != 1.0:
            multiplier = f"{rule.reference_multiplier:g}".replace(".", "p")
            return f"{rule.field}_{rule.condition}_{rule.reference}_x{multiplier}"
        return f"{rule.field}_{rule.condition}_{rule.reference}"
    threshold = int(rule.threshold) if rule.threshold is not None and float(rule.threshold).is_integer() else rule.threshold
    return f"{rule.field}_{rule.condition}_{threshold}"
