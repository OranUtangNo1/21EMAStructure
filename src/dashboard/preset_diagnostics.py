from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.dashboard.watchlist import WatchlistViewModelBuilder
from src.scan.rules import ScanConfig, WatchlistPresetConfig, annotation_filter_column_name
from src.watchlist_presets import ResolvedWatchlistPreset


@dataclass(frozen=True, slots=True)
class PresetDiagnosticsArtifact:
    manifest: dict[str, object]
    scan_counts: pd.DataFrame
    annotation_counts: pd.DataFrame
    preset_steps: pd.DataFrame
    preset_ticker_steps: pd.DataFrame
    preset_hits: pd.DataFrame


SCAN_COUNTS_COLUMNS = [
    "trade_date",
    "scan_name",
    "hit_row_count",
    "ticker_count",
]
ANNOTATION_COUNTS_COLUMNS = [
    "trade_date",
    "filter_name",
    "pass_count",
    "watchlist_count",
]
PRESET_STEPS_COLUMNS = [
    "trade_date",
    "preset_name",
    "preset_source",
    "step_order",
    "step_type",
    "step_name",
    "required_min",
    "scan_names",
    "filter_names",
    "input_ticker_count",
    "pass_ticker_count",
    "output_ticker_count",
]
PRESET_TICKER_STEPS_COLUMNS = [
    "trade_date",
    "preset_name",
    "preset_source",
    "ticker",
    "step_order",
    "step_type",
    "step_name",
    "input_eligible",
    "step_pass",
    "cumulative_pass",
    "hit_count",
    "hit_names",
]
PRESET_HITS_COLUMNS = [
    "trade_date",
    "preset_name",
    "preset_source",
    "ticker",
    "selected_scan_hit_count",
    "selected_scan_names",
]


def build_preset_diagnostics(
    *,
    config_path: str | Path,
    scan_config: ScanConfig,
    watchlist: pd.DataFrame,
    scan_hits: pd.DataFrame,
    presets: Iterable[ResolvedWatchlistPreset],
    trade_date: pd.Timestamp | str | None,
    generated_at: datetime | None = None,
) -> PresetDiagnosticsArtifact:
    resolved_trade_date = _format_trade_date(trade_date)
    generated_at_text = (generated_at or datetime.now()).isoformat(timespec="seconds")
    normalized_hits = _scan_hits_frame(scan_hits)
    normalized_watchlist = _watchlist_frame(watchlist)
    resolved_presets = tuple(presets)
    builder = WatchlistViewModelBuilder(scan_config)

    scan_counts = _build_scan_counts(resolved_trade_date, scan_config, normalized_hits)
    annotation_counts = _build_annotation_counts(resolved_trade_date, scan_config, normalized_watchlist)
    preset_steps, preset_ticker_steps, preset_hits = _build_preset_frames(
        resolved_trade_date,
        normalized_watchlist,
        normalized_hits,
        resolved_presets,
        builder,
    )
    manifest = {
        "schema_version": "preset_diagnostics.v1",
        "generated_at": generated_at_text,
        "trade_date": resolved_trade_date,
        "config_path": str(Path(config_path).expanduser().resolve(strict=False)),
        "watchlist_count": int(len(normalized_watchlist)),
        "scan_hit_count": int(len(normalized_hits)),
        "scan_count_rows": int(len(scan_counts)),
        "annotation_count_rows": int(len(annotation_counts)),
        "preset_count": int(len(resolved_presets)),
        "preset_step_rows": int(len(preset_steps)),
        "preset_ticker_step_rows": int(len(preset_ticker_steps)),
        "preset_hit_rows": int(len(preset_hits)),
        "files": {
            "scan_counts": "latest_scan_counts.csv",
            "annotation_counts": "latest_annotation_counts.csv",
            "preset_steps": "latest_preset_steps.csv",
            "preset_ticker_steps": "latest_preset_ticker_steps.csv",
            "preset_hits": "latest_preset_hits.csv",
        },
    }
    return PresetDiagnosticsArtifact(
        manifest=manifest,
        scan_counts=scan_counts,
        annotation_counts=annotation_counts,
        preset_steps=preset_steps,
        preset_ticker_steps=preset_ticker_steps,
        preset_hits=preset_hits,
    )


def _build_scan_counts(trade_date: str, scan_config: ScanConfig, scan_hits: pd.DataFrame) -> pd.DataFrame:
    configured_names = list(dict.fromkeys([*scan_config.enabled_scan_rules, *(scan_hits["name"].tolist() if "name" in scan_hits.columns else [])]))
    rows = []
    for scan_name in configured_names:
        frame = scan_hits.loc[scan_hits["name"] == scan_name] if not scan_hits.empty else scan_hits
        rows.append(
            {
                "trade_date": trade_date,
                "scan_name": scan_name,
                "hit_row_count": int(len(frame)),
                "ticker_count": int(frame["ticker"].nunique()) if "ticker" in frame.columns else 0,
            }
        )
    return pd.DataFrame(rows, columns=SCAN_COUNTS_COLUMNS)


def _build_annotation_counts(trade_date: str, scan_config: ScanConfig, watchlist: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for section in scan_config.annotation_filters:
        column_name = annotation_filter_column_name(section.filter_name)
        pass_count = int(watchlist[column_name].fillna(False).astype(bool).sum()) if column_name in watchlist.columns else 0
        rows.append(
            {
                "trade_date": trade_date,
                "filter_name": section.filter_name,
                "pass_count": pass_count,
                "watchlist_count": int(len(watchlist)),
            }
        )
    return pd.DataFrame(rows, columns=ANNOTATION_COUNTS_COLUMNS)


def _build_preset_frames(
    trade_date: str,
    watchlist: pd.DataFrame,
    scan_hits: pd.DataFrame,
    presets: tuple[ResolvedWatchlistPreset, ...],
    builder: WatchlistViewModelBuilder,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    step_rows: list[dict[str, object]] = []
    ticker_step_rows: list[dict[str, object]] = []
    hit_rows: list[dict[str, object]] = []

    for resolved in presets:
        preset = resolved.config
        current_index = pd.Index(watchlist.index.astype(str), name=watchlist.index.name)
        cumulative = pd.Series(True, index=watchlist.index.astype(str), dtype=bool)
        selected_hits_by_ticker = _hits_by_ticker(scan_hits, preset.selected_scan_names)

        for step_order, spec in enumerate(_preset_step_specs(preset), start=1):
            input_index = current_index
            step_pass, hit_counts, hit_names = _evaluate_step(watchlist, scan_hits, input_index, spec)
            output_index = input_index.intersection(step_pass[step_pass].index)
            cumulative = cumulative & cumulative.index.to_series().isin(output_index)
            step_rows.append(
                {
                    "trade_date": trade_date,
                    "preset_name": preset.preset_name,
                    "preset_source": resolved.source,
                    "step_order": step_order,
                    "step_type": spec["step_type"],
                    "step_name": spec["step_name"],
                    "required_min": int(spec["required_min"]),
                    "scan_names": _join_names(spec["scan_names"]),
                    "filter_names": _join_names(spec["filter_names"]),
                    "input_ticker_count": int(len(input_index)),
                    "pass_ticker_count": int(step_pass.sum()),
                    "output_ticker_count": int(len(output_index)),
                }
            )
            input_set = set(input_index)
            for ticker in watchlist.index.astype(str):
                ticker_step_rows.append(
                    {
                        "trade_date": trade_date,
                        "preset_name": preset.preset_name,
                        "preset_source": resolved.source,
                        "ticker": ticker,
                        "step_order": step_order,
                        "step_type": spec["step_type"],
                        "step_name": spec["step_name"],
                        "input_eligible": bool(ticker in input_set),
                        "step_pass": bool(step_pass.get(ticker, False)),
                        "cumulative_pass": bool(cumulative.get(ticker, False)),
                        "hit_count": int(hit_counts.get(ticker, 0)),
                        "hit_names": str(hit_names.get(ticker, "")),
                    }
                )
            current_index = output_index

        if not _preset_step_specs(preset):
            projected = builder.apply_selected_scan_metrics(
                watchlist,
                scan_hits,
                min_count=preset.duplicate_threshold,
                selected_scan_names=preset.selected_scan_names,
                duplicate_rule=preset.duplicate_rule,
            )
            current_index = projected.loc[projected["duplicate_ticker"].fillna(False)].index.astype(str)

        for ticker in current_index:
            selected_names = selected_hits_by_ticker.get(str(ticker), [])
            hit_rows.append(
                {
                    "trade_date": trade_date,
                    "preset_name": preset.preset_name,
                    "preset_source": resolved.source,
                    "ticker": str(ticker),
                    "selected_scan_hit_count": int(len(selected_names)),
                    "selected_scan_names": _join_names(selected_names),
                }
            )

    return (
        pd.DataFrame(step_rows, columns=PRESET_STEPS_COLUMNS),
        pd.DataFrame(ticker_step_rows, columns=PRESET_TICKER_STEPS_COLUMNS),
        pd.DataFrame(hit_rows, columns=PRESET_HITS_COLUMNS),
    )


def _preset_step_specs(preset: WatchlistPresetConfig) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    for filter_name in preset.selected_annotation_filters:
        specs.append(
            {
                "step_type": "annotation_filter",
                "step_name": filter_name,
                "required_min": 1,
                "scan_names": tuple(),
                "filter_names": (filter_name,),
            }
        )

    rule = preset.duplicate_rule
    if rule.mode == "grouped_threshold":
        if rule.required_scans:
            specs.append(
                {
                    "step_type": "required_scans_all",
                    "step_name": "required_scans",
                    "required_min": len(rule.required_scans),
                    "scan_names": rule.required_scans,
                    "filter_names": tuple(),
                }
            )
        for group in rule.optional_groups:
            specs.append(
                {
                    "step_type": "scan_group_min",
                    "step_name": group.group_name,
                    "required_min": int(group.min_hits),
                    "scan_names": group.scans,
                    "filter_names": tuple(),
                }
            )
        return specs

    if rule.mode == "required_plus_optional_min":
        specs.append(
            {
                "step_type": "required_scans_all",
                "step_name": "required_scans",
                "required_min": len(rule.required_scans),
                "scan_names": rule.required_scans,
                "filter_names": tuple(),
            }
        )
        specs.append(
            {
                "step_type": "optional_scans_min",
                "step_name": "optional_scans",
                "required_min": int(rule.optional_min_hits),
                "scan_names": rule.optional_scans,
                "filter_names": tuple(),
            }
        )
        return specs

    specs.append(
        {
            "step_type": "selected_scans_min",
            "step_name": "selected_scans",
            "required_min": int(rule.min_count),
            "scan_names": preset.selected_scan_names,
            "filter_names": tuple(),
        }
    )
    return specs


def _evaluate_step(
    watchlist: pd.DataFrame,
    scan_hits: pd.DataFrame,
    input_index: pd.Index,
    spec: dict[str, object],
) -> tuple[pd.Series, pd.Series, pd.Series]:
    input_index = pd.Index(input_index.astype(str))
    scan_names = tuple(str(name) for name in spec["scan_names"])
    filter_names = tuple(str(name) for name in spec["filter_names"])
    required_min = int(spec["required_min"])

    if filter_names:
        filter_name = filter_names[0]
        column_name = annotation_filter_column_name(filter_name)
        raw = watchlist[column_name].fillna(False).astype(bool) if column_name in watchlist.columns else pd.Series(False, index=watchlist.index)
        raw.index = raw.index.astype(str)
        step_pass = raw.reindex(input_index).fillna(False).astype(bool)
        hit_counts = step_pass.astype(int)
        hit_names = step_pass.map(lambda passed: filter_name if passed else "")
        return step_pass, hit_counts, hit_names

    frame = scan_hits.loc[scan_hits["ticker"].isin(input_index) & scan_hits["name"].isin(scan_names)].copy() if not scan_hits.empty else scan_hits
    if frame.empty:
        step_pass = pd.Series(False, index=input_index, dtype=bool)
        hit_counts = pd.Series(0, index=input_index, dtype=int)
        hit_names = pd.Series("", index=input_index, dtype=object)
        return step_pass, hit_counts, hit_names

    counts = frame.groupby("ticker")["name"].nunique().reindex(input_index).fillna(0).astype(int)
    names = frame.groupby("ticker")["name"].agg(lambda values: _join_names(sorted(set(str(value) for value in values)))).reindex(input_index).fillna("")
    return counts >= required_min, counts, names


def _scan_hits_frame(scan_hits: pd.DataFrame) -> pd.DataFrame:
    columns = ["ticker", "name", "kind"]
    if scan_hits is None or scan_hits.empty:
        return pd.DataFrame(columns=columns)
    frame = scan_hits.copy()
    if "scan_name" in frame.columns and "name" not in frame.columns:
        frame = frame.rename(columns={"scan_name": "name"})
    if "kind" in frame.columns:
        frame = frame.loc[frame["kind"].astype(str).str.lower() == "scan"].copy()
    else:
        frame["kind"] = "scan"
    for column in columns:
        if column not in frame.columns:
            frame[column] = ""
    frame["ticker"] = frame["ticker"].astype(str).str.strip().str.upper()
    frame["name"] = frame["name"].astype(str).str.strip()
    frame["kind"] = frame["kind"].astype(str).str.strip()
    return frame.loc[(frame["ticker"] != "") & (frame["name"] != ""), columns].copy()


def _watchlist_frame(watchlist: pd.DataFrame) -> pd.DataFrame:
    if watchlist is None or watchlist.empty:
        return pd.DataFrame()
    frame = watchlist.copy()
    frame.index = frame.index.astype(str).str.upper()
    return frame


def _hits_by_ticker(scan_hits: pd.DataFrame, scan_names: Iterable[str]) -> dict[str, list[str]]:
    names = tuple(str(name) for name in scan_names)
    frame = scan_hits.loc[scan_hits["name"].isin(names)].copy() if not scan_hits.empty else scan_hits
    if frame.empty:
        return {}
    return {
        str(ticker): sorted(set(str(name) for name in group["name"].tolist()))
        for ticker, group in frame.groupby("ticker")
    }


def _format_trade_date(trade_date: pd.Timestamp | str | None) -> str:
    if trade_date is None:
        return ""
    parsed = pd.to_datetime(trade_date, errors="coerce")
    if pd.isna(parsed):
        return str(trade_date)
    return pd.Timestamp(parsed).strftime("%Y-%m-%d")


def _join_names(values: Iterable[object]) -> str:
    return "|".join(str(value).strip() for value in values if str(value).strip())
