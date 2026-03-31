from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(slots=True)
class StructurePivotConfig:
    """Configuration for Structure Pivot detection."""

    lengths: tuple[int, ...] = (10, 20, 40)
    priority_mode: str = "tightest"
    min_separation_bars: int = 3

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "StructurePivotConfig":
        lengths = tuple(int(value) for value in payload.get("lengths", [10, 20, 40]))
        return cls(
            lengths=lengths,
            priority_mode=str(payload.get("priority_mode", "tightest")),
            min_separation_bars=int(payload.get("min_separation_bars", 3)),
        )


@dataclass(slots=True)
class StructurePivotCandidate:
    """A detected LL-HL pivot candidate."""

    length: int
    ll_date: pd.Timestamp
    hl_date: pd.Timestamp
    pivot_price: float
    hl_price: float
    compression_pct: float
    breakout_active: bool


@dataclass(slots=True)
class StructurePivotResult:
    """Selected Structure Pivot output for one symbol."""

    ticker: str
    is_valid: bool
    priority_mode: str
    selected_length: int | None = None
    ll_date: pd.Timestamp | None = None
    hl_date: pd.Timestamp | None = None
    pivot_price: float | None = None
    breakout_trigger_price: float | None = None
    breakout_active: bool = False
    higher_low_exists: bool = False
    candidate_count: int = 0
    all_candidates: list[StructurePivotCandidate] = field(default_factory=list)


class StructurePivotDetector:
    """Detect LL-HL Structure Pivot patterns across multiple lookback lengths."""

    def __init__(self, config: StructurePivotConfig) -> None:
        self.config = config

    def detect(self, history: pd.DataFrame, ticker: str) -> StructurePivotResult:
        if history.empty:
            return StructurePivotResult(ticker=ticker, is_valid=False, priority_mode=self.config.priority_mode)

        candidates: list[StructurePivotCandidate] = []
        for length in self.config.lengths:
            window = history.tail(length)
            candidate = self._detect_window(window, length)
            if candidate is not None:
                candidates.append(candidate)

        if not candidates:
            return StructurePivotResult(ticker=ticker, is_valid=False, priority_mode=self.config.priority_mode)

        selected = self._select_candidate(candidates)
        return StructurePivotResult(
            ticker=ticker,
            is_valid=True,
            priority_mode=self.config.priority_mode,
            selected_length=selected.length,
            ll_date=selected.ll_date,
            hl_date=selected.hl_date,
            pivot_price=selected.pivot_price,
            breakout_trigger_price=selected.pivot_price,
            breakout_active=selected.breakout_active,
            higher_low_exists=True,
            candidate_count=len(candidates),
            all_candidates=candidates,
        )

    def _detect_window(self, window: pd.DataFrame, length: int) -> StructurePivotCandidate | None:
        if len(window) < max(6, self.config.min_separation_bars + 3):
            return None

        swing_lows = self._find_swing_lows(window)
        if len(swing_lows) < 2:
            return None

        for ll_pos in swing_lows:
            ll_price = float(window["low"].iloc[ll_pos])
            valid_hl = [
                hl_pos
                for hl_pos in swing_lows
                if hl_pos >= ll_pos + self.config.min_separation_bars and float(window["low"].iloc[hl_pos]) > ll_price
            ]
            if not valid_hl:
                continue
            hl_pos = valid_hl[-1]
            pivot_slice = window.iloc[ll_pos : hl_pos + 1]
            pivot_price = float(pivot_slice["high"].max())
            hl_price = float(window["low"].iloc[hl_pos])
            latest_close = float(window["close"].iloc[-1])
            compression_pct = (pivot_price - hl_price) / pivot_price * 100.0 if pivot_price else 0.0
            return StructurePivotCandidate(
                length=length,
                ll_date=window.index[ll_pos],
                hl_date=window.index[hl_pos],
                pivot_price=pivot_price,
                hl_price=hl_price,
                compression_pct=compression_pct,
                breakout_active=latest_close > pivot_price,
            )
        return None

    def _find_swing_lows(self, window: pd.DataFrame) -> list[int]:
        lows = window["low"].reset_index(drop=True)
        positions: list[int] = []
        for position in range(1, len(lows) - 1):
            current = lows.iloc[position]
            if current < lows.iloc[position - 1] and current <= lows.iloc[position + 1]:
                positions.append(position)
        return positions

    def _select_candidate(self, candidates: list[StructurePivotCandidate]) -> StructurePivotCandidate:
        if self.config.priority_mode == "longest":
            return max(candidates, key=lambda item: item.length)
        if self.config.priority_mode == "shortest":
            return min(candidates, key=lambda item: item.length)
        return min(candidates, key=lambda item: (item.compression_pct, -item.length))
