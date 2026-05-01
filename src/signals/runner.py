from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.dashboard.watchlist import WatchlistViewModelBuilder
from src.data.signal_tracking import ACTIVE_POOL_STATUS, insert_signal_evaluation
from src.data.tracking_db import connect_tracking_db
from src.pipeline import PlatformArtifacts
from src.scan.rules import ScanConfig, WatchlistPresetConfig
from src.signals.evaluators.accumulation_breakout import evaluate_accumulation_breakout
from src.signals.evaluators.early_cycle_recovery import evaluate_early_cycle_recovery
from src.signals.evaluators.momentum_acceleration import evaluate_momentum_acceleration
from src.signals.evaluators.orderly_pullback import evaluate_orderly_pullback
from src.signals.evaluators.power_gap_pullback import evaluate_power_gap_pullback
from src.signals.evaluators.pullback_resumption import evaluate_pullback_resumption
from src.signals.pool import (
    INVALIDATED_POOL_STATUS,
    SignalPoolEntry,
    create_pool_entry,
    expire_pool_entries,
    invalidate_pool_entry,
    orphan_pool_entries,
    update_tracking_fields,
)
from src.signals.rules import EntrySignalConfig, EntrySignalDefinition, evaluate_invalidation
from src.watchlist_presets import ResolvedWatchlistPreset, load_watchlist_preset_configs


@dataclass(frozen=True, slots=True)
class EntrySignalSyncResult:
    pool_inserted_count: int
    pool_updated_count: int
    pool_invalidated_count: int
    pool_expired_count: int
    pool_orphaned_count: int
    evaluation_count: int


class EntrySignalRunner:
    """Build signal pools from preset duplicates and evaluate active pools."""

    def __init__(
        self,
        signal_config: EntrySignalConfig,
        scan_config: ScanConfig,
        *,
        config_path: str | None = None,
    ) -> None:
        self.signal_config = signal_config
        self.scan_config = scan_config
        self.config_path = config_path
        self.watchlist_builder = WatchlistViewModelBuilder(scan_config)

    def sync_and_evaluate(
        self,
        artifacts: PlatformArtifacts,
        selected_signal_names: list[str] | tuple[str, ...],
        *,
        root_dir: str | Path | None = None,
    ) -> pd.DataFrame:
        self.sync_tracking(artifacts, root_dir=root_dir)
        return self.evaluate_active_pools(artifacts, selected_signal_names, root_dir=root_dir)

    def sync_tracking(
        self,
        artifacts: PlatformArtifacts,
        *,
        root_dir: str | Path | None = None,
    ) -> EntrySignalSyncResult:
        resolved_definitions = self._enabled_definitions()
        if not resolved_definitions:
            return EntrySignalSyncResult(0, 0, 0, 0, 0, 0)
        trade_date = self._latest_trade_date(artifacts)
        if trade_date is None:
            return EntrySignalSyncResult(0, 0, 0, 0, 0, 0)

        watchlist = artifacts.entry_signal_watchlist if artifacts.entry_signal_watchlist is not None else artifacts.watchlist
        preset_definitions = self._load_preset_definitions()
        preset_frames = self._build_preset_duplicate_frames(watchlist, artifacts.scan_hits, preset_definitions)
        available_preset_names = [preset.preset_name for preset in preset_definitions]
        current_lookup = self._build_current_row_lookup(artifacts)

        pool_inserted_count = 0
        pool_updated_count = 0
        conn = connect_tracking_db(root_dir=root_dir) if root_dir is not None else connect_tracking_db()
        try:
            for signal_name, definition in resolved_definitions.items():
                tickers_by_signal = self._collect_signal_detection_candidates(
                    definition,
                    preset_frames,
                    current_lookup,
                )
                for ticker, payload in tickers_by_signal.items():
                    upsert_result = create_pool_entry(
                        conn,
                        definition=definition,
                        ticker=ticker,
                        detected_date=trade_date,
                        preset_sources=payload["preset_sources"],
                        snapshot=payload["snapshot_at_detection"],
                    )
                    if upsert_result.action == "inserted":
                        pool_inserted_count += 1
                    else:
                        pool_updated_count += 1

            pool_orphaned_count = orphan_pool_entries(conn, valid_presets=available_preset_names)
            self._update_active_pool_tracking(conn, current_lookup)
            pool_expired_count = self._expire_stale_pool_entries(conn, resolved_definitions, trade_date)
            conn.commit()
        finally:
            conn.close()

        return EntrySignalSyncResult(
            pool_inserted_count=pool_inserted_count,
            pool_updated_count=pool_updated_count,
            pool_invalidated_count=0,
            pool_expired_count=pool_expired_count,
            pool_orphaned_count=pool_orphaned_count,
            evaluation_count=0,
        )

    def evaluate_active_pools(
        self,
        artifacts: PlatformArtifacts,
        selected_signal_names: list[str] | tuple[str, ...],
        *,
        root_dir: str | Path | None = None,
    ) -> pd.DataFrame:
        selected_definitions = self._selected_definitions(selected_signal_names)
        if not selected_definitions:
            return pd.DataFrame(columns=self._result_columns())

        trade_date = self._latest_trade_date(artifacts)
        if trade_date is None:
            return pd.DataFrame(columns=self._result_columns())

        current_lookup = self._build_current_row_lookup(artifacts)
        conn = connect_tracking_db(root_dir=root_dir) if root_dir is not None else connect_tracking_db()
        rows: list[dict[str, object]] = []
        try:
            pool_rows = conn.execute(
                f"""
                SELECT *
                FROM signal_pool_entry
                WHERE pool_status = ?
                  AND signal_name IN ({", ".join("?" for _ in selected_definitions)})
                ORDER BY signal_name, ticker, first_detected_date
                """,
                [ACTIVE_POOL_STATUS, *selected_definitions],
            ).fetchall()
            for pool_row in pool_rows:
                definition = selected_definitions[str(pool_row["signal_name"])]
                pool_entry = self._row_to_pool_entry(pool_row)
                current_row = current_lookup.get(pool_entry.ticker)
                if current_row is None:
                    continue

                current_payload = current_row.to_dict()
                invalidated_reason = evaluate_invalidation(definition, current_payload)
                if invalidated_reason:
                    invalidate_pool_entry(
                        conn,
                        signal_name=definition.signal_key,
                        ticker=pool_entry.ticker,
                        changed_date=trade_date,
                        reason=invalidated_reason,
                    )
                    rows.append(
                        self._build_result_row(
                            ticker=pool_entry.ticker,
                            definition=definition,
                            pool_entry=pool_entry,
                            current_row=current_row,
                            setup_maturity_score=0.0,
                            timing_score=0.0,
                            risk_reward_score=0.0,
                            entry_strength=0.0,
                            maturity_detail={},
                            timing_detail={},
                            stop_price=None,
                            reward_target=None,
                            rr_ratio=None,
                            risk_in_atr=None,
                        reward_in_atr=None,
                        stop_adjusted=False,
                        trade_date=trade_date,
                        pool_status=INVALIDATED_POOL_STATUS,
                        pool_transition=INVALIDATED_POOL_STATUS,
                    )
                    )
                    continue

                evaluation = self._evaluate_signal(
                    definition,
                    current_row,
                    pool_entry,
                    trade_date,
                )
                entry_strength, timing_detail = self._apply_context_guards(
                    definition,
                    current_payload,
                    evaluation.entry_strength,
                    evaluation.timing_detail,
                )
                insert_signal_evaluation(
                    conn,
                    pool_entry_id=pool_entry.id,
                    signal_name=definition.signal_key,
                    ticker=pool_entry.ticker,
                    eval_date=trade_date,
                    signal_version=definition.signal_version,
                    setup_maturity_score=evaluation.setup_maturity_score,
                    timing_score=evaluation.timing_score,
                    risk_reward_score=evaluation.risk_reward_score,
                    entry_strength=entry_strength,
                    maturity_detail=evaluation.maturity_detail,
                    timing_detail=timing_detail,
                    stop_price=evaluation.risk_reward.stop_price,
                    reward_target=evaluation.risk_reward.reward_target,
                    rr_ratio=evaluation.risk_reward.rr_ratio,
                    risk_in_atr=evaluation.risk_reward.risk_in_atr,
                    reward_in_atr=evaluation.risk_reward.reward_in_atr,
                    stop_adjusted=evaluation.risk_reward.stop_adjusted,
                )
                rows.append(
                    self._build_result_row(
                        ticker=pool_entry.ticker,
                        definition=definition,
                        pool_entry=pool_entry,
                        current_row=current_row,
                        setup_maturity_score=evaluation.setup_maturity_score,
                        timing_score=evaluation.timing_score,
                        risk_reward_score=evaluation.risk_reward_score,
                        entry_strength=entry_strength,
                        maturity_detail=evaluation.maturity_detail,
                        timing_detail=timing_detail,
                        stop_price=evaluation.risk_reward.stop_price,
                        reward_target=evaluation.risk_reward.reward_target,
                        rr_ratio=evaluation.risk_reward.rr_ratio,
                        risk_in_atr=evaluation.risk_reward.risk_in_atr,
                        reward_in_atr=evaluation.risk_reward.reward_in_atr,
                        stop_adjusted=evaluation.risk_reward.stop_adjusted,
                        trade_date=trade_date,
                        pool_status=ACTIVE_POOL_STATUS,
                        pool_transition="",
                    )
                )
            conn.commit()
        finally:
            conn.close()

        if not rows:
            return pd.DataFrame(columns=self._result_columns())
        result = pd.DataFrame(rows, columns=self._result_columns())
        for column in self._numeric_result_columns():
            if column in result.columns:
                result[column] = pd.to_numeric(result[column], errors="coerce").round(2)
        bucket_rank = result["Display Bucket"].map(
            {"Signal Detected": 0, "Approaching": 1, "Tracking": 2}
        ).fillna(3)
        result = result.assign(_bucket_rank=bucket_rank)
        return result.sort_values(
            ["_bucket_rank", "Entry Strength", "Timing", "Setup Maturity", "Signal", "Ticker"],
            ascending=[True, False, False, False, True, True],
        ).drop(columns="_bucket_rank").reset_index(drop=True)

    def _enabled_definitions(self) -> dict[str, EntrySignalDefinition]:
        return {
            name: self.signal_config.definition_for(name)
            for name in self.signal_config.enabled_signal_names()
        }

    def _selected_definitions(
        self,
        selected_signal_names: list[str] | tuple[str, ...],
    ) -> dict[str, EntrySignalDefinition]:
        enabled_definitions = self._enabled_definitions()
        return {
            name: enabled_definitions[name]
            for name in dict.fromkeys(str(value).strip() for value in selected_signal_names if str(value).strip())
            if name in enabled_definitions
        }

    def _load_preset_definitions(self) -> tuple[ResolvedWatchlistPreset, ...]:
        if self.config_path:
            return load_watchlist_preset_configs(self.config_path, self.scan_config)
        return tuple(
            ResolvedWatchlistPreset(preset_name=preset.preset_name, source="Built-in", config=preset)
            for preset in self.scan_config.watchlist_presets
            if preset.export_enabled
        )

    def _build_preset_duplicate_frames(
        self,
        watchlist: pd.DataFrame,
        hits: pd.DataFrame,
        preset_definitions: tuple[ResolvedWatchlistPreset, ...],
    ) -> dict[str, pd.DataFrame]:
        frames: dict[str, pd.DataFrame] = {}
        for preset in preset_definitions:
            frame = self._project_preset_duplicates(watchlist, hits, preset.config)
            if not frame.empty:
                frame.index = frame.index.astype(str).str.upper()
            frames[preset.preset_name] = frame
        return frames

    def _project_preset_duplicates(
        self,
        watchlist: pd.DataFrame,
        hits: pd.DataFrame,
        preset: WatchlistPresetConfig,
    ) -> pd.DataFrame:
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

    def _collect_signal_detection_candidates(
        self,
        definition: EntrySignalDefinition,
        preset_frames: dict[str, pd.DataFrame],
        current_lookup: dict[str, pd.Series],
    ) -> dict[str, dict[str, object]]:
        candidates: dict[str, dict[str, object]] = {}
        for preset_name in definition.pool.preset_sources:
            frame = preset_frames.get(preset_name)
            if frame is None or frame.empty:
                continue
            for ticker in frame.index.astype(str).str.upper():
                snapshot_row = current_lookup.get(ticker)
                if snapshot_row is None and ticker in frame.index:
                    snapshot_row = frame.loc[ticker]
                if snapshot_row is None:
                    continue
                existing = candidates.setdefault(
                    ticker,
                    {
                        "preset_sources": [],
                        "snapshot_at_detection": self._snapshot_payload(snapshot_row, definition),
                    },
                )
                if preset_name not in existing["preset_sources"]:
                    existing["preset_sources"].append(preset_name)
        return candidates

    def _build_current_row_lookup(self, artifacts: PlatformArtifacts) -> dict[str, pd.Series]:
        lookup: dict[str, pd.Series] = {}
        for frame in [artifacts.eligible_snapshot, artifacts.entry_signal_watchlist, artifacts.watchlist]:
            if frame is None or frame.empty:
                continue
            working = frame.copy()
            working.index = working.index.astype(str).str.upper()
            for ticker, row in working.iterrows():
                normalized_ticker = str(ticker).upper()
                if normalized_ticker not in lookup:
                    lookup[normalized_ticker] = row
        return lookup

    def _update_active_pool_tracking(
        self,
        conn: sqlite3.Connection,
        current_lookup: dict[str, pd.Series],
    ) -> None:
        rows = conn.execute(
            """
            SELECT id, ticker
            FROM signal_pool_entry
            WHERE pool_status = ?
            """,
            (ACTIVE_POOL_STATUS,),
        ).fetchall()
        for row in rows:
            ticker = str(row["ticker"]).upper()
            current_row = current_lookup.get(ticker)
            if current_row is None:
                continue
            update_tracking_fields(
                conn,
                entry_id=int(row["id"]),
                today_low=current_row.get("low"),
                today_high=current_row.get("high"),
            )

    def _expire_stale_pool_entries(
        self,
        conn: sqlite3.Connection,
        definitions: dict[str, EntrySignalDefinition],
        trade_date: pd.Timestamp,
    ) -> int:
        rows = conn.execute(
            """
            SELECT signal_name, ticker, latest_detected_date
            FROM signal_pool_entry
            WHERE pool_status = ?
            """,
            (ACTIVE_POOL_STATUS,),
        ).fetchall()
        tickers_by_signal: dict[str, list[str]] = {}
        for row in rows:
            signal_name = str(row["signal_name"])
            definition = definitions.get(signal_name)
            if definition is None:
                continue
            latest_detected_date = pd.to_datetime(row["latest_detected_date"], errors="coerce")
            if pd.isna(latest_detected_date):
                continue
            if self._business_day_distance(pd.Timestamp(latest_detected_date).normalize(), trade_date) > definition.pool.detection_window_days:
                tickers_by_signal.setdefault(signal_name, []).append(str(row["ticker"]).upper())
        expired_count = 0
        for signal_name, tickers in tickers_by_signal.items():
            expired_count += expire_pool_entries(conn, signal_name=signal_name, tickers=tickers)
        return expired_count

    def _evaluate_signal(
        self,
        definition: EntrySignalDefinition,
        current_row: pd.Series,
        pool_entry: SignalPoolEntry,
        trade_date: pd.Timestamp,
    ):
        if definition.signal_key == "orderly_pullback_entry":
            return evaluate_orderly_pullback(current_row, pool_entry, definition, eval_date=trade_date)
        if definition.signal_key == "pullback_resumption_entry":
            return evaluate_pullback_resumption(current_row, pool_entry, definition, eval_date=trade_date)
        if definition.signal_key == "momentum_acceleration_entry":
            return evaluate_momentum_acceleration(current_row, pool_entry, definition, eval_date=trade_date)
        if definition.signal_key == "accumulation_breakout_entry":
            return evaluate_accumulation_breakout(current_row, pool_entry, definition, eval_date=trade_date)
        if definition.signal_key == "early_cycle_recovery_entry":
            return evaluate_early_cycle_recovery(current_row, pool_entry, definition, eval_date=trade_date)
        if definition.signal_key == "power_gap_pullback_entry":
            return evaluate_power_gap_pullback(current_row, pool_entry, definition, eval_date=trade_date)
        raise ValueError(f"no evaluator registered for signal: {definition.signal_key}")

    def _apply_context_guards(
        self,
        definition: EntrySignalDefinition,
        current_row: dict[str, object],
        entry_strength: float,
        timing_detail: dict[str, float],
    ) -> tuple[float, dict[str, float]]:
        guard = self.signal_config.context_guard
        if not guard.enabled or not guard.cap_below_signal_detected:
            return entry_strength, timing_detail

        reasons: list[str] = []
        market_score = self._to_float(current_row.get("market_score"))
        weak_market_score_threshold = guard.weak_market_threshold_for(definition.signal_key)
        if (
            weak_market_score_threshold is not None
            and market_score is not None
            and market_score < weak_market_score_threshold
        ):
            reasons.append("weak_market_warning")
        if guard.earnings_today_field and bool(current_row.get(guard.earnings_today_field)):
            reasons.append("earnings_today_warning")
        elif guard.earnings_warning_field and bool(current_row.get(guard.earnings_warning_field)):
            reasons.append("earnings_warning")

        if not reasons:
            return entry_strength, timing_detail

        adjusted_detail = dict(timing_detail)
        for reason in reasons:
            adjusted_detail[reason] = 100.0
        capped_strength = min(float(entry_strength), definition.display.signal_detected - 0.01)
        return round(capped_strength, 2), adjusted_detail

    def _snapshot_payload(
        self,
        row: pd.Series,
        definition: EntrySignalDefinition,
    ) -> dict[str, object]:
        keys = list(definition.pool.snapshot_fields)
        for required in ("low", "high"):
            if required not in keys:
                keys.append(required)
        return {key: self._normalize_cell_value(row.get(key)) for key in keys}

    def _build_result_row(
        self,
        *,
        ticker: str,
        definition: EntrySignalDefinition,
        pool_entry: SignalPoolEntry,
        current_row: pd.Series,
        setup_maturity_score: float,
        timing_score: float,
        risk_reward_score: float,
        entry_strength: float,
        maturity_detail: dict[str, float],
        timing_detail: dict[str, float],
        stop_price: float | None,
        reward_target: float | None,
        rr_ratio: float | None,
        risk_in_atr: float | None,
        reward_in_atr: float | None,
        stop_adjusted: bool,
        trade_date: pd.Timestamp,
        pool_status: str,
        pool_transition: str,
    ) -> dict[str, object]:
        pool_days = self._business_day_distance(pool_entry.first_detected_date, trade_date)
        display_bucket = definition.display.classify(entry_strength)
        return {
            "Ticker": ticker,
            "Signal": definition.display_name,
            "Signal Key": definition.signal_key,
            "Display Bucket": display_bucket,
            "Preset Sources": ", ".join(pool_entry.preset_sources),
            "First Detected": pool_entry.first_detected_date.strftime("%Y-%m-%d"),
            "Latest Detected": pool_entry.latest_detected_date.strftime("%Y-%m-%d"),
            "Pool Days": pool_days,
            "Detection Count": pool_entry.detection_count,
            "Setup Maturity": setup_maturity_score,
            "Timing": timing_score,
            "Risk/Reward": risk_reward_score,
            "Entry Strength": entry_strength,
            "Close": current_row.get("close"),
            "RS21": current_row.get("rs21"),
            "ATR 21EMA Zone": current_row.get("atr_21ema_zone"),
            "Volume Ratio 20D": current_row.get("volume_ratio_20d"),
            "Drawdown 20D High %": current_row.get("drawdown_from_20d_high_pct"),
            "Low Since Detection": pool_entry.low_since_detection,
            "High Since Detection": pool_entry.high_since_detection,
            "Stop Price": stop_price,
            "Reward Target": reward_target,
            "R/R Ratio": rr_ratio,
            "Risk In ATR": risk_in_atr,
            "Reward In ATR": reward_in_atr,
            "Stop Adjusted": "Yes" if stop_adjusted else "",
            "Maturity Detail": json.dumps(maturity_detail, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
            "Timing Detail": json.dumps(timing_detail, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
            "Pool Status": pool_status,
            "Pool Transition": pool_transition,
            "Signal Version": definition.signal_version,
            "Pool Entry Id": pool_entry.id,
        }

    def _result_columns(self) -> list[str]:
        return [
            "Ticker",
            "Signal",
            "Signal Key",
            "Display Bucket",
            "Preset Sources",
            "First Detected",
            "Latest Detected",
            "Pool Days",
            "Detection Count",
            "Setup Maturity",
            "Timing",
            "Risk/Reward",
            "Entry Strength",
            "Close",
            "RS21",
            "ATR 21EMA Zone",
            "Volume Ratio 20D",
            "Drawdown 20D High %",
            "Low Since Detection",
            "High Since Detection",
            "Stop Price",
            "Reward Target",
            "R/R Ratio",
            "Risk In ATR",
            "Reward In ATR",
            "Stop Adjusted",
            "Maturity Detail",
            "Timing Detail",
            "Pool Status",
            "Pool Transition",
            "Signal Version",
            "Pool Entry Id",
        ]

    def _numeric_result_columns(self) -> list[str]:
        return [
            "Pool Days",
            "Detection Count",
            "Setup Maturity",
            "Timing",
            "Risk/Reward",
            "Entry Strength",
            "Close",
            "RS21",
            "ATR 21EMA Zone",
            "Volume Ratio 20D",
            "Drawdown 20D High %",
            "Low Since Detection",
            "High Since Detection",
            "Stop Price",
            "Reward Target",
            "R/R Ratio",
            "Risk In ATR",
            "Reward In ATR",
        ]

    def _latest_trade_date(self, artifacts: PlatformArtifacts) -> pd.Timestamp | None:
        if artifacts.snapshot.empty or "trade_date" not in artifacts.snapshot.columns:
            return None
        trade_date = pd.to_datetime(artifacts.snapshot["trade_date"], errors="coerce").max()
        if pd.isna(trade_date):
            return None
        return pd.Timestamp(trade_date).normalize()

    def _normalize_cell_value(self, value: object) -> object:
        try:
            if value is None or pd.isna(value):
                return None
        except TypeError:
            pass
        if hasattr(value, "item"):
            return value.item()
        return value

    def _row_to_pool_entry(self, row: sqlite3.Row) -> SignalPoolEntry:
        invalidated_date = pd.to_datetime(row["invalidated_date"], errors="coerce")
        return SignalPoolEntry(
            id=int(row["id"]),
            signal_name=str(row["signal_name"]),
            ticker=str(row["ticker"]).upper(),
            preset_sources=tuple(self._deserialize_json_list(row["preset_sources"])),
            first_detected_date=pd.Timestamp(row["first_detected_date"]).normalize(),
            latest_detected_date=pd.Timestamp(row["latest_detected_date"]).normalize(),
            detection_count=int(row["detection_count"] or 0),
            pool_status=str(row["pool_status"]),
            invalidated_date=None if pd.isna(invalidated_date) else pd.Timestamp(invalidated_date).normalize(),
            invalidated_reason=str(row["invalidated_reason"]).strip() if row["invalidated_reason"] else None,
            snapshot_at_detection=self._deserialize_json_dict(row["snapshot_at_detection"]),
            low_since_detection=self._to_float(row["low_since_detection"]),
            high_since_detection=self._to_float(row["high_since_detection"]),
        )

    def _deserialize_json_list(self, payload: str | None) -> list[str]:
        if not payload:
            return []
        try:
            loaded = json.loads(payload)
        except json.JSONDecodeError:
            return []
        if not isinstance(loaded, list):
            return []
        return [str(value).strip() for value in loaded if str(value).strip()]

    def _deserialize_json_dict(self, payload: str | None) -> dict[str, object]:
        if not payload:
            return {}
        try:
            loaded = json.loads(payload)
        except json.JSONDecodeError:
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def _to_float(self, value: object) -> float | None:
        try:
            if value is None or pd.isna(value):
                return None
        except TypeError:
            if value is None:
                return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _business_day_distance(self, left: pd.Timestamp, right: pd.Timestamp) -> int:
        left_date = pd.Timestamp(left).normalize().date()
        right_date = pd.Timestamp(right).normalize().date()
        if right_date <= left_date:
            return 1 if right_date == left_date else 0
        return int(np.busday_count(left_date, right_date)) + 1
