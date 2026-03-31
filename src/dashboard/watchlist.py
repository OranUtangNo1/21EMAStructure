from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.scan.rules import ScanCardConfig, ScanConfig


@dataclass(slots=True)
class ScanCardViewModel:
    scan_name: str
    display_name: str
    ticker_count: int
    rows: pd.DataFrame


class WatchlistViewModelBuilder:
    """Prepare screening-only watchlist outputs for Streamlit."""

    def __init__(self, config: ScanConfig | None = None) -> None:
        self.config = config or ScanConfig()

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
            "scan_hit_count",
            "list_overlap_count",
            "duplicate_ticker",
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

        cards: list[ScanCardViewModel] = []
        for section in self.config.card_sections:
            card = self._build_single_card(section, watchlist, hits)
            if card is not None:
                cards.append(card)
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

    def build_duplicate_tickers(self, watchlist: pd.DataFrame, hits: pd.DataFrame, min_count: int) -> pd.DataFrame:
        if watchlist.empty or hits.empty:
            return pd.DataFrame(columns=["Ticker", "Scan Hits", "Hybrid-RS", "Overlap", "VCS"])

        scan_hits = hits.loc[hits["kind"] == "scan"].copy()
        if scan_hits.empty:
            return pd.DataFrame(columns=["Ticker", "Scan Hits", "Hybrid-RS", "Overlap", "VCS"])

        scan_counts = scan_hits.groupby("ticker")["name"].nunique()
        duplicate_symbols = scan_counts.loc[scan_counts >= int(min_count)].index.tolist()
        if not duplicate_symbols:
            return pd.DataFrame(columns=["Ticker", "Scan Hits", "Hybrid-RS", "Overlap", "VCS"])

        frame = watchlist.loc[watchlist.index.intersection(duplicate_symbols)].copy()
        if frame.empty:
            return pd.DataFrame(columns=["Ticker", "Scan Hits", "Hybrid-RS", "Overlap", "VCS"])

        frame["scan_hit_count"] = scan_counts.reindex(frame.index).fillna(0).astype(int)
        if "overlap_count" not in frame.columns:
            frame["overlap_count"] = frame["scan_hit_count"]
        frame["duplicate_ticker"] = frame["scan_hit_count"] >= int(min_count)
        sort_columns = [column for column in ["scan_hit_count", "hybrid_score", "overlap_count", "vcs"] if column in frame.columns]
        if sort_columns:
            frame = frame.sort_values(sort_columns, ascending=[False] * len(sort_columns))

        display = frame.reset_index(names="Ticker").copy()
        columns = ["Ticker", "scan_hit_count", "hybrid_score", "overlap_count", "vcs"]
        available = [column for column in columns if column in display.columns]
        display = display[available].copy()
        display = display.rename(columns={"scan_hit_count": "Scan Hits", "hybrid_score": "Hybrid-RS", "overlap_count": "Overlap", "vcs": "VCS"})
        for column in ["Hybrid-RS", "VCS"]:
            if column in display.columns:
                display[column] = display[column].round(2)
        return display

    def _build_single_card(self, section: ScanCardConfig, watchlist: pd.DataFrame, hits: pd.DataFrame) -> ScanCardViewModel | None:
        section_hits = hits.loc[(hits["kind"] == "scan") & (hits["name"] == section.scan_name), "ticker"].drop_duplicates().tolist()
        if not section_hits:
            return None
        frame = watchlist.loc[watchlist.index.intersection(section_hits)].copy()
        if frame.empty:
            return None
        sort_columns = [column for column in section.sort_columns if column in frame.columns]
        if sort_columns:
            frame = frame.sort_values(sort_columns, ascending=[False] * len(sort_columns))
        return ScanCardViewModel(
            scan_name=section.scan_name,
            display_name=section.display_name or section.scan_name,
            ticker_count=len(frame),
            rows=self._build_card_rows(frame),
        )

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
