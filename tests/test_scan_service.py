from __future__ import annotations

import pandas as pd

from src.dashboard.watchlist import WatchlistViewModelBuilder
from src.scan.runner import ScanRunResult
from src.scan.rules import ScanCardConfig, ScanConfig, WatchlistPresetConfig
from src.services.indicator_service import IndicatorRunResult
from src.services.module_output_store import ModuleOutputStore
from src.services.scan_service import ScanService


def test_scan_service_runs_from_indicator_frame_and_writes_public_outputs(tmp_path) -> None:
    config = _scan_config()
    output_store = ModuleOutputStore(tmp_path / "outputs")
    service = ScanService(
        indicator_service=None,
        scan_config=config,
        scan_runner=FakeScanRunner(),
        preset_builder=WatchlistViewModelBuilder(config),
        output_store=output_store,
    )

    result = service.run_from_frame(_indicator_frame(), write_outputs=True)

    assert result.scan[["date_key", "ticker", "scan_name", "passed"]].to_dict("records") == [
        {"date_key": "20260303", "ticker": "AAA", "scan_name": "21EMA Pattern H", "passed": True},
        {"date_key": "20260303", "ticker": "AAA", "scan_name": "Pocket Pivot", "passed": True},
        {"date_key": "20260303", "ticker": "BBB", "scan_name": "21EMA Pattern H", "passed": True},
        {"date_key": "20260304", "ticker": "AAA", "scan_name": "21EMA Pattern H", "passed": True},
        {"date_key": "20260304", "ticker": "AAA", "scan_name": "Pocket Pivot", "passed": True},
        {"date_key": "20260304", "ticker": "BBB", "scan_name": "21EMA Pattern H", "passed": True},
    ]
    assert result.preset[["date_key", "ticker", "hit_presets", "hit_preset_count"]].to_dict("records") == [
        {"date_key": "20260303", "ticker": "AAA", "hit_presets": "Momentum Core, EMA Follow Through", "hit_preset_count": 2},
        {"date_key": "20260303", "ticker": "BBB", "hit_presets": "EMA Follow Through", "hit_preset_count": 1},
        {"date_key": "20260304", "ticker": "AAA", "hit_presets": "Momentum Core, EMA Follow Through", "hit_preset_count": 2},
        {"date_key": "20260304", "ticker": "BBB", "hit_presets": "EMA Follow Through", "hit_preset_count": 1},
    ]
    assert result.diagnostics.loc[
        (result.diagnostics["date_key"] == "20260303")
        & (result.diagnostics["scan_name"] == "Pocket Pivot"),
        ["issue_name", "evaluated_count", "pass_count", "fail_count", "diagnostic_grain"],
    ].to_dict("records") == [
        {
            "issue_name": "pp_count_window_gte_pocket_pivot_min",
            "evaluated_count": 2,
            "pass_count": 1,
            "fail_count": 1,
            "diagnostic_grain": "issue",
        }
    ]
    assert sorted(record.module for record in result.output_records) == [
        "preset",
        "preset",
        "scan",
        "scan",
        "scan_diagnostics",
        "scan_diagnostics",
    ]
    assert output_store.load_frame("scan", "20260303")["ticker"].tolist() == ["AAA", "AAA", "BBB"]
    assert output_store.load_frame("preset", "20260303")["ticker"].tolist() == ["AAA", "BBB"]
    assert output_store.list_date_keys("issue") == []


def test_scan_service_run_uses_indicator_service_ticker_pool_and_date_range(tmp_path) -> None:
    config = _scan_config()
    indicator_service = FakeIndicatorService()
    service = ScanService(
        indicator_service=indicator_service,
        scan_config=config,
        scan_runner=FakeScanRunner(),
        preset_builder=WatchlistViewModelBuilder(config),
        output_store=ModuleOutputStore(tmp_path / "outputs"),
    )

    result = service.run(["AAA", "BBB"], start_date="2026-03-03", end_date="2026-03-04")

    assert indicator_service.calls == [
        {
            "symbols": ("AAA", "BBB"),
            "start_date": "2026-03-03",
            "end_date": "2026-03-04",
            "as_of_date": None,
            "refresh_missing": False,
            "force_refresh": False,
            "write_outputs": False,
        }
    ]
    assert result.missing == {"ZZZ": "price history unavailable"}
    assert set(result.scan["date_key"]) == {"20260303", "20260304"}


def test_scan_service_runs_from_pipeline_snapshot_and_keeps_raw_scan_result(tmp_path) -> None:
    config = _scan_config()
    output_store = ModuleOutputStore(tmp_path / "outputs")
    service = ScanService(
        indicator_service=None,
        scan_config=config,
        scan_runner=FakeScanRunner(),
        preset_builder=WatchlistViewModelBuilder(config),
        output_store=output_store,
    )
    snapshot = pd.DataFrame(
        [
            {"close": 11.0, "pp_count_window": 1, "trade_date": pd.Timestamp("2026-03-05")},
            {"close": 21.0, "pp_count_window": 0, "trade_date": pd.Timestamp("2026-03-05")},
        ],
        index=["AAA", "BBB"],
    )

    result = service.run_from_snapshot(snapshot, write_outputs=True)

    assert result.scan_run_result is not None
    assert result.scan_run_result.hits["ticker"].tolist() == ["AAA", "AAA", "BBB"]
    assert result.scan["date_key"].unique().tolist() == ["20260305"]
    assert result.preset[["date_key", "ticker", "hit_preset_count"]].to_dict("records") == [
        {"date_key": "20260305", "ticker": "AAA", "hit_preset_count": 2},
        {"date_key": "20260305", "ticker": "BBB", "hit_preset_count": 1},
    ]
    assert output_store.load_frame("scan", "20260305")["ticker"].tolist() == ["AAA", "AAA", "BBB"]
    assert output_store.list_date_keys("scan_diagnostics") == ["20260305"]


class FakeScanRunner:
    def run(self, snapshot: pd.DataFrame) -> ScanRunResult:
        watchlist = snapshot.copy()
        watchlist["hybrid_score"] = [95.0, 80.0][: len(watchlist)]
        watchlist["overlap_count"] = [2, 1][: len(watchlist)]
        watchlist["vcs"] = [70.0, 60.0][: len(watchlist)]
        hits = pd.DataFrame(
            [
                {"ticker": "AAA", "kind": "scan", "name": "21EMA Pattern H"},
                {"ticker": "AAA", "kind": "scan", "name": "Pocket Pivot"},
                {"ticker": "BBB", "kind": "scan", "name": "21EMA Pattern H"},
            ]
        )
        return ScanRunResult(hits=hits, watchlist=watchlist)


class FakeIndicatorService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def build(
        self,
        symbols,
        *,
        start_date=None,
        end_date=None,
        as_of_date=None,
        refresh_missing=False,
        force_refresh=False,
        write_outputs=False,
    ) -> IndicatorRunResult:
        self.calls.append(
            {
                "symbols": tuple(symbols),
                "start_date": start_date,
                "end_date": end_date,
                "as_of_date": as_of_date,
                "refresh_missing": refresh_missing,
                "force_refresh": force_refresh,
                "write_outputs": write_outputs,
            }
        )
        return IndicatorRunResult(frame=_indicator_frame(), histories={}, missing={"ZZZ": "price history unavailable"})


def _scan_config() -> ScanConfig:
    return ScanConfig(
        enabled_scan_rules=("21EMA Pattern H", "Pocket Pivot"),
        card_sections=(
            ScanCardConfig(scan_name="21EMA Pattern H", display_name="21EMA"),
            ScanCardConfig(scan_name="Pocket Pivot", display_name="Pocket Pivot"),
        ),
        watchlist_presets=(
            WatchlistPresetConfig.from_dict(
                {
                    "preset_name": "Momentum Core",
                    "selected_scan_names": ["21EMA Pattern H", "Pocket Pivot"],
                    "duplicate_threshold": 2,
                }
            ),
            WatchlistPresetConfig.from_dict(
                {
                    "preset_name": "EMA Follow Through",
                    "selected_scan_names": ["21EMA Pattern H"],
                    "duplicate_threshold": 1,
                }
            ),
        ),
    )


def _indicator_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"date_key": "20260303", "ticker": "AAA", "close": 10.0, "pp_count_window": 1},
            {"date_key": "20260303", "ticker": "BBB", "close": 20.0, "pp_count_window": 0},
            {"date_key": "20260304", "ticker": "AAA", "close": 11.0, "pp_count_window": 1},
            {"date_key": "20260304", "ticker": "BBB", "close": 21.0, "pp_count_window": 0},
        ]
    )
