from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from src.utils import percent_rank


@dataclass(slots=True)
class RadarUniverseItem:
    ticker: str
    name: str
    major_stocks: tuple[str, ...] = ()

    @classmethod
    def from_payload(cls, payload: object) -> "RadarUniverseItem":
        if isinstance(payload, str):
            ticker = payload.strip().upper()
            return cls(ticker=ticker, name=ticker)
        if not isinstance(payload, dict):
            raise TypeError(f"Unsupported radar item payload: {type(payload)!r}")
        ticker = str(payload.get("ticker", "")).strip().upper()
        name = str(payload.get("name", ticker)).strip() or ticker
        major_raw = payload.get("major_stocks", [])
        major_stocks = tuple(str(value).strip().upper() for value in major_raw if str(value).strip())
        return cls(ticker=ticker, name=name, major_stocks=major_stocks)


@dataclass(slots=True)
class RadarConfig:
    sector_etfs: tuple[RadarUniverseItem, ...] = (
        RadarUniverseItem("QQQ", "Nasdaq 100"),
        RadarUniverseItem("QQQE", "Nasdaq 100 Equal Weight"),
        RadarUniverseItem("RSP", "S&P 500 Equal Weight"),
        RadarUniverseItem("DIA", "Dow Jones"),
        RadarUniverseItem("IWM", "Russell 2000"),
        RadarUniverseItem("XLV", "Health Care"),
        RadarUniverseItem("XLE", "Energy"),
        RadarUniverseItem("XLF", "Financials"),
        RadarUniverseItem("XLRE", "Real Estate"),
        RadarUniverseItem("XLB", "Materials"),
        RadarUniverseItem("XLP", "Consumer Staples"),
        RadarUniverseItem("XLU", "Utilities"),
        RadarUniverseItem("XLY", "Consumer Discretionary"),
        RadarUniverseItem("XLK", "Technology"),
        RadarUniverseItem("XLC", "Communication Services"),
        RadarUniverseItem("XLI", "Industrials"),
    )
    industry_etfs: tuple[RadarUniverseItem, ...] = (
        RadarUniverseItem("SLX", "Steel"),
        RadarUniverseItem("IBB", "Biotechnology"),
        RadarUniverseItem("KRE", "Regional Bank"),
        RadarUniverseItem("XBI", "Biotech"),
        RadarUniverseItem("PEJ", "Leisure"),
        RadarUniverseItem("LIT", "Lithium"),
        RadarUniverseItem("UFO", "Space"),
        RadarUniverseItem("JETS", "Global Jets"),
        RadarUniverseItem("SMH", "Semiconductor"),
        RadarUniverseItem("IYT", "Transportation"),
        RadarUniverseItem("MOO", "Agribusiness"),
        RadarUniverseItem("KARS", "Electric Cars"),
        RadarUniverseItem("TAN", "Solar"),
        RadarUniverseItem("WOOD", "Timber"),
        RadarUniverseItem("COPX", "Copper Miners"),
        RadarUniverseItem("QTUM", "Quantum-Tech"),
        RadarUniverseItem("URA", "Uranium"),
        RadarUniverseItem("IAI", "Broker-Dealers"),
        RadarUniverseItem("ICLN", "Clean Energy"),
        RadarUniverseItem("XOP", "Oil & Gas Exp."),
        RadarUniverseItem("GDX", "Gold Miners"),
        RadarUniverseItem("XRT", "Retail"),
        RadarUniverseItem("SIL", "Silver Miners"),
        RadarUniverseItem("IPO", "IPO"),
        RadarUniverseItem("REMX", "Rare Earth"),
        RadarUniverseItem("KIE", "Insurance"),
        RadarUniverseItem("ITA", "Aerospace"),
        RadarUniverseItem("CIBR", "Cybersecurity"),
        RadarUniverseItem("ITB", "Home Construction"),
        RadarUniverseItem("BLOK", "Blockchain"),
        RadarUniverseItem("WGMI", "Bitcoin Miners"),
        RadarUniverseItem("IGV", "Tech-Software"),
        RadarUniverseItem("KWEB", "China Internet"),
        RadarUniverseItem("IPAY", "Mobile Payments"),
        RadarUniverseItem("IHI", "Med. Devices"),
        RadarUniverseItem("FINX", "FinTech"),
    )
    top_movers_count: int = 3
    overall_rs_weights: tuple[float, float, float] = (1.0, 2.0, 2.0)
    near_high_threshold_pct: float = 0.5

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "RadarConfig":
        sector_payload = payload.get("sector_etfs", [])
        industry_payload = payload.get("industry_etfs", [])
        sector_items = tuple(RadarUniverseItem.from_payload(item) for item in sector_payload) if sector_payload else cls.__dataclass_fields__["sector_etfs"].default
        industry_items = tuple(RadarUniverseItem.from_payload(item) for item in industry_payload) if industry_payload else cls.__dataclass_fields__["industry_etfs"].default
        weights_raw = payload.get("overall_rs_weights", [1.0, 2.0, 2.0])
        weights = tuple(float(value) for value in weights_raw)
        if len(weights) != 3:
            weights = (1.0, 2.0, 2.0)
        return cls(
            sector_etfs=sector_items,
            industry_etfs=industry_items,
            top_movers_count=int(payload.get("top_movers_count", 3)),
            overall_rs_weights=(weights[0], weights[1], weights[2]),
            near_high_threshold_pct=float(payload.get("near_high_threshold_pct", 0.5)),
        )


@dataclass(slots=True)
class RadarResult:
    sector_leaders: pd.DataFrame
    industry_leaders: pd.DataFrame
    top_daily: pd.DataFrame
    top_weekly: pd.DataFrame
    update_time: str


class RadarViewModelBuilder:
    """Build an ETF-based RS Radar from configured sector and industry universes."""

    def __init__(self, config: RadarConfig | None = None) -> None:
        self.config = config or RadarConfig()

    def required_symbols(self) -> list[str]:
        symbols = [item.ticker for item in [*self.config.sector_etfs, *self.config.industry_etfs] if item.ticker]
        return list(dict.fromkeys(symbols))

    def build(self, etf_histories: dict[str, pd.DataFrame], benchmark_history: pd.DataFrame) -> RadarResult:
        universe = self._build_universe_frame(etf_histories, benchmark_history)
        if universe.empty:
            empty = pd.DataFrame()
            return RadarResult(
                sector_leaders=empty,
                industry_leaders=empty,
                top_daily=empty,
                top_weekly=empty,
                update_time=datetime.now().isoformat(timespec="seconds"),
            )

        sector_leaders = self._build_leader_table(universe, self.config.sector_etfs, include_major_stocks=False)
        industry_leaders = self._build_leader_table(universe, self.config.industry_etfs, include_major_stocks=True)
        top_daily = self._build_top_movers(universe, metric_column="RS DAY%", perf_column="DAY %")
        top_weekly = self._build_top_movers(universe, metric_column="RS WK%", perf_column="WK %")
        return RadarResult(
            sector_leaders=sector_leaders,
            industry_leaders=industry_leaders,
            top_daily=top_daily,
            top_weekly=top_weekly,
            update_time=datetime.now().isoformat(timespec="seconds"),
        )

    def _build_universe_frame(self, etf_histories: dict[str, pd.DataFrame], benchmark_history: pd.DataFrame) -> pd.DataFrame:
        if benchmark_history.empty or "close" not in benchmark_history.columns:
            return pd.DataFrame()

        benchmark_close = benchmark_history["close"].sort_index().astype(float)
        benchmark_day = self._pct_change(benchmark_close, 1)
        benchmark_week = self._pct_change(benchmark_close, 5)
        benchmark_month = self._pct_change(benchmark_close, 21)

        records: list[dict[str, object]] = []
        items = {item.ticker: item for item in [*self.config.sector_etfs, *self.config.industry_etfs]}
        for ticker, item in items.items():
            history = etf_histories.get(ticker)
            if history is None or history.empty or "close" not in history.columns:
                continue

            close = history["close"].dropna().astype(float)
            if close.empty:
                continue

            day_pct = self._pct_change(close, 1)
            week_pct = self._pct_change(close, 5)
            month_pct = self._pct_change(close, 21)
            rs_day_pct = day_pct - benchmark_day if pd.notna(day_pct) and pd.notna(benchmark_day) else np.nan
            rs_week_pct = week_pct - benchmark_week if pd.notna(week_pct) and pd.notna(benchmark_week) else np.nan
            rs_month_pct = month_pct - benchmark_month if pd.notna(month_pct) and pd.notna(benchmark_month) else np.nan

            high_source = history["high"].dropna().astype(float) if "high" in history.columns else close
            rolling_high = high_source.rolling(252).max().iloc[-1] if len(high_source) >= 1 else np.nan
            price = float(close.iloc[-1])
            high_label = self._format_high_label(price, rolling_high)

            records.append(
                {
                    "ticker": ticker,
                    "NAME": item.name,
                    "PRICE": price,
                    "DAY %": day_pct,
                    "WK %": week_pct,
                    "MTH %": month_pct,
                    "RS DAY%": rs_day_pct,
                    "RS WK%": rs_week_pct,
                    "RS MTH%": rs_month_pct,
                    "52W HIGH": high_label,
                    "MAJOR STOCKS": ", ".join(item.major_stocks),
                }
            )

        frame = pd.DataFrame(records)
        if frame.empty:
            return frame

        frame = frame.set_index("ticker")
        frame["1D"] = percent_rank(frame["RS DAY%"])
        frame["1W"] = percent_rank(frame["RS WK%"])
        frame["1M"] = percent_rank(frame["RS MTH%"])
        frame["RS"] = frame[["1D", "1W", "1M"]].apply(
            lambda row: self._weighted_average(row.to_list(), self.config.overall_rs_weights),
            axis=1,
        )
        return frame.sort_values(["RS", "1W", "1D"], ascending=[False, False, False])

    def _build_leader_table(
        self,
        universe: pd.DataFrame,
        items: tuple[RadarUniverseItem, ...],
        include_major_stocks: bool,
    ) -> pd.DataFrame:
        tickers = [item.ticker for item in items]
        frame = universe.loc[universe.index.intersection(tickers)].copy()
        if frame.empty:
            return pd.DataFrame()

        display = frame.reset_index(names="TICKER")
        columns = ["RS", "1D", "1W", "1M", "TICKER", "NAME", "DAY %", "WK %", "MTH %", "RS DAY%", "RS WK%", "RS MTH%", "52W HIGH"]
        if include_major_stocks:
            columns.append("MAJOR STOCKS")
        display = display[columns].copy()
        for column in ["RS", "1D", "1W", "1M", "PRICE", "DAY %", "WK %", "MTH %", "RS DAY%", "RS WK%", "RS MTH%"]:
            if column in display.columns:
                display[column] = display[column].round(2)
        if not include_major_stocks and "MAJOR STOCKS" in display.columns:
            display = display.drop(columns=["MAJOR STOCKS"])
        return display.reset_index(drop=True)

    def _build_top_movers(self, universe: pd.DataFrame, metric_column: str, perf_column: str) -> pd.DataFrame:
        if universe.empty or metric_column not in universe.columns:
            return pd.DataFrame()

        display = universe.sort_values([metric_column, "RS"], ascending=[False, False]).head(self.config.top_movers_count)
        if display.empty:
            return pd.DataFrame()

        display = display.reset_index(names="TICKER")
        columns = ["RS", "TICKER", "NAME", "PRICE", perf_column, metric_column]
        display = display[columns].copy()
        for column in ["RS", "PRICE", perf_column, metric_column]:
            display[column] = display[column].round(2)
        return display.reset_index(drop=True)

    def _pct_change(self, series: pd.Series, periods: int) -> float:
        if len(series) <= periods:
            return float("nan")
        value = series.pct_change(periods, fill_method=None).iloc[-1] * 100.0
        return float(value) if pd.notna(value) else float("nan")

    def _weighted_average(self, values: list[float], weights: tuple[float, float, float]) -> float:
        values_array = np.asarray(values, dtype=float)
        weights_array = np.asarray(weights, dtype=float)
        valid_mask = ~np.isnan(values_array)
        if not valid_mask.any():
            return float("nan")
        return float(np.average(values_array[valid_mask], weights=weights_array[valid_mask]))

    def _format_high_label(self, price: float, rolling_high: float) -> str:
        if pd.isna(rolling_high) or rolling_high <= 0:
            return ""
        threshold = rolling_high * (1.0 - self.config.near_high_threshold_pct / 100.0)
        if price >= threshold:
            return "Yes"
        off_pct = (price / rolling_high - 1.0) * 100.0
        return f"{off_pct:.1f}%"


class GroupStrengthAggregator(RadarViewModelBuilder):
    """Docs-facing alias for the ETF-based RS radar aggregator."""

    pass
