from __future__ import annotations

import pandas as pd

from src.entry.evaluator import EntryEvaluationResult
from src.risk.exits import ExitEvaluationResult
from src.risk.position_sizing import PositionSizingResult
from src.structure.pivot import StructurePivotResult


class CockpitPanelBuilder:
    """Build the structured sections for the 21EMA Cockpit panel."""

    def build(
        self,
        row: pd.Series,
        entry_result: EntryEvaluationResult,
        position_result: PositionSizingResult,
        pivot_result: StructurePivotResult,
        exit_result: ExitEvaluationResult,
    ) -> dict[str, pd.DataFrame]:
        notes = "; ".join(entry_result.notes) if entry_result.notes else ""
        return {
            "Core Stats": pd.DataFrame(
                {
                    "Metric": [
                        "ADR%",
                        "ATR 21EMA",
                        "ATR 10WMA",
                        "ATR 50SMA",
                        "21EMA Low",
                        "21EMA Low %",
                        "3WT",
                        "ATR% from 50SMA",
                        "IPO Timer",
                    ],
                    "Value": [
                        round(float(row.get("adr_percent", 0.0)), 2),
                        round(float(row.get("atr_21ema_zone", 0.0)), 2),
                        round(float(row.get("atr_10wma_zone", 0.0)), 2),
                        round(float(row.get("atr_50sma_zone", 0.0)), 2),
                        round(float(row.get("ema21_low", 0.0)), 2),
                        round(float(row.get("ema21_low_pct", 0.0)), 2),
                        bool(row.get("three_weeks_tight", False)),
                        round(float(row.get("atr_pct_from_50sma", 0.0)), 2),
                        self._format_ipo_timer(row.get("listing_age_days")),
                    ],
                }
            ),
            "Growth / Fundamentals": pd.DataFrame(
                {
                    "Metric": ["EPS growth", "Revenue growth", "Fundamental Score", "Earnings flag"],
                    "Value": [
                        round(float(row.get("eps_growth", 0.0)), 2) if pd.notna(row.get("eps_growth")) else None,
                        round(float(row.get("revenue_growth", 0.0)), 2) if pd.notna(row.get("revenue_growth")) else None,
                        round(float(row.get("fundamental_score", 0.0)), 2) if pd.notna(row.get("fundamental_score")) else None,
                        bool(row.get("earnings_in_7d", False)),
                    ],
                }
            ),
            "RS / Hybrid": pd.DataFrame(
                {
                    "Metric": ["RS5", "RS21", "RS63", "RS126", "Industry Score", "Hybrid Score"],
                    "Value": [
                        round(float(row.get("rs5", 0.0)), 2) if pd.notna(row.get("rs5")) else None,
                        round(float(row.get("rs21", 0.0)), 2) if pd.notna(row.get("rs21")) else None,
                        round(float(row.get("rs63", 0.0)), 2) if pd.notna(row.get("rs63")) else None,
                        round(float(row.get("rs126", 0.0)), 2) if pd.notna(row.get("rs126")) else None,
                        round(float(row.get("industry_score", 0.0)), 2) if pd.notna(row.get("industry_score")) else None,
                        round(float(row.get("hybrid_score", 0.0)), 2) if pd.notna(row.get("hybrid_score")) else None,
                    ],
                }
            ),
            "Entry Aid": pd.DataFrame(
                {
                    "Metric": [
                        "Structure Pivot",
                        "Breakout state",
                        "Volume confirmation",
                        "Candidate status",
                        "Exit phase",
                        "Notes",
                    ],
                    "Value": [
                        round(float(pivot_result.pivot_price), 2) if pivot_result.pivot_price is not None else None,
                        entry_result.breakout_state,
                        entry_result.volume_confirmation,
                        entry_result.candidate_status,
                        exit_result.phase,
                        notes,
                    ],
                }
            ),
            "Position Sizing": pd.DataFrame(
                {
                    "Metric": ["Entry price", "Stop price", "Risk %", "Position size", "Max loss amount"],
                    "Value": [
                        round(position_result.entry_price, 2),
                        round(position_result.stop_price, 2),
                        round(position_result.risk_ratio, 2),
                        position_result.position_size,
                        round(position_result.max_loss_amount, 2),
                    ],
                }
            ),
        }

    def _format_ipo_timer(self, listing_age_days: object) -> str:
        if listing_age_days is None or pd.isna(listing_age_days):
            return "unknown"
        years = float(listing_age_days) / 365.25
        if years < 1.0:
            return f"{int(listing_age_days)}d"
        return f"{years:.1f}y"
