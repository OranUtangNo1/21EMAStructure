from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.utils import percent_rank

RuleEvaluator = Callable[[pd.Series, "ScanConfig"], bool]

DEFAULT_SCAN_RULE_NAMES = (
    "21EMA Pattern H",
    "21EMA Pattern L",
    "Pullback Quality scan",
    "Reclaim scan",
    "4% bullish",
    "Volume Accumulation",
    "Momentum 97",
    "VCS 52 High",
    "Pocket Pivot",
    "PP Count",
    "Weekly 20% plus gainers",
    "VCP 3T",
    "LL-HL Structure 1st Pivot",
    "LL-HL Structure 2nd Pivot",
    "LL-HL Structure Trend Line Break",
    "50SMA Reclaim",
    "RS New High",
    "RS 3Y New High",
    "RS Leads Price Setup",
    "Trend Template",
    "Fresh Stage 2 Breakout",
)

DEFAULT_ANNOTATION_FILTER_NAMES = (
    "RS 21 >= 63",
    "High Est. EPS Growth",
    "PP Count (20d)",
    "Trend Base",
    "Stage 2 Confirmed",
    "Stage 2 Quality Score",
    "Trend Template",
    "Mature / Late Stage Risk Filter",
    "Industry Leadership Gate",
    "Stage 4 Avoid",
    "Fund Score > 70",
    "Resistance Tests >= 2",
    "Recent Power Gap",
)

ANNOTATION_FILTER_NAME_ALIASES = {
    "Relative Strength 21 > 63": "RS 21 >= 63",
    "PP Count": "PP Count (20d)",
    "2+ Pocket Pivots (20d)": "PP Count (20d)",
    "3+ Pocket Pivots (20d)": "PP Count (20d)",
}

DEFAULT_CARD_SORT_COLUMNS = ("hybrid_score", "overlap_count", "vcs")
DEFAULT_CARD_SECTION_PAYLOADS = (
    {"scan_name": "21EMA Pattern H", "display_name": "21EMA PH"},
    {"scan_name": "21EMA Pattern L", "display_name": "21EMA PL"},
    {"scan_name": "Pullback Quality scan", "display_name": "PB Quality"},
    {"scan_name": "Reclaim scan", "display_name": "Reclaim"},
    {"scan_name": "4% bullish", "display_name": "4% bullish"},
    {"scan_name": "Volume Accumulation", "display_name": "Volume Accumulation"},
    {"scan_name": "Momentum 97", "display_name": "Momentum 97"},
    {"scan_name": "VCS 52 High", "display_name": "VCS 52 High"},
    {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
    {"scan_name": "PP Count", "display_name": "PP Count"},
    {"scan_name": "Weekly 20% plus gainers", "display_name": "Weekly 20%+ Gainers"},
    {"scan_name": "VCP 3T", "display_name": "VCP 3T"},
    {"scan_name": "LL-HL Structure 1st Pivot", "display_name": "LL-HL 1st"},
    {"scan_name": "LL-HL Structure 2nd Pivot", "display_name": "LL-HL 2nd"},
    {"scan_name": "LL-HL Structure Trend Line Break", "display_name": "CT Break"},
    {"scan_name": "50SMA Reclaim", "display_name": "50SMA Reclaim"},
    {"scan_name": "RS New High", "display_name": "RS New High"},
    {"scan_name": "RS 3Y New High", "display_name": "RS 3Y New High"},
    {"scan_name": "RS Leads Price Setup", "display_name": "RS Leads Price"},
    {"scan_name": "Trend Template", "display_name": "Trend Template"},
    {"scan_name": "Fresh Stage 2 Breakout", "display_name": "Fresh Stage 2"},
)
DEFAULT_ANNOTATION_FILTER_PAYLOADS = (
    {"filter_name": "RS 21 >= 63", "display_name": "RS 21 >= 63"},
    {"filter_name": "High Est. EPS Growth", "display_name": "High Est. EPS Growth"},
    {"filter_name": "PP Count (20d)", "display_name": "PP Count (20d)"},
    {"filter_name": "Trend Base", "display_name": "Trend Base"},
    {"filter_name": "Stage 2 Confirmed", "display_name": "Stage 2 Confirmed"},
    {"filter_name": "Stage 2 Quality Score", "display_name": "Stage 2 Quality"},
    {"filter_name": "Trend Template", "display_name": "Trend Template"},
    {"filter_name": "Mature / Late Stage Risk Filter", "display_name": "Mature Risk Filter"},
    {"filter_name": "Industry Leadership Gate", "display_name": "Industry Leadership"},
    {"filter_name": "Stage 4 Avoid", "display_name": "Stage 4 Avoid"},
    {"filter_name": "Fund Score > 70", "display_name": "Fund Score > 70"},
    {"filter_name": "Resistance Tests >= 2", "display_name": "Resistance Tests >= 2"},
    {"filter_name": "Recent Power Gap", "display_name": "Recent Power Gap"},
)
ANNOTATION_FILTER_COLUMN_NAMES = {
    "RS 21 >= 63": "annotation_rs21_gte_63",
    "High Est. EPS Growth": "annotation_high_eps_growth",
    "PP Count (20d)": "annotation_pp_count_20d",
    "3+ Pocket Pivots (20d)": "annotation_pp_count_20d",
    "Trend Base": "annotation_trend_base",
    "Stage 2 Confirmed": "annotation_stage2_confirmed",
    "Stage 2 Quality Score": "annotation_stage2_quality_score",
    "Trend Template": "annotation_trend_template",
    "Mature / Late Stage Risk Filter": "annotation_mature_late_stage_risk_filter",
    "Industry Leadership Gate": "annotation_industry_leadership_gate",
    "Stage 4 Avoid": "annotation_stage4_avoid",
    "Fund Score > 70": "annotation_fund_score_gt_70",
    "Resistance Tests >= 2": "annotation_resistance_tests_gte_2",
    "Recent Power Gap": "annotation_recent_power_gap",
}
SCAN_STATUS_VALUES = ("enabled", "disabled")
ANNOTATION_FILTER_STATUS_VALUES = ("enabled", "disabled")
WATCHLIST_PRESET_STATUS_VALUES = ("enabled", "hidden_enabled", "disabled")


@dataclass(slots=True)
class ScanCardConfig:
    """Config for a single scan card section."""

    scan_name: str
    display_name: str | None = None
    sort_columns: tuple[str, ...] = DEFAULT_CARD_SORT_COLUMNS

    @classmethod
    def from_dict(cls, payload: dict[str, object] | str) -> "ScanCardConfig":
        if isinstance(payload, str):
            return cls(scan_name=payload, display_name=payload)
        scan_name = str(payload.get("scan_name", payload.get("source_name", ""))).strip()
        if not scan_name:
            raise ValueError("card_sections items require scan_name")
        source_kind = str(payload.get("source_kind", "scan")).strip().lower() or "scan"
        if source_kind != "scan":
            raise ValueError("card_sections supports scan-based cards only")
        display_name = payload.get("display_name")
        raw_sort_columns = payload.get("sort_columns", DEFAULT_CARD_SORT_COLUMNS)
        sort_columns = tuple(str(column).strip() for column in raw_sort_columns if str(column).strip())
        if not sort_columns:
            sort_columns = DEFAULT_CARD_SORT_COLUMNS
        return cls(
            scan_name=scan_name,
            display_name=str(display_name).strip() if display_name is not None else None,
            sort_columns=sort_columns,
        )


@dataclass(slots=True)
class AnnotationFilterConfig:
    """Config for a single post-scan annotation filter."""

    filter_name: str
    display_name: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, object] | str) -> "AnnotationFilterConfig":
        if isinstance(payload, str):
            canonical_name = _canonical_annotation_filter_name(payload)
            return cls(filter_name=canonical_name, display_name=canonical_name)
        filter_name = _canonical_annotation_filter_name(str(payload.get("filter_name", payload.get("name", ""))).strip())
        if not filter_name:
            raise ValueError("annotation_filters items require filter_name")
        display_name = payload.get("display_name")
        return cls(
            filter_name=filter_name,
            display_name=str(display_name).strip() if display_name is not None else None,
        )


@dataclass(slots=True)
class DuplicateRuleGroupConfig:
    """A named scan group with its own hit threshold."""

    group_name: str
    scans: tuple[str, ...]
    min_hits: int = 1

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "DuplicateRuleGroupConfig":
        group_name = str(payload.get("group_name", payload.get("name", "Optional Condition"))).strip() or "Optional Condition"
        scans = _normalize_name_tuple(payload.get("scans", ()))
        try:
            min_hits = int(payload.get("min_hits", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError("duplicate_rule optional_groups min_hits must be an integer") from exc
        if not scans:
            raise ValueError("duplicate_rule optional_groups requires scans")
        if min_hits < 1:
            raise ValueError("duplicate_rule optional_groups min_hits must be >= 1")
        if min_hits > len(scans):
            raise ValueError("duplicate_rule optional_groups min_hits cannot exceed scans count")
        return cls(group_name=group_name, scans=scans, min_hits=min_hits)

    def to_dict(self) -> dict[str, object]:
        return {
            "group_name": self.group_name,
            "scans": list(self.scans),
            "min_hits": int(self.min_hits),
        }


@dataclass(slots=True)
class DuplicateRuleConfig:
    """Configurable duplicate-ticker rule."""

    mode: str = "min_count"
    min_count: int = 1
    required_scans: tuple[str, ...] = field(default_factory=tuple)
    optional_scans: tuple[str, ...] = field(default_factory=tuple)
    optional_min_hits: int = 1
    optional_groups: tuple[DuplicateRuleGroupConfig, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, object] | None,
        *,
        default_min_count: int = 1,
    ) -> "DuplicateRuleConfig":
        data = payload if isinstance(payload, dict) else {}
        mode = str(data.get("mode", "min_count")).strip().lower().replace("-", "_").replace(" ", "_")
        if mode not in {"min_count", "required_plus_optional_min", "grouped_threshold"}:
            raise ValueError("duplicate_rule mode must be one of: min_count, required_plus_optional_min, grouped_threshold")
        try:
            min_count = int(data.get("min_count", default_min_count))
        except (TypeError, ValueError) as exc:
            raise ValueError("duplicate_rule min_count must be an integer") from exc
        if min_count < 1:
            raise ValueError("duplicate_rule min_count must be >= 1")
        required_scans = _normalize_name_tuple(data.get("required_scans", ()))
        optional_scans = _normalize_name_tuple(data.get("optional_scans", ()))
        raw_optional_groups = data.get("optional_groups", ())
        if raw_optional_groups is None:
            raw_optional_groups = ()
        if not isinstance(raw_optional_groups, (list, tuple)):
            raise ValueError("duplicate_rule optional_groups must be a list")
        optional_groups = tuple(
            DuplicateRuleGroupConfig.from_dict(item)
            for item in raw_optional_groups
            if isinstance(item, dict)
        )
        if len(optional_groups) != len(raw_optional_groups):
            raise ValueError("duplicate_rule optional_groups items must be mappings")
        try:
            optional_min_hits = int(data.get("optional_min_hits", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError("duplicate_rule optional_min_hits must be an integer") from exc
        if optional_min_hits < 1:
            raise ValueError("duplicate_rule optional_min_hits must be >= 1")
        if mode == "required_plus_optional_min":
            if not required_scans:
                raise ValueError("duplicate_rule required_plus_optional_min requires required_scans")
            if not optional_scans:
                raise ValueError("duplicate_rule required_plus_optional_min requires optional_scans")
            if optional_min_hits > len(optional_scans):
                raise ValueError("duplicate_rule optional_min_hits cannot exceed optional_scans count")
        if mode == "grouped_threshold":
            if not required_scans and not optional_groups:
                raise ValueError("duplicate_rule grouped_threshold requires required_scans or optional_groups")
        return cls(
            mode=mode,
            min_count=min_count,
            required_scans=required_scans,
            optional_scans=optional_scans,
            optional_min_hits=optional_min_hits,
            optional_groups=optional_groups,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "min_count": int(self.min_count),
            "required_scans": list(self.required_scans),
            "optional_scans": list(self.optional_scans),
            "optional_min_hits": int(self.optional_min_hits),
            "optional_groups": [group.to_dict() for group in self.optional_groups],
        }


@dataclass(slots=True)
class WatchlistPresetConfig:
    """Built-in watchlist preset definition loaded from config."""

    preset_name: str
    selected_scan_names: tuple[str, ...]
    selected_annotation_filters: tuple[str, ...] = field(default_factory=tuple)
    selected_duplicate_subfilters: tuple[str, ...] = field(default_factory=tuple)
    duplicate_threshold: int = 1
    duplicate_rule: DuplicateRuleConfig = field(default_factory=DuplicateRuleConfig)
    preset_status: str = "enabled"

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "WatchlistPresetConfig":
        preset_name = str(payload.get("preset_name", payload.get("name", ""))).strip()
        if not preset_name:
            raise ValueError("watchlist_presets items require preset_name")
        selected_scan_names = _normalize_name_tuple(payload.get("selected_scan_names", ()))
        if not selected_scan_names:
            raise ValueError("watchlist_presets items require selected_scan_names")
        selected_annotation_filters = _normalize_annotation_name_tuple(payload.get("selected_annotation_filters", ()))
        selected_duplicate_subfilters = _normalize_name_tuple(payload.get("selected_duplicate_subfilters", ()))
        try:
            duplicate_threshold = int(payload.get("duplicate_threshold", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError("watchlist_presets duplicate_threshold must be an integer") from exc
        if duplicate_threshold < 1:
            raise ValueError("watchlist_presets duplicate_threshold must be >= 1")
        duplicate_rule = DuplicateRuleConfig.from_dict(
            payload.get("duplicate_rule"),
            default_min_count=duplicate_threshold,
        )
        raw_status = payload.get("preset_status")
        if raw_status is None:
            raw_status = "enabled" if bool(payload.get("export_enabled", True)) else "disabled"
        preset_status = _normalize_watchlist_preset_status(raw_status)
        return cls(
            preset_name=preset_name,
            selected_scan_names=selected_scan_names,
            selected_annotation_filters=selected_annotation_filters,
            selected_duplicate_subfilters=selected_duplicate_subfilters,
            duplicate_threshold=duplicate_threshold,
            duplicate_rule=duplicate_rule,
            preset_status=preset_status,
        )

    def to_control_values(self) -> dict[str, object]:
        return {
            "selected_scan_names": list(self.selected_scan_names),
            "selected_annotation_filters": list(self.selected_annotation_filters),
            "selected_duplicate_subfilters": list(self.selected_duplicate_subfilters),
            "duplicate_threshold": int(self.duplicate_threshold),
            "duplicate_rule": self.duplicate_rule.to_dict(),
        }

    @property
    def export_enabled(self) -> bool:
        return self.preset_status in {"enabled", "hidden_enabled"}

    @property
    def visible_in_ui(self) -> bool:
        return self.preset_status == "enabled"


@dataclass(slots=True)
class WatchlistPresetCsvExportConfig:
    """Config for automatic preset CSV exports."""

    enabled: bool = True
    output_dir: str = "data_runs/preset_exports"
    write_details: bool = True
    top_ticker_limit: int = 5

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "WatchlistPresetCsvExportConfig":
        data = payload if isinstance(payload, dict) else {}
        try:
            top_ticker_limit = int(data.get("top_ticker_limit", 5))
        except (TypeError, ValueError) as exc:
            raise ValueError("preset_csv_export top_ticker_limit must be an integer") from exc
        if top_ticker_limit < 1:
            raise ValueError("preset_csv_export top_ticker_limit must be >= 1")
        return cls(
            enabled=bool(data.get("enabled", True)),
            output_dir=str(data.get("output_dir", "data_runs/preset_exports")).strip() or "data_runs/preset_exports",
            write_details=bool(data.get("write_details", True)),
            top_ticker_limit=top_ticker_limit,
        )


@dataclass(slots=True)
class ScanConfig:
    """Configurable thresholds, rule selection, and scan-card settings."""

    daily_gain_bullish_threshold: float = 4.0
    relative_volume_bullish_threshold: float = 1.0
    momentum_97_weekly_rank: float = 97.0
    momentum_97_quarterly_rank: float = 85.0
    vcs_52_high_vcs_min: float = 55.0
    vcs_52_high_rs21_min: float = 25.0
    vcs_52_high_dist_max: float = -20.0
    vol_accum_ud_ratio_min: float = 1.5
    vol_accum_rel_vol_min: float = 1.0
    weekly_gainer_threshold: float = 20.0
    duplicate_min_count: int = 3
    high_eps_growth_rank_threshold: float = 90.0
    pp_count_scan_min: int = 3
    pocket_pivot_pp_count_min: int = 1
    pp_count_annotation_min: int = 2
    llhl_1st_rs21_min: float = 60.0
    llhl_2nd_rs21_min: float = 60.0
    power_gap_annotation_min_pct: float = 10.0
    power_gap_annotation_max_days: int = 20
    rs_new_high_price_dist_max: float = -5.0
    rs_new_high_price_dist_min: float = -30.0
    rs_3y_new_high_price_dist_max: float = -5.0
    rs_3y_new_high_price_dist_min: float = -35.0
    rs_leads_price_rs_min: float = 75.0
    rs_leads_price_quality_min: float = 70.0
    rs_leads_price_dist_from_52w_high_max: float = -3.0
    rs_leads_price_dist_from_52w_high_min: float = -30.0
    trend_template_price_score_min: int = 7
    trend_template_rs_min: float = 70.0
    stage2_price_score_min: int = 5
    stage2_rs_min: float = 60.0
    stage2_quality_min_score: float = 75.0
    fresh_stage2_max_days_since_start: int = 21
    fresh_stage2_min_base_days_3m: int = 20
    fresh_stage2_rs_min: float = 70.0
    fresh_stage2_volume_ratio_min: float = 1.2
    fresh_stage2_dcr_min: float = 60.0
    mature_stage_max_days_since_start: int = 252
    mature_stage_dist_from_52w_low_max: float = 250.0
    mature_stage_atr_from_50sma_max: float = 7.0
    industry_leadership_min_score: float = 70.0
    earnings_warning_days: int = 7
    watchlist_sort_mode: str = "hybrid_score"
    scan_status_map: dict[str, str] = field(default_factory=dict)
    enabled_scan_rules: tuple[str, ...] = field(default_factory=lambda: DEFAULT_SCAN_RULE_NAMES)
    default_selected_scan_names: tuple[str, ...] | None = None
    annotation_filter_status_map: dict[str, str] = field(default_factory=dict)
    enabled_annotation_filters: tuple[str, ...] = field(default_factory=tuple)
    annotation_filters: tuple[AnnotationFilterConfig, ...] = field(
        default_factory=lambda: tuple(AnnotationFilterConfig.from_dict(payload) for payload in DEFAULT_ANNOTATION_FILTER_PAYLOADS)
    )
    watchlist_presets: tuple[WatchlistPresetConfig, ...] = field(default_factory=tuple)
    preset_csv_export: WatchlistPresetCsvExportConfig = field(default_factory=WatchlistPresetCsvExportConfig)
    card_sections: tuple[ScanCardConfig, ...] = field(
        default_factory=lambda: tuple(ScanCardConfig.from_dict(payload) for payload in DEFAULT_CARD_SECTION_PAYLOADS)
    )

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ScanConfig":
        base_payload = {
            key: value
            for key, value in payload.items()
            if key in cls.__dataclass_fields__
            and key
            not in {
                "enabled_scan_rules",
                "scan_status_map",
                "default_selected_scan_names",
                "annotation_filter_status_map",
                "enabled_annotation_filters",
                "annotation_filters",
                "watchlist_presets",
                "preset_csv_export",
                "card_sections",
            }
        }
        enabled_scan_rules = _normalize_name_tuple(payload.get("enabled_scan_rules", DEFAULT_SCAN_RULE_NAMES))
        if "default_selected_scan_names" in payload:
            default_selected_scan_names = _normalize_name_tuple(payload.get("default_selected_scan_names", ()))
        else:
            default_selected_scan_names = None
        if "enabled_annotation_filters" in payload:
            raw_annotation_names = payload.get("enabled_annotation_filters", ())
        else:
            legacy_names = payload.get("enabled_list_rules", ())
            raw_annotation_names = [name for name in legacy_names if _canonical_annotation_filter_name(name) in ANNOTATION_FILTER_REGISTRY]
        enabled_scan_rules, enabled_annotation_filters = _coerce_enabled_annotation_filters(
            raw_annotation_names,
            enabled_scan_rules,
        )
        scan_status_map = _normalize_scan_status_map(payload.get("scan_status_map"))
        enabled_scan_rules = tuple(
            name for name in enabled_scan_rules if scan_status_map.get(name, "enabled") == "enabled"
        )
        annotation_filter_status_map = _normalize_annotation_filter_status_map(payload.get("annotation_filter_status_map"))
        annotation_payloads = payload.get("annotation_filters", DEFAULT_ANNOTATION_FILTER_PAYLOADS)
        raw_annotation_filters = tuple(AnnotationFilterConfig.from_dict(item) for item in annotation_payloads)
        annotation_filters = tuple(
            section
            for section in raw_annotation_filters
            if annotation_filter_status_map.get(section.filter_name, "enabled") == "enabled"
        )
        active_annotation_filter_names = {section.filter_name for section in annotation_filters}
        enabled_annotation_filters = tuple(
            name for name in enabled_annotation_filters if name in active_annotation_filter_names
        )
        watchlist_preset_payloads = payload.get("watchlist_presets", ())
        watchlist_presets = tuple(WatchlistPresetConfig.from_dict(item) for item in watchlist_preset_payloads)
        preset_csv_export = WatchlistPresetCsvExportConfig.from_dict(payload.get("preset_csv_export"))
        card_payloads = payload.get("card_sections", DEFAULT_CARD_SECTION_PAYLOADS)
        raw_card_sections = tuple(ScanCardConfig.from_dict(item) for item in card_payloads)
        card_sections = tuple(
            section for section in raw_card_sections if scan_status_map.get(section.scan_name, "enabled") == "enabled"
        )
        active_card_scan_names = {section.scan_name for section in card_sections}
        if default_selected_scan_names is not None:
            default_selected_scan_names = tuple(
                name for name in default_selected_scan_names if name in active_card_scan_names
            )
        watchlist_presets = tuple(
            _drop_inactive_filters_from_preset(preset, active_annotation_filter_names)
            for preset in watchlist_presets
        )
        watchlist_presets = tuple(
            _disable_preset_when_scans_inactive(preset, active_card_scan_names)
            for preset in watchlist_presets
        )
        config = cls(
            **base_payload,
            scan_status_map=scan_status_map,
            enabled_scan_rules=enabled_scan_rules,
            default_selected_scan_names=default_selected_scan_names,
            annotation_filter_status_map=annotation_filter_status_map,
            enabled_annotation_filters=enabled_annotation_filters,
            annotation_filters=annotation_filters,
            watchlist_presets=watchlist_presets,
            preset_csv_export=preset_csv_export,
            card_sections=card_sections,
        )
        _validate_rule_names(config.enabled_scan_rules, SCAN_RULE_REGISTRY, "scan")
        _validate_rule_names(config.enabled_annotation_filters, ANNOTATION_FILTER_REGISTRY, "annotation filter")
        _validate_annotation_filter_status_map(config.annotation_filter_status_map)
        _validate_annotation_filters(raw_annotation_filters)
        available_filter_names = {section.filter_name for section in config.annotation_filters}
        unknown_enabled = [name for name in config.enabled_annotation_filters if name not in available_filter_names]
        if unknown_enabled:
            raise ValueError(f"enabled_annotation_filters must be defined in annotation_filters: {', '.join(sorted(unknown_enabled))}")
        _validate_card_sections(raw_card_sections)
        _validate_watchlist_presets(config.watchlist_presets, available_filter_names)
        return config

    def startup_selected_scan_names(self) -> tuple[str, ...]:
        available_names = tuple(section.scan_name for section in self.card_sections)
        if self.default_selected_scan_names is None:
            return available_names
        available_name_set = set(available_names)
        return tuple(name for name in self.default_selected_scan_names if name in available_name_set)


def enrich_with_scan_context(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Add cross-sectional ranks used by momentum-oriented scans."""
    result = snapshot.copy()
    result["weekly_return_rank"] = percent_rank(result["weekly_return"])
    result["quarterly_return_rank"] = percent_rank(result["quarterly_return"])
    if "eps_growth" in result.columns:
        result["eps_growth_rank"] = percent_rank(result["eps_growth"])
    else:
        result["eps_growth_rank"] = pd.Series(np.nan, index=result.index, dtype=float)
    return result


def evaluate_scan_rules(row: pd.Series, config: ScanConfig) -> dict[str, bool]:
    """Evaluate the configured scan families on a single latest snapshot row."""
    return _evaluate_rule_set(row, config.enabled_scan_rules, config, SCAN_RULE_REGISTRY, "scan")


def evaluate_annotation_filters(row: pd.Series, config: ScanConfig) -> dict[str, bool]:
    """Evaluate all configured post-scan annotation filters on a single latest snapshot row."""
    filter_names = tuple(section.filter_name for section in config.annotation_filters)
    return _evaluate_rule_set(
        row,
        filter_names,
        config,
        ANNOTATION_FILTER_REGISTRY,
        "annotation filter",
    )


def annotation_filter_column_name(filter_name: str) -> str:
    canonical_name = _canonical_annotation_filter_name(filter_name)
    if canonical_name not in ANNOTATION_FILTER_COLUMN_NAMES:
        raise ValueError(f"Unknown annotation filter: {filter_name}")
    return ANNOTATION_FILTER_COLUMN_NAMES[canonical_name]


def _canonical_annotation_filter_name(name: object) -> str:
    cleaned = str(name).strip()
    return ANNOTATION_FILTER_NAME_ALIASES.get(cleaned, cleaned)


def _normalize_name_tuple(raw_names: object) -> tuple[str, ...]:
    if raw_names is None:
        return tuple()
    if isinstance(raw_names, str):
        items = [raw_names]
    else:
        try:
            items = list(raw_names)
        except TypeError:
            items = [raw_names]
    return tuple(dict.fromkeys(str(name).strip() for name in items if str(name).strip()))


def _normalize_annotation_name_tuple(raw_names: object) -> tuple[str, ...]:
    if raw_names is None:
        return tuple()
    if isinstance(raw_names, str):
        items = [raw_names]
    else:
        try:
            items = list(raw_names)
        except TypeError:
            items = [raw_names]
    return tuple(
        dict.fromkeys(
            canonical
            for canonical in (_canonical_annotation_filter_name(name) for name in items)
            if canonical
        )
    )


def _merge_name_tuples(*name_groups: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    for group in name_groups:
        for name in group:
            if name not in merged:
                merged.append(name)
    return tuple(merged)


def _coerce_enabled_annotation_filters(
    raw_names: object,
    enabled_scan_rules: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    annotation_names = _normalize_annotation_name_tuple(raw_names)
    compatible_annotation_names = tuple(name for name in annotation_names if name in ANNOTATION_FILTER_REGISTRY)
    misplaced_scan_names = tuple(name for name in annotation_names if name in SCAN_RULE_REGISTRY and name not in ANNOTATION_FILTER_REGISTRY)
    unknown_names = tuple(
        name
        for name in annotation_names
        if name not in ANNOTATION_FILTER_REGISTRY and name not in SCAN_RULE_REGISTRY
    )
    if unknown_names:
        raise ValueError(f"Unknown annotation filter rule(s): {', '.join(sorted(unknown_names))}")
    return _merge_name_tuples(enabled_scan_rules, misplaced_scan_names), compatible_annotation_names


def _evaluate_rule_set(
    row: pd.Series,
    rule_names: tuple[str, ...],
    config: ScanConfig,
    registry: dict[str, RuleEvaluator],
    rule_kind: str,
) -> dict[str, bool]:
    _validate_rule_names(rule_names, registry, rule_kind)
    return {name: bool(registry[name](row, config)) for name in rule_names}


def _validate_rule_names(rule_names: tuple[str, ...], registry: dict[str, RuleEvaluator], rule_kind: str) -> None:
    unknown = [name for name in rule_names if name not in registry]
    if unknown:
        raise ValueError(f"Unknown {rule_kind} rule(s): {', '.join(sorted(unknown))}")


def _validate_card_sections(card_sections: tuple[ScanCardConfig, ...]) -> None:
    unknown = [section.scan_name for section in card_sections if section.scan_name not in SCAN_RULE_REGISTRY]
    if unknown:
        raise ValueError(f"Unknown scan card section(s): {', ' .join(sorted(unknown))}")


def _validate_annotation_filters(annotation_filters: tuple[AnnotationFilterConfig, ...]) -> None:
    unknown = [
        section.filter_name
        for section in annotation_filters
        if _canonical_annotation_filter_name(section.filter_name) not in ANNOTATION_FILTER_REGISTRY
    ]
    if unknown:
        raise ValueError(f"Unknown annotation filter section(s): {', '.join(sorted(unknown))}")


def _validate_annotation_filter_status_map(status_map: dict[str, str]) -> None:
    unknown = [name for name in status_map if name not in ANNOTATION_FILTER_REGISTRY]
    if unknown:
        raise ValueError(f"annotation_filter_status_map references unknown annotation filter: {', '.join(sorted(unknown))}")


def _validate_watchlist_presets(
    watchlist_presets: tuple[WatchlistPresetConfig, ...],
    available_filter_names: set[str],
) -> None:
    seen_names: set[str] = set()
    for preset in watchlist_presets:
        if preset.preset_name in seen_names:
            raise ValueError(f"Duplicate watchlist preset name: {preset.preset_name}")
        seen_names.add(preset.preset_name)
        unknown_scans = [name for name in preset.selected_scan_names if name not in SCAN_RULE_REGISTRY]
        if unknown_scans:
            raise ValueError(
                f"watchlist preset '{preset.preset_name}' references unknown scan(s): {', '.join(sorted(unknown_scans))}"
            )
        unknown_filters = [name for name in preset.selected_annotation_filters if name not in available_filter_names]
        if unknown_filters:
            raise ValueError(
                f"watchlist preset '{preset.preset_name}' references unknown annotation filter(s): {', '.join(sorted(unknown_filters))}"
            )
        rule_scan_names = list(preset.duplicate_rule.required_scans)
        rule_scan_names.extend(preset.duplicate_rule.optional_scans)
        for group in preset.duplicate_rule.optional_groups:
            rule_scan_names.extend(group.scans)
        unknown_rule_scans = [name for name in rule_scan_names if name not in preset.selected_scan_names]
        if unknown_rule_scans:
            raise ValueError(
                f"watchlist preset '{preset.preset_name}' duplicate_rule references scans outside selected_scan_names: {', '.join(sorted(set(unknown_rule_scans)))}"
            )


def _normalize_scan_status_map(raw_map: object) -> dict[str, str]:
    if raw_map is None:
        return {}
    if not isinstance(raw_map, dict):
        raise ValueError("scan_status_map must be a mapping of scan name to status")
    normalized: dict[str, str] = {}
    for raw_name, raw_status in raw_map.items():
        scan_name = str(raw_name).strip()
        if not scan_name:
            continue
        if scan_name not in SCAN_RULE_REGISTRY:
            raise ValueError(f"scan_status_map references unknown scan: {scan_name}")
        status = str(raw_status).strip().lower().replace("-", "_").replace(" ", "_")
        status = {
            "enabled": "enabled",
            "active": "enabled",
            "disabled": "disabled",
            "inactive": "disabled",
            "off": "disabled",
        }.get(status, status)
        if status not in SCAN_STATUS_VALUES:
            raise ValueError(f"scan_status_map status for '{scan_name}' must be one of: {', '.join(SCAN_STATUS_VALUES)}")
        normalized[scan_name] = status
    return normalized


def _normalize_annotation_filter_status_map(raw_map: object) -> dict[str, str]:
    if raw_map is None:
        return {}
    if not isinstance(raw_map, dict):
        raise ValueError("annotation_filter_status_map must be a mapping of annotation filter name to status")
    normalized: dict[str, str] = {}
    for raw_name, raw_status in raw_map.items():
        filter_name = _canonical_annotation_filter_name(raw_name)
        if not filter_name:
            continue
        if filter_name not in ANNOTATION_FILTER_REGISTRY:
            raise ValueError(f"annotation_filter_status_map references unknown annotation filter: {filter_name}")
        status = str(raw_status).strip().lower().replace("-", "_").replace(" ", "_")
        status = {
            "enabled": "enabled",
            "active": "enabled",
            "disabled": "disabled",
            "inactive": "disabled",
            "off": "disabled",
        }.get(status, status)
        if status not in ANNOTATION_FILTER_STATUS_VALUES:
            raise ValueError(
                "annotation_filter_status_map status for "
                f"'{filter_name}' must be one of: {', '.join(ANNOTATION_FILTER_STATUS_VALUES)}"
            )
        normalized[filter_name] = status
    return normalized


def _disable_preset_when_scans_inactive(
    preset: WatchlistPresetConfig,
    active_scan_names: set[str],
) -> WatchlistPresetConfig:
    if all(name in active_scan_names for name in preset.selected_scan_names):
        return preset
    preset.preset_status = "disabled"
    return preset


def _drop_inactive_filters_from_preset(
    preset: WatchlistPresetConfig,
    active_annotation_filter_names: set[str],
) -> WatchlistPresetConfig:
    preset.selected_annotation_filters = tuple(
        name for name in preset.selected_annotation_filters if name in active_annotation_filter_names
    )
    return preset


def _normalize_watchlist_preset_status(raw_status: object) -> str:
    status = str(raw_status).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "enabled": "enabled",
        "active": "enabled",
        "visible": "enabled",
        "hidden_enabled": "hidden_enabled",
        "hidden_export": "hidden_enabled",
        "hidden": "hidden_enabled",
        "disabled": "disabled",
        "inactive": "disabled",
        "off": "disabled",
    }
    normalized = aliases.get(status, status)
    if normalized not in WATCHLIST_PRESET_STATUS_VALUES:
        raise ValueError(
            "watchlist_presets preset_status must be one of: "
            + ", ".join(WATCHLIST_PRESET_STATUS_VALUES)
        )
    return normalized


def _scan_21ema(row: pd.Series, config: ScanConfig) -> bool:
    weekly_return = row.get("weekly_return", float("nan"))
    return bool(
        weekly_return >= 0.0
        and weekly_return <= 15.0
        and row.get("dcr_percent", 0.0) > 20.0
        and -0.5 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
        and 0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
    )


def _scan_21ema_pattern_h(row: pd.Series, config: ScanConfig) -> bool:
    return bool(
        0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
        and 0.3 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
        and row.get("atr_low_to_ema21_high", float("nan")) >= -0.2
        and row.get("high", 0.0) > row.get("prev_high", float("inf"))
    )


def _scan_21ema_pattern_l(row: pd.Series, config: ScanConfig) -> bool:
    return bool(
        0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
        and -0.5 <= row.get("atr_21ema_zone", float("nan")) <= -0.1
        and row.get("atr_low_to_ema21_low", float("nan")) < 0.0
        and row.get("atr_21emaL_zone", float("nan")) > 0.0
        and row.get("high", 0.0) > row.get("prev_high", float("inf"))
    )


def _scan_pullback_quality(row: pd.Series, config: ScanConfig) -> bool:
    weekly_return = row.get("weekly_return", float("nan"))
    return bool(
        row.get("ema21_slope_5d_pct", float("nan")) > 0.0
        and row.get("sma50_slope_10d_pct", float("nan")) > 0.0
        and -1.25 <= row.get("atr_21ema_zone", float("nan")) <= 0.25
        and 0.75 <= row.get("atr_50sma_zone", float("nan")) <= 3.5
        and -8.0 <= weekly_return <= 3.0
        and row.get("dcr_percent", 0.0) >= 50.0
        and 3.0 <= row.get("drawdown_from_20d_high_pct", float("nan")) <= 15.0
        and row.get("volume_ma5_to_ma20_ratio", float("nan")) <= 0.85
    )


def _scan_reclaim(row: pd.Series, config: ScanConfig) -> bool:
    weekly_return = row.get("weekly_return", float("nan"))
    return bool(
        row.get("ema21_slope_5d_pct", float("nan")) > 0.0
        and row.get("sma50_slope_10d_pct", float("nan")) > 0.0
        and 0.0 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
        and 0.75 <= row.get("atr_50sma_zone", float("nan")) <= 4.0
        and -3.0 <= weekly_return <= 10.0
        and row.get("dcr_percent", 0.0) >= 60.0
        and 2.0 <= row.get("drawdown_from_20d_high_pct", float("nan")) <= 12.0
        and row.get("volume_ratio_20d", float("nan")) >= 1.10
        and row.get("close_crossed_above_ema21", False)
        and row.get("min_atr_21ema_zone_5d", float("nan")) <= -0.25
    )


def _scan_50sma_reclaim(row: pd.Series, config: ScanConfig) -> bool:
    return bool(
        row.get("sma50_slope_10d_pct", float("nan")) > 0.0
        and 0.0 <= row.get("atr_50sma_zone", float("nan")) <= 1.0
        and row.get("close_crossed_above_sma50", False)
        and row.get("min_atr_50sma_zone_5d", float("nan")) <= -0.25
        and row.get("dcr_percent", 0.0) >= 60.0
        and row.get("volume_ratio_20d", float("nan")) >= 1.10
        and 3.0 <= row.get("drawdown_from_20d_high_pct", float("nan")) <= 20.0
    )


def _scan_bullish_4pct(row: pd.Series, config: ScanConfig) -> bool:
    return bool(
        row.get("rel_volume", 0.0) >= config.relative_volume_bullish_threshold
        and row.get("daily_change_pct", 0.0) >= config.daily_gain_bullish_threshold
        and row.get("from_open_pct", 0.0) > 0.0
    )


def _scan_volume_accumulation(row: pd.Series, config: ScanConfig) -> bool:
    return bool(
        row.get("ud_volume_ratio", 0.0) >= config.vol_accum_ud_ratio_min
        and row.get("rel_volume", 0.0) >= config.vol_accum_rel_vol_min
        and row.get("daily_change_pct", 0.0) > 0.0
    )


def _scan_momentum_97(row: pd.Series, config: ScanConfig) -> bool:
    return bool(
        row.get("weekly_return_rank", 0.0) >= config.momentum_97_weekly_rank
        and row.get("quarterly_return_rank", 0.0) >= config.momentum_97_quarterly_rank
    )


def _scan_vcs_52_high(row: pd.Series, config: ScanConfig) -> bool:
    raw_rs21 = _raw_rs(row, 21)
    return bool(
        row.get("vcs", 0.0) >= config.vcs_52_high_vcs_min
        and raw_rs21 > config.vcs_52_high_rs21_min
        and row.get("dist_from_52w_high", float("nan")) >= config.vcs_52_high_dist_max
    )


def _scan_pocket_pivot(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("pp_count_window", 0) >= config.pocket_pivot_pp_count_min)


def _scan_pp_count(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("pp_count_window", 0) >= config.pp_count_scan_min)


def _scan_weekly_gainer(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("weekly_return", 0.0) >= config.weekly_gainer_threshold)


def _scan_vcp_3t(row: pd.Series, config: ScanConfig) -> bool:
    value = row.get("vcp_tightening", False)
    return bool(pd.notna(value) and value)


def _scan_llhl_1st_pivot(row: pd.Series, config: ScanConfig) -> bool:
    raw_rs21 = _raw_rs(row, 21)
    return bool(
        raw_rs21 >= config.llhl_1st_rs21_min
        and row.get("structure_pivot_1st_break", False)
    )


def _scan_llhl_2nd_pivot(row: pd.Series, config: ScanConfig) -> bool:
    raw_rs21 = _raw_rs(row, 21)
    return bool(
        raw_rs21 >= config.llhl_2nd_rs21_min
        and row.get("structure_pivot_2nd_break", False)
    )


def _scan_llhl_ct_break(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("ct_trendline_break", False))


def _scan_rs_new_high(row: pd.Series, config: ScanConfig) -> bool:
    return bool(
        row.get("rs_ratio_at_52w_high", False)
        and row.get("dist_from_52w_high", float("nan")) <= config.rs_new_high_price_dist_max
        and row.get("dist_from_52w_high", float("nan")) >= config.rs_new_high_price_dist_min
    )


def _scan_rs_3y_new_high(row: pd.Series, config: ScanConfig) -> bool:
    return bool(
        row.get("rs_ratio_at_3y_high", False)
        and row.get("dist_from_52w_high", float("nan")) <= config.rs_3y_new_high_price_dist_max
        and row.get("dist_from_52w_high", float("nan")) >= config.rs_3y_new_high_price_dist_min
    )


def _scan_rs_leads_price_setup(row: pd.Series, config: ScanConfig) -> bool:
    rs21 = _raw_rs(row, 21)
    dist_from_52w_high = row.get("dist_from_52w_high", float("nan"))
    return bool(
        _stage2_confirmed_pass(row, config)
        and _mature_stage_risk_pass(row, config)
        and pd.notna(rs21)
        and float(rs21) >= config.rs_leads_price_rs_min
        and _stage2_quality_score(row, config) >= config.rs_leads_price_quality_min
        and (row.get("rs_ratio_at_52w_high", False) or row.get("rs_ratio_at_3y_high", False))
        and pd.notna(dist_from_52w_high)
        and config.rs_leads_price_dist_from_52w_high_min <= float(dist_from_52w_high) <= config.rs_leads_price_dist_from_52w_high_max
    )


def _scan_trend_template(row: pd.Series, config: ScanConfig) -> bool:
    return _trend_template_pass(row, config)


def _scan_fresh_stage2_breakout(row: pd.Series, config: ScanConfig) -> bool:
    rs21 = _raw_rs(row, 21)
    days_since_start = row.get("days_since_stage2_start", float("nan"))
    base_days = row.get("stage_base_days_3m", 0.0)
    return bool(
        _stage2_confirmed_pass(row, config)
        and _mature_stage_risk_pass(row, config)
        and pd.notna(days_since_start)
        and 0.0 <= float(days_since_start) <= config.fresh_stage2_max_days_since_start
        and float(base_days) >= config.fresh_stage2_min_base_days_3m
        and pd.notna(rs21)
        and float(rs21) >= config.fresh_stage2_rs_min
        and row.get("close", 0.0) > row.get("sma50", float("inf"))
        and (
            row.get("vcp_pivot_breakout", False)
            or row.get("structure_pivot_long_breakout_first_day", False)
            or row.get("dist_from_52w_high", float("nan")) >= -5.0
        )
        and row.get("volume_ratio_20d", 0.0) >= config.fresh_stage2_volume_ratio_min
        and row.get("dcr_percent", 0.0) >= config.fresh_stage2_dcr_min
    )


def _annotation_rs21_gte_63(row: pd.Series, config: ScanConfig) -> bool:
    rs21 = _raw_rs(row, 21)
    return bool(pd.notna(rs21) and float(rs21) >= 63.0)


def _annotation_high_eps_growth(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("eps_growth_rank", 0.0) >= config.high_eps_growth_rank_threshold)


def _annotation_pp_count_20d(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("pp_count_window", 0) >= config.pp_count_annotation_min)


def _annotation_trend_base(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("trend_base", False))


def _annotation_stage2_confirmed(row: pd.Series, config: ScanConfig) -> bool:
    return _stage2_confirmed_pass(row, config)


def _annotation_stage2_quality_score(row: pd.Series, config: ScanConfig) -> bool:
    return bool(
        _stage2_confirmed_pass(row, config)
        and _stage2_quality_score(row, config) >= config.stage2_quality_min_score
    )


def _annotation_trend_template(row: pd.Series, config: ScanConfig) -> bool:
    return _trend_template_pass(row, config)


def _annotation_mature_late_stage_risk_filter(row: pd.Series, config: ScanConfig) -> bool:
    return bool(_stage2_confirmed_pass(row, config) and _mature_stage_risk_pass(row, config))


def _annotation_industry_leadership_gate(row: pd.Series, config: ScanConfig) -> bool:
    industry_score = row.get("industry_score", float("nan"))
    return bool(pd.notna(industry_score) and float(industry_score) >= config.industry_leadership_min_score)


def _annotation_stage4_avoid(row: pd.Series, config: ScanConfig) -> bool:
    return bool(str(row.get("stage_label", "")) == "stage4_avoid")


def _annotation_fund_score_gt_70(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("fundamental_score", 0.0) >= 70.0)


def _annotation_resistance_tests_gte_2(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("resistance_test_count", 0.0) >= 2.0)


def _annotation_recent_power_gap(row: pd.Series, config: ScanConfig) -> bool:
    power_gap_up_pct = row.get("power_gap_up_pct", float("nan"))
    days_since = row.get("days_since_power_gap", float("nan"))
    return bool(
        pd.notna(power_gap_up_pct)
        and power_gap_up_pct >= config.power_gap_annotation_min_pct
        and pd.notna(days_since)
        and days_since <= config.power_gap_annotation_max_days
    )


SCAN_RULE_REGISTRY: dict[str, RuleEvaluator] = {
    "21EMA scan": _scan_21ema,
    "21EMA Pattern H": _scan_21ema_pattern_h,
    "21EMA Pattern L": _scan_21ema_pattern_l,
    "Pullback Quality scan": _scan_pullback_quality,
    "Reclaim scan": _scan_reclaim,
    "4% bullish": _scan_bullish_4pct,
    "Volume Accumulation": _scan_volume_accumulation,
    "Momentum 97": _scan_momentum_97,
    "VCS 52 High": _scan_vcs_52_high,
    "Pocket Pivot": _scan_pocket_pivot,
    "PP Count": _scan_pp_count,
    "Weekly 20% plus gainers": _scan_weekly_gainer,
    "VCP 3T": _scan_vcp_3t,
    "LL-HL Structure 1st Pivot": _scan_llhl_1st_pivot,
    "LL-HL Structure 2nd Pivot": _scan_llhl_2nd_pivot,
    "LL-HL Structure Trend Line Break": _scan_llhl_ct_break,
    "50SMA Reclaim": _scan_50sma_reclaim,
    "RS New High": _scan_rs_new_high,
    "RS 3Y New High": _scan_rs_3y_new_high,
    "RS Leads Price Setup": _scan_rs_leads_price_setup,
    "Trend Template": _scan_trend_template,
    "Fresh Stage 2 Breakout": _scan_fresh_stage2_breakout,
}

ANNOTATION_FILTER_REGISTRY: dict[str, RuleEvaluator] = {
    "RS 21 >= 63": _annotation_rs21_gte_63,
    "High Est. EPS Growth": _annotation_high_eps_growth,
    "PP Count (20d)": _annotation_pp_count_20d,
    "3+ Pocket Pivots (20d)": _annotation_pp_count_20d,
    "Trend Base": _annotation_trend_base,
    "Stage 2 Confirmed": _annotation_stage2_confirmed,
    "Stage 2 Quality Score": _annotation_stage2_quality_score,
    "Trend Template": _annotation_trend_template,
    "Mature / Late Stage Risk Filter": _annotation_mature_late_stage_risk_filter,
    "Industry Leadership Gate": _annotation_industry_leadership_gate,
    "Stage 4 Avoid": _annotation_stage4_avoid,
    "Fund Score > 70": _annotation_fund_score_gt_70,
    "Resistance Tests >= 2": _annotation_resistance_tests_gte_2,
    "Recent Power Gap": _annotation_recent_power_gap,
}


def _raw_rs(row: pd.Series, lookback: int) -> float:
    value = row.get(f"raw_rs{lookback}", row.get(f"rs{lookback}", float("nan")))
    return float(value) if pd.notna(value) else float("nan")


def stage2_quality_score(row: pd.Series, config: ScanConfig) -> float:
    return _stage2_quality_score(row, config)


def mature_late_stage_risk(row: pd.Series, config: ScanConfig) -> bool:
    return not _mature_stage_risk_pass(row, config)


def _stage2_confirmed_pass(row: pd.Series, config: ScanConfig) -> bool:
    rs21 = _raw_rs(row, 21)
    return bool(
        str(row.get("stage_label", "")) == "stage2_candidate"
        and row.get("trend_template_price_score", 0) >= config.stage2_price_score_min
        and pd.notna(rs21)
        and float(rs21) >= config.stage2_rs_min
    )


def _stage2_quality_score(row: pd.Series, config: ScanConfig) -> float:
    existing = row.get("stage2_quality_score", float("nan"))
    if pd.notna(existing):
        return float(existing)

    price_score = _bounded_ratio(row.get("trend_template_price_score", 0.0), 0.0, 7.0) * 35.0
    rs21 = _raw_rs(row, 21)
    rs63 = row.get("raw_rs63", row.get("rs63", float("nan")))
    if pd.notna(rs21) and pd.notna(rs63):
        rs_composite = float(rs21) * 0.65 + float(rs63) * 0.35
    elif pd.notna(rs21):
        rs_composite = float(rs21)
    else:
        rs_composite = 0.0
    rs_score = _bounded_ratio(rs_composite, 0.0, 100.0) * 25.0

    slope_score = (
        _bounded_ratio(row.get("sma150_slope_1m_pct", 0.0), 0.0, 5.0) * 8.0
        + _bounded_ratio(row.get("sma200_slope_1m_pct", 0.0), 0.0, 3.0) * 7.0
    )
    location_score = (
        _bounded_ratio(row.get("dist_from_52w_high", -25.0), -25.0, -5.0) * 10.0
        + _bounded_ratio(row.get("dist_from_52w_low", 0.0), 30.0, 80.0) * 5.0
    )
    demand_score = (
        _bounded_ratio(row.get("ud_volume_ratio", 0.0), 1.0, 2.0) * 5.0
        + _bounded_ratio(row.get("pp_count_window", 0.0), 0.0, 3.0) * 5.0
    )
    return round(float(min(100.0, max(0.0, price_score + rs_score + slope_score + location_score + demand_score))), 2)


def _mature_stage_risk_pass(row: pd.Series, config: ScanConfig) -> bool:
    if str(row.get("stage_label", "")) == "stage4_avoid":
        return False

    days_since_start = row.get("days_since_stage2_start", float("nan"))
    dist_from_52w_low = row.get("dist_from_52w_low", float("nan"))
    atr_from_50sma = row.get("atr_pct_from_50sma", float("nan"))

    if pd.notna(atr_from_50sma) and float(atr_from_50sma) > config.mature_stage_atr_from_50sma_max:
        return False
    if pd.notna(dist_from_52w_low) and float(dist_from_52w_low) > config.mature_stage_dist_from_52w_low_max:
        return False
    if (
        pd.notna(days_since_start)
        and float(days_since_start) > config.mature_stage_max_days_since_start
        and pd.notna(dist_from_52w_low)
        and float(dist_from_52w_low) > 150.0
    ):
        return False
    return True


def _bounded_ratio(value: object, low: float, high: float) -> float:
    if pd.isna(value):
        return 0.0
    if high <= low:
        return 0.0
    numeric = float(value)
    if numeric <= low:
        return 0.0
    if numeric >= high:
        return 1.0
    return (numeric - low) / (high - low)


def _trend_template_pass(row: pd.Series, config: ScanConfig) -> bool:
    rs21 = _raw_rs(row, 21)
    return bool(
        row.get("trend_template_price_score", 0) >= config.trend_template_price_score_min
        and pd.notna(rs21)
        and float(rs21) >= config.trend_template_rs_min
    )
