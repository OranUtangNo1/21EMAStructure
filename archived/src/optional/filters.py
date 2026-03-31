from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(slots=True)
class OptionalFilterResult:
    """Neutral result wrapper for optional modules."""

    name: str
    enabled: bool
    passed: bool | None
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DarvasRetestFilterConfig:
    """Optional Darvas retest filter configuration."""

    enable_darvas_retest_filter: bool = False


class DarvasRetestFilter:
    """Stub implementation reserved for later experiments."""

    def __init__(self, config: DarvasRetestFilterConfig) -> None:
        self.config = config

    def evaluate(self, history: pd.DataFrame) -> OptionalFilterResult:
        return OptionalFilterResult(
            name="DarvasRetestFilter",
            enabled=self.config.enable_darvas_retest_filter,
            passed=None,
            notes=["Stub: consolidation/range/retest logic is intentionally left replaceable."],
        )


@dataclass(slots=True)
class TrendRegimeFilterConfig:
    """Optional trend regime filter configuration."""

    enable_trend_regime_filter: bool = False


class TrendRegimeFilter:
    """Stub implementation reserved for later regime research."""

    def __init__(self, config: TrendRegimeFilterConfig) -> None:
        self.config = config

    def evaluate(self, history: pd.DataFrame) -> OptionalFilterResult:
        return OptionalFilterResult(
            name="TrendRegimeFilter",
            enabled=self.config.enable_trend_regime_filter,
            passed=None,
            notes=["Stub: O'Neil / Minervini alignment is intentionally configurable and not fixed yet."],
        )
