from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

SCAN_DISPLAY_ORDER = [
    "21EMA scan",
    "4% bullish",
    "Vol Up",
    "Momentum 97",
    "97 Club",
    "VCS",
    "Pocket Pivot",
    "PP Count",
    "Weekly 20% plus gainers",
]

SCAN_DISPLAY_NAMES = {
    "21EMA scan": "21EMA",
    "4% bullish": "4% bullish",
    "Vol Up": "Vol Up",
    "Momentum 97": "Momentum 97",
    "97 Club": "97 Club",
    "VCS": "VCS",
    "Pocket Pivot": "Pocket Pivot",
    "PP Count": "3+ Pocket Pivots (30d)",
    "Weekly 20% plus gainers": "Weekly 20%+ Gainers",
}


@dataclass(slots=True)
class ScanCardViewModel:
    scan_name: str
    display_name: str
    ticker_count: int
    rows: pd.DataFrame


class WatchlistViewModelBuilder:
    """Prepare screening-only watchlist outputs for Streamlit."""

    def build(self, watchlist: pd.DataFrame) -> pd.DataFrame:
        if watchlist.empty:
            return watchlist.copy()

        table = watchlist.copy()
        table["earnings"] = table["earnings_in_7d"].fillna(False).map(lambda value: "Yes" if value else "No")

        columns = [
            "name",
            "sector",
            "industry",
            "H",
            "F",
            "I",
            "21",
            "63",
            "126",
            "rs5",
            "overlap_count",
            "hit_scans",
            "hit_lists",
            "vcs",
            "earnings",
            "pp_count_30d",
            "ema21_low_pct",
            "atr_21ema_zone",
            "atr_50sma_zone",
            "three_weeks_tight",
            "atr_pct_from_50sma",
            "price_data_source",
            "fundamental_data_source",
            "data_quality_label",
            "data_quality_score",
            "data_warning",
        ]
        available_columns = [column for column in columns if column in table.columns]
        display = table[available_columns].copy()
        numeric_columns = display.select_dtypes(include="number").columns
        display.loc[:, numeric_columns] = display.loc[:, numeric_columns].round(2)
        return display

    def build_scan_cards(self, watchlist: pd.DataFrame, hits: pd.DataFrame) -> list[ScanCardViewModel]:
        if watchlist.empty or hits.empty:
            return []

        scan_hits = hits.loc[hits["kind"] == "scan"].copy()
        if scan_hits.empty:
            return []

        cards: list[ScanCardViewModel] = []
        for scan_name in SCAN_DISPLAY_ORDER:
            tickers = scan_hits.loc[scan_hits["name"] == scan_name, "ticker"].drop_duplicates().tolist()
            if not tickers:
                continue
            frame = watchlist.loc[watchlist.index.intersection(tickers)].copy()
            if frame.empty:
                continue
            sort_columns = [column for column in ["hybrid_score", "overlap_count", "vcs"] if column in frame.columns]
            if sort_columns:
                frame = frame.sort_values(sort_columns, ascending=[False] * len(sort_columns))
            cards.append(
                ScanCardViewModel(
                    scan_name=scan_name,
                    display_name=SCAN_DISPLAY_NAMES.get(scan_name, scan_name),
                    ticker_count=len(frame),
                    rows=self._build_card_rows(frame),
                )
            )
        return cards

    def build_earnings_today(self, snapshot: pd.DataFrame) -> pd.DataFrame:
        if snapshot.empty or "earnings_today" not in snapshot.columns:
            return pd.DataFrame(columns=["Ticker", "Name", "Sector", "Industry", "Hybrid-RS"])

        frame = snapshot.loc[snapshot["earnings_today"].fillna(False)].copy()
        if frame.empty:
            return pd.DataFrame(columns=["Ticker", "Name", "Sector", "Industry", "Hybrid-RS"])

        frame = frame.sort_values(["hybrid_score", "market_cap"], ascending=[False, False])
        display = frame.reset_index(names="Ticker")
        columns = ["Ticker", "name", "sector", "industry", "hybrid_score"]
        available = [column for column in columns if column in display.columns]
        display = display[available].copy()
        display = display.rename(
            columns={
                "name": "Name",
                "sector": "Sector",
                "industry": "Industry",
                "hybrid_score": "Hybrid-RS",
            }
        )
        if "Hybrid-RS" in display.columns:
            display["Hybrid-RS"] = display["Hybrid-RS"].round(2)
        return display

    def _build_card_rows(self, frame: pd.DataFrame) -> pd.DataFrame:
        display = frame.reset_index(names="Ticker").copy()
        duplicate_series = display["duplicate_ticker"] if "duplicate_ticker" in display.columns else pd.Series(False, index=display.index)
        earnings_series = display["earnings_in_7d"] if "earnings_in_7d" in display.columns else pd.Series(False, index=display.index)
        display["Duplicate"] = duplicate_series.fillna(False).map(lambda value: "Yes" if value else "")
        display["Earnings"] = earnings_series.fillna(False).map(lambda value: "Soon" if value else "")
        columns = ["Ticker", "name", "hybrid_score", "overlap_count", "vcs", "Duplicate", "Earnings"]
        available = [column for column in columns if column in display.columns]
        display = display[available].copy()
        display = display.rename(
            columns={
                "name": "Name",
                "hybrid_score": "Hybrid-RS",
                "overlap_count": "Overlap",
                "vcs": "VCS",
            }
        )
        for column in ["Hybrid-RS", "VCS"]:
            if column in display.columns:
                display[column] = display[column].round(2)
        return display


class WatchlistCardGridBuilder(WatchlistViewModelBuilder):
    """Docs-facing alias for the scan card grid builder."""

    pass
