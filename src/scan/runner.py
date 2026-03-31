from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.scan.rules import ScanConfig, enrich_with_scan_context, evaluate_list_rules, evaluate_scan_rules


@dataclass(slots=True)
class ScanRunResult:
    """Normalized output of scan execution."""

    hits: pd.DataFrame
    watchlist: pd.DataFrame


class ScanRunner:
    """Execute scans and aggregate watchlist candidates."""

    def __init__(self, config: ScanConfig) -> None:
        self.config = config

    def run(self, snapshot: pd.DataFrame) -> ScanRunResult:
        if snapshot.empty:
            empty = snapshot.copy()
            return ScanRunResult(hits=pd.DataFrame(columns=["ticker", "kind", "name"]), watchlist=empty)

        working = enrich_with_scan_context(snapshot)
        records: list[dict[str, object]] = []
        for ticker, row in working.iterrows():
            for name, matched in evaluate_scan_rules(row, self.config).items():
                if matched:
                    records.append({"ticker": ticker, "kind": "scan", "name": name})
            for name, matched in evaluate_list_rules(row, self.config).items():
                if matched:
                    records.append({"ticker": ticker, "kind": "list", "name": name})

        hits = pd.DataFrame(records, columns=["ticker", "kind", "name"])
        watchlist = working.copy()
        if hits.empty:
            watchlist["hit_scans"] = ""
            watchlist["hit_lists"] = ""
            watchlist["overlap_count"] = 0
            watchlist["list_overlap_count"] = 0
            watchlist["duplicate_ticker"] = False
            watchlist = self._sort_watchlist(watchlist)
            return ScanRunResult(hits=hits, watchlist=watchlist)

        scan_hits = hits.loc[hits["kind"] == "scan"].groupby("ticker")["name"].agg(lambda values: ", ".join(sorted(values)))
        list_hits = hits.loc[hits["kind"] == "list"].groupby("ticker")["name"].agg(lambda values: ", ".join(sorted(values)))
        list_overlap_count = hits.loc[hits["kind"] == "list"].groupby("ticker").size()
        scan_hit_count = hits.loc[hits["kind"] == "scan"].groupby("ticker").size()
        hit_count = hits.groupby("ticker").size()

        watchlist["hit_scans"] = scan_hits.reindex(watchlist.index).fillna("")
        watchlist["hit_lists"] = list_hits.reindex(watchlist.index).fillna("")
        watchlist["scan_hit_count"] = scan_hit_count.reindex(watchlist.index).fillna(0).astype(int)
        watchlist["overlap_count"] = watchlist["scan_hit_count"]
        watchlist["list_overlap_count"] = list_overlap_count.reindex(watchlist.index).fillna(0).astype(int)
        watchlist["hit_count"] = hit_count.reindex(watchlist.index).fillna(0).astype(int)
        watchlist["duplicate_ticker"] = watchlist["scan_hit_count"] >= self.config.duplicate_min_count
        watchlist = watchlist.loc[watchlist["scan_hit_count"] > 0].copy()
        watchlist = self._sort_watchlist(watchlist)
        return ScanRunResult(hits=hits, watchlist=watchlist)

    def _sort_watchlist(self, watchlist: pd.DataFrame) -> pd.DataFrame:
        if watchlist.empty:
            return watchlist
        if self.config.watchlist_sort_mode == "overlap_then_hybrid":
            priorities = ["overlap_count", "hybrid_score", "vcs", "rs21"]
        else:
            priorities = ["hybrid_score", "overlap_count", "vcs", "rs21"]
        sort_columns = [column for column in priorities if column in watchlist.columns]
        if not sort_columns:
            return watchlist
        return watchlist.sort_values(sort_columns, ascending=[False] * len(sort_columns))
