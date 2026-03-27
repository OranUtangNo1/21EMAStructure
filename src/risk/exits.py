from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class RiskModelConfig:
    """Configuration for phased exit evaluation."""

    r_hit_method: str = "high"
    trim_fraction: float = 0.33
    overheat_threshold: float = 7.0

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "RiskModelConfig":
        return cls(**{key: value for key, value in payload.items() if key in cls.__dataclass_fields__})


@dataclass(slots=True)
class ExitEvaluationResult:
    """Current exit posture inferred from the two-phase risk model."""

    ticker: str
    initial_stop: float
    initial_risk: float
    hit_1r: bool
    hit_3r: bool
    phase: str
    exit_signal: bool
    exit_reason: str | None
    partial_take_profit_signal: bool


class ExitRuleEvaluator:
    """Evaluate phased exit conditions from a history and current position anchor."""

    def __init__(self, config: RiskModelConfig) -> None:
        self.config = config

    def evaluate(self, ticker: str, history: pd.DataFrame, entry_price: float, initial_stop: float) -> ExitEvaluationResult:
        initial_risk = entry_price - initial_stop
        if history.empty or initial_risk <= 0:
            return ExitEvaluationResult(
                ticker=ticker,
                initial_stop=float(initial_stop),
                initial_risk=float(max(initial_risk, 0.0)),
                hit_1r=False,
                hit_3r=False,
                phase="invalid",
                exit_signal=False,
                exit_reason=None,
                partial_take_profit_signal=False,
            )

        hit_series = history["high"] if self.config.r_hit_method == "high" else history["close"]
        hit_1r = bool(hit_series.max() >= entry_price + initial_risk)
        hit_3r = bool(hit_series.max() >= entry_price + 3.0 * initial_risk)
        latest = history.iloc[-1]

        if not hit_1r:
            phase = "phase_1"
            exit_signal = bool(latest["close"] < latest.get("ema21_low", initial_stop))
            exit_reason = "close_below_ema21_low_before_1R" if exit_signal else None
        elif not hit_3r:
            phase = "phase_2"
            exit_signal = bool(latest["close"] < entry_price)
            exit_reason = "close_below_entry_after_1R" if exit_signal else None
        else:
            phase = "final_tp"
            exit_signal = bool(latest["close"] < latest.get("ema21_low", initial_stop))
            exit_reason = "close_below_ema21_low_after_3R" if exit_signal else None

        partial_take_profit_signal = bool(hit_3r or latest.get("atr_pct_from_50sma", 0.0) >= self.config.overheat_threshold)
        return ExitEvaluationResult(
            ticker=ticker,
            initial_stop=float(initial_stop),
            initial_risk=float(initial_risk),
            hit_1r=hit_1r,
            hit_3r=hit_3r,
            phase=phase,
            exit_signal=exit_signal,
            exit_reason=exit_reason,
            partial_take_profit_signal=partial_take_profit_signal,
        )
