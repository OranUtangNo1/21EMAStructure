from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class HybridScoreConfig:
    """Configuration for Hybrid Score weight composition."""

    rs_weights: tuple[float, float, float] = (1.0, 2.0, 2.0)
    fundamental_weight: float = 2.0
    industry_weight: float = 3.0
    hybrid_missing_value_policy: str = "fill_neutral_50"

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "HybridScoreConfig":
        rs_weights = tuple(float(value) for value in payload.get("rs_weights", [1.0, 2.0, 2.0]))
        return cls(
            rs_weights=(rs_weights[0], rs_weights[1], rs_weights[2]),
            fundamental_weight=float(payload.get("fundamental_weight", 2.0)),
            industry_weight=float(payload.get("industry_weight", 3.0)),
            hybrid_missing_value_policy=str(payload.get("hybrid_missing_value_policy", "fill_neutral_50")),
        )


@dataclass(slots=True)
class HybridScoreBreakdown:
    """Explainable Hybrid Score output for a single symbol."""

    ticker: str
    trade_date: str | None
    hybrid_score: float | None
    fundamental_score: float | None
    industry_score: float | None
    rs21: float | None
    rs63: float | None
    rs126: float | None


class HybridScoreCalculator:
    """Blend RS, fundamental, and industry inputs into a single ranking score."""

    def __init__(self, config: HybridScoreConfig) -> None:
        self.config = config

    def score(self, snapshot: pd.DataFrame) -> pd.DataFrame:
        result = snapshot.copy()
        component_columns = ["rs21", "rs63", "rs126", "fundamental_score", "industry_score"]
        weights = np.array(
            [
                self.config.rs_weights[0],
                self.config.rs_weights[1],
                self.config.rs_weights[2],
                self.config.fundamental_weight,
                self.config.industry_weight,
            ],
            dtype=float,
        )

        scores = []
        for _, row in result[component_columns].iterrows():
            values = row.to_numpy(dtype=float)
            if self.config.hybrid_missing_value_policy == "fill_neutral_50":
                values = np.where(np.isnan(values), 50.0, values)
                scores.append(float(np.average(values, weights=weights)))
                continue
            if self.config.hybrid_missing_value_policy == "drop_symbol" and np.isnan(values).any():
                scores.append(np.nan)
                continue
            valid_mask = ~np.isnan(values)
            if not valid_mask.any():
                scores.append(np.nan)
                continue
            usable_values = values[valid_mask]
            usable_weights = weights[valid_mask]
            scores.append(float(np.average(usable_values, weights=usable_weights)))

        result["hybrid_score"] = scores
        result["H"] = result["hybrid_score"]
        result["F"] = result["fundamental_score"]
        result["I"] = result["industry_score"]
        result["21"] = result["rs21"]
        result["63"] = result["rs63"]
        result["126"] = result["rs126"]
        return result
