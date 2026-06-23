from __future__ import annotations

from pathlib import Path
import inspect
from types import SimpleNamespace

import pandas as pd

from src.cli import oratek
from src.cli.oratek import (
    _index_absorb_values,
    _parse_symbols,
    _read_symbol_file,
    _resolve_menu_action,
    _resolve_default_universe_symbols,
    _run_interactive_action,
    _stock_card_as_of_warnings,
    build_parser,
    run_interactive,
)
from src.dashboard.stock_card import StockCardDocument


def test_cli_parse_symbols_accepts_commas_spaces_and_dedupes() -> None:
    assert _parse_symbols("aapl, AMD nvda\taapl") == ["AAPL", "AMD", "NVDA"]


def test_cli_reads_symbol_file_from_csv_ticker_column(tmp_path: Path) -> None:
    path = tmp_path / "universe.csv"
    pd.DataFrame({"ticker": ["aapl", "AMD", "aapl"]}).to_csv(path, index=False)

    assert _read_symbol_file(path) == ["AAPL", "AMD"]


def test_cli_resolves_menu_action_from_japanese_or_english_text() -> None:
    assert _resolve_menu_action("\u682a\u4fa1\u30c7\u30fc\u30bf\u3092\u53d6\u5f97\u3057\u305f\u3044") == "price_fetch"
    assert _resolve_menu_action("stockcard\u3092\u4f5c\u308a\u305f\u3044") == "stockcard"
    assert _resolve_menu_action("\u30b9\u30ad\u30e3\u30f3\u3092\u5b9f\u884c") == "scan"
    assert _resolve_menu_action("market report input") == "market_environment"
    assert _resolve_menu_action("rader") == "market_environment"
    assert _resolve_menu_action("\u7dcf\u5408\u5e02\u6cc1") == "market_environment"
    assert _resolve_menu_action("0") == "exit"


def test_cli_parser_accepts_direct_stockcard_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["stockcard", "--symbols", "AAPL,AMD", "--as-of", "2026-03-05"])

    assert args.command == "stockcard"
    assert args.symbols == ["AAPL,AMD"]
    assert args.as_of == "2026-03-05"



def test_cli_parser_accepts_unified_market_environment_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["market-env", "--as-of", "2026-06-18"])

    assert args.command == "market-env"
    assert args.as_of == "2026-06-18"


def test_cli_price_fetch_accepts_default_universe_without_symbols() -> None:
    parser = build_parser()
    args = parser.parse_args(["price", "fetch", "--default-universe"])

    assert args.command == "price"
    assert args.price_command == "fetch"
    assert args.symbols is None
    assert args.default_universe is True


def test_cli_resolves_default_universe_from_latest_snapshot(tmp_path: Path) -> None:
    universe_dir = tmp_path / "universe_snapshots"
    universe_dir.mkdir(parents=True)
    pd.DataFrame({"ticker": ["aapl", "AMD", "aapl"]}).to_csv(universe_dir / "latest.csv", index=False)
    (universe_dir / "latest.json").write_text('{"saved_at":"2099-01-01T00:00:00"}', encoding="utf-8")

    context = type(
        "Context",
        (),
        {
            "settings": {
                "app": {"default_symbols": ["NVDA"]},
                "universe": {},
                "universe_discovery": {
                    "enabled": True,
                    "use_snapshot_when_no_manual_symbols": True,
                    "snapshot_ttl_days": 7,
                    "snapshot_dir": str(universe_dir),
                },
            }
        },
    )()

    symbols, mode, path = _resolve_default_universe_symbols(context)

    assert symbols == ["AAPL", "AMD"]
    assert mode == "weekly_snapshot_cached"
    assert path == str(universe_dir / "latest.csv")


def test_interactive_market_environment_does_not_prompt_for_symbols() -> None:
    source = inspect.getsource(_run_interactive_action)
    branch = source.split('if action == "market_environment":', 1)[1].split("raise ValueError", 1)[0]

    assert "_prompt_symbols" not in branch
    assert "symbols: list[str] = []" in branch


def test_interactive_scan_allows_default_universe_without_symbol_input() -> None:
    source = inspect.getsource(_run_interactive_action)
    branch = source.split('if action == "scan":', 1)[1].split('if action == "market_environment":', 1)[0]

    assert '_prompt_symbols(required=False' in branch
    assert 'symbols=symbols or ["default universe"]' in branch


def test_scan_command_uses_default_universe_when_symbols_are_omitted(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeService:
        def run(self, symbols, **kwargs):
            captured["symbols"] = symbols
            return SimpleNamespace(
                output_records=[],
                scan=pd.DataFrame(),
                preset=pd.DataFrame(),
                missing={},
            )

    monkeypatch.setattr(oratek, "_resolve_default_universe_symbols", lambda context: (["AAA", "BBB"], "cached", "latest.csv"))
    monkeypatch.setattr(oratek, "ScanService", SimpleNamespace(from_config=lambda *args, **kwargs: FakeService()))
    args = SimpleNamespace(
        symbols=[],
        symbols_file=None,
        start_date=None,
        end_date=None,
        as_of=None,
        refresh_missing=False,
        force_refresh=False,
    )
    context = SimpleNamespace(config_path=Path("config/default.yaml"), module_output_store=None)

    assert oratek.command_scan(args, context) == 0
    assert captured["symbols"] == ["AAA", "BBB"]


def test_interactive_cli_returns_to_menu_loop() -> None:
    source = inspect.getsource(run_interactive) + inspect.getsource(_run_interactive_action)

    assert "_run_interactive_loop" in source


def test_cli_warns_when_stockcard_effective_date_is_before_requested_as_of() -> None:
    documents = [StockCardDocument(ticker="ALMU", text="", end_date=pd.Timestamp("2026-06-12"))]

    assert _stock_card_as_of_warnings(documents, "20260617") == [
        "ALMU: requested as_of=2026-06-17, effective price date=2026-06-12"
    ]


def test_index_absorb_values_uses_unified_distribution_day_count() -> None:
    index = pd.date_range("2026-01-01", periods=30, freq="B")
    close = pd.Series(100.0, index=index)
    volume = pd.Series(1000.0, index=index)
    close.iloc[[5, 10, 20, 29]] = close.iloc[[5, 10, 20, 29]] * 0.99
    volume.iloc[[5, 10, 20, 29]] = 1200.0
    frame = pd.DataFrame({"close": close, "high": close + 1.0, "volume": volume}, index=index)

    values = _index_absorb_values(frame)

    assert values["DISTRIBUTION DAY FLAG"] == 1.0
    assert values["DISTRIBUTION DAY COUNT"] == 4.0
