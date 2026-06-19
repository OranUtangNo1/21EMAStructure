from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from src.configuration import load_settings
from src.dashboard.market_context import MarketContextBuilder, MarketContextConfig, MarketContextMarkdownRenderer
from src.dashboard.market_report import MarketReportBuilder, MarketReportConfig, MarketReportMarkdownRenderer
from src.dashboard.stock_card import StockCardConfig, StockCardDocument, StockCardExportResult
from src.services.market_service import MarketService
from src.services.module_output_store import ModuleOutputRecord, ModuleOutputStore
from src.services.price_data_service import PriceDataService
from src.services.scan_service import ScanService
from src.services.stock_card_service import StockCardService


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"
MENU_ACTIONS = ("price_fetch", "stockcard", "scan", "market_environment", "exit")


@dataclass(frozen=True, slots=True)
class CliContext:
    config_path: Path
    settings: dict[str, object]

    @property
    def snapshot_dir(self) -> Path:
        app_settings = self.settings.get("app", {}) if isinstance(self.settings.get("app", {}), dict) else {}
        return _resolve_project_path(str(app_settings.get("snapshot_dir", "data_runs")))

    @property
    def data_runs_dir(self) -> Path:
        return _resolve_project_path("data_runs")

    @property
    def service_output_dir(self) -> Path:
        return self.data_runs_dir / "service_outputs"

    @property
    def module_output_store(self) -> ModuleOutputStore:
        return ModuleOutputStore(self.service_output_dir)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        return run_interactive()
    parser = build_parser()
    namespace = parser.parse_args(args)
    context = _context(namespace.config)
    try:
        return int(namespace.func(namespace, context) or 0)
    except KeyboardInterrupt:
        print("Interrupted.")
        return 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m src.cli.oratek", description="OraTek service CLI")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Config path. Default: config/default.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    price = subparsers.add_parser("price", help="Price-data operations")
    price_sub = price.add_subparsers(dest="price_command", required=True)
    fetch = price_sub.add_parser("fetch", help="Fetch or load shared price cache")
    _add_symbol_args(fetch)
    fetch.add_argument("--period", default=None, help="Provider fetch period. Default uses app.price_period")
    fetch.add_argument("--start-date", default=None)
    fetch.add_argument("--end-date", default=None)
    fetch.add_argument("--force-refresh", action="store_true", help="Fetch all requested symbols from provider")
    fetch.add_argument("--cache-only", action="store_true", help="Do not fetch missing symbols")
    fetch.set_defaults(func=command_price_fetch)

    stockcard = subparsers.add_parser("stockcard", help="Build StockCard markdown files")
    _add_symbol_args(stockcard)
    stockcard.add_argument("--as-of", default=None, help="Effective trade date")
    stockcard.add_argument("--start-date", default=None)
    stockcard.add_argument("--refresh-missing", action="store_true", help="Fetch missing price histories")
    stockcard.add_argument("--force-refresh", action="store_true", help="Fetch all requested price histories")
    stockcard.set_defaults(func=command_stockcard)

    scan = subparsers.add_parser("scan", help="Run scan and preset services")
    _add_symbol_args(scan)
    scan.add_argument("--as-of", default=None, help="Effective trade date")
    scan.add_argument("--start-date", default=None, help="Optional historical date-range start")
    scan.add_argument("--end-date", default=None, help="Optional historical date-range end")
    scan.add_argument("--refresh-missing", action="store_true")
    scan.add_argument("--force-refresh", action="store_true")
    scan.set_defaults(func=command_scan)

    market_env = subparsers.add_parser("market-env", help="Build unified market/radar/report/context outputs")
    _add_optional_symbol_args(market_env)
    market_env.add_argument("--as-of", default=None, help="Effective trade date")
    market_env.add_argument("--refresh-missing", action="store_true")
    market_env.add_argument("--force-refresh", action="store_true")
    market_env.set_defaults(func=command_market_environment)

    market = subparsers.add_parser("market", help="Build market outputs")
    _add_optional_symbol_args(market)
    market.add_argument("--as-of", default=None, help="Effective trade date")
    market.add_argument("--refresh-missing", action="store_true")
    market.add_argument("--force-refresh", action="store_true")
    market.set_defaults(func=command_market)

    radar = subparsers.add_parser("radar", help="Build RS Radar outputs")
    radar.add_argument("--as-of", default=None, help="Effective trade date")
    radar.add_argument("--refresh-missing", action="store_true")
    radar.add_argument("--force-refresh", action="store_true")
    radar.set_defaults(func=command_radar)

    report = subparsers.add_parser("market-report-input", help="Build AI market-report input")
    _add_optional_symbol_args(report)
    report.add_argument("--as-of", default=None, help="Effective trade date")
    report.add_argument("--refresh-missing", action="store_true")
    report.add_argument("--force-refresh", action="store_true")
    report.set_defaults(func=command_market_report_input)
    return parser


def run_interactive() -> int:
    print("OraTek CLI")
    print("")
    print("実行したい処理を選んでください。番号でも文章でも入力できます。")
    print("1. 株価データを取得する")
    print("2. StockCardを出力する")
    print("3. Scanを実行する")
    print("4. Market Environment (market + radar + market-report input + market_context)")
    print("0. 終了")
    print("")

    action = _resolve_menu_action(_prompt("入力", default="0"))
    if action == "exit":
        print("終了します。")
        return 0

    context = _context(str(DEFAULT_CONFIG))
    try:
        if action == "price_fetch":
            symbols = _prompt_symbols(required=True)
            period = _prompt("取得期間", default=str(_app_settings(context).get("price_period", "3y")))
            force_refresh = _prompt_yes_no("全銘柄を強制取得しますか", default=False)
            return command_price_fetch(
                argparse.Namespace(
                    symbols=symbols,
                    symbols_file=None,
                    period=period,
                    start_date=None,
                    end_date=None,
                    force_refresh=force_refresh,
                    cache_only=False,
                ),
                context,
            )
        if action == "stockcard":
            symbols = _prompt_symbols(required=True)
            as_of = _prompt("対象日 YYYY-MM-DD / YYYYMMDD", default="")
            force_refresh = _prompt_yes_no("指定日まで価格データを強制更新しますか", default=False)
            if not _confirm("StockCardを出力します", symbols=symbols, as_of=as_of or "latest"):
                return 0
            return command_stockcard(
                argparse.Namespace(
                    symbols=symbols,
                    symbols_file=None,
                    as_of=as_of or None,
                    start_date=None,
                    refresh_missing=False,
                    force_refresh=force_refresh,
                ),
                context,
            )
        if action == "scan":
            symbols = _prompt_symbols(required=True)
            as_of = _prompt("対象日 YYYY-MM-DD / YYYYMMDD", default="")
            refresh_missing = _prompt_yes_no("キャッシュ不足時に取得しますか", default=False)
            if not _confirm("Scanを実行します", symbols=symbols, as_of=as_of or "latest"):
                return 0
            return command_scan(
                argparse.Namespace(
                    symbols=symbols,
                    symbols_file=None,
                    as_of=as_of or None,
                    start_date=None,
                    end_date=None,
                    refresh_missing=refresh_missing,
                    force_refresh=False,
                ),
                context,
            )
        if action == "market_environment":
            symbols: list[str] = []
            as_of = _prompt("as_of YYYY-MM-DD / YYYYMMDD", default="")
            refresh_missing = _prompt_yes_no("Fetch missing cache data", default=False)
            if not _confirm("Market Environment output", symbols=symbols or ["market universe"], as_of=as_of or "latest"):
                return 0
            return command_market_environment(
                argparse.Namespace(
                    symbols=symbols,
                    symbols_file=None,
                    as_of=as_of or None,
                    refresh_missing=refresh_missing,
                    force_refresh=False,
                ),
                context,
            )
        if action == "market":
            symbols = _prompt_symbols(required=False)
            as_of = _prompt("対象日 YYYY-MM-DD / YYYYMMDD", default="")
            refresh_missing = _prompt_yes_no("キャッシュ不足時に取得しますか", default=False)
            if not _confirm("Marketを作成します", symbols=symbols or ["なし"], as_of=as_of or "latest"):
                return 0
            return command_market(
                argparse.Namespace(
                    symbols=symbols,
                    symbols_file=None,
                    as_of=as_of or None,
                    refresh_missing=refresh_missing,
                    force_refresh=False,
                ),
                context,
            )
        if action == "radar":
            as_of = _prompt("対象日 YYYY-MM-DD / YYYYMMDD", default="")
            refresh_missing = _prompt_yes_no("キャッシュ不足時に取得しますか", default=False)
            if not _confirm("Radarを作成します", symbols=["Radar universe"], as_of=as_of or "latest"):
                return 0
            return command_radar(
                argparse.Namespace(as_of=as_of or None, refresh_missing=refresh_missing, force_refresh=False),
                context,
            )
        if action == "market_report_input":
            symbols = _prompt_symbols(required=False)
            as_of = _prompt("対象日 YYYY-MM-DD / YYYYMMDD", default="")
            refresh_missing = _prompt_yes_no("キャッシュ不足時に取得しますか", default=False)
            if not _confirm("MarketReport用 input を作成します", symbols=symbols or ["なし"], as_of=as_of or "latest"):
                return 0
            return command_market_report_input(
                argparse.Namespace(
                    symbols=symbols,
                    symbols_file=None,
                    as_of=as_of or None,
                    refresh_missing=refresh_missing,
                    force_refresh=False,
                ),
                context,
            )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


def command_price_fetch(args: argparse.Namespace, context: CliContext) -> int:
    symbols = _symbols_from_args(args)
    if not symbols:
        raise ValueError("At least one symbol is required.")
    service = PriceDataService.from_config(context.config_path)
    batch = service.get_histories(
        symbols,
        start_date=args.start_date,
        end_date=args.end_date,
        refresh_missing=not bool(args.cache_only),
        force_refresh=bool(args.force_refresh),
        period=args.period,
    )
    _print_price_summary(batch.histories, batch.statuses)
    return 0


def command_stockcard(args: argparse.Namespace, context: CliContext) -> int:
    symbols = _symbols_from_args(args)
    if not symbols:
        raise ValueError("At least one symbol is required.")
    result = build_stock_cards(
        context,
        symbols,
        as_of_date=args.as_of,
        start_date=args.start_date,
        refresh_missing=bool(args.refresh_missing),
        force_refresh=bool(args.force_refresh),
    )
    print(f"StockCard output: {result.output_dir}")
    print(f"Documents: {len(result.documents)}")
    warnings = _stock_card_as_of_warnings(result.documents, args.as_of)
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
        print("- 指定日まで更新したい場合は --force-refresh を付けて再実行してください。")
    if result.missing:
        print("Missing:")
        for symbol, reason in result.missing.items():
            print(f"- {symbol}: {reason}")
    print(f"Manifest: {result.manifest_path}")
    return 0


def command_scan(args: argparse.Namespace, context: CliContext) -> int:
    symbols = _symbols_from_args(args)
    if not symbols:
        raise ValueError("At least one symbol is required.")
    service = ScanService.from_config(context.config_path, output_store=context.module_output_store)
    result = service.run(
        symbols,
        start_date=args.start_date,
        end_date=args.end_date,
        as_of_date=args.as_of,
        refresh_missing=bool(args.refresh_missing),
        force_refresh=bool(args.force_refresh),
        write_outputs=True,
    )
    _print_records("Scan outputs", result.output_records)
    print(f"Scan hits: {len(result.scan)}")
    print(f"Preset hits: {len(result.preset)}")
    if result.missing:
        _print_missing(result.missing)
    return 0


def command_market_environment(args: argparse.Namespace, context: CliContext) -> int:
    result = _run_market_service(args, context, write_outputs=True)
    report_output = write_market_report_input(context, result)
    context_output = write_market_context_output(context, result)
    print(f"Market Environment: {result.market_result.label} / score={result.market_result.score:.1f}")
    print(f"- radar sector leaders: {len(result.radar_result.sector_leaders)}")
    print(f"- radar industry leaders: {len(result.radar_result.industry_leaders)}")
    _print_records("Market/Radar module outputs", result.output_records)
    print(f"MarketReport input JSON: {report_output['json_path']}")
    if report_output.get("markdown_path") is not None:
        print(f"MarketReport input Markdown: {report_output['markdown_path']}")
    print(f"Market summary: {report_output['summary_path']}")
    if context_output.get("json_path") is not None:
        print(f"MarketContext JSON: {context_output['json_path']}")
    if context_output.get("markdown_path") is not None:
        print(f"MarketContext Markdown: {context_output['markdown_path']}")
    if result.missing:
        _print_missing(result.missing)
    return 0


def command_market(args: argparse.Namespace, context: CliContext) -> int:
    result = _run_market_service(args, context, write_outputs=True)
    print(f"Market: {result.market_result.label} / score={result.market_result.score:.1f}")
    _print_records("Market outputs", result.output_records)
    if result.missing:
        _print_missing(result.missing)
    return 0


def command_radar(args: argparse.Namespace, context: CliContext) -> int:
    result = MarketService.from_config(context.config_path, output_store=context.module_output_store).run(
        stock_symbols=[],
        as_of_date=args.as_of,
        refresh_missing=bool(args.refresh_missing),
        force_refresh=bool(args.force_refresh),
        write_outputs=True,
    )
    print("Radar output:")
    print(f"- sector leaders: {len(result.radar_result.sector_leaders)}")
    print(f"- industry leaders: {len(result.radar_result.industry_leaders)}")
    _print_records("Radar module outputs", [record for record in result.output_records if record.module.startswith("rs_radar")])
    if result.missing:
        _print_missing(result.missing)
    return 0


def command_market_report_input(args: argparse.Namespace, context: CliContext) -> int:
    result = _run_market_service(args, context, write_outputs=False)
    output = write_market_report_input(context, result)
    print(f"MarketReport input JSON: {output['json_path']}")
    if output.get("markdown_path") is not None:
        print(f"MarketReport input Markdown: {output['markdown_path']}")
    print(f"Market summary: {output['summary_path']}")
    return 0


def build_stock_cards(
    context: CliContext,
    symbols: list[str],
    *,
    as_of_date: str | pd.Timestamp | None = None,
    start_date: str | pd.Timestamp | None = None,
    refresh_missing: bool = False,
    force_refresh: bool = False,
) -> StockCardExportResult:
    settings = context.settings
    raw_config = settings.get("stock_card", {}) if isinstance(settings.get("stock_card", {}), dict) else {}
    if not bool(raw_config.get("enabled", True)):
        raise RuntimeError("stock_card export is disabled by config.")
    card_config = StockCardConfig.from_dict(raw_config)
    if not card_config.write_markdown and not card_config.write_json:
        raise RuntimeError("stock_card export requires write_markdown or write_json.")
    output_base_dir = _resolve_project_path(str(raw_config.get("output_dir", "data_runs/documents/stock_cards")))
    service = StockCardService.from_config(context.config_path, card_config)
    build_result = service.build_many(
        symbols,
        as_of_date=as_of_date,
        start_date=start_date,
        refresh_missing=refresh_missing,
        force_refresh=force_refresh,
    )
    output_dir = output_base_dir / _stock_card_folder_name(build_result.documents, as_of_date)
    output_dir.mkdir(parents=True, exist_ok=True)

    documents: list[StockCardDocument] = []
    for document in build_result.documents:
        path = output_dir / document.filename if card_config.write_markdown else None
        json_path = output_dir / document.json_filename if card_config.write_json else None
        if path is not None:
            path.write_text(document.text, encoding="utf-8", newline="\n")
        if json_path is not None:
            json_path.write_text(json.dumps(document.payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        documents.append(
            StockCardDocument(
                ticker=document.ticker,
                text=document.text,
                end_date=document.end_date,
                path=path,
                payload=document.payload,
                json_path=json_path,
            )
        )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "stock_card_manifest_v1",
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "source": "oratek_cli",
                "output_dir": str(output_dir),
                "write_markdown": bool(card_config.write_markdown),
                "write_json": bool(card_config.write_json),
                "requested_as_of_date": _date_text(as_of_date),
                "effective_date_warnings": _stock_card_as_of_warnings(documents, as_of_date),
                "documents": [
                    {
                        "ticker": document.ticker,
                        "filename": document.filename,
                        "path": str(document.path) if document.path is not None else "",
                        "json_filename": document.json_filename,
                        "json_path": str(document.json_path) if document.json_path is not None else "",
                        "end_date": document.end_date.strftime("%Y-%m-%d"),
                    }
                    for document in documents
                ],
                "missing": build_result.missing,
                "fetch_status": build_result.fetch_status,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return StockCardExportResult(output_dir=output_dir, documents=documents, missing=build_result.missing, manifest_path=manifest_path)


def _stock_card_as_of_warnings(
    documents: list[StockCardDocument],
    as_of_date: str | pd.Timestamp | None,
) -> list[str]:
    requested = _normalized_date(as_of_date)
    if requested is None:
        return []
    warnings: list[str] = []
    for document in documents:
        effective = pd.Timestamp(document.end_date).normalize()
        if effective < requested:
            warnings.append(
                f"{document.ticker}: requested as_of={requested.strftime('%Y-%m-%d')}, "
                f"effective price date={effective.strftime('%Y-%m-%d')}"
            )
    return warnings


def write_market_report_input(context: CliContext, result) -> dict[str, Path | None]:
    date_key = _date_key_from_market_result(result.market_result)
    output_dir = context.service_output_dir / "market_report_input"
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / f"market_summary_{date_key}.json"
    summary = _market_summary_payload(result)
    _enrich_index_absorb_inputs(context, summary, result.market_result.trade_date)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    market_settings = context.settings.get("market", {}) if isinstance(context.settings.get("market", {}), dict) else {}
    report_config = MarketReportConfig.from_dict(market_settings.get("market_report", {}))
    report = MarketReportBuilder(report_config).build(
        summary,
        source_summary_path=str(summary_path),
        history_summaries=_recent_market_summaries(context, date_key),
    )
    stem = _output_stem(date_key, report_config.output_mode) or date_key
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md" if report_config.write_markdown else None
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if markdown_path is not None:
        markdown_path.write_text(MarketReportMarkdownRenderer().render(report), encoding="utf-8", newline="\n")
    return {"summary_path": summary_path, "json_path": json_path, "markdown_path": markdown_path}


def write_market_context_output(context: CliContext, result) -> dict[str, Path | None]:
    date_key = _date_key_from_market_result(result.market_result)
    raw_config = context.settings.get("market_context", {}) if isinstance(context.settings.get("market_context", {}), dict) else {}
    config = MarketContextConfig.from_dict(raw_config)
    output_dir = _resolve_project_path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = _output_stem(date_key, config.output_mode)
    if stem is None:
        return {"json_path": None, "markdown_path": None}
    summary = _market_summary_payload(result)
    _enrich_index_absorb_inputs(context, summary, result.market_result.trade_date)
    market_context = MarketContextBuilder(config).build(
        summary,
        history_summaries=_recent_market_summaries(context, date_key),
    )
    renderer = MarketContextMarkdownRenderer()
    json_path = output_dir / f"{stem}.json" if config.write_json else None
    markdown_path = output_dir / f"{stem}.md" if config.write_markdown else None
    if json_path is not None:
        json_path.write_text(renderer.render_json(market_context), encoding="utf-8", newline="\n")
    if markdown_path is not None:
        markdown_path.write_text(renderer.render(market_context), encoding="utf-8", newline="\n")
    return {"json_path": json_path, "markdown_path": markdown_path}


def _run_market_service(args: argparse.Namespace, context: CliContext, *, write_outputs: bool):
    service = MarketService.from_config(context.config_path, output_store=context.module_output_store)
    return service.run(
        stock_symbols=_symbols_from_args(args),
        as_of_date=args.as_of,
        refresh_missing=bool(args.refresh_missing),
        force_refresh=bool(args.force_refresh),
        write_outputs=write_outputs,
    )


def _add_symbol_args(parser: argparse.ArgumentParser) -> None:
    _add_optional_symbol_args(parser)


def _add_optional_symbol_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--symbols", nargs="*", default=None, help="Tickers. Accepts space or comma-separated values.")
    parser.add_argument("--symbols-file", default=None, help="Text/CSV file containing tickers.")


def _context(config_path: str | Path) -> CliContext:
    resolved = Path(config_path).expanduser()
    if not resolved.is_absolute():
        resolved = ROOT / resolved
    return CliContext(config_path=resolved.resolve(strict=False), settings=load_settings(resolved))


def _app_settings(context: CliContext) -> dict[str, object]:
    return context.settings.get("app", {}) if isinstance(context.settings.get("app", {}), dict) else {}


def _symbols_from_args(args: argparse.Namespace) -> list[str]:
    symbols: list[str] = []
    for value in args.symbols or []:
        symbols.extend(_parse_symbols(value))
    if getattr(args, "symbols_file", None):
        symbols.extend(_read_symbol_file(Path(args.symbols_file)))
    return _normalize_symbols(symbols)


def _parse_symbols(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = value.replace("\n", ",").replace("\t", ",").replace(" ", ",").split(",")
    else:
        raw_items = []
        for item in value:
            raw_items.extend(_parse_symbols(str(item)))
    return _normalize_symbols(raw_items)


def _read_symbol_file(path: Path) -> list[str]:
    resolved = path.expanduser()
    if not resolved.exists():
        raise FileNotFoundError(f"symbol file not found: {resolved}")
    if resolved.suffix.lower() == ".csv":
        frame = pd.read_csv(resolved)
        if frame.empty:
            return []
        for column in ("ticker", "symbol", "Ticker", "Symbol"):
            if column in frame.columns:
                return _normalize_symbols(frame[column].tolist())
        return _normalize_symbols(frame.iloc[:, 0].tolist())
    return _parse_symbols(resolved.read_text(encoding="utf-8"))


def _normalize_symbols(values: Iterable[object]) -> list[str]:
    return list(dict.fromkeys(str(value).strip().upper() for value in values if str(value).strip()))


def _resolve_menu_action(value: str) -> str:
    text = str(value).strip().lower()
    if text in {"0", "q", "quit", "exit", "\u7d42\u4e86"}:
        return "exit"
    if text == "1" or any(keyword in text for keyword in ("\u682a\u4fa1", "\u4fa1\u683c", "price", "fetch")):
        return "price_fetch"
    if text == "2" or any(keyword in text for keyword in ("stockcard", "stock card", "\u30ab\u30fc\u30c9", "card")):
        return "stockcard"
    if text == "3" or any(keyword in text for keyword in ("scan", "\u30b9\u30ad\u30e3\u30f3")):
        return "scan"
    if text in {"4", "5", "6"} or any(
        keyword in text
        for keyword in (
            "market",
            "radar",
            "rader",
            "rs",
            "report",
            "input",
            "\u5e02\u6cc1",
            "\u5e02\u5834",
            "\u7dcf\u5408",
            "\u74b0\u5883",
        )
    ):
        return "market_environment"
    return "exit"


def _prompt(label: str, *, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value if value else default


def _prompt_symbols(*, required: bool) -> list[str]:
    while True:
        value = _prompt("ティッカー 例: AAPL, AMD または @C:\\path\\universe.csv", default="")
        if value.startswith("@"):
            symbols = _read_symbol_file(Path(value[1:]))
        else:
            symbols = _parse_symbols(value)
        if symbols or not required:
            return symbols
        print("少なくとも1銘柄を入力してください。")


def _prompt_yes_no(label: str, *, default: bool) -> bool:
    default_text = "Y/n" if default else "y/N"
    value = input(f"{label} [{default_text}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "1", "true", "はい"}


def _confirm(title: str, *, symbols: list[str], as_of: str) -> bool:
    print("")
    print(title)
    print(f"- symbols: {', '.join(symbols)}")
    print(f"- as_of: {as_of}")
    return _prompt_yes_no("実行しますか", default=True)


def _resolve_project_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def _stock_card_folder_name(documents: list[StockCardDocument], as_of_date: str | pd.Timestamp | None) -> str:
    if documents:
        return max(document.end_date for document in documents).strftime("%Y%m%d")
    if as_of_date:
        return pd.Timestamp(pd.to_datetime(as_of_date, errors="coerce")).strftime("%Y%m%d")
    return pd.Timestamp.today().strftime("%Y%m%d")


def _normalized_date(value: str | pd.Timestamp | None) -> pd.Timestamp | None:
    if value in (None, ""):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    stamp = pd.Timestamp(parsed)
    if stamp.tzinfo is not None:
        stamp = stamp.tz_localize(None)
    return stamp.normalize()


def _date_text(value: str | pd.Timestamp | None) -> str | None:
    parsed = _normalized_date(value)
    return None if parsed is None else parsed.strftime("%Y-%m-%d")


def _date_key_from_market_result(result) -> str:
    if result.trade_date is not None and pd.notna(result.trade_date):
        return pd.Timestamp(result.trade_date).strftime("%Y%m%d")
    return pd.Timestamp.today().strftime("%Y%m%d")


def _output_stem(date_key: str, mode: object) -> str | None:
    normalized = str(mode or "daily_history").strip().lower()
    if normalized == "latest_only":
        return "latest"
    if normalized == "daily_history":
        return date_key
    if normalized in {"on_demand", "disabled"}:
        return None
    return date_key


def _recent_market_summaries(context: CliContext, date_key: str, *, limit: int = 25) -> list[dict[str, object]]:
    summary_dir = context.service_output_dir / "market_report_input"
    if not summary_dir.exists():
        return []
    rows: list[tuple[str, dict[str, object]]] = []
    for path in summary_dir.glob("market_summary_*.json"):
        key = path.stem.replace("market_summary_", "", 1)
        if key >= date_key:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            rows.append((key, payload))
    rows.sort(key=lambda item: item[0])
    return [payload for _, payload in rows[-limit:]]


def _enrich_index_absorb_inputs(
    context: CliContext,
    summary: dict[str, object],
    trade_date: object,
    symbols: tuple[str, ...] = ("SPY", "QQQ"),
) -> None:
    index_context = summary.setdefault("index_context_summary", {})
    if not isinstance(index_context, dict):
        return
    service = PriceDataService.from_config(context.config_path)
    end_date = _date_text(trade_date)
    for symbol in symbols:
        history = service.load_range(symbol, end_date=end_date)
        values = _index_absorb_values(history)
        for key, value in values.items():
            index_context[f"{symbol} {key}"] = value
        index_state = summary.get("index_state_summary")
        if isinstance(index_state, dict) and "DISTRIBUTION DAY COUNT" in values:
            index_state[f"{symbol} DISTRIBUTION DAY COUNT"] = values["DISTRIBUTION DAY COUNT"]


def _index_absorb_values(history: pd.DataFrame) -> dict[str, object]:
    if history is None or history.empty or len(history) < 2:
        return {}
    frame = history.copy().sort_index()
    close = pd.to_numeric(frame["close"], errors="coerce")
    high = pd.to_numeric(frame["high"], errors="coerce")
    volume = pd.to_numeric(frame["volume"], errors="coerce")
    daily_return = close.pct_change(fill_method=None) * 100.0
    previous_volume = volume.shift(1)
    distribution = (daily_return <= -0.2) & (volume > previous_volume)
    accumulation = (daily_return >= 0.2) & (volume > previous_volume)
    recent = frame.tail(10).index
    dd_window = distribution.fillna(False).tail(25)
    latest_close = close.iloc[-1]
    ema21 = close.ewm(span=21, adjust=False, min_periods=1).mean().iloc[-1]
    last_dd_indices = distribution[distribution.fillna(False)].index
    higher_high_after_last_dd: float | None = None
    if len(last_dd_indices) > 0:
        last_dd = last_dd_indices[-1]
        future_high = high.loc[high.index > last_dd]
        dd_high = high.loc[last_dd]
        if pd.notna(dd_high):
            higher_high_after_last_dd = 1.0 if not future_high.empty and bool((future_high > dd_high).any()) else 0.0
    return {
        "PRICE DATE": frame.index[-1].strftime("%Y-%m-%d") if hasattr(frame.index[-1], "strftime") else str(frame.index[-1]),
        "HIGH": _float_or_none(high.iloc[-1]),
        "VOLUME": _float_or_none(volume.iloc[-1]),
        "PREVIOUS VOLUME": _float_or_none(previous_volume.iloc[-1]),
        "DISTRIBUTION DAY FLAG": 1.0 if bool(distribution.iloc[-1]) else 0.0,
        "DISTRIBUTION DAY COUNT": float(dd_window.sum()),
        "ACC DAYS 10D": float(accumulation.loc[recent].sum()),
        "DIST DAYS 10D": float(distribution.loc[recent].sum()),
        "CLOSE ABOVE 21EMA FLAG": 1.0 if pd.notna(latest_close) and pd.notna(ema21) and latest_close > ema21 else 0.0,
        "HIGHER HIGH AFTER LAST DD FLAG": higher_high_after_last_dd,
    }


def _market_summary_payload(result) -> dict[str, object]:
    market = result.market_result
    radar = result.radar_result
    return _jsonable(
        {
            "trade_date": market.trade_date,
            "score": market.score,
            "label": market.label,
            "score_1d_ago": market.score_1d_ago,
            "score_1w_ago": market.score_1w_ago,
            "score_1m_ago": market.score_1m_ago,
            "score_3m_ago": market.score_3m_ago,
            "label_1d_ago": getattr(market, "label_1d_ago", None),
            "label_1w_ago": getattr(market, "label_1w_ago", None),
            "label_1m_ago": getattr(market, "label_1m_ago", None),
            "label_3m_ago": getattr(market, "label_3m_ago", None),
            "component_scores": getattr(market, "component_scores", {}),
            "breadth_summary": getattr(market, "breadth_summary", {}),
            "breadth_momentum_summary": getattr(market, "breadth_momentum_summary", {}),
            "breadth_internal_summary": getattr(market, "breadth_internal_summary", {}),
            "participation_summary": getattr(market, "participation_summary", {}),
            "metric_deltas": getattr(market, "metric_deltas", {}),
            "performance_overview": getattr(market, "performance_overview", {}),
            "high_vix_summary": getattr(market, "high_vix_summary", {}),
            "risk_on_ratio_summary": getattr(market, "risk_on_ratio_summary", {}),
            "volatility_term_structure": getattr(market, "volatility_term_structure", {}),
            "credit_risk_proxy": getattr(market, "credit_risk_proxy", {}),
            "index_state_summary": getattr(market, "index_state_summary", {}),
            "drawdown_summary": getattr(market, "drawdown_summary", {}),
            "index_context_summary": getattr(market, "index_context_summary", {}),
            "vix_close": getattr(market, "vix_close", None),
            "update_time": getattr(market, "update_time", None),
            "market_snapshot": _frame_to_records(getattr(market, "market_snapshot", pd.DataFrame())),
            "leadership_snapshot": _frame_to_records(getattr(market, "leadership_snapshot", pd.DataFrame())),
            "external_snapshot": _frame_to_records(getattr(market, "external_snapshot", pd.DataFrame())),
            "factors_vs_sp500": _frame_to_records(getattr(market, "factors_vs_sp500", pd.DataFrame())),
            "sector_relative_strength": _frame_to_records(getattr(market, "sector_relative_strength", pd.DataFrame())),
            "style_pair_summary": _frame_to_records(getattr(market, "style_pair_summary", pd.DataFrame())),
            "defensive_cyclical_summary": getattr(market, "defensive_cyclical_summary", {}),
            "sector_leaders": _frame_to_records(getattr(radar, "sector_leaders", pd.DataFrame())),
            "industry_leaders": _frame_to_records(getattr(radar, "industry_leaders", pd.DataFrame())),
        }
    )


def _frame_to_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return []
    normalized = frame.copy()
    for column in normalized.columns:
        if pd.api.types.is_datetime64_any_dtype(normalized[column]):
            normalized[column] = normalized[column].astype(str)
    return normalized.to_dict(orient="records")


def _float_or_none(value: object) -> float | None:
    number = pd.to_numeric(value, errors="coerce")
    return float(number) if pd.notna(number) else None


def _jsonable(value):
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value.isoformat()
    try:
        import numpy as np

        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return None if np.isnan(value) else float(value)
    except Exception:
        pass
    if isinstance(value, float) and pd.isna(value):
        return None
    return value


def _print_price_summary(histories: dict[str, pd.DataFrame], statuses: dict[str, object]) -> None:
    print(f"Price histories: {len(histories)}")
    for symbol in sorted(set(histories) | set(statuses)):
        history = histories.get(symbol, pd.DataFrame())
        status = statuses.get(symbol)
        source = getattr(status, "source", "unknown")
        note = getattr(status, "note", "") or ""
        if history.empty:
            print(f"- {symbol}: missing ({note})")
        else:
            print(f"- {symbol}: {len(history)} rows, {history.index.min().date()} -> {history.index.max().date()} [{source}]")


def _print_records(title: str, records: list[ModuleOutputRecord]) -> None:
    print(title + ":")
    if not records:
        print("- no files written")
        return
    for record in records:
        print(f"- {record.module} {record.date_key}: {record.path}")


def _print_missing(missing: dict[str, str]) -> None:
    print("Missing:")
    for symbol, reason in missing.items():
        print(f"- {symbol}: {reason}")


if __name__ == "__main__":
    raise SystemExit(main())
