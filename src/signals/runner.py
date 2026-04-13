from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

import pandas as pd

from src.dashboard.watchlist import WatchlistViewModelBuilder
from src.scan.rules import DuplicateRuleConfig, ScanConfig
from src.signals.rules import ENTRY_SIGNAL_REGISTRY, EntrySignalConfig


class EntrySignalRunner:
    """Evaluate entry-timing signals on duplicate-ticker universes."""

    def __init__(self, signal_config: EntrySignalConfig, scan_config: ScanConfig) -> None:
        self.signal_config = signal_config
        self.scan_config = scan_config
        self.watchlist_builder = WatchlistViewModelBuilder(scan_config)

    def build_default_universe(
        self,
        watchlist: pd.DataFrame,
        hits: pd.DataFrame,
        *,
        selected_scan_names: Iterable[str],
        duplicate_threshold: int,
        selected_annotation_filters: Iterable[str] | None = None,
        selected_duplicate_subfilters: Iterable[str] | None = None,
        duplicate_rule: DuplicateRuleConfig | None = None,
    ) -> pd.DataFrame:
        source_by_ticker: dict[str, set[str]] = defaultdict(set)

        for preset in self.scan_config.watchlist_presets:
            if not preset.export_enabled:
                continue
            preset_frame = self._project_preset_duplicates(watchlist, hits, preset)
            for ticker in preset_frame.index.astype(str):
                source_by_ticker[ticker.upper()].add(preset.preset_name)

        current_frame = self._project_current_duplicates(
            watchlist,
            hits,
            selected_scan_names=selected_scan_names,
            duplicate_threshold=duplicate_threshold,
            selected_annotation_filters=selected_annotation_filters,
            selected_duplicate_subfilters=selected_duplicate_subfilters,
            duplicate_rule=duplicate_rule,
        )
        for ticker in current_frame.index.astype(str):
            source_by_ticker[ticker.upper()].add("Current Selection")

        if not source_by_ticker or watchlist.empty:
            return pd.DataFrame()

        lookup = watchlist.copy()
        lookup.index = lookup.index.astype(str).str.upper()
        tickers = [ticker for ticker in sorted(source_by_ticker) if ticker in lookup.index]
        if not tickers:
            return pd.DataFrame()
        universe = lookup.loc[tickers].copy()
        universe["universe_sources"] = [", ".join(sorted(source_by_ticker[ticker])) for ticker in universe.index]
        return universe

    def evaluate(
        self,
        universe: pd.DataFrame,
        selected_signal_names: Iterable[str],
    ) -> pd.DataFrame:
        selected_names = self._normalize_selected_signal_names(selected_signal_names)
        if universe.empty or not selected_names:
            return pd.DataFrame(columns=self._result_columns())

        rows: list[dict[str, object]] = []
        for ticker, row in universe.iterrows():
            hit_names: list[str] = []
            notes: list[str] = []
            risk_refs: list[str] = []
            for signal_name in selected_names:
                definition = ENTRY_SIGNAL_REGISTRY[signal_name]
                if definition.evaluator(row):
                    hit_names.append(definition.display_name)
                    note = definition.note_builder(row)
                    risk = definition.risk_builder(row)
                    if note:
                        notes.append(note)
                    if risk:
                        risk_refs.append(risk)
            if not hit_names:
                continue
            rows.append(
                {
                    "Ticker": str(ticker).upper(),
                    "Entry Signals": ", ".join(hit_names),
                    "Universe Sources": row.get("universe_sources", ""),
                    "Close": row.get("close"),
                    "RS21": row.get("rs21"),
                    "VCS": row.get("vcs"),
                    "Rel Volume": row.get("rel_volume"),
                    "Dist 52W High": row.get("dist_from_52w_high"),
                    "Risk Reference": ", ".join(dict.fromkeys(risk_refs)),
                    "Entry Note": " | ".join(dict.fromkeys(notes)),
                }
            )

        result = pd.DataFrame(rows, columns=self._result_columns())
        if result.empty:
            return result
        for column in ["Close", "RS21", "VCS", "Rel Volume", "Dist 52W High"]:
            if column in result.columns:
                result[column] = pd.to_numeric(result[column], errors="coerce").round(2)
        sort_columns = [column for column in ["RS21", "VCS", "Rel Volume"] if column in result.columns]
        if sort_columns:
            result = result.sort_values(sort_columns, ascending=[False] * len(sort_columns)).reset_index(drop=True)
        return result

    def _project_preset_duplicates(self, watchlist: pd.DataFrame, hits: pd.DataFrame, preset) -> pd.DataFrame:
        filtered = self.watchlist_builder.filter_by_annotation_filters(watchlist, preset.selected_annotation_filters)
        projected = self.watchlist_builder.apply_selected_scan_metrics(
            filtered,
            hits,
            min_count=preset.duplicate_threshold,
            selected_scan_names=preset.selected_scan_names,
            duplicate_rule=preset.duplicate_rule,
        )
        if projected.empty or "duplicate_ticker" not in projected.columns:
            return projected.iloc[0:0].copy()
        return projected.loc[projected["duplicate_ticker"].fillna(False)].copy()

    def _project_current_duplicates(
        self,
        watchlist: pd.DataFrame,
        hits: pd.DataFrame,
        *,
        selected_scan_names: Iterable[str],
        duplicate_threshold: int,
        selected_annotation_filters: Iterable[str] | None,
        selected_duplicate_subfilters: Iterable[str] | None,
        duplicate_rule: DuplicateRuleConfig | None,
    ) -> pd.DataFrame:
        filtered = self.watchlist_builder.filter_by_annotation_filters(watchlist, selected_annotation_filters)
        projected = self.watchlist_builder.apply_selected_scan_metrics(
            filtered,
            hits,
            min_count=duplicate_threshold,
            selected_scan_names=selected_scan_names,
            duplicate_rule=duplicate_rule,
        )
        duplicate_display = self.watchlist_builder.build_duplicate_tickers(
            projected,
            hits,
            min_count=duplicate_threshold,
            selected_scan_names=selected_scan_names,
            selected_duplicate_subfilters=selected_duplicate_subfilters,
            duplicate_rule=duplicate_rule,
        )
        if duplicate_display.empty or "Ticker" not in duplicate_display.columns:
            return projected.iloc[0:0].copy()
        tickers = duplicate_display["Ticker"].astype(str).str.upper().tolist()
        projected_lookup = projected.copy()
        projected_lookup.index = projected_lookup.index.astype(str).str.upper()
        return projected_lookup.loc[projected_lookup.index.intersection(tickers)].copy()

    def _normalize_selected_signal_names(self, selected_signal_names: Iterable[str]) -> tuple[str, ...]:
        enabled_names = set(self.signal_config.enabled_signal_names())
        return tuple(
            dict.fromkeys(
                str(name).strip()
                for name in selected_signal_names
                if str(name).strip() in enabled_names and str(name).strip() in ENTRY_SIGNAL_REGISTRY
            )
        )

    def _result_columns(self) -> list[str]:
        return [
            "Ticker",
            "Entry Signals",
            "Universe Sources",
            "Close",
            "RS21",
            "VCS",
            "Rel Volume",
            "Dist 52W High",
            "Risk Reference",
            "Entry Note",
        ]
