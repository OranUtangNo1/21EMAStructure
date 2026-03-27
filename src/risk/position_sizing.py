from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass(slots=True)
class PositionSizingConfig:
    """Configuration for independent position sizing logic."""

    stop_mode: str = "ema21_low"
    risk_per_trade_pct: float = 0.5
    fixed_stop_pct: float = 8.0
    atr_stop_multiple: float = 2.0
    position_rounding_policy: str = "floor"

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "PositionSizingConfig":
        return cls(**{key: value for key, value in payload.items() if key in cls.__dataclass_fields__})


@dataclass(slots=True)
class PositionSizingResult:
    """Calculated position size and risk summary."""

    ticker: str
    entry_price: float
    stop_price: float
    risk_per_trade_pct: float
    risk_amount: float
    position_size: int
    max_loss_amount: float
    stop_distance: float
    risk_ratio: float
    stop_mode: str


class PositionSizingCalculator:
    """Calculate size from account risk, entry, and a configurable stop model."""

    def __init__(self, config: PositionSizingConfig) -> None:
        self.config = config

    def calculate(
        self,
        ticker: str,
        account_size: float,
        entry_price: float,
        reference_stop_price: float | None = None,
        atr: float | None = None,
    ) -> PositionSizingResult:
        stop_price = self._resolve_stop(entry_price, reference_stop_price, atr)
        stop_distance = max(entry_price - stop_price, 0.0)
        risk_amount = account_size * self.config.risk_per_trade_pct / 100.0
        if stop_distance <= 0:
            position_size = 0
        else:
            raw_position_size = risk_amount / stop_distance
            position_size = floor(raw_position_size) if self.config.position_rounding_policy == "floor" else round(raw_position_size)
        max_loss_amount = position_size * stop_distance
        risk_ratio = stop_distance / entry_price * 100.0 if entry_price else 0.0
        return PositionSizingResult(
            ticker=ticker,
            entry_price=float(entry_price),
            stop_price=float(stop_price),
            risk_per_trade_pct=float(self.config.risk_per_trade_pct),
            risk_amount=float(risk_amount),
            position_size=int(position_size),
            max_loss_amount=float(max_loss_amount),
            stop_distance=float(stop_distance),
            risk_ratio=float(risk_ratio),
            stop_mode=self.config.stop_mode,
        )

    def _resolve_stop(self, entry_price: float, reference_stop_price: float | None, atr: float | None) -> float:
        if self.config.stop_mode == "fixed_percent":
            return entry_price * (1.0 - self.config.fixed_stop_pct / 100.0)
        if self.config.stop_mode == "atr_based":
            if atr is None:
                raise ValueError("ATR is required for atr_based stop mode.")
            return entry_price - atr * self.config.atr_stop_multiple
        if reference_stop_price is None:
            raise ValueError("reference_stop_price is required for ema21_low stop mode.")
        return reference_stop_price
