from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.configuration import load_settings
from src.data.universe_snapshot_cache import UniverseSnapshotCache
from src.scoring.fundamental import FundamentalScoreConfig, FundamentalScorer
from src.scoring.hybrid import HybridScoreCalculator, HybridScoreConfig
from src.scoring.industry import IndustryScoreConfig, IndustryScorer
from src.scoring.rs import RSConfig, RSScorer
from src.scoring.vcs import VCSCalculator, VCSConfig


@dataclass(slots=True)
class ScanScoringService:
    """Restore reusable scoring fields required by scans and presets."""

    rs_scorer: RSScorer
    fundamental_scorer: FundamentalScorer
    industry_scorer: IndustryScorer
    hybrid_calculator: HybridScoreCalculator
    vcs_calculator: VCSCalculator
    benchmark_symbol: str = "SPY"
    universe_snapshot_cache: UniverseSnapshotCache | None = None

    @classmethod
    def from_config(cls, config_path: str | Path | None = None) -> "ScanScoringService":
        settings = load_settings(config_path)
        scoring = settings.get("scoring", {}) if isinstance(settings.get("scoring", {}), dict) else {}
        rs_config = RSConfig.from_dict(scoring.get("rs", {}) if isinstance(scoring.get("rs", {}), dict) else {})
        discovery = (
            settings.get("universe_discovery", {})
            if isinstance(settings.get("universe_discovery", {}), dict)
            else {}
        )
        root = Path(__file__).resolve().parents[2]
        snapshot_dir = Path(str(discovery.get("snapshot_dir", "data_cache/universe_snapshots"))).expanduser()
        if not snapshot_dir.is_absolute():
            snapshot_dir = root / snapshot_dir
        return cls(
            rs_scorer=RSScorer(rs_config),
            fundamental_scorer=FundamentalScorer(
                FundamentalScoreConfig.from_dict(
                    scoring.get("fundamental", {}) if isinstance(scoring.get("fundamental", {}), dict) else {}
                )
            ),
            industry_scorer=IndustryScorer(
                IndustryScoreConfig.from_dict(
                    scoring.get("industry", {}) if isinstance(scoring.get("industry", {}), dict) else {}
                )
            ),
            hybrid_calculator=HybridScoreCalculator(
                HybridScoreConfig.from_dict(
                    scoring.get("hybrid", {}) if isinstance(scoring.get("hybrid", {}), dict) else {}
                )
            ),
            vcs_calculator=VCSCalculator(
                VCSConfig.from_dict(scoring.get("vcs", {}) if isinstance(scoring.get("vcs", {}), dict) else {})
            ),
            benchmark_symbol=rs_config.benchmark_symbol.strip().upper() or "SPY",
            universe_snapshot_cache=UniverseSnapshotCache(snapshot_dir),
        )

    def load_universe_snapshot(self, as_of_date: str | pd.Timestamp | None = None) -> pd.DataFrame:
        if self.universe_snapshot_cache is None:
            return pd.DataFrame()
        root = Path(self.universe_snapshot_cache.root_dir)
        if as_of_date is not None:
            parsed = pd.to_datetime(as_of_date, errors="coerce")
            if pd.notna(parsed):
                dated_path = root / f"{pd.Timestamp(parsed).strftime('%Y%m%d')}.csv"
                if dated_path.exists():
                    return self._normalize_universe_snapshot(pd.read_csv(dated_path))
        cached = self.universe_snapshot_cache.load(max_age_days=None)
        return self._normalize_universe_snapshot(cached.snapshot)

    def score(
        self,
        snapshot: pd.DataFrame,
        histories: dict[str, pd.DataFrame],
        benchmark_history: pd.DataFrame,
        *,
        universe_snapshot: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        if snapshot is None or snapshot.empty:
            return pd.DataFrame() if snapshot is None else snapshot.copy()
        enriched = self._merge_universe_snapshot(snapshot, universe_snapshot)
        selected_histories = {
            str(ticker): histories[str(ticker)]
            for ticker in enriched.index
            if str(ticker) in histories and histories[str(ticker)] is not None
        }
        enriched = self.rs_scorer.score(enriched, selected_histories, benchmark_history)
        if enriched["raw_rs21"].notna().sum() == 0:
            raise RuntimeError(
                "Scan scoring produced no raw_rs21 values; benchmark or symbol histories are unavailable."
            )
        enriched = self.fundamental_scorer.score(enriched)
        if enriched["industry"].notna().any() and enriched["industry"].astype(str).ne("Unknown").any():
            enriched = self.industry_scorer.score(enriched)
        else:
            enriched["industry_score"] = np.nan
        enriched = self.hybrid_calculator.score(enriched)
        enriched = self.vcs_calculator.add_scores(enriched, selected_histories)
        return enriched

    def _merge_universe_snapshot(
        self,
        snapshot: pd.DataFrame,
        universe_snapshot: pd.DataFrame | None,
    ) -> pd.DataFrame:
        result = snapshot.copy()
        result.index = result.index.astype(str).str.strip().str.upper()
        metadata = self._normalize_universe_snapshot(universe_snapshot)
        if not metadata.empty:
            metadata = metadata.drop_duplicates(subset=["ticker"], keep="last").set_index("ticker")
            for column in metadata.columns:
                values = metadata[column].reindex(result.index)
                if column in result.columns:
                    result[column] = result[column].where(result[column].notna(), values)
                else:
                    result[column] = values
        if "ticker" in result.columns:
            result["ticker"] = result.index
        else:
            result.insert(0, "ticker", result.index)
        for column in ("name", "sector", "industry", "country", "exchange"):
            if column not in result.columns:
                result[column] = pd.NA
        result["name"] = result["name"].fillna(pd.Series(result.index, index=result.index))
        result["sector"] = result["sector"].fillna("Unknown")
        result["industry"] = result["industry"].fillna("Unknown")
        for column in ("market_cap", "eps_growth", "revenue_growth"):
            if column not in result.columns:
                result[column] = np.nan
            result[column] = pd.to_numeric(result[column], errors="coerce")
        return result

    def _normalize_universe_snapshot(self, snapshot: pd.DataFrame | None) -> pd.DataFrame:
        if snapshot is None or snapshot.empty or "ticker" not in snapshot.columns:
            return pd.DataFrame()
        result = snapshot.copy()
        result["ticker"] = result["ticker"].astype(str).str.strip().str.upper()
        return result.loc[result["ticker"] != ""].copy()
