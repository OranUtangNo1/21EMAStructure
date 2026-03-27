from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.utils import normalize_series


@dataclass(slots=True)
class FundamentalScoreConfig:
    """Configuration for the replaceable fundamental scoring model."""

    eps_weight: float = 1.0
    revenue_weight: float = 1.0
    fundamental_normalization_method: str = "percentile"
    missing_fundamental_policy: str = "fill_neutral"

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "FundamentalScoreConfig":
        return cls(
            eps_weight=float(payload.get("eps_weight", 1.0)),
            revenue_weight=float(payload.get("revenue_weight", 1.0)),
            fundamental_normalization_method=str(payload.get("fundamental_normalization_method", "percentile")),
            missing_fundamental_policy=str(payload.get("missing_fundamental_policy", "fill_neutral")),
        )


class FundamentalScorer:
    """Transform EPS and revenue growth into a tunable 0-100 score."""

    def __init__(self, config: FundamentalScoreConfig) -> None:
        self.config = config

    def score(self, snapshot: pd.DataFrame) -> pd.DataFrame:
        result = snapshot.copy()
        eps_score = normalize_series(result["eps_growth"], self.config.fundamental_normalization_method)
        revenue_score = normalize_series(result["revenue_growth"], self.config.fundamental_normalization_method)
        result["eps_growth_score"] = eps_score
        result["revenue_growth_score"] = revenue_score

        if self.config.missing_fundamental_policy == "fill_neutral":
            eps_score = eps_score.fillna(50.0)
            revenue_score = revenue_score.fillna(50.0)
            denominator = self.config.eps_weight + self.config.revenue_weight
            result["fundamental_score"] = (
                eps_score * self.config.eps_weight + revenue_score * self.config.revenue_weight
            ) / denominator
        elif self.config.missing_fundamental_policy == "renormalize":
            values = pd.concat([eps_score, revenue_score], axis=1)
            weights = np.array([self.config.eps_weight, self.config.revenue_weight], dtype=float)
            scores = []
            for _, row in values.iterrows():
                valid_mask = row.notna().to_numpy()
                if not valid_mask.any():
                    scores.append(np.nan)
                    continue
                usable_values = row.to_numpy(dtype=float)[valid_mask]
                usable_weights = weights[valid_mask]
                scores.append(float(np.average(usable_values, weights=usable_weights)))
            result["fundamental_score"] = scores
        else:
            valid = eps_score.notna() & revenue_score.notna()
            result["fundamental_score"] = np.where(
                valid,
                (eps_score * self.config.eps_weight + revenue_score * self.config.revenue_weight)
                / (self.config.eps_weight + self.config.revenue_weight),
                np.nan,
            )
        return result
