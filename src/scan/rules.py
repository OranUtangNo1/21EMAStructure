from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.utils import percent_rank

RuleEvaluator = Callable[[pd.Series, "ScanConfig"], bool]

DEFAULT_SCAN_RULE_NAMES = (
    "21EMA scan",
    "4% bullish",
    "Vol Up",
    "Momentum 97",
    "97 Club",
    "VCS",
    "Pocket Pivot",
    "PP Count",
    "Weekly 20% plus gainers",
)

DEFAULT_LIST_RULE_NAMES = (
    "Momentum 97",
    "Volatility Contraction Score",
    "21EMA Watch",
    "4% Gainers",
    "Relative Strength 21 > 63",
    "Vol Up Gainers",
    "High Est. EPS Growth",
)

DEFAULT_CARD_SORT_COLUMNS = ("hybrid_score", "overlap_count", "vcs")
DEFAULT_CARD_SECTION_PAYLOADS = (
    {"scan_name": "21EMA scan", "display_name": "21EMA"},
    {"scan_name": "4% bullish", "display_name": "4% bullish"},
    {"scan_name": "Vol Up", "display_name": "Vol Up"},
    {"scan_name": "Momentum 97", "display_name": "Momentum 97"},
    {"scan_name": "97 Club", "display_name": "97 Club"},
    {"scan_name": "VCS", "display_name": "VCS"},
    {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
    {"scan_name": "PP Count", "display_name": "3+ Pocket Pivots (30d)"},
    {"scan_name": "Weekly 20% plus gainers", "display_name": "Weekly 20%+ Gainers"},
)


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
class ScanConfig:
    """Configurable thresholds, rule selection, and scan-card settings."""

    daily_gain_bullish_threshold: float = 4.0
    relative_volume_bullish_threshold: float = 1.0
    relative_volume_vol_up_threshold: float = 1.5
    momentum_97_weekly_rank: float = 97.0
    momentum_97_quarterly_rank: float = 85.0
    club_97_hybrid_threshold: float = 90.0
    club_97_rs21_threshold: float = 97.0
    vcs_min_threshold: float = 60.0
    weekly_gainer_threshold: float = 20.0
    duplicate_min_count: int = 3
    high_eps_growth_rank_threshold: float = 90.0
    earnings_warning_days: int = 7
    watchlist_sort_mode: str = "hybrid_score"
    enabled_scan_rules: tuple[str, ...] = field(default_factory=lambda: DEFAULT_SCAN_RULE_NAMES)
    enabled_list_rules: tuple[str, ...] = field(default_factory=lambda: DEFAULT_LIST_RULE_NAMES)
    card_sections: tuple[ScanCardConfig, ...] = field(
        default_factory=lambda: tuple(ScanCardConfig.from_dict(payload) for payload in DEFAULT_CARD_SECTION_PAYLOADS)
    )

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ScanConfig":
        base_payload = {key: value for key, value in payload.items() if key in cls.__dataclass_fields__ and key not in {"enabled_scan_rules", "enabled_list_rules", "card_sections"}}
        enabled_scan_rules = tuple(str(name).strip() for name in payload.get("enabled_scan_rules", DEFAULT_SCAN_RULE_NAMES) if str(name).strip())
        enabled_list_rules = tuple(str(name).strip() for name in payload.get("enabled_list_rules", DEFAULT_LIST_RULE_NAMES) if str(name).strip())
        card_payloads = payload.get("card_sections", DEFAULT_CARD_SECTION_PAYLOADS)
        card_sections = tuple(ScanCardConfig.from_dict(item) for item in card_payloads)
        config = cls(
            **base_payload,
            enabled_scan_rules=enabled_scan_rules or DEFAULT_SCAN_RULE_NAMES,
            enabled_list_rules=enabled_list_rules or DEFAULT_LIST_RULE_NAMES,
            card_sections=card_sections,
        )
        _validate_rule_names(config.enabled_scan_rules, SCAN_RULE_REGISTRY, "scan")
        _validate_rule_names(config.enabled_list_rules, LIST_RULE_REGISTRY, "list")
        _validate_card_sections(config.card_sections)
        return config


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


def evaluate_list_rules(row: pd.Series, config: ScanConfig) -> dict[str, bool]:
    """Evaluate the configured working lists used to derive duplicate tickers."""
    return _evaluate_rule_set(row, config.enabled_list_rules, config, LIST_RULE_REGISTRY, "list")


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


def _scan_21ema(row: pd.Series, config: ScanConfig) -> bool:
    weekly_return = row.get("weekly_return", float("nan"))
    return bool(
        weekly_return >= 0.0
        and weekly_return <= 15.0
        and row.get("dcr_percent", 0.0) > 20.0
        and -0.5 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
        and 0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
        and row.get("pp_count_30d", 0) > 1
        and row.get("trend_base", False)
    )


def _scan_bullish_4pct(row: pd.Series, config: ScanConfig) -> bool:
    raw_rs21 = _raw_rs(row, 21)
    return bool(
        row.get("rel_volume", 0.0) >= config.relative_volume_bullish_threshold
        and row.get("daily_change_pct", 0.0) >= config.daily_gain_bullish_threshold
        and row.get("from_open_pct", 0.0) > 0.0
        and raw_rs21 > 60.0
    )


def _scan_vol_up(row: pd.Series, config: ScanConfig) -> bool:
    return bool(
        row.get("rel_volume", 0.0) >= config.relative_volume_vol_up_threshold
        and row.get("daily_change_pct", 0.0) > 0.0
    )


def _scan_momentum_97(row: pd.Series, config: ScanConfig) -> bool:
    return bool(
        row.get("weekly_return_rank", 0.0) >= config.momentum_97_weekly_rank
        and row.get("quarterly_return_rank", 0.0) >= config.momentum_97_quarterly_rank
        and row.get("trend_base", False)
    )


def _scan_97_club(row: pd.Series, config: ScanConfig) -> bool:
    raw_rs21 = _raw_rs(row, 21)
    return bool(
        row.get("hybrid_score", 0.0) >= config.club_97_hybrid_threshold
        and raw_rs21 >= config.club_97_rs21_threshold
        and row.get("trend_base", False)
    )


def _scan_vcs(row: pd.Series, config: ScanConfig) -> bool:
    raw_rs21 = _raw_rs(row, 21)
    return bool(row.get("vcs", 0.0) >= config.vcs_min_threshold and raw_rs21 > 60.0)


def _scan_pocket_pivot(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("close", 0.0) > row.get("sma50", float("inf")) and row.get("pocket_pivot", False))


def _scan_pp_count(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("pp_count_30d", 0) > 3 and row.get("trend_base", False))


def _scan_weekly_gainer(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("weekly_return", 0.0) >= config.weekly_gainer_threshold)


def _list_momentum_97(row: pd.Series, config: ScanConfig) -> bool:
    return bool(
        row.get("weekly_return_rank", 0.0) >= config.momentum_97_weekly_rank
        and row.get("quarterly_return_rank", 0.0) >= config.momentum_97_quarterly_rank
    )


def _list_vcs(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("vcs", 0.0) >= config.vcs_min_threshold)


def _list_21ema_watch(row: pd.Series, config: ScanConfig) -> bool:
    return bool(
        row.get("close", 0.0) >= row.get("ema21_low", float("inf"))
        and row.get("ema21_low_pct", float("inf")) <= 8.0
        and -0.5 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
    )


def _list_4pct_gainers(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("daily_change_pct", 0.0) >= config.daily_gain_bullish_threshold)


def _list_rs21_gt_63(row: pd.Series, config: ScanConfig) -> bool:
    rsi21 = row.get("rsi21", float("nan"))
    rsi63 = row.get("rsi63", float("nan"))
    return bool(pd.notna(rsi21) and pd.notna(rsi63) and float(rsi21) > float(rsi63))


def _list_vol_up_gainers(row: pd.Series, config: ScanConfig) -> bool:
    return bool(
        row.get("rel_volume", 0.0) >= config.relative_volume_vol_up_threshold
        and row.get("daily_change_pct", 0.0) > 0.0
    )


def _list_high_eps_growth(row: pd.Series, config: ScanConfig) -> bool:
    return bool(row.get("eps_growth_rank", 0.0) >= config.high_eps_growth_rank_threshold)


SCAN_RULE_REGISTRY: dict[str, RuleEvaluator] = {
    "21EMA scan": _scan_21ema,
    "4% bullish": _scan_bullish_4pct,
    "Vol Up": _scan_vol_up,
    "Momentum 97": _scan_momentum_97,
    "97 Club": _scan_97_club,
    "VCS": _scan_vcs,
    "Pocket Pivot": _scan_pocket_pivot,
    "PP Count": _scan_pp_count,
    "Weekly 20% plus gainers": _scan_weekly_gainer,
}

LIST_RULE_REGISTRY: dict[str, RuleEvaluator] = {
    "Momentum 97": _list_momentum_97,
    "Volatility Contraction Score": _list_vcs,
    "21EMA Watch": _list_21ema_watch,
    "4% Gainers": _list_4pct_gainers,
    "Relative Strength 21 > 63": _list_rs21_gt_63,
    "Vol Up Gainers": _list_vol_up_gainers,
    "High Est. EPS Growth": _list_high_eps_growth,
}


def _raw_rs(row: pd.Series, lookback: int) -> float:
    value = row.get(f"raw_rs{lookback}", row.get(f"rs{lookback}", float("nan")))
    return float(value) if pd.notna(value) else float("nan")
