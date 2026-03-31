from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.structure.pivot import StructurePivotResult


@dataclass(slots=True)
class EntryCriteriaConfig:
    """Configurable initial hypothesis for entry candidate evaluation."""

    max_distance_to_ema21_low_pct: float = 8.0
    full_size_distance_to_ema21_low_pct: float = 5.0
    min_rs21: float = 80.0
    min_rs63: float = 80.0
    min_rs126: float = 70.0
    min_hybrid_score: float = 75.0
    min_fundamental_score: float = 50.0
    min_industry_score: float = 40.0
    min_vcs: float = 60.0
    require_higher_low_structure: bool = True
    require_structure_pivot_break: bool = False
    require_volume_confirmation: bool = True
    volume_confirmation_method: str = "relvol"
    min_rel_volume: float = 1.0
    require_price_in_or_above_ema_cloud: bool = True
    min_atr_21ema: float = -0.5
    max_atr_21ema: float = 1.0
    max_atr_50sma: float = 3.0

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "EntryCriteriaConfig":
        return cls(**{key: value for key, value in payload.items() if key in cls.__dataclass_fields__})


@dataclass(slots=True)
class EntryEvaluationResult:
    """Explainable result for entry candidate evaluation."""

    ticker: str
    is_candidate: bool
    candidate_status: str
    passed_rules: list[str] = field(default_factory=list)
    failed_rules: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    distance_to_ema21_low_pct: float | None = None
    atr_21ema_zone: float | None = None
    atr_10wma_zone: float | None = None
    atr_50sma_zone: float | None = None
    three_weeks_tight: bool = False
    rs21: float | None = None
    rs63: float | None = None
    hybrid_score: float | None = None
    vcs: float | None = None
    structure_pivot_price: float | None = None
    volume_confirmation: bool = False
    breakout_state: str = "not_applicable"


class EntryEvaluator:
    """Evaluate a symbol snapshot against a configurable entry hypothesis."""

    def __init__(self, config: EntryCriteriaConfig) -> None:
        self.config = config

    def evaluate(self, ticker: str, row: pd.Series, pivot_result: StructurePivotResult) -> EntryEvaluationResult:
        passed_rules: list[str] = []
        failed_rules: list[str] = []
        notes: list[str] = []

        volume_confirmation = self._volume_confirmation(row)
        breakout_state = "breakout" if pivot_result.breakout_active else "pre_breakout"
        size_bucket = self._size_bucket(float(row.get("ema21_low_pct", float("nan"))))

        self._check_rule(
            "ema21_low_pct <= max",
            row.get("ema21_low_pct", float("inf")) <= self.config.max_distance_to_ema21_low_pct,
            passed_rules,
            failed_rules,
        )
        self._check_rule("close >= ema21_low", row.get("close", 0.0) >= row.get("ema21_low", float("inf")), passed_rules, failed_rules)
        self._check_rule(
            "price in or above 21EMA cloud",
            row.get("close", 0.0) >= row.get("ema21_low", float("inf")) if self.config.require_price_in_or_above_ema_cloud else True,
            passed_rules,
            failed_rules,
        )
        self._check_rule(
            "ATR 21EMA in range",
            self.config.min_atr_21ema <= row.get("atr_21ema_zone", float("nan")) <= self.config.max_atr_21ema,
            passed_rules,
            failed_rules,
        )
        self._check_rule(
            "ATR 50SMA in range",
            row.get("atr_50sma_zone", float("inf")) <= self.config.max_atr_50sma,
            passed_rules,
            failed_rules,
        )
        self._check_rule("close > 50SMA", row.get("close", 0.0) > row.get("sma50", float("inf")), passed_rules, failed_rules)
        self._check_rule(
            "Higher Low structure",
            pivot_result.higher_low_exists if self.config.require_higher_low_structure else True,
            passed_rules,
            failed_rules,
        )
        self._check_rule(
            "Structure Pivot exists",
            pivot_result.is_valid,
            passed_rules,
            failed_rules,
        )
        self._check_rule(
            "RS21 threshold",
            row.get("rs21", 0.0) >= self.config.min_rs21,
            passed_rules,
            failed_rules,
        )
        self._check_rule(
            "RS63 threshold",
            row.get("rs63", 0.0) >= self.config.min_rs63,
            passed_rules,
            failed_rules,
        )
        self._check_rule(
            "RS126 threshold",
            row.get("rs126", 0.0) >= self.config.min_rs126,
            passed_rules,
            failed_rules,
        )
        self._check_rule(
            "Fundamental threshold",
            row.get("fundamental_score", 0.0) >= self.config.min_fundamental_score,
            passed_rules,
            failed_rules,
        )
        self._check_rule(
            "Industry threshold",
            row.get("industry_score", 0.0) >= self.config.min_industry_score,
            passed_rules,
            failed_rules,
        )
        self._check_rule(
            "Hybrid threshold",
            row.get("hybrid_score", 0.0) >= self.config.min_hybrid_score,
            passed_rules,
            failed_rules,
        )

        if self.config.require_volume_confirmation:
            self._check_rule("volume confirmation", volume_confirmation, passed_rules, failed_rules)
        if self.config.require_structure_pivot_break:
            self._check_rule("pivot breakout", pivot_result.breakout_active, passed_rules, failed_rules)

        if row.get("vcs", 0.0) >= self.config.min_vcs:
            notes.append("VCS supports contraction quality")
        if bool(row.get("three_weeks_tight", False)):
            notes.append("3WT detected")
        if size_bucket == "full":
            notes.append("ema21_low_pct is in full-size candidate range")
        elif size_bucket == "reduced":
            notes.append("ema21_low_pct suggests reduced size")
        else:
            notes.append("ema21_low_pct suggests avoid")
        if row.get("overheat", False):
            notes.append("ATR% from 50SMA is overheated")

        is_candidate = len(failed_rules) == 0
        candidate_status = f"{'pass' if is_candidate else 'fail'}:{size_bucket}"
        return EntryEvaluationResult(
            ticker=ticker,
            is_candidate=is_candidate,
            candidate_status=candidate_status,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            notes=notes,
            distance_to_ema21_low_pct=row.get("ema21_low_pct"),
            atr_21ema_zone=row.get("atr_21ema_zone"),
            atr_10wma_zone=row.get("atr_10wma_zone"),
            atr_50sma_zone=row.get("atr_50sma_zone"),
            three_weeks_tight=bool(row.get("three_weeks_tight", False)),
            rs21=row.get("rs21"),
            rs63=row.get("rs63"),
            hybrid_score=row.get("hybrid_score"),
            vcs=row.get("vcs"),
            structure_pivot_price=pivot_result.pivot_price,
            volume_confirmation=volume_confirmation,
            breakout_state=breakout_state,
        )

    def _check_rule(self, label: str, condition: bool, passed_rules: list[str], failed_rules: list[str]) -> None:
        if condition:
            passed_rules.append(label)
        else:
            failed_rules.append(label)

    def _volume_confirmation(self, row: pd.Series) -> bool:
        if self.config.volume_confirmation_method == "pocket_pivot_like":
            return bool(row.get("pocket_pivot", False))
        if self.config.volume_confirmation_method == "10d_high_volume":
            return bool(row.get("pocket_pivot", False) or row.get("rel_volume", 0.0) >= 1.25)
        return bool(row.get("rel_volume", 0.0) >= self.config.min_rel_volume)

    def _size_bucket(self, distance_pct: float) -> str:
        if pd.isna(distance_pct):
            return "unknown"
        if distance_pct <= self.config.full_size_distance_to_ema21_low_pct:
            return "full"
        if distance_pct <= self.config.max_distance_to_ema21_low_pct:
            return "reduced"
        return "avoid"
