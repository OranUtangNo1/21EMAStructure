from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.scan.rules import (
    ScanConfig,
    annotation_filter_column_name,
    enrich_with_scan_context,
    evaluate_annotation_filters,
    evaluate_scan_rules,
)


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
        scan_records: list[dict[str, object]] = []
        annotation_records: dict[str, dict[str, bool]] = {}
        annotation_filter_names = tuple(section.filter_name for section in self.config.annotation_filters)

        for ticker, row in working.iterrows():
            scan_results = evaluate_scan_rules(row, self.config)
            annotation_results = evaluate_annotation_filters(row, self.config)
            annotation_records[ticker] = annotation_results

            for name, matched in scan_results.items():
                if matched:
                    scan_records.append({"ticker": ticker, "kind": "scan", "name": name})

        hits = pd.DataFrame(scan_records, columns=["ticker", "kind", "name"])
        watchlist = working.copy()

        for filter_name in annotation_filter_names:
            column_name = annotation_filter_column_name(filter_name)
            watchlist[column_name] = [bool(annotation_records.get(ticker, {}).get(filter_name, False)) for ticker in watchlist.index]

        if annotation_filter_names:
            annotation_names_by_ticker: dict[str, str] = {}
            annotation_counts_by_ticker: dict[str, int] = {}
            for ticker in watchlist.index:
                matched_names = [name for name in annotation_filter_names if annotation_records.get(ticker, {}).get(name, False)]
                annotation_names_by_ticker[ticker] = ", ".join(matched_names)
                annotation_counts_by_ticker[ticker] = len(matched_names)
            watchlist["annotation_hits"] = pd.Series(annotation_names_by_ticker).reindex(watchlist.index).fillna("")
            watchlist["annotation_hit_count"] = (
                pd.Series(annotation_counts_by_ticker).reindex(watchlist.index).fillna(0).astype(int)
            )
        else:
            watchlist["annotation_hits"] = ""
            watchlist["annotation_hit_count"] = 0

        if hits.empty:
            watchlist["hit_scans"] = ""
            watchlist["hit_lists"] = ""
            watchlist["scan_hit_count"] = 0
            watchlist["overlap_count"] = 0
            watchlist["list_overlap_count"] = 0
            watchlist["hit_count"] = 0
            watchlist["duplicate_ticker"] = False
            watchlist = watchlist.iloc[0:0].copy()
            watchlist = self._sort_watchlist(watchlist)
            return ScanRunResult(hits=hits, watchlist=watchlist)

        scan_hits = hits.groupby("ticker")["name"].agg(lambda values: ", ".join(sorted(values)))
        scan_hit_count = hits.groupby("ticker").size()

        watchlist["hit_scans"] = scan_hits.reindex(watchlist.index).fillna("")
        watchlist["scan_hit_count"] = scan_hit_count.reindex(watchlist.index).fillna(0).astype(int)
        watchlist["overlap_count"] = watchlist["scan_hit_count"]
        watchlist["hit_lists"] = watchlist["hit_scans"]
        watchlist["list_overlap_count"] = watchlist["scan_hit_count"]
        watchlist["hit_count"] = watchlist["scan_hit_count"]
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
