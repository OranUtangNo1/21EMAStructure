from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd

from src.scan.rules import (
    AnnotationFilterConfig,
    DuplicateRuleConfig,
    ScanCardConfig,
    ScanConfig,
    WatchlistPresetConfig,
    annotation_filter_column_name,
)

DUPLICATE_SUBFILTER_TOP3_HYBRID_RS = "Top3 HybridRS"
AVAILABLE_DUPLICATE_SUBFILTERS = (DUPLICATE_SUBFILTER_TOP3_HYBRID_RS,)


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

    def available_card_sections(self) -> tuple[ScanCardConfig, ...]:
        return self.config.card_sections

    def available_annotation_filters(self) -> tuple[AnnotationFilterConfig, ...]:
        return self.config.annotation_filters

    def available_duplicate_subfilters(self) -> tuple[str, ...]:
        return AVAILABLE_DUPLICATE_SUBFILTERS

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
            "annotation_hit_count",
            "duplicate_ticker",
            "hit_scans",
            "annotation_hits",
            "vcs",
            "dist_from_52w_high",
            "dist_from_52w_low",
            "ud_volume_ratio",
            "structure_pivot_long_active",
            "structure_pivot_long_breakout",
            "structure_pivot_long_breakout_first_day",
            "structure_pivot_long_breakout_gap_up",
            "structure_pivot_long_pivot_price",
            "structure_pivot_long_length",
            "earnings",
            "pp_count_window",
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
        annotation_columns = [
            annotation_filter_column_name(section.filter_name)
            for section in self.config.annotation_filters
            if annotation_filter_column_name(section.filter_name) in table.columns
        ]
        available_columns = [column for column in columns if column in table.columns]
        display_columns = list(dict.fromkeys([*available_columns, *annotation_columns]))
        display = table[display_columns].copy()
        numeric_columns = display.select_dtypes(include="number").columns
        display.loc[:, numeric_columns] = display.loc[:, numeric_columns].round(2)
        return display

    def filter_by_annotation_filters(
        self,
        watchlist: pd.DataFrame,
        selected_filter_names: Iterable[str] | None = None,
    ) -> pd.DataFrame:
        if watchlist.empty:
            return watchlist.copy()

        selected_names = self._normalize_selected_annotation_filter_names(selected_filter_names)
        if not selected_names:
            return watchlist.copy()

        filtered = watchlist.copy()
        for filter_name in selected_names:
            column_name = annotation_filter_column_name(filter_name)
            if column_name not in filtered.columns:
                filtered[column_name] = False
            filtered = filtered.loc[filtered[column_name].fillna(False)].copy()
            if filtered.empty:
                break
        return filtered

    def apply_selected_scan_metrics(
        self,
        watchlist: pd.DataFrame,
        hits: pd.DataFrame,
        min_count: int,
        selected_scan_names: Iterable[str] | None = None,
        duplicate_rule: DuplicateRuleConfig | None = None,
    ) -> pd.DataFrame:
        if watchlist.empty:
            return watchlist.copy()

        frame = watchlist.copy()
        scan_hits = self._scan_hits_frame(hits)
        selected_names = self._normalize_selected_scan_names(selected_scan_names)
        if selected_names is not None:
            if not selected_names:
                frame["selected_scan_hit_count"] = 0
                frame["selected_overlap_count"] = 0
                frame["duplicate_ticker"] = False
                frame["overlap_count"] = 0
                return frame
            scan_hits = scan_hits.loc[scan_hits["name"].isin(selected_names)].copy()

        if scan_hits.empty:
            frame["selected_scan_hit_count"] = 0
            frame["selected_overlap_count"] = 0
            frame["duplicate_ticker"] = False
            frame["overlap_count"] = 0
            return frame

        scan_counts = scan_hits.groupby("ticker")["name"].nunique()
        frame["selected_scan_hit_count"] = scan_counts.reindex(frame.index).fillna(0).astype(int)
        frame["selected_overlap_count"] = frame["selected_scan_hit_count"]
        effective_rule = duplicate_rule or DuplicateRuleConfig(min_count=int(min_count))
        frame["duplicate_ticker"] = self._evaluate_duplicate_rule(frame.index, scan_hits, effective_rule)
        frame["overlap_count"] = frame["selected_overlap_count"]
        return frame

    def build_scan_cards(
        self,
        watchlist: pd.DataFrame,
        hits: pd.DataFrame,
        selected_scan_names: Iterable[str] | None = None,
    ) -> list[ScanCardViewModel]:
        if watchlist.empty:
            return []

        cards: list[ScanCardViewModel] = []
        for section in self._iter_card_sections(selected_scan_names):
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

    def build_duplicate_tickers(
        self,
        watchlist: pd.DataFrame,
        hits: pd.DataFrame,
        min_count: int,
        selected_scan_names: Iterable[str] | None = None,
        selected_duplicate_subfilters: Iterable[str] | None = None,
        duplicate_rule: DuplicateRuleConfig | None = None,
    ) -> pd.DataFrame:
        if watchlist.empty or hits.empty:
            return pd.DataFrame(columns=["Ticker", "Scan Hits", "Hybrid-RS", "Overlap", "VCS"])

        frame = self.apply_selected_scan_metrics(
            watchlist,
            hits,
            min_count=min_count,
            selected_scan_names=selected_scan_names,
            duplicate_rule=duplicate_rule,
        )
        frame = frame.loc[frame["duplicate_ticker"].fillna(False)].copy()
        if frame.empty:
            return pd.DataFrame(columns=["Ticker", "Scan Hits", "Hybrid-RS", "Overlap", "VCS"])

        hybrid_column = "hybrid_score" if "hybrid_score" in frame.columns else "H" if "H" in frame.columns else None
        vcs_column = "vcs" if "vcs" in frame.columns else "VCS" if "VCS" in frame.columns else None
        frame = self._apply_selected_duplicate_subfilters(
            frame,
            selected_duplicate_subfilters,
            hybrid_column=hybrid_column,
            vcs_column=vcs_column,
        )
        if frame.empty:
            return pd.DataFrame(columns=["Ticker", "Scan Hits", "Hybrid-RS", "Overlap", "VCS"])

        sort_columns: list[str] = ["selected_scan_hit_count"]
        if hybrid_column:
            sort_columns.append(hybrid_column)
        sort_columns.append("selected_overlap_count")
        if vcs_column:
            sort_columns.append(vcs_column)
        frame = frame.sort_values(sort_columns, ascending=[False] * len(sort_columns))

        display = frame.reset_index(names="Ticker").copy()
        selected_columns = ["Ticker", "selected_scan_hit_count"]
        rename_map = {"selected_scan_hit_count": "Scan Hits", "selected_overlap_count": "Overlap"}
        if hybrid_column:
            selected_columns.append(hybrid_column)
            rename_map[hybrid_column] = "Hybrid-RS"
        selected_columns.append("selected_overlap_count")
        if vcs_column:
            selected_columns.append(vcs_column)
            rename_map[vcs_column] = "VCS"

        display = display[selected_columns].copy().rename(columns=rename_map)
        for column in ["Hybrid-RS", "VCS"]:
            if column in display.columns:
                display[column] = display[column].round(2)
        return display

    def build_preset_export(
        self,
        preset_name: str,
        watchlist: pd.DataFrame,
        hits: pd.DataFrame,
        *,
        export_target: str = "Today's Watchlist",
        selected_scan_names: Iterable[str] | None = None,
        min_count: int = 1,
        selected_annotation_filters: Iterable[str] | None = None,
        selected_duplicate_subfilters: Iterable[str] | None = None,
        duplicate_rule: DuplicateRuleConfig | None = None,
    ) -> pd.DataFrame:
        effective_selected_scan_names = (
            list(selected_scan_names)
            if selected_scan_names is not None
            else [section.scan_name for section in self.available_card_sections()]
        )
        filtered_watchlist = self.filter_by_annotation_filters(
            watchlist,
            selected_annotation_filters,
        )
        projected_watchlist = self.apply_selected_scan_metrics(
            filtered_watchlist,
            hits,
            min_count=min_count,
            selected_scan_names=effective_selected_scan_names,
            duplicate_rule=duplicate_rule,
        )
        duplicate_frame = self.build_duplicate_tickers(
            projected_watchlist,
            hits,
            min_count=min_count,
            selected_scan_names=effective_selected_scan_names,
            selected_duplicate_subfilters=selected_duplicate_subfilters,
            duplicate_rule=duplicate_rule,
        )
        cards = self.build_scan_cards(
            projected_watchlist,
            hits,
            selected_scan_names=effective_selected_scan_names,
        )

        row: dict[str, str] = {
            "Output Target": str(export_target).strip(),
            "Preset Name": str(preset_name).strip(),
            "Duplicate Tickers": self._join_tickers(duplicate_frame),
        }
        for card in cards:
            row[f"{card.display_name} Hit Tickers"] = self._join_tickers(card.rows)
        return pd.DataFrame([row])

    def build_preset_summary_exports(
        self,
        presets: Iterable[WatchlistPresetConfig],
        watchlist: pd.DataFrame,
        hits: pd.DataFrame,
        *,
        trade_date: str,
        output_date: str,
        export_target: str = "Today's Watchlist",
        top_ticker_limit: int = 5,
    ) -> pd.DataFrame:
        rows: list[dict[str, object]] = []
        limit = max(int(top_ticker_limit), 1)
        for preset in presets:
            duplicate_frame, _ = self._build_preset_frames(preset, watchlist, hits)
            top_tickers = duplicate_frame["Ticker"].head(limit).tolist() if "Ticker" in duplicate_frame.columns else []
            rows.append(
                {
                    "Output Target": str(export_target).strip(),
                    "trade_date": str(trade_date).strip(),
                    "output_date": str(output_date).strip(),
                    "preset_name": preset.preset_name,
                    "has_candidates": bool(not duplicate_frame.empty),
                    "candidate_count": int(len(duplicate_frame)),
                    "top_tickers": ", ".join(str(ticker).strip() for ticker in top_tickers if str(ticker).strip()),
                    "selected_scan_names": ", ".join(preset.selected_scan_names),
                    "selected_annotation_filters": ", ".join(preset.selected_annotation_filters),
                    "duplicate_threshold": int(preset.duplicate_threshold),
                    "duplicate_rule_mode": preset.duplicate_rule.mode,
                }
            )
        return pd.DataFrame(rows)

    def build_preset_detail_exports(
        self,
        presets: Iterable[WatchlistPresetConfig],
        watchlist: pd.DataFrame,
        hits: pd.DataFrame,
        *,
        export_target: str = "Today's Watchlist",
    ) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for preset in presets:
            frames.append(
                self.build_preset_export(
                    preset.preset_name,
                    watchlist,
                    hits,
                    export_target=export_target,
                    selected_scan_names=preset.selected_scan_names,
                    min_count=preset.duplicate_threshold,
                    selected_annotation_filters=preset.selected_annotation_filters,
                    selected_duplicate_subfilters=preset.selected_duplicate_subfilters,
                    duplicate_rule=preset.duplicate_rule,
                )
            )
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True).fillna("")

    def _build_preset_frames(
        self,
        preset: WatchlistPresetConfig,
        watchlist: pd.DataFrame,
        hits: pd.DataFrame,
    ) -> tuple[pd.DataFrame, list[ScanCardViewModel]]:
        filtered_watchlist = self.filter_by_annotation_filters(
            watchlist,
            preset.selected_annotation_filters,
        )
        projected_watchlist = self.apply_selected_scan_metrics(
            filtered_watchlist,
            hits,
            min_count=preset.duplicate_threshold,
            selected_scan_names=preset.selected_scan_names,
            duplicate_rule=preset.duplicate_rule,
        )
        duplicate_frame = self.build_duplicate_tickers(
            projected_watchlist,
            hits,
            min_count=preset.duplicate_threshold,
            selected_scan_names=preset.selected_scan_names,
            selected_duplicate_subfilters=preset.selected_duplicate_subfilters,
            duplicate_rule=preset.duplicate_rule,
        )
        cards = self.build_scan_cards(
            projected_watchlist,
            hits,
            selected_scan_names=preset.selected_scan_names,
        )
        return duplicate_frame, cards

    def _empty_card_rows(self) -> pd.DataFrame:
        return pd.DataFrame(columns=["Ticker", "Name", "Hybrid-RS", "Overlap", "VCS", "Duplicate", "Earnings"])

    def _build_single_card(self, section: ScanCardConfig, watchlist: pd.DataFrame, hits: pd.DataFrame) -> ScanCardViewModel | None:
        scan_hits = self._scan_hits_frame(hits)
        section_hits = scan_hits.loc[scan_hits["name"] == section.scan_name, "ticker"].drop_duplicates().tolist()
        frame = watchlist.loc[watchlist.index.intersection(section_hits)].copy() if section_hits else watchlist.iloc[0:0].copy()
        sort_columns = [column for column in section.sort_columns if column in frame.columns]
        if sort_columns and not frame.empty:
            frame = frame.sort_values(sort_columns, ascending=[False] * len(sort_columns))
        return ScanCardViewModel(
            scan_name=section.scan_name,
            display_name=section.display_name or section.scan_name,
            ticker_count=len(frame),
            rows=self._build_card_rows(frame),
        )

    def _build_card_rows(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return self._empty_card_rows()

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

    def _iter_card_sections(self, selected_scan_names: Iterable[str] | None) -> tuple[ScanCardConfig, ...]:
        selected_names = self._normalize_selected_scan_names(selected_scan_names)
        if selected_names is None:
            return self.config.card_sections
        selected_name_set = set(selected_names)
        return tuple(section for section in self.config.card_sections if section.scan_name in selected_name_set)

    def _normalize_selected_scan_names(self, selected_scan_names: Iterable[str] | None) -> tuple[str, ...] | None:
        if selected_scan_names is None:
            return None
        valid_names = {section.scan_name for section in self.config.card_sections}
        names = tuple(
            dict.fromkeys(
                str(name).strip()
                for name in selected_scan_names
                if str(name).strip() and str(name).strip() in valid_names
            )
        )
        return names

    def _normalize_selected_annotation_filter_names(
        self,
        selected_filter_names: Iterable[str] | None,
    ) -> tuple[str, ...]:
        if selected_filter_names is None:
            return tuple()
        valid_names = {section.filter_name for section in self.config.annotation_filters}
        return tuple(
            dict.fromkeys(
                str(name).strip()
                for name in selected_filter_names
                if str(name).strip() and str(name).strip() in valid_names
            )
        )

    def _normalize_selected_duplicate_subfilter_names(
        self,
        selected_subfilter_names: Iterable[str] | None,
    ) -> tuple[str, ...]:
        if selected_subfilter_names is None:
            return tuple()
        valid_names = set(self.available_duplicate_subfilters())
        return tuple(
            dict.fromkeys(
                str(name).strip()
                for name in selected_subfilter_names
                if str(name).strip() and str(name).strip() in valid_names
            )
        )

    def _evaluate_duplicate_rule(
        self,
        tickers: pd.Index,
        scan_hits: pd.DataFrame,
        rule: DuplicateRuleConfig,
    ) -> pd.Series:
        if scan_hits.empty:
            return pd.Series(False, index=tickers, dtype=bool)
        if rule.mode == "required_plus_optional_min":
            required_hits = scan_hits.loc[scan_hits["name"].isin(rule.required_scans)].groupby("ticker")["name"].nunique()
            optional_hits = scan_hits.loc[scan_hits["name"].isin(rule.optional_scans)].groupby("ticker")["name"].nunique()
            required_ok = required_hits.reindex(tickers).fillna(0).astype(int) >= len(rule.required_scans)
            optional_ok = optional_hits.reindex(tickers).fillna(0).astype(int) >= int(rule.optional_min_hits)
            return required_ok & optional_ok
        counts = scan_hits.groupby("ticker")["name"].nunique().reindex(tickers).fillna(0).astype(int)
        return counts >= int(rule.min_count)

    def _apply_selected_duplicate_subfilters(
        self,
        frame: pd.DataFrame,
        selected_subfilter_names: Iterable[str] | None,
        *,
        hybrid_column: str | None,
        vcs_column: str | None,
    ) -> pd.DataFrame:
        selected_names = self._normalize_selected_duplicate_subfilter_names(selected_subfilter_names)
        if not selected_names or hybrid_column is None:
            return frame

        filtered = frame.copy()
        if DUPLICATE_SUBFILTER_TOP3_HYBRID_RS in selected_names:
            sort_columns = [hybrid_column]
            ascending = [False]
            for column in ("selected_scan_hit_count", "selected_overlap_count"):
                if column in filtered.columns:
                    sort_columns.append(column)
                    ascending.append(False)
            if vcs_column and vcs_column in filtered.columns:
                sort_columns.append(vcs_column)
                ascending.append(False)
            filtered = filtered.sort_values(sort_columns, ascending=ascending).head(3).copy()
        return filtered

    def _scan_hits_frame(self, hits: pd.DataFrame) -> pd.DataFrame:
        if hits.empty:
            return hits.copy()
        if "kind" not in hits.columns:
            return hits.copy()
        return hits.loc[hits["kind"] == "scan"].copy()

    def _join_tickers(self, frame: pd.DataFrame) -> str:
        if frame.empty:
            return ""
        ticker_column = "Ticker" if "Ticker" in frame.columns else "TICKER" if "TICKER" in frame.columns else None
        if ticker_column is None:
            return ""
        values = [
            str(value).strip().upper()
            for value in frame[ticker_column].tolist()
            if str(value).strip()
        ]
        return ", ".join(values)


class WatchlistCardGridBuilder(WatchlistViewModelBuilder):
    """Docs-facing alias for the scan card grid builder."""

    pass

