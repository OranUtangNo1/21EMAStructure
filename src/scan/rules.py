from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.utils import percent_rank


@dataclass(slots=True)
class ScanConfig:
    """Configurable thresholds for scans and list generation."""

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

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ScanConfig":
        return cls(**{key: value for key, value in payload.items() if key in cls.__dataclass_fields__})


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
    """Evaluate the nine scan families on a single latest snapshot row."""
    weekly_return = row.get("weekly_return", float("nan"))
    raw_rs21 = _raw_rs(row, 21)
    return {
        "21EMA scan": bool(
            row.get("weekly_return", float("nan")) >= 0.0
            and weekly_return <= 15.0
            and row.get("dcr_percent", 0.0) > 20.0
            and -0.5 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
            and 0.0 <= row.get("atr_50sma_zone", float("nan")) <= 3.0
            and row.get("pp_count_30d", 0) > 1
            and row.get("trend_base", False)
        ),
        "4% bullish": bool(
            row.get("rel_volume", 0.0) >= config.relative_volume_bullish_threshold
            and row.get("daily_change_pct", 0.0) >= config.daily_gain_bullish_threshold
            and row.get("from_open_pct", 0.0) > 0.0
            and raw_rs21 > 60.0
        ),
        "Vol Up": bool(
            row.get("rel_volume", 0.0) >= config.relative_volume_vol_up_threshold
            and row.get("daily_change_pct", 0.0) > 0.0
        ),
        "Momentum 97": bool(
            row.get("weekly_return_rank", 0.0) >= config.momentum_97_weekly_rank
            and row.get("quarterly_return_rank", 0.0) >= config.momentum_97_quarterly_rank
            and row.get("trend_base", False)
        ),
        "97 Club": bool(
            row.get("hybrid_score", 0.0) >= config.club_97_hybrid_threshold
            and raw_rs21 >= config.club_97_rs21_threshold
            and row.get("trend_base", False)
        ),
        "VCS": bool(
            row.get("vcs", 0.0) >= config.vcs_min_threshold
            and raw_rs21 > 60.0
        ),
        "Pocket Pivot": bool(
            row.get("close", 0.0) > row.get("sma50", float("inf"))
            and row.get("pocket_pivot", False)
        ),
        "PP Count": bool(
            row.get("pp_count_30d", 0) > 3
            and row.get("trend_base", False)
        ),
        "Weekly 20% plus gainers": bool(row.get("weekly_return", 0.0) >= config.weekly_gainer_threshold),
    }


def evaluate_list_rules(row: pd.Series, config: ScanConfig) -> dict[str, bool]:
    """Evaluate the seven working lists used to derive duplicate tickers."""
    return {
        "Momentum 97": bool(
            row.get("weekly_return_rank", 0.0) >= config.momentum_97_weekly_rank
            and row.get("quarterly_return_rank", 0.0) >= config.momentum_97_quarterly_rank
        ),
        "Volatility Contraction Score": bool(row.get("vcs", 0.0) >= config.vcs_min_threshold),
        "21EMA Watch": bool(
            row.get("close", 0.0) >= row.get("ema21_low", float("inf"))
            and row.get("ema21_low_pct", float("inf")) <= 8.0
            and -0.5 <= row.get("atr_21ema_zone", float("nan")) <= 1.0
        ),
        "4% Gainers": bool(row.get("daily_change_pct", 0.0) >= config.daily_gain_bullish_threshold),
        "Relative Strength 21 > 63": bool(_raw_rs(row, 21) > _raw_rs(row, 63)),
        "Vol Up Gainers": bool(
            row.get("rel_volume", 0.0) >= config.relative_volume_vol_up_threshold
            and row.get("daily_change_pct", 0.0) > 0.0
        ),
        "High Est. EPS Growth": bool(row.get("eps_growth_rank", 0.0) >= config.high_eps_growth_rank_threshold),
    }


def _raw_rs(row: pd.Series, lookback: int) -> float:
    value = row.get(f"raw_rs{lookback}", row.get(f"rs{lookback}", float("nan")))
    return float(value) if pd.notna(value) else float("nan")
