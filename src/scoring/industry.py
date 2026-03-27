from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.utils import normalize_series, weighted_mean


@dataclass(slots=True)
class IndustryScoreConfig:
    """Configuration for industry-relative strength aggregation."""

    industry_aggregation_method: str = "mean"
    industry_rs_input_metric: str = "weighted_rs"
    industry_score_normalization_method: str = "percentile"

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "IndustryScoreConfig":
        return cls(
            industry_aggregation_method=str(payload.get("industry_aggregation_method", "mean")),
            industry_rs_input_metric=str(payload.get("industry_rs_input_metric", "weighted_rs")),
            industry_score_normalization_method=str(payload.get("industry_score_normalization_method", "percentile")),
        )


class IndustryScorer:
    """Aggregate symbol-level RS into a configurable industry score."""

    def __init__(self, config: IndustryScoreConfig) -> None:
        self.config = config

    def score(self, snapshot: pd.DataFrame) -> pd.DataFrame:
        result = snapshot.copy()
        metric = self._resolve_input_metric(result)
        working = pd.DataFrame(
            {
                "industry": result["industry"].fillna("Unknown"),
                "metric": metric,
                "market_cap": result["market_cap"].fillna(0.0),
            },
            index=result.index,
        )

        aggregated: dict[str, float] = {}
        for industry, group in working.groupby("industry"):
            if self.config.industry_aggregation_method == "median":
                aggregated[industry] = float(group["metric"].median())
            elif self.config.industry_aggregation_method == "market_cap_weighted_mean":
                aggregated[industry] = weighted_mean(group["metric"], group["market_cap"])
            else:
                aggregated[industry] = float(group["metric"].mean())

        group_scores = pd.Series(aggregated, dtype=float)
        normalized = normalize_series(group_scores, self.config.industry_score_normalization_method)
        result["industry_score"] = working["industry"].map(normalized)
        return result

    def _resolve_input_metric(self, snapshot: pd.DataFrame) -> pd.Series:
        if self.config.industry_rs_input_metric == "rs21":
            return snapshot["rs21"]
        if self.config.industry_rs_input_metric == "rs63":
            return snapshot["rs63"]
        if self.config.industry_rs_input_metric == "rs126":
            return snapshot["rs126"]
        return (snapshot["rs21"] + snapshot["rs63"] * 2.0 + snapshot["rs126"] * 2.0) / 5.0
