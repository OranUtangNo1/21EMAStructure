from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.configuration import load_settings
from src.dashboard.preset_diagnostics import build_preset_diagnostics
from src.dashboard.watchlist import WatchlistViewModelBuilder
from src.scan.runner import ScanRunResult, ScanRunner
from src.scan.rules import (
    ScanConfig,
    ScanCardConfig,
    enrich_with_scan_context,
    evaluate_scan_issues,
    mature_late_stage_risk,
    stage2_quality_score,
)
from src.services.indicator_service import IndicatorService
from src.services.module_output_store import ModuleOutputRecord, ModuleOutputStore
from src.services.scan_scoring_service import ScanScoringService
from src.watchlist_presets import ResolvedWatchlistPreset


SCAN_OUTPUT_MODULE = "scan"
PRESET_OUTPUT_MODULE = "preset"
SCAN_DIAGNOSTICS_OUTPUT_MODULE = "scan_diagnostics"


@dataclass(frozen=True, slots=True)
class ScanServiceResult:
    scan: pd.DataFrame
    preset: pd.DataFrame
    diagnostics: pd.DataFrame
    missing: dict[str, str] = field(default_factory=dict)
    output_records: list[ModuleOutputRecord] = field(default_factory=list)
    document_paths: list[Path] = field(default_factory=list)
    preset_diagnostic_paths: list[Path] = field(default_factory=list)
    scan_run_result: ScanRunResult | None = None


@dataclass(slots=True)
class ScanService:
    """Date-addressable scan/preset service over indicator snapshots."""

    indicator_service: IndicatorService | None
    scan_config: ScanConfig
    scan_runner: object
    preset_builder: WatchlistViewModelBuilder
    scoring_service: ScanScoringService | None = None
    output_store: ModuleOutputStore | None = None
    config_path: str | Path = "config/default.yaml"

    @classmethod
    def from_config(
        cls,
        config_path: str | Path | None = None,
        *,
        indicator_service: IndicatorService | None = None,
        output_store: ModuleOutputStore | None = None,
    ) -> "ScanService":
        settings = load_settings(config_path)
        scan_config = ScanConfig.from_dict(settings.get("scan", {}))
        resolved_indicator_service = indicator_service or IndicatorService.from_config(config_path)
        return cls(
            indicator_service=resolved_indicator_service,
            scan_config=scan_config,
            scan_runner=ScanRunner(scan_config),
            preset_builder=WatchlistViewModelBuilder(scan_config),
            scoring_service=ScanScoringService.from_config(config_path),
            output_store=output_store,
            config_path=config_path or Path(__file__).resolve().parents[2] / "config" / "default.yaml",
        )

    def run(
        self,
        symbols: list[str] | tuple[str, ...],
        *,
        start_date: str | pd.Timestamp | None = None,
        end_date: str | pd.Timestamp | None = None,
        as_of_date: str | pd.Timestamp | None = None,
        scan_names: Iterable[str] | None = None,
        preset_names: Iterable[str] | None = None,
        refresh_missing: bool = False,
        force_refresh: bool = False,
        write_outputs: bool = False,
        progress_callback: object | None = None,
    ) -> ScanServiceResult:
        if self.indicator_service is None:
            raise ValueError("ScanService.run requires indicator_service")
        self._progress(progress_callback, f"Scan: preparing indicators for {len(symbols)} symbols")
        indicator_result = self.indicator_service.build(
            symbols,
            start_date=start_date,
            end_date=end_date,
            as_of_date=as_of_date,
            refresh_missing=refresh_missing,
            force_refresh=force_refresh,
            write_outputs=False,
            progress_callback=progress_callback,
        )
        indicator_frame = indicator_result.frame
        missing = dict(indicator_result.missing)
        benchmark_history = pd.DataFrame()
        universe_snapshot = pd.DataFrame()
        if self.scoring_service is not None:
            benchmark_symbol = self.scoring_service.benchmark_symbol
            benchmark_history = indicator_result.histories.get(benchmark_symbol, pd.DataFrame())
            if benchmark_history.empty:
                benchmark_result = self.indicator_service.build(
                    [benchmark_symbol],
                    end_date=end_date,
                    as_of_date=as_of_date,
                    refresh_missing=refresh_missing,
                    force_refresh=force_refresh,
                    write_outputs=False,
                    progress_callback=progress_callback,
                )
                benchmark_history = benchmark_result.histories.get(benchmark_symbol, pd.DataFrame())
                missing.update(benchmark_result.missing)
            universe_snapshot = self.scoring_service.load_universe_snapshot(as_of_date or end_date)
        if start_date is None:
            indicator_frame, stale = self._latest_date_only(indicator_frame)
            missing.update(stale)
            if stale:
                scan_date = indicator_frame["date_key"].max() if not indicator_frame.empty else "unavailable"
                self._progress(
                    progress_callback,
                    f"Scan: excluded {len(stale)} stale symbol(s); scan date={scan_date}",
                )
        self._progress(progress_callback, f"Scan: indicator frame rows={len(indicator_frame)}")
        return self.run_from_frame(
            indicator_frame,
            histories=indicator_result.histories,
            benchmark_history=benchmark_history,
            universe_snapshot=universe_snapshot,
            scan_names=scan_names,
            preset_names=preset_names,
            missing=missing,
            write_outputs=write_outputs,
            progress_callback=progress_callback,
        )

    def _latest_date_only(self, indicator_frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
        frame = self._normalize_indicator_frame(indicator_frame)
        if frame.empty:
            return frame, {}
        latest_date_key = str(frame["date_key"].max())
        ticker_latest_dates = frame.groupby("ticker", sort=True)["date_key"].max()
        stale_dates = ticker_latest_dates.loc[ticker_latest_dates < latest_date_key]
        stale = {
            str(ticker): f"stale latest data date {date_key}; excluded from scan date {latest_date_key}"
            for ticker, date_key in stale_dates.items()
        }
        return frame.loc[frame["date_key"] == latest_date_key].reset_index(drop=True), stale

    def run_from_frame(
        self,
        indicator_frame: pd.DataFrame,
        *,
        histories: dict[str, pd.DataFrame] | None = None,
        benchmark_history: pd.DataFrame | None = None,
        universe_snapshot: pd.DataFrame | None = None,
        scan_names: Iterable[str] | None = None,
        preset_names: Iterable[str] | None = None,
        missing: dict[str, str] | None = None,
        write_outputs: bool = False,
        progress_callback: object | None = None,
    ) -> ScanServiceResult:
        frame = self._normalize_indicator_frame(indicator_frame)
        runtime_config = self._runtime_scan_config(scan_names)
        runner = self.scan_runner if runtime_config is self.scan_config else ScanRunner(runtime_config)
        preset_builder = (
            self.preset_builder
            if runtime_config is self.scan_config
            else WatchlistViewModelBuilder(runtime_config)
        )

        scan_frames: list[pd.DataFrame] = []
        preset_frames: list[pd.DataFrame] = []
        diagnostic_frames: list[pd.DataFrame] = []
        preset_diagnostic_paths: list[Path] = []
        date_groups = list(frame.groupby("date_key", sort=True))
        self._progress(progress_callback, f"Scan: evaluating {len(date_groups)} date group(s)")
        for index, (date_key, group) in enumerate(date_groups, start=1):
            if index == 1 or index == len(date_groups) or index % 5 == 0:
                self._progress(progress_callback, f"Scan: evaluating date {index}/{len(date_groups)} ({date_key})")
            snapshot = self._snapshot_for_date(group)
            if self.scoring_service is not None and histories is not None:
                parsed_as_of = pd.to_datetime(str(date_key), format="%Y%m%d", errors="coerce")
                as_of_date = None if pd.isna(parsed_as_of) else pd.Timestamp(parsed_as_of)
                dated_histories = self._slice_histories(histories, as_of_date)
                dated_benchmark = self._slice_history(benchmark_history, as_of_date)
                self._progress(progress_callback, f"Scan: scoring snapshot rows={len(snapshot)}")
                snapshot = self.scoring_service.score(
                    snapshot,
                    dated_histories,
                    dated_benchmark,
                    universe_snapshot=universe_snapshot,
                )
            result = runner.run(snapshot)
            scan_frames.append(self._scan_output(str(date_key), result))
            preset_frames.append(
                self._preset_output(
                    str(date_key),
                    result,
                    runtime_config=runtime_config,
                    preset_builder=preset_builder,
                    preset_names=preset_names,
                )
            )
            diagnostic_frames.append(
                self._diagnostic_output(str(date_key), snapshot, result, runtime_config)
            )
            if write_outputs:
                preset_diagnostic_paths.extend(
                    self._write_preset_diagnostics(
                        str(date_key),
                        result,
                        runtime_config=runtime_config,
                        preset_names=preset_names,
                    )
                )

        scan = self._concat(scan_frames, self._scan_columns())
        preset = self._concat(preset_frames, self._preset_columns())
        diagnostics = self._concat(diagnostic_frames, self._diagnostic_columns())
        self._progress(progress_callback, f"Scan: completed scan_rows={len(scan)}, preset_rows={len(preset)}")
        output_records = self._write_outputs(scan, preset, diagnostics) if write_outputs else []
        document_paths = self._write_preset_documents(preset) if write_outputs else []
        return ScanServiceResult(
            scan=scan,
            preset=preset,
            diagnostics=diagnostics,
            missing=missing or {},
            output_records=output_records,
            document_paths=document_paths,
            preset_diagnostic_paths=preset_diagnostic_paths,
        )

    def run_from_snapshot(
        self,
        snapshot: pd.DataFrame,
        *,
        date_key: str | pd.Timestamp | None = None,
        scan_names: Iterable[str] | None = None,
        preset_names: Iterable[str] | None = None,
        missing: dict[str, str] | None = None,
        write_outputs: bool = False,
    ) -> ScanServiceResult:
        normalized_snapshot = self._normalize_snapshot(snapshot)
        runtime_config = self._runtime_scan_config(scan_names)
        runner = self.scan_runner if runtime_config is self.scan_config else ScanRunner(runtime_config)
        preset_builder = (
            self.preset_builder
            if runtime_config is self.scan_config
            else WatchlistViewModelBuilder(runtime_config)
        )
        effective_date_key = self._date_key_for_snapshot(normalized_snapshot, date_key)
        result = runner.run(normalized_snapshot)
        scan = self._scan_output(effective_date_key, result)
        preset = self._preset_output(
            effective_date_key,
            result,
            runtime_config=runtime_config,
            preset_builder=preset_builder,
            preset_names=preset_names,
        )
        diagnostics = self._diagnostic_output(effective_date_key, normalized_snapshot, result, runtime_config)
        output_records = self._write_outputs(scan, preset, diagnostics) if write_outputs else []
        document_paths = self._write_preset_documents(preset) if write_outputs else []
        preset_diagnostic_paths = (
            self._write_preset_diagnostics(
                effective_date_key,
                result,
                runtime_config=runtime_config,
                preset_names=preset_names,
            )
            if write_outputs
            else []
        )
        return ScanServiceResult(
            scan=scan,
            preset=preset,
            diagnostics=diagnostics,
            missing=missing or {},
            output_records=output_records,
            document_paths=document_paths,
            preset_diagnostic_paths=preset_diagnostic_paths,
            scan_run_result=result,
        )

    def _normalize_indicator_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame(columns=["date_key", "ticker"])
        result = frame.copy()
        if "ticker" not in result.columns:
            raise ValueError("indicator_frame requires ticker column")
        if "date_key" not in result.columns:
            if "trade_date" not in result.columns:
                raise ValueError("indicator_frame requires date_key or trade_date column")
            result["date_key"] = pd.to_datetime(result["trade_date"], errors="coerce").dt.strftime("%Y%m%d")
        result["ticker"] = result["ticker"].astype(str).str.strip().str.upper()
        result["date_key"] = result["date_key"].astype(str).str.strip()
        result = result.loc[(result["ticker"] != "") & result["date_key"].str.fullmatch(r"\d{8}", na=False)].copy()
        return result.sort_values(["date_key", "ticker"]).reset_index(drop=True)

    def _runtime_scan_config(self, scan_names: Iterable[str] | None) -> ScanConfig:
        selected = self._normalize_selected_names(scan_names)
        if selected is None:
            return self.scan_config
        selected_set = set(selected)
        enabled_scan_rules = tuple(name for name in self.scan_config.enabled_scan_rules if name in selected_set)
        card_sections = tuple(section for section in self.scan_config.card_sections if section.scan_name in selected_set)
        if not enabled_scan_rules:
            return replace(self.scan_config, enabled_scan_rules=tuple(), card_sections=tuple())
        card_names = {section.scan_name for section in card_sections}
        missing_cards = tuple(name for name in enabled_scan_rules if name not in card_names)
        card_sections = (
            *card_sections,
            *(ScanCardConfig(scan_name=name, display_name=name) for name in missing_cards),
        )
        return replace(self.scan_config, enabled_scan_rules=enabled_scan_rules, card_sections=card_sections)

    def _snapshot_for_date(self, frame: pd.DataFrame) -> pd.DataFrame:
        snapshot = frame.drop_duplicates(subset=["ticker"], keep="last").copy()
        snapshot.index = snapshot["ticker"]
        snapshot.index.name = None
        return snapshot

    def _slice_histories(
        self,
        histories: dict[str, pd.DataFrame],
        as_of_date: pd.Timestamp | None,
    ) -> dict[str, pd.DataFrame]:
        return {
            str(symbol): self._slice_history(history, as_of_date)
            for symbol, history in histories.items()
            if history is not None and not history.empty
        }

    def _slice_history(
        self,
        history: pd.DataFrame | None,
        as_of_date: pd.Timestamp | None,
    ) -> pd.DataFrame:
        if history is None or history.empty:
            return pd.DataFrame()
        frame = history.copy()
        frame.index = pd.to_datetime(frame.index, errors="coerce")
        frame = frame.loc[frame.index.notna()].sort_index()
        if pd.notna(as_of_date):
            frame = frame.loc[frame.index <= pd.Timestamp(as_of_date)]
        return frame

    def _normalize_snapshot(self, snapshot: pd.DataFrame) -> pd.DataFrame:
        if snapshot is None:
            return pd.DataFrame()
        result = snapshot.copy()
        if "ticker" in result.columns:
            result["ticker"] = result["ticker"].astype(str).str.strip().str.upper()
            result = result.loc[result["ticker"] != ""].copy()
            result.index = result["ticker"]
            result.index.name = None
        else:
            result.index = result.index.astype(str).str.strip().str.upper()
        return result

    def _date_key_for_snapshot(self, snapshot: pd.DataFrame, date_key: str | pd.Timestamp | None) -> str:
        if date_key is not None:
            normalized = pd.to_datetime(date_key, errors="coerce")
            if pd.notna(normalized):
                return normalized.strftime("%Y%m%d")
            raw = str(date_key).strip()
            if raw:
                return raw.replace("-", "")
        if "trade_date" in snapshot.columns:
            parsed = pd.to_datetime(snapshot["trade_date"], errors="coerce").dropna()
            if not parsed.empty:
                return parsed.max().strftime("%Y%m%d")
        return pd.Timestamp.today().strftime("%Y%m%d")

    def _scan_output(self, date_key: str, result: ScanRunResult) -> pd.DataFrame:
        if result.hits.empty:
            return pd.DataFrame(columns=self._scan_columns())
        hits = result.hits.copy()
        if "kind" in hits.columns:
            hits = hits.loc[hits["kind"] == "scan"].copy()
        if hits.empty:
            return pd.DataFrame(columns=self._scan_columns())
        output = hits.rename(columns={"name": "scan_name"}).copy()
        output.insert(0, "date_key", date_key)
        output["ticker"] = output["ticker"].astype(str).str.upper()
        output["passed"] = True
        return output[self._scan_columns()]

    def _preset_output(
        self,
        date_key: str,
        result: ScanRunResult,
        *,
        runtime_config: ScanConfig,
        preset_builder: WatchlistViewModelBuilder,
        preset_names: Iterable[str] | None,
    ) -> pd.DataFrame:
        presets = self._selected_presets(runtime_config, preset_names)
        if not presets:
            return pd.DataFrame(columns=self._preset_columns())
        trade_date = self._display_date(date_key)
        summary = preset_builder.build_preset_summary_exports(
            presets,
            result.watchlist,
            result.hits,
            trade_date=trade_date,
            output_date=trade_date,
        )
        if summary.empty:
            return pd.DataFrame(columns=self._preset_columns())
        summary = summary.copy()
        summary.insert(0, "date_key", date_key)
        return summary[self._preset_columns()]

    def _diagnostic_output(
        self,
        date_key: str,
        snapshot: pd.DataFrame,
        result: ScanRunResult,
        runtime_config: ScanConfig,
    ) -> pd.DataFrame:
        _ = result
        working = self._diagnostic_snapshot(snapshot, runtime_config)
        counters: dict[tuple[str, str], dict[str, int]] = {}
        for _, row in working.iterrows():
            issue_results = evaluate_scan_issues(row, runtime_config)
            for scan_name, issues in issue_results.items():
                for issue_name, matched in issues.items():
                    counter = counters.setdefault(
                        (scan_name, issue_name),
                        {"evaluated_count": 0, "pass_count": 0},
                    )
                    counter["evaluated_count"] += 1
                    if matched:
                        counter["pass_count"] += 1

        rows: list[dict[str, object]] = []
        for (scan_name, issue_name), counter in sorted(counters.items()):
            evaluated_count = int(counter["evaluated_count"])
            pass_count = int(counter["pass_count"])
            fail_count = max(0, evaluated_count - pass_count)
            rows.append(
                {
                    "date_key": date_key,
                    "scan_name": scan_name,
                    "issue_name": issue_name,
                    "diagnostic_grain": "issue",
                    "evaluated_count": evaluated_count,
                    "pass_count": pass_count,
                    "fail_count": fail_count,
                    "missing_count": 0,
                    "pass_rate": pass_count / evaluated_count if evaluated_count else 0.0,
                    "fail_rate": fail_count / evaluated_count if evaluated_count else 0.0,
                }
            )
        return pd.DataFrame(rows, columns=self._diagnostic_columns())

    def _diagnostic_snapshot(self, snapshot: pd.DataFrame, runtime_config: ScanConfig) -> pd.DataFrame:
        if snapshot.empty:
            return snapshot.copy()
        base = snapshot.copy()
        for column in ("weekly_return", "quarterly_return"):
            if column not in base.columns:
                base[column] = pd.NA
        working = enrich_with_scan_context(base)
        working["stage2_quality_score"] = [stage2_quality_score(row, runtime_config) for _, row in working.iterrows()]
        working["mature_late_stage_risk"] = [mature_late_stage_risk(row, runtime_config) for _, row in working.iterrows()]
        return working

    def _selected_presets(self, config: ScanConfig, preset_names: Iterable[str] | None):
        selected = self._normalize_selected_names(preset_names)
        if selected is None:
            return tuple(preset for preset in config.watchlist_presets if preset.export_enabled)
        selected_set = set(selected)
        return tuple(
            preset
            for preset in config.watchlist_presets
            if preset.export_enabled and preset.preset_name in selected_set
        )

    def _write_outputs(
        self,
        scan: pd.DataFrame,
        preset: pd.DataFrame,
        diagnostics: pd.DataFrame,
    ) -> list[ModuleOutputRecord]:
        if self.output_store is None:
            return []
        records: list[ModuleOutputRecord] = []
        records.extend(self._write_frame_by_date(SCAN_OUTPUT_MODULE, scan))
        records.extend(self._write_frame_by_date(PRESET_OUTPUT_MODULE, preset))
        records.extend(self._write_frame_by_date(SCAN_DIAGNOSTICS_OUTPUT_MODULE, diagnostics))
        return records

    def _write_frame_by_date(self, module: str, frame: pd.DataFrame) -> list[ModuleOutputRecord]:
        if frame.empty or "date_key" not in frame.columns:
            return []
        records: list[ModuleOutputRecord] = []
        for date_key, group in frame.groupby("date_key", sort=True):
            records.append(
                self.output_store.save_frame(
                    module,
                    str(date_key),
                    group.reset_index(drop=True),
                    metadata={"ticker_count": int(group["ticker"].nunique()) if "ticker" in group.columns else 0},
                )
            )
        return records

    def _write_preset_documents(self, preset: pd.DataFrame) -> list[Path]:
        if self.output_store is None or preset.empty or "date_key" not in preset.columns:
            return []
        documents_dir = Path(self.output_store.root_dir).parent / "documents" / "preset"
        documents_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for date_key, group in preset.groupby("date_key", sort=True):
            path = documents_dir / f"{date_key}_preset_hits.csv"
            group.reset_index(drop=True).to_csv(path, index=False, encoding="utf-8-sig")
            paths.append(path)
        return paths

    def _write_preset_diagnostics(
        self,
        date_key: str,
        result: ScanRunResult,
        *,
        runtime_config: ScanConfig,
        preset_names: Iterable[str] | None,
    ) -> list[Path]:
        if self.output_store is None:
            return []
        presets = tuple(
            ResolvedWatchlistPreset(
                preset_name=preset.preset_name,
                source="Built-in",
                config=preset,
            )
            for preset in self._selected_presets(runtime_config, preset_names)
        )
        artifact = build_preset_diagnostics(
            config_path=self.config_path,
            scan_config=runtime_config,
            watchlist=result.watchlist,
            scan_hits=result.hits,
            presets=presets,
            trade_date=self._display_date(date_key),
        )
        output_dir = Path(self.output_store.root_dir) / "preset_diagnostics"
        output_dir.mkdir(parents=True, exist_ok=True)
        frames = {
            "scan_counts": artifact.scan_counts,
            "annotation_counts": artifact.annotation_counts,
            "preset_steps": artifact.preset_steps,
            "preset_ticker_steps": artifact.preset_ticker_steps,
        }
        paths: list[Path] = []
        files: dict[str, str] = {}
        for key, frame in frames.items():
            path = output_dir / f"{date_key}_{key}.csv"
            frame.to_csv(path, index=False, encoding="utf-8-sig")
            paths.append(path)
            files[key] = path.name
        manifest = dict(artifact.manifest)
        manifest.pop("preset_hit_rows", None)
        manifest["files"] = files
        manifest_path = output_dir / f"{date_key}_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        paths.append(manifest_path)
        return paths

    def _normalize_selected_names(self, names: Iterable[str] | None) -> tuple[str, ...] | None:
        if names is None:
            return None
        return tuple(dict.fromkeys(str(name).strip() for name in names if str(name).strip()))

    def _concat(self, frames: list[pd.DataFrame], columns: list[str]) -> pd.DataFrame:
        non_empty = [frame for frame in frames if frame is not None and not frame.empty]
        if not non_empty:
            return pd.DataFrame(columns=columns)
        return pd.concat(non_empty, ignore_index=True)[columns]

    def _progress(self, callback: object | None, message: str) -> None:
        if callable(callback):
            callback(message)

    def _display_date(self, date_key: str) -> str:
        return f"{date_key[0:4]}-{date_key[4:6]}-{date_key[6:8]}"

    def _scan_columns(self) -> list[str]:
        return ["date_key", "ticker", "scan_name", "kind", "passed"]

    def _preset_columns(self) -> list[str]:
        return [
            "date_key",
            "Output Target",
            "trade_date",
            "output_date",
            "ticker",
            "hit_presets",
            "hit_preset_count",
            "selected_scan_names",
            "selected_annotation_filters",
            "duplicate_thresholds",
            "duplicate_rule_modes",
        ]

    def _diagnostic_columns(self) -> list[str]:
        return [
            "date_key",
            "scan_name",
            "issue_name",
            "diagnostic_grain",
            "evaluated_count",
            "pass_count",
            "fail_count",
            "missing_count",
            "pass_rate",
            "fail_rate",
        ]
