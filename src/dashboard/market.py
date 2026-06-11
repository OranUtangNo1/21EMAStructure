from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd


@dataclass(slots=True)
class MarketUniverseItem:
    ticker: str
    name: str

    @classmethod
    def from_payload(cls, payload: object) -> "MarketUniverseItem":
        if isinstance(payload, str):
            ticker = payload.strip().upper()
            return cls(ticker=ticker, name=ticker)
        if not isinstance(payload, dict):
            raise TypeError(f"Unsupported market universe payload: {type(payload)!r}")
        ticker = str(payload.get("ticker", "")).strip().upper()
        name = str(payload.get("name", ticker)).strip() or ticker
        return cls(ticker=ticker, name=name)


DEFAULT_MARKET_CONDITION_ETFS = (
    MarketUniverseItem("SPY", "S&P 500"),
    MarketUniverseItem("QQQ", "Nasdaq 100"),
    MarketUniverseItem("DIA", "Dow Jones"),
    MarketUniverseItem("IWM", "Russell 2000"),
    MarketUniverseItem("RSP", "S&P 500 Equal Weight"),
    MarketUniverseItem("QQQE", "Nasdaq 100 Equal Weight"),
    MarketUniverseItem("MDY", "S&P MidCap 400"),
    MarketUniverseItem("IJR", "S&P SmallCap 600"),
    MarketUniverseItem("XLB", "Materials"),
    MarketUniverseItem("XLC", "Communication Services"),
    MarketUniverseItem("XLE", "Energy"),
    MarketUniverseItem("XLF", "Financials"),
    MarketUniverseItem("XLI", "Industrials"),
    MarketUniverseItem("XLK", "Technology"),
    MarketUniverseItem("XLP", "Consumer Staples"),
    MarketUniverseItem("XLRE", "Real Estate"),
    MarketUniverseItem("XLU", "Utilities"),
    MarketUniverseItem("XLV", "Health Care"),
    MarketUniverseItem("XLY", "Consumer Discretionary"),
)

DEFAULT_EXTERNAL_ETFS = (
    MarketUniverseItem("EEM", "Emerging Markets"),
    MarketUniverseItem("FXI", "China Large Cap"),
    MarketUniverseItem("KWEB", "China Internet"),
)

DEFAULT_FACTOR_ETFS = (
    MarketUniverseItem("VUG", "Growth"),
    MarketUniverseItem("VTV", "Value"),
    MarketUniverseItem("VYM", "High Dividend"),
    MarketUniverseItem("MGC", "Large Cap"),
    MarketUniverseItem("VO", "Mid Cap"),
    MarketUniverseItem("VB", "Small Cap"),
    MarketUniverseItem("MTUM", "Momentum"),
)

SECTOR_ROTATION_TICKERS = frozenset({"XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"})
DEFENSIVE_SECTOR_TICKERS = ("XLP", "XLU", "XLV")
CYCLICAL_GROWTH_SECTOR_TICKERS = ("XLC", "XLE", "XLF", "XLI", "XLK", "XLY")
STYLE_RATIO_PAIRS = (
    ("VUG", "VTV", "Growth vs Value"),
    ("MTUM", "SPY", "Momentum vs Market"),
    ("VB", "MGC", "Small vs Large"),
    ("VO", "MGC", "Mid vs Large"),
    ("VYM", "SPY", "Dividend vs Market"),
)

DEFAULT_COMPONENT_WEIGHTS = {
    "pct_above_sma20": 0.12,
    "pct_above_sma50": 0.14,
    "pct_above_sma200": 0.14,
    "pct_sma50_gt_sma200": 0.08,
    "pct_positive_1m": 0.09,
    "pct_positive_3m": 0.08,
    "pct_2w_high": 0.05,
    "safe_haven_score": 0.15,
    "vix_score": 0.15,
}

VALID_MARKET_CALCULATION_MODES = frozenset({"etf", "active_symbols", "blended"})
DEFAULT_MARKET_CALCULATION_MODE = "etf"


@dataclass(slots=True)
class MarketConditionConfig:
    """Configurable scoring model for the market dashboard."""

    condition_etfs: tuple[MarketUniverseItem, ...] = field(default_factory=lambda: DEFAULT_MARKET_CONDITION_ETFS)
    leadership_etfs: tuple[MarketUniverseItem, ...] = ()
    external_etfs: tuple[MarketUniverseItem, ...] = field(default_factory=lambda: DEFAULT_EXTERNAL_ETFS)
    factor_etfs: tuple[MarketUniverseItem, ...] = field(default_factory=lambda: DEFAULT_FACTOR_ETFS)
    component_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_COMPONENT_WEIGHTS))
    calculation_mode: str = DEFAULT_MARKET_CALCULATION_MODE
    etf_weight: float = 0.5
    active_symbols_weight: float = 0.5
    bullish_threshold: float = 80.0
    positive_threshold: float = 60.0
    neutral_threshold: float = 40.0
    negative_threshold: float = 20.0
    vix_neutral_level: float = 17.0
    vix_score_slope: float = 5.0
    safe_haven_risk_on_symbol: str = "SPY"
    safe_haven_risk_off_symbol: str = "TLT"
    safe_haven_window: int = 20
    safe_haven_score_scale: float = 4.0
    risk_on_ratio_numerator_symbol: str = "IWO"
    risk_on_ratio_denominator_symbol: str = "IWN"
    risk_on_ratio_high_window: int = 756
    risk_on_ratio_ma_windows: tuple[int, ...] = (20, 50, 200)
    vix9d_symbol: str = "^VIX9D"
    vix3m_symbol: str = "^VIX3M"
    credit_high_yield_symbol: str = "HYG"
    credit_investment_grade_symbol: str = "LQD"
    credit_treasury_symbol: str = "IEF"
    credit_high_yield_oas_symbol: str = "BAMLH0A0HYM2"
    drawdown_window: int = 252
    index_state_symbols: tuple[str, ...] = ("SPY", "QQQ")
    index_state_rally_low_lookback: int = 25
    index_state_ftd_min_gain_pct: float = 1.7
    index_state_ftd_min_rally_day: int = 4
    index_state_distribution_decline_pct: float = -0.2
    index_state_distribution_lookback: int = 25
    index_state_distribution_pressure_count: int = 5

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "MarketConditionConfig":
        condition_payload = payload.get("market_condition_etf_universe", payload.get("condition_etfs", []))
        leadership_payload = payload.get("leadership_etfs", [])
        external_payload = payload.get("external_etfs", [])
        factor_payload = payload.get("factor_etfs", [])
        condition_items = tuple(MarketUniverseItem.from_payload(item) for item in condition_payload) if condition_payload else DEFAULT_MARKET_CONDITION_ETFS
        leadership_items = tuple(MarketUniverseItem.from_payload(item) for item in leadership_payload) if leadership_payload else ()
        external_items = tuple(MarketUniverseItem.from_payload(item) for item in external_payload) if external_payload else DEFAULT_EXTERNAL_ETFS
        factor_items = tuple(MarketUniverseItem.from_payload(item) for item in factor_payload) if factor_payload else DEFAULT_FACTOR_ETFS
        component_weights = dict(DEFAULT_COMPONENT_WEIGHTS)
        component_weights.update({str(key): float(value) for key, value in dict(payload.get("component_weights", {})).items()})
        calculation_mode = str(payload.get("calculation_mode", DEFAULT_MARKET_CALCULATION_MODE)).strip().lower() or DEFAULT_MARKET_CALCULATION_MODE
        if calculation_mode not in VALID_MARKET_CALCULATION_MODES:
            raise ValueError(
                f"Unsupported market calculation_mode: {calculation_mode!r}. Expected one of {sorted(VALID_MARKET_CALCULATION_MODES)!r}."
            )
        etf_weight = float(payload.get("etf_weight", 0.5))
        active_symbols_weight = float(payload.get("active_symbols_weight", 0.5))
        if etf_weight < 0 or active_symbols_weight < 0:
            raise ValueError("Market blend weights must be non-negative.")
        if calculation_mode == "blended" and (etf_weight + active_symbols_weight) <= 0:
            raise ValueError("Blended market calculation_mode requires a positive total weight.")
        risk_on_ratio_ma_windows_raw = payload.get("risk_on_ratio_ma_windows", [20, 50, 200])
        risk_on_ratio_ma_windows = tuple(
            int(value)
            for value in risk_on_ratio_ma_windows_raw
            if int(value) > 0
        )
        if not risk_on_ratio_ma_windows:
            risk_on_ratio_ma_windows = (20, 50, 200)
        auxiliary_payload = payload.get("market_auxiliary_symbols", {})
        auxiliary = auxiliary_payload if isinstance(auxiliary_payload, dict) else {}
        index_state_payload = payload.get("index_state", {})
        index_state = index_state_payload if isinstance(index_state_payload, dict) else {}
        index_symbols_raw = index_state.get("symbols", payload.get("index_state_symbols", ["SPY", "QQQ"]))
        if isinstance(index_symbols_raw, str):
            index_symbols_iterable = [index_symbols_raw]
        else:
            index_symbols_iterable = index_symbols_raw
        index_state_symbols = tuple(
            str(symbol).strip().upper()
            for symbol in index_symbols_iterable
            if str(symbol).strip()
        )
        if not index_state_symbols:
            index_state_symbols = ("SPY", "QQQ")
        return cls(
            condition_etfs=condition_items,
            leadership_etfs=leadership_items,
            external_etfs=external_items,
            factor_etfs=factor_items,
            component_weights=component_weights,
            calculation_mode=calculation_mode,
            etf_weight=etf_weight,
            active_symbols_weight=active_symbols_weight,
            bullish_threshold=float(payload.get("bullish_threshold", 80.0)),
            positive_threshold=float(payload.get("positive_threshold", 60.0)),
            neutral_threshold=float(payload.get("neutral_threshold", 40.0)),
            negative_threshold=float(payload.get("negative_threshold", 20.0)),
            vix_neutral_level=float(payload.get("vix_neutral_level", 17.0)),
            vix_score_slope=float(payload.get("vix_score_slope", 5.0)),
            safe_haven_risk_on_symbol=str(payload.get("safe_haven_risk_on_symbol", "SPY")).strip().upper() or "SPY",
            safe_haven_risk_off_symbol=str(payload.get("safe_haven_risk_off_symbol", "TLT")).strip().upper() or "TLT",
            safe_haven_window=int(payload.get("safe_haven_window", 20)),
            safe_haven_score_scale=float(payload.get("safe_haven_score_scale", 4.0)),
            risk_on_ratio_numerator_symbol=str(payload.get("risk_on_ratio_numerator_symbol", "IWO")).strip().upper() or "IWO",
            risk_on_ratio_denominator_symbol=str(payload.get("risk_on_ratio_denominator_symbol", "IWN")).strip().upper() or "IWN",
            risk_on_ratio_high_window=int(payload.get("risk_on_ratio_high_window", 756)),
            risk_on_ratio_ma_windows=risk_on_ratio_ma_windows,
            vix9d_symbol=str(auxiliary.get("vix9d_symbol", payload.get("vix9d_symbol", "^VIX9D"))).strip().upper() or "^VIX9D",
            vix3m_symbol=str(auxiliary.get("vix3m_symbol", payload.get("vix3m_symbol", "^VIX3M"))).strip().upper() or "^VIX3M",
            credit_high_yield_symbol=str(auxiliary.get("credit_high_yield_symbol", payload.get("credit_high_yield_symbol", "HYG"))).strip().upper() or "HYG",
            credit_investment_grade_symbol=str(auxiliary.get("credit_investment_grade_symbol", payload.get("credit_investment_grade_symbol", "LQD"))).strip().upper() or "LQD",
            credit_treasury_symbol=str(auxiliary.get("credit_treasury_symbol", payload.get("credit_treasury_symbol", "IEF"))).strip().upper() or "IEF",
            credit_high_yield_oas_symbol=str(auxiliary.get("credit_high_yield_oas_symbol", payload.get("credit_high_yield_oas_symbol", "BAMLH0A0HYM2"))).strip().upper() or "BAMLH0A0HYM2",
            drawdown_window=int(payload.get("drawdown_window", 252)),
            index_state_symbols=index_state_symbols,
            index_state_rally_low_lookback=int(index_state.get("rally_low_lookback", payload.get("index_state_rally_low_lookback", 25))),
            index_state_ftd_min_gain_pct=float(index_state.get("ftd_min_gain_pct", payload.get("index_state_ftd_min_gain_pct", 1.7))),
            index_state_ftd_min_rally_day=int(index_state.get("ftd_min_rally_day", payload.get("index_state_ftd_min_rally_day", 4))),
            index_state_distribution_decline_pct=float(index_state.get("distribution_decline_pct", payload.get("index_state_distribution_decline_pct", -0.2))),
            index_state_distribution_lookback=int(index_state.get("distribution_lookback", payload.get("index_state_distribution_lookback", 25))),
            index_state_distribution_pressure_count=int(index_state.get("distribution_pressure_count", payload.get("index_state_distribution_pressure_count", 5))),
        )


@dataclass(slots=True)
class MarketConditionResult:
    """Summary object for the market dashboard page."""

    trade_date: pd.Timestamp | None
    score: float
    label: str
    score_1d_ago: float | None
    score_1w_ago: float | None
    score_1m_ago: float | None
    score_3m_ago: float | None
    label_1d_ago: str | None
    label_1w_ago: str | None
    label_1m_ago: str | None
    label_3m_ago: str | None
    component_scores: dict[str, float]
    breadth_summary: dict[str, float]
    breadth_momentum_summary: dict[str, float]
    breadth_internal_summary: dict[str, float]
    participation_summary: dict[str, float]
    metric_deltas: dict[str, dict[str, float]]
    performance_overview: dict[str, float]
    high_vix_summary: dict[str, float]
    risk_on_ratio_summary: dict[str, float]
    market_snapshot: pd.DataFrame
    leadership_snapshot: pd.DataFrame
    external_snapshot: pd.DataFrame
    factors_vs_sp500: pd.DataFrame
    s5th_series: pd.DataFrame
    vix_close: float | None
    update_time: str
    sector_relative_strength: pd.DataFrame = field(default_factory=pd.DataFrame)
    style_pair_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    defensive_cyclical_summary: dict[str, float] = field(default_factory=dict)
    volatility_term_structure: dict[str, float] = field(default_factory=dict)
    credit_risk_proxy: dict[str, float] = field(default_factory=dict)
    index_state_summary: dict[str, float] = field(default_factory=dict)
    drawdown_summary: dict[str, float] = field(default_factory=dict)


class MarketSnapshotBuilder:
    """Build the Market Snapshot panel rows."""

    def __init__(self, config: MarketConditionConfig) -> None:
        self.config = config

    def build(self, market_histories: dict[str, pd.DataFrame], items: tuple[MarketUniverseItem, ...]) -> pd.DataFrame:
        rows: list[dict[str, object]] = []
        for item in items:
            history = market_histories.get(item.ticker, pd.DataFrame())
            if history.empty or "close" not in history.columns:
                continue
            latest = history.iloc[-1]
            rows.append(
                {
                    "TICKER": item.ticker,
                    "NAME": item.name,
                    "PRICE": self._safe_float(latest.get("close")),
                    "DAY %": self._safe_float(latest.get("daily_change_pct")),
                    "VOL vs 50D %": self._volume_vs_50d_pct(latest),
                    "21EMA POS": self._ema_position_label(latest),
                }
            )

        frame = pd.DataFrame(rows)
        if frame.empty:
            return frame
        for column in ["PRICE", "DAY %", "VOL vs 50D %"]:
            if column in frame.columns:
                frame[column] = pd.to_numeric(frame[column], errors="coerce").round(2)
        return frame

    def _volume_vs_50d_pct(self, latest: pd.Series) -> float | None:
        rel_volume = latest.get("rel_volume")
        if pd.isna(rel_volume):
            return None
        return (float(rel_volume) - 1.0) * 100.0

    def _ema_position_label(self, latest: pd.Series) -> str:
        close = latest.get("close")
        ema_low = latest.get("ema21_low")
        ema_high = latest.get("ema21_high")
        if pd.isna(close) or pd.isna(ema_low) or pd.isna(ema_high):
            return "unknown"
        if float(close) < float(ema_low):
            return "below 21EMA Low"
        if float(close) > float(ema_high):
            return "above 21EMA High"
        return "inside 21EMA Cloud"

    def _safe_float(self, value: object) -> float | None:
        if value is None or pd.isna(value):
            return None
        return float(value)


class FactorRelativeStrengthCalculator:
    """Build Factors vs SP500 rows."""

    def __init__(self, config: MarketConditionConfig) -> None:
        self.config = config

    def build(self, market_histories: dict[str, pd.DataFrame], benchmark_history: pd.DataFrame) -> pd.DataFrame:
        if benchmark_history.empty or "close" not in benchmark_history.columns:
            return pd.DataFrame()
        benchmark_close = benchmark_history["close"].astype(float)
        rows: list[dict[str, object]] = []
        for item in self.config.factor_etfs:
            history = market_histories.get(item.ticker, pd.DataFrame())
            if history.empty or "close" not in history.columns:
                continue
            close = history["close"].astype(float)
            rows.append(
                {
                    "TICKER": item.ticker,
                    "NAME": item.name,
                    "REL 1W %": self._relative_return(close, benchmark_close, 5),
                    "REL 1M %": self._relative_return(close, benchmark_close, 21),
                    "REL 1Y %": self._relative_return(close, benchmark_close, 252),
                }
            )
        frame = pd.DataFrame(rows)
        if frame.empty:
            return frame
        for column in ["REL 1W %", "REL 1M %", "REL 1Y %"]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").round(2)
        return frame.sort_values(["REL 1M %", "REL 1W %"], ascending=[False, False]).reset_index(drop=True)

    def _relative_return(self, asset_close: pd.Series, benchmark_close: pd.Series, periods: int) -> float | None:
        aligned = pd.concat([asset_close, benchmark_close], axis=1, join="inner").dropna()
        if len(aligned) <= periods:
            return None
        asset_return = aligned.iloc[:, 0].pct_change(periods, fill_method=None).iloc[-1] * 100.0
        benchmark_return = aligned.iloc[:, 1].pct_change(periods, fill_method=None).iloc[-1] * 100.0
        if pd.isna(asset_return) or pd.isna(benchmark_return):
            return None
        return float(asset_return - benchmark_return)


class MarketConditionScorer:
    """Score the tape using a configurable ETF universe plus market context tables."""

    def __init__(self, config: MarketConditionConfig) -> None:
        self.config = config
        self.snapshot_builder = MarketSnapshotBuilder(config)
        self.factor_calculator = FactorRelativeStrengthCalculator(config)

    def required_symbols(self) -> list[str]:
        symbols = [
            item.ticker
            for item in [*self.config.condition_etfs, *self.config.external_etfs, *self.config.factor_etfs]
        ]
        symbols.extend(
            [
                "^VIX",
                self.config.safe_haven_risk_on_symbol,
                self.config.safe_haven_risk_off_symbol,
                self.config.risk_on_ratio_numerator_symbol,
                self.config.risk_on_ratio_denominator_symbol,
                self.config.vix9d_symbol,
                self.config.vix3m_symbol,
                self.config.credit_high_yield_symbol,
                self.config.credit_investment_grade_symbol,
                self.config.credit_treasury_symbol,
                *self.config.index_state_symbols,
            ]
        )
        return list(dict.fromkeys(symbols))

    def required_fred_series(self) -> list[str]:
        symbols = [self.config.credit_high_yield_oas_symbol]
        return list(dict.fromkeys(symbol for symbol in symbols if symbol))

    def score(
        self,
        stock_histories: dict[str, pd.DataFrame],
        market_histories: dict[str, pd.DataFrame],
        benchmark_history: pd.DataFrame,
    ) -> MarketConditionResult:
        if benchmark_history.empty or "close" not in benchmark_history.columns:
            return self._empty_result()

        latest_raw_components = self._raw_component_values_at_offset(stock_histories, market_histories, 0)
        latest_components = self._score_components(latest_raw_components, market_histories, 0)
        score = self._score_from_components(latest_components)
        score_1d_ago = self._rounded_score_at_offset(stock_histories, market_histories, 1)
        score_1w_ago = self._rounded_score_at_offset(stock_histories, market_histories, 5)
        score_1m_ago = self._rounded_score_at_offset(stock_histories, market_histories, 21)
        score_3m_ago = self._rounded_score_at_offset(stock_histories, market_histories, 63)
        performance_overview = self._performance_overview(benchmark_history)
        vix_history = market_histories.get("^VIX", pd.DataFrame())
        vix_close = self._latest_close(vix_history)
        market_snapshot = self.snapshot_builder.build(market_histories, self.config.condition_etfs)
        leadership_snapshot = pd.DataFrame()
        external_snapshot = self.snapshot_builder.build(market_histories, self.config.external_etfs)
        factors_vs_sp500 = self.factor_calculator.build(market_histories, benchmark_history)
        sector_relative_strength = pd.DataFrame()
        style_pair_summary = self._style_pair_summary(market_histories)
        defensive_cyclical_summary = self._defensive_cyclical_summary(market_histories)
        s5th_series = self._build_s5th_series(stock_histories)
        risk_on_ratio_summary = self._risk_on_ratio_summary(market_histories)
        volatility_term_structure = self._volatility_term_structure(market_histories)
        credit_risk_proxy = self._credit_risk_proxy(market_histories)
        index_state_summary = self._index_state_summary(market_histories, benchmark_history)
        metric_deltas = self._market_metric_deltas(stock_histories, market_histories)
        breadth_momentum_summary = self._breadth_momentum_summary(latest_raw_components, metric_deltas)
        breadth_internal_summary = self._breadth_internal_summary(stock_histories)
        drawdown_summary = self._drawdown_summary(market_histories, benchmark_history)

        return MarketConditionResult(
            trade_date=self._latest_trade_date(benchmark_history),
            score=round(score, 2),
            label=self._label(score),
            score_1d_ago=score_1d_ago,
            score_1w_ago=score_1w_ago,
            score_1m_ago=score_1m_ago,
            score_3m_ago=score_3m_ago,
            label_1d_ago=self._label_for_optional_score(score_1d_ago),
            label_1w_ago=self._label_for_optional_score(score_1w_ago),
            label_1m_ago=self._label_for_optional_score(score_1m_ago),
            label_3m_ago=self._label_for_optional_score(score_3m_ago),
            component_scores={key: round(value, 2) for key, value in latest_components.items()},
            breadth_summary={key: round(latest_raw_components[key], 2) for key in self._breadth_keys() if key in latest_raw_components},
            breadth_momentum_summary={key: round(value, 3) for key, value in breadth_momentum_summary.items()},
            breadth_internal_summary={key: round(value, 3) for key, value in breadth_internal_summary.items()},
            participation_summary={
                key: round(latest_raw_components[key], 2)
                for key in self._participation_keys()
                if key in latest_raw_components
            },
            metric_deltas=metric_deltas,
            performance_overview={key: round(value, 2) for key, value in performance_overview.items()},
            high_vix_summary={
                "S2W HIGH %": round(latest_raw_components.get("pct_2w_high", 0.0), 2),
                "VIX": round(vix_close, 2) if vix_close is not None else np.nan,
                "SAFE HAVEN %": round(self._safe_haven_spread(market_histories, 0), 2),
            },
            risk_on_ratio_summary={key: round(value, 3) for key, value in risk_on_ratio_summary.items()},
            volatility_term_structure={key: round(value, 3) for key, value in volatility_term_structure.items()},
            credit_risk_proxy={key: round(value, 3) for key, value in credit_risk_proxy.items()},
            index_state_summary={key: round(value, 3) for key, value in index_state_summary.items()},
            drawdown_summary={key: round(value, 3) for key, value in drawdown_summary.items()},
            market_snapshot=market_snapshot,
            leadership_snapshot=leadership_snapshot,
            external_snapshot=external_snapshot,
            factors_vs_sp500=factors_vs_sp500,
            s5th_series=s5th_series,
            vix_close=round(vix_close, 2) if vix_close is not None else None,
            update_time=datetime.now().isoformat(timespec="seconds"),
            sector_relative_strength=sector_relative_strength,
            style_pair_summary=style_pair_summary,
            defensive_cyclical_summary={key: round(value, 3) for key, value in defensive_cyclical_summary.items()},
        )

    def _empty_result(self) -> MarketConditionResult:
        empty = pd.DataFrame()
        return MarketConditionResult(
            trade_date=None,
            score=0.0,
            label="No Data",
            score_1d_ago=None,
            score_1w_ago=None,
            score_1m_ago=None,
            score_3m_ago=None,
            label_1d_ago=None,
            label_1w_ago=None,
            label_1m_ago=None,
            label_3m_ago=None,
            component_scores={},
            breadth_summary={},
            breadth_momentum_summary={},
            breadth_internal_summary={},
            participation_summary={},
            metric_deltas={},
            performance_overview={},
            high_vix_summary={},
            risk_on_ratio_summary={},
            volatility_term_structure={},
            credit_risk_proxy={},
            index_state_summary={},
            drawdown_summary={},
            market_snapshot=empty,
            leadership_snapshot=empty,
            external_snapshot=empty,
            factors_vs_sp500=empty,
            s5th_series=empty,
            vix_close=None,
            update_time=datetime.now().isoformat(timespec="seconds"),
            sector_relative_strength=empty,
            style_pair_summary=empty,
            defensive_cyclical_summary={},
        )

    def _raw_component_values_at_offset(
        self,
        stock_histories: dict[str, pd.DataFrame],
        market_histories: dict[str, pd.DataFrame],
        offset: int,
    ) -> dict[str, float]:
        etf_components, etf_count = self._raw_component_values_for_histories(
            [market_histories.get(item.ticker, pd.DataFrame()) for item in self.config.condition_etfs],
            offset,
        )
        active_components, active_count = self._raw_component_values_for_histories(
            list(stock_histories.values()),
            offset,
        )

        if self.config.calculation_mode == "etf":
            return etf_components
        if self.config.calculation_mode == "active_symbols":
            return active_components
        if etf_count == 0:
            return active_components
        if active_count == 0:
            return etf_components
        return self._blend_components(
            etf_components,
            active_components,
            self.config.etf_weight,
            self.config.active_symbols_weight,
        )

    def _raw_component_values_for_histories(
        self,
        histories: list[pd.DataFrame],
        offset: int,
    ) -> tuple[dict[str, float], int]:
        rows: list[dict[str, float]] = []
        for history in histories:
            feature_row = self._feature_row(history, offset)
            if feature_row is not None:
                rows.append(feature_row)
        frame = pd.DataFrame(rows)
        if frame.empty:
            return self._empty_components(), 0

        components = {
            "pct_above_sma10": float((frame["close"] >= frame["sma10"]).mean() * 100.0),
            "pct_above_sma20": float((frame["close"] >= frame["sma20"]).mean() * 100.0),
            "pct_above_sma50": float((frame["close"] >= frame["sma50"]).mean() * 100.0),
            "pct_above_sma200": float((frame["close"] >= frame["sma200"]).mean() * 100.0),
            "pct_sma20_gt_sma50": float((frame["sma20"] >= frame["sma50"]).mean() * 100.0),
            "pct_sma50_gt_sma200": float((frame["sma50"] >= frame["sma200"]).mean() * 100.0),
            "pct_positive_1w": float((frame["ret_1w"] > 0).mean() * 100.0),
            "pct_positive_1m": float((frame["ret_1m"] > 0).mean() * 100.0),
            "pct_positive_3m": float((frame["ret_3m"] > 0).mean() * 100.0),
            "pct_positive_1y": float((frame["ret_1y"] > 0).mean() * 100.0),
            "pct_positive_ytd": float((frame["ret_ytd"] > 0).mean() * 100.0),
            "pct_2w_high": float(frame["is_2w_high"].mean() * 100.0),
        }
        return components, len(rows)

    def _market_metric_values_at_offset(
        self,
        stock_histories: dict[str, pd.DataFrame],
        market_histories: dict[str, pd.DataFrame],
        offset: int,
    ) -> dict[str, float]:
        values = self._raw_component_values_at_offset(stock_histories, market_histories, offset)
        vix_score = self._vix_score(market_histories.get("^VIX", pd.DataFrame()), offset)
        safe_haven = self._safe_haven_spread(market_histories, offset)
        risk_on_ratio = self._risk_on_ratio_summary(market_histories, offset)
        volatility_term_structure = self._volatility_term_structure(market_histories, offset)
        credit_risk_proxy = self._credit_risk_proxy(market_histories, offset)
        breadth_internal_summary = self._breadth_internal_summary(stock_histories, offset)
        drawdown_summary = self._drawdown_summary(market_histories, pd.DataFrame(), offset)

        enriched = dict(values)
        vix_close = self._close_at_offset(market_histories.get("^VIX", pd.DataFrame()), offset)
        if vix_close is not None:
            enriched["VIX"] = vix_close
        enriched["SAFE HAVEN %"] = safe_haven
        enriched["vix_score"] = vix_score
        enriched["safe_haven_score"] = self._safe_haven_score(market_histories, offset)
        for key, value in risk_on_ratio.items():
            enriched[f"risk_on:{key}"] = value
        for key, value in volatility_term_structure.items():
            enriched[f"vix_term:{key}"] = value
        for key, value in credit_risk_proxy.items():
            enriched[f"credit:{key}"] = value
        for key, value in breadth_internal_summary.items():
            enriched[f"breadth_internal:{key}"] = value
        for key, value in drawdown_summary.items():
            enriched[f"drawdown:{key}"] = value
        return enriched

    def _market_metric_deltas(
        self,
        stock_histories: dict[str, pd.DataFrame],
        market_histories: dict[str, pd.DataFrame],
    ) -> dict[str, dict[str, float]]:
        current = self._market_metric_values_at_offset(stock_histories, market_histories, 0)
        offsets = {"1D": 1, "1W": 5, "2W": 10, "1M": 21}
        deltas: dict[str, dict[str, float]] = {}
        for label, offset in offsets.items():
            previous = self._market_metric_values_at_offset(stock_histories, market_histories, offset)
            for key, current_value in current.items():
                previous_value = previous.get(key)
                if not self._is_finite_number(current_value) or not self._is_finite_number(previous_value):
                    continue
                deltas.setdefault(key, {})[label] = round(float(current_value) - float(previous_value), 3)
        return deltas

    def _breadth_momentum_summary(
        self,
        raw_components: dict[str, float],
        metric_deltas: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        a20 = raw_components.get("pct_above_sma20")
        if not self._is_finite_number(a20):
            return {}
        deltas = metric_deltas.get("pct_above_sma20", {})
        summary: dict[str, float] = {"A20": float(a20)}
        for label, output_key in (
            ("1D", "A20 DELTA 1D"),
            ("1W", "A20 DELTA 5D"),
            ("2W", "A20 DELTA 10D"),
            ("1M", "A20 DELTA 21D"),
        ):
            value = deltas.get(label)
            if self._is_finite_number(value):
                summary[output_key] = float(value)

        delta_5d = summary.get("A20 DELTA 5D")
        delta_10d = summary.get("A20 DELTA 10D")
        if self._is_finite_number(delta_10d) and abs(float(delta_10d)) >= 15.0:
            summary["A20 MOMENTUM FLAG"] = 1.0 if float(delta_10d) > 0 else -1.0
        elif self._is_finite_number(delta_5d) and abs(float(delta_5d)) >= 10.0:
            summary["A20 MOMENTUM FLAG"] = 1.0 if float(delta_5d) > 0 else -1.0
        else:
            summary["A20 MOMENTUM FLAG"] = 0.0
        return summary

    def _breadth_internal_summary(self, stock_histories: dict[str, pd.DataFrame], offset: int = 0) -> dict[str, float]:
        breadth_frame = self._breadth_internal_frame(stock_histories)
        if breadth_frame.empty or len(breadth_frame) <= offset:
            return {}
        if offset > 0:
            breadth_frame = breadth_frame.iloc[: len(breadth_frame) - offset]
        if breadth_frame.empty:
            return {}
        latest = breadth_frame.iloc[-1]
        summary = {
            "UNIVERSE COUNT": latest.get("universe_count"),
            "ADVANCERS": latest.get("advancers"),
            "DECLINERS": latest.get("decliners"),
            "ADVANCE DECLINE NET": latest.get("advance_decline_net"),
            "ADVANCE RATIO": latest.get("advance_ratio"),
            "AD LINE": latest.get("ad_line"),
            "NEW HIGH 52W COUNT": latest.get("new_high_52w_count"),
            "NEW LOW 52W COUNT": latest.get("new_low_52w_count"),
            "NET NEW HIGH LOW": latest.get("net_new_high_low"),
            "NET NEW HIGH LOW %": latest.get("net_new_high_low_pct"),
            "STAGE2 %": latest.get("stage2_pct"),
            "MCCLELLAN OSCILLATOR": latest.get("mcclellan_oscillator"),
            "MCCLELLAN SUMMATION": latest.get("mcclellan_summation"),
            "ZWEIG BREADTH THRUST": latest.get("zweig_breadth_thrust"),
            "ZWEIG THRUST FLAG": latest.get("zweig_thrust_flag"),
        }
        return {key: float(value) for key, value in summary.items() if self._is_finite_number(value)}

    def _breadth_internal_frame(self, stock_histories: dict[str, pd.DataFrame]) -> pd.DataFrame:
        rows: list[pd.DataFrame] = []
        for history in stock_histories.values():
            if history.empty or "close" not in history.columns:
                continue
            close = pd.to_numeric(history["close"], errors="coerce")
            high = pd.to_numeric(history["high"], errors="coerce") if "high" in history.columns else close
            low = pd.to_numeric(history["low"], errors="coerce") if "low" in history.columns else close
            previous_close = close.shift(1)
            row = pd.DataFrame(index=history.index)
            row["valid"] = close.notna() & previous_close.notna()
            row["advance"] = (close > previous_close) & row["valid"]
            row["decline"] = (close < previous_close) & row["valid"]
            if "high_52w" in history.columns:
                high_52w = pd.to_numeric(history["high_52w"], errors="coerce")
                row["new_high_52w"] = (high >= high_52w) & high_52w.notna()
            else:
                row["new_high_52w"] = False
            if "low_52w" in history.columns:
                low_52w = pd.to_numeric(history["low_52w"], errors="coerce")
                row["new_low_52w"] = (low <= low_52w) & low_52w.notna()
            else:
                row["new_low_52w"] = False
            if "stage_label" in history.columns:
                row["stage2"] = history["stage_label"].astype(str).eq("stage2_candidate")
            else:
                row["stage2"] = False
            rows.append(row)
        if not rows:
            return pd.DataFrame()

        combined = pd.concat(rows, axis=1, keys=range(len(rows))).sort_index()
        valid = combined.xs("valid", axis=1, level=1).fillna(False)
        advances = combined.xs("advance", axis=1, level=1).fillna(False)
        declines = combined.xs("decline", axis=1, level=1).fillna(False)
        new_highs = combined.xs("new_high_52w", axis=1, level=1).fillna(False)
        new_lows = combined.xs("new_low_52w", axis=1, level=1).fillna(False)
        stage2 = combined.xs("stage2", axis=1, level=1).fillna(False)

        universe_count = valid.sum(axis=1).astype(float)
        advancers = advances.sum(axis=1).astype(float)
        decliners = declines.sum(axis=1).astype(float)
        advance_decline_net = advancers - decliners
        advance_ratio = (advancers / (advancers + decliners).replace(0, np.nan)).fillna(0.5)
        ratio_adjusted_net = ((advance_ratio - 0.5) * 200.0).where(universe_count > 0)
        new_high_count = new_highs.sum(axis=1).astype(float)
        new_low_count = new_lows.sum(axis=1).astype(float)
        net_new_high_low = new_high_count - new_low_count
        stage2_count = (stage2 & valid).sum(axis=1).astype(float)

        frame = pd.DataFrame(
            {
                "universe_count": universe_count,
                "advancers": advancers,
                "decliners": decliners,
                "advance_decline_net": advance_decline_net,
                "advance_ratio": advance_ratio,
                "ad_line": advance_decline_net.fillna(0.0).cumsum(),
                "new_high_52w_count": new_high_count,
                "new_low_52w_count": new_low_count,
                "net_new_high_low": net_new_high_low,
                "net_new_high_low_pct": (net_new_high_low / universe_count.replace(0, np.nan)) * 100.0,
                "stage2_pct": (stage2_count / universe_count.replace(0, np.nan)) * 100.0,
                "mcclellan_oscillator": ratio_adjusted_net.ewm(span=19, adjust=False, min_periods=1).mean()
                - ratio_adjusted_net.ewm(span=39, adjust=False, min_periods=1).mean(),
                "zweig_breadth_thrust": advance_ratio.ewm(span=10, adjust=False, min_periods=1).mean(),
            }
        )
        frame["mcclellan_summation"] = frame["mcclellan_oscillator"].fillna(0.0).cumsum()
        prior_10d_min = frame["zweig_breadth_thrust"].shift(1).rolling(10, min_periods=1).min()
        frame["zweig_thrust_flag"] = ((prior_10d_min < 0.4) & (frame["zweig_breadth_thrust"] > 0.615)).astype(float)
        return frame

    @staticmethod
    def _is_finite_number(value: object) -> bool:
        try:
            return bool(pd.notna(value) and np.isfinite(float(value)))
        except (TypeError, ValueError):
            return False

    def _empty_components(self) -> dict[str, float]:
        component_names = set(self.config.component_weights)
        component_names.update({"pct_above_sma10", "pct_sma20_gt_sma50", "pct_positive_1w", "pct_positive_1y", "pct_positive_ytd"})
        return {name: 0.0 for name in component_names}

    def _score_components(
        self,
        raw_components: dict[str, float],
        market_histories: dict[str, pd.DataFrame],
        offset: int,
    ) -> dict[str, float]:
        component_names = set(raw_components) | set(self.config.component_weights)
        scored = {
            name: self._ratio_component_score(raw_components.get(name, 50.0))
            for name in component_names
            if name not in {"vix_score", "safe_haven_score"}
        }
        scored["vix_score"] = self._vix_score(market_histories.get("^VIX", pd.DataFrame()), offset)
        scored["safe_haven_score"] = self._safe_haven_score(market_histories, offset)
        return scored

    def _blend_components(
        self,
        etf_components: dict[str, float],
        active_components: dict[str, float],
        etf_weight: float,
        active_symbols_weight: float,
    ) -> dict[str, float]:
        total_weight = etf_weight + active_symbols_weight
        if total_weight <= 0:
            return dict(etf_components)
        component_names = set(etf_components) | set(active_components)
        return {
            name: float(
                (
                    etf_components.get(name, 0.0) * etf_weight
                    + active_components.get(name, 0.0) * active_symbols_weight
                )
                / total_weight
            )
            for name in component_names
        }

    def _feature_row(self, history: pd.DataFrame, offset: int) -> dict[str, float] | None:
        if history.empty or "close" not in history.columns:
            return None
        close = history["close"].astype(float)
        if len(close) <= offset:
            return None
        index_position = len(close) - 1 - offset
        current_date = close.index[index_position]
        current_close = close.iloc[index_position]
        if pd.isna(current_close):
            return None

        sma10 = close.rolling(10).mean().iloc[index_position]
        sma20 = close.rolling(20).mean().iloc[index_position]
        sma50 = self._series_or_fallback(history, "sma50", 50).iloc[index_position]
        sma200 = self._series_or_fallback(history, "sma200", 200).iloc[index_position]
        ret_1w = close.pct_change(5, fill_method=None).iloc[index_position] * 100.0
        ret_1m = close.pct_change(21, fill_method=None).iloc[index_position] * 100.0
        ret_3m = close.pct_change(63, fill_method=None).iloc[index_position] * 100.0
        ret_1y = close.pct_change(252, fill_method=None).iloc[index_position] * 100.0
        ret_ytd = self._ytd_return(close, current_date, index_position)
        two_week_high = close.rolling(10).max().iloc[index_position]
        return {
            "close": float(current_close),
            "sma10": float(sma10) if pd.notna(sma10) else np.nan,
            "sma20": float(sma20) if pd.notna(sma20) else np.nan,
            "sma50": float(sma50) if pd.notna(sma50) else np.nan,
            "sma200": float(sma200) if pd.notna(sma200) else np.nan,
            "ret_1w": float(ret_1w) if pd.notna(ret_1w) else np.nan,
            "ret_1m": float(ret_1m) if pd.notna(ret_1m) else np.nan,
            "ret_3m": float(ret_3m) if pd.notna(ret_3m) else np.nan,
            "ret_1y": float(ret_1y) if pd.notna(ret_1y) else np.nan,
            "ret_ytd": float(ret_ytd) if pd.notna(ret_ytd) else np.nan,
            "is_2w_high": float(current_close >= two_week_high) if pd.notna(two_week_high) else 0.0,
        }

    def _ratio_component_score(self, value: float) -> float:
        clamped = max(0.0, min(float(value), 100.0))
        if clamped <= 50.0:
            return clamped
        return min(100.0, 50.0 + ((clamped - 50.0) / 50.0) * 30.0)

    def _series_or_fallback(self, history: pd.DataFrame, column: str, window: int) -> pd.Series:
        if column in history.columns:
            return history[column].astype(float)
        return history["close"].astype(float).rolling(window).mean()

    def _ytd_return(self, close: pd.Series, current_date: pd.Timestamp, index_position: int) -> float:
        year_mask = (close.index.year == current_date.year) & (close.index <= current_date)
        year_slice = close.loc[year_mask]
        if year_slice.empty:
            return float("nan")
        start_close = year_slice.iloc[0]
        current_close = close.iloc[index_position]
        if start_close == 0 or pd.isna(start_close) or pd.isna(current_close):
            return float("nan")
        return float((current_close / start_close - 1.0) * 100.0)

    def _vix_score(self, vix_history: pd.DataFrame, offset: int) -> float:
        vix_close = self._close_at_offset(vix_history, offset)
        if vix_close is None:
            return 50.0
        centered_score = 50.0 - ((vix_close - self.config.vix_neutral_level) * self.config.vix_score_slope)
        return max(0.0, min(100.0, centered_score))

    def _safe_haven_score(self, market_histories: dict[str, pd.DataFrame], offset: int) -> float:
        spread = self._safe_haven_spread(market_histories, offset)
        return max(0.0, min(100.0, 50.0 + (spread * self.config.safe_haven_score_scale)))

    def _safe_haven_spread(self, market_histories: dict[str, pd.DataFrame], offset: int) -> float:
        risk_on_history = market_histories.get(self.config.safe_haven_risk_on_symbol, pd.DataFrame())
        risk_off_history = market_histories.get(self.config.safe_haven_risk_off_symbol, pd.DataFrame())
        risk_on_return = self._return_at_offset(risk_on_history, self.config.safe_haven_window, offset)
        risk_off_return = self._return_at_offset(risk_off_history, self.config.safe_haven_window, offset)
        if risk_on_return is None or risk_off_return is None:
            return 0.0
        return float(risk_on_return - risk_off_return)

    def _risk_on_ratio_summary(self, market_histories: dict[str, pd.DataFrame], offset: int = 0) -> dict[str, float]:
        numerator_history = market_histories.get(self.config.risk_on_ratio_numerator_symbol, pd.DataFrame())
        denominator_history = market_histories.get(self.config.risk_on_ratio_denominator_symbol, pd.DataFrame())
        if numerator_history.empty or denominator_history.empty:
            return {}
        if "close" not in numerator_history.columns or "close" not in denominator_history.columns:
            return {}

        aligned = pd.concat(
            [
                numerator_history["close"].astype(float),
                denominator_history["close"].astype(float),
            ],
            axis=1,
            join="inner",
        ).dropna()
        if aligned.empty:
            return {}
        aligned = aligned.loc[aligned.iloc[:, 1] != 0]
        if aligned.empty:
            return {}

        ratio = aligned.iloc[:, 0] / aligned.iloc[:, 1]
        if len(ratio) <= offset:
            return {}
        ratio = ratio.iloc[: len(ratio) - offset]
        latest_ratio = ratio.iloc[-1]
        if pd.isna(latest_ratio):
            return {}

        above_count = 0
        available_ma_count = 0
        for window in self.config.risk_on_ratio_ma_windows:
            if len(ratio) < window:
                continue
            moving_average = ratio.rolling(window).mean().iloc[-1]
            if pd.isna(moving_average):
                continue
            available_ma_count += 1
            if float(latest_ratio) >= float(moving_average):
                above_count += 1

        high_window = max(1, min(self.config.risk_on_ratio_high_window, len(ratio)))
        rolling_high = ratio.tail(high_window).max()
        high_distance_pct = np.nan
        if pd.notna(rolling_high) and float(rolling_high) != 0.0:
            high_distance_pct = float((float(latest_ratio) / float(rolling_high) - 1.0) * 100.0)

        return {
            "RATIO": float(latest_ratio),
            "REL 1W %": self._ratio_return(ratio, 5),
            "REL 1M %": self._ratio_return(ratio, 21),
            "REL 3M %": self._ratio_return(ratio, 63),
            "HIGH DIST %": high_distance_pct,
            "HIGH LOOKBACK DAYS": float(high_window),
            "ABOVE MA COUNT": float(above_count),
            "MA COUNT": float(available_ma_count),
        }

    def _volatility_term_structure(self, market_histories: dict[str, pd.DataFrame], offset: int = 0) -> dict[str, float]:
        summary = self._ratio_diagnostic_summary(
            market_histories,
            numerator_symbol="^VIX",
            denominator_symbol=self.config.vix3m_symbol,
            offset=offset,
        )
        vix_close = self._close_at_offset(market_histories.get("^VIX", pd.DataFrame()), offset)
        vix9d_close = self._close_at_offset(market_histories.get(self.config.vix9d_symbol, pd.DataFrame()), offset)
        vix3m_close = self._close_at_offset(market_histories.get(self.config.vix3m_symbol, pd.DataFrame()), offset)
        if vix_close is not None:
            summary["VIX"] = vix_close
        if vix9d_close is not None:
            summary["VIX9D"] = vix9d_close
        if vix3m_close is not None:
            summary["VIX3M"] = vix3m_close
        ratio = summary.get("RATIO")
        if ratio is not None and pd.notna(ratio):
            summary["INVERSION FLAG"] = 1.0 if float(ratio) >= 1.0 else 0.0
        if vix9d_close is not None and vix_close is not None and float(vix_close) != 0.0:
            front_ratio = float(vix9d_close) / float(vix_close)
            summary["VIX9D/VIX RATIO"] = front_ratio
            summary["FRONT INVERSION FLAG"] = 1.0 if front_ratio >= 1.0 else 0.0
        if vix9d_close is not None and vix_close is not None and vix3m_close is not None:
            summary["FULL BACKWARDATION FLAG"] = 1.0 if float(vix9d_close) >= float(vix_close) >= float(vix3m_close) else 0.0
        return summary

    def _credit_risk_proxy(self, market_histories: dict[str, pd.DataFrame], offset: int = 0) -> dict[str, float]:
        high_yield = self.config.credit_high_yield_symbol
        investment_grade = self.config.credit_investment_grade_symbol
        treasury = self.config.credit_treasury_symbol
        high_yield_oas = self.config.credit_high_yield_oas_symbol
        high_yield_vs_credit = self._ratio_diagnostic_summary(
            market_histories,
            numerator_symbol=high_yield,
            denominator_symbol=investment_grade,
            offset=offset,
        )
        high_yield_vs_treasury = self._ratio_diagnostic_summary(
            market_histories,
            numerator_symbol=high_yield,
            denominator_symbol=treasury,
            offset=offset,
        )
        summary: dict[str, float] = {}
        for prefix, values in (("HYG/LQD", high_yield_vs_credit), ("HYG/IEF", high_yield_vs_treasury)):
            for key, value in values.items():
                summary[f"{prefix} {key}"] = value
        rel_1w_values = [
            summary.get("HYG/LQD REL 1W %"),
            summary.get("HYG/IEF REL 1W %"),
        ]
        if all(value is not None and pd.notna(value) for value in rel_1w_values):
            summary["CREDIT RISK-OFF FLAG"] = 1.0 if all(float(value) < 0.0 for value in rel_1w_values) else 0.0
        oas_close = self._close_at_offset(market_histories.get(high_yield_oas, pd.DataFrame()), offset)
        if oas_close is not None:
            summary["HY OAS"] = oas_close
            previous_5d = self._close_at_offset(market_histories.get(high_yield_oas, pd.DataFrame()), offset + 5)
            previous_21d = self._close_at_offset(market_histories.get(high_yield_oas, pd.DataFrame()), offset + 21)
            if previous_5d is not None:
                delta_5d_bps = (float(oas_close) - float(previous_5d)) * 100.0
                summary["HY OAS DELTA 5D BPS"] = delta_5d_bps
                summary["HY OAS WIDENING 5D FLAG"] = 1.0 if delta_5d_bps >= 25.0 else 0.0
            if previous_21d is not None:
                summary["HY OAS DELTA 21D BPS"] = (float(oas_close) - float(previous_21d)) * 100.0
        return summary

    def _drawdown_summary(
        self,
        market_histories: dict[str, pd.DataFrame],
        benchmark_history: pd.DataFrame,
        offset: int = 0,
    ) -> dict[str, float]:
        summary: dict[str, float] = {}
        for symbol in self.config.index_state_symbols:
            history = market_histories.get(symbol, pd.DataFrame())
            if history.empty and symbol == "SPY":
                history = benchmark_history
            state = self._single_drawdown_state(history, offset)
            for key, value in state.items():
                summary[f"{symbol} {key}"] = value
        return summary

    def _single_drawdown_state(self, history: pd.DataFrame, offset: int = 0) -> dict[str, float]:
        if history.empty or "close" not in history.columns:
            return {}
        close = pd.to_numeric(history["close"], errors="coerce").dropna().astype(float)
        if offset > 0:
            if len(close) <= offset:
                return {}
            close = close.iloc[: len(close) - offset]
        if close.empty:
            return {}
        window = max(1, min(self.config.drawdown_window, len(close)))
        window_close = close.tail(window)
        high = float(window_close.max())
        latest = float(window_close.iloc[-1])
        if high == 0.0 or pd.isna(high):
            return {}
        high_positions = np.flatnonzero(np.isclose(window_close.to_numpy(dtype=float), high, equal_nan=False))
        last_high_position = int(high_positions[-1]) if len(high_positions) else len(window_close) - 1
        return {
            "DD 252D %": (latest / high - 1.0) * 100.0,
            "T_DD": float(len(window_close) - 1 - last_high_position),
            "ROLLING HIGH": high,
            "DRAWDOWN WINDOW DAYS": float(window),
        }

    def _index_state_summary(
        self,
        market_histories: dict[str, pd.DataFrame],
        benchmark_history: pd.DataFrame,
    ) -> dict[str, float]:
        summary: dict[str, float] = {}
        for symbol in self.config.index_state_symbols:
            history = market_histories.get(symbol, pd.DataFrame())
            if history.empty and symbol == "SPY":
                history = benchmark_history
            state = self._single_index_state(history)
            for key, value in state.items():
                summary[f"{symbol} {key}"] = value
        return summary

    def _single_index_state(self, history: pd.DataFrame) -> dict[str, float]:
        required_columns = {"close", "volume"}
        if history.empty or not required_columns.issubset(history.columns):
            return {}
        frame = history.loc[:, ["close", "volume"]].copy()
        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        frame["volume"] = pd.to_numeric(frame["volume"], errors="coerce")
        frame = frame.dropna()
        if len(frame) < 2:
            return {}
        close = frame["close"].astype(float)
        volume = frame["volume"].astype(float)
        daily_return = close.pct_change(fill_method=None) * 100.0
        previous_volume = volume.shift(1)

        distribution = (daily_return <= self.config.index_state_distribution_decline_pct) & (volume > previous_volume)
        distribution_lookback = max(1, min(self.config.index_state_distribution_lookback, len(distribution)))
        distribution_count = float(distribution.tail(distribution_lookback).sum())

        low_lookback = max(2, min(self.config.index_state_rally_low_lookback, len(close)))
        recent_close = close.tail(low_lookback)
        low_label = recent_close.idxmin()
        low_pos = close.index.get_loc(low_label)
        if isinstance(low_pos, slice):
            low_pos = low_pos.start
        low_pos = int(low_pos)
        latest_pos = len(close) - 1
        sessions_since_low = latest_pos - low_pos
        rally_attempt_day = float(sessions_since_low) if sessions_since_low > 0 and close.iloc[-1] > close.iloc[low_pos] else 0.0

        ftd_pos: int | None = None
        min_rally_day = max(1, self.config.index_state_ftd_min_rally_day)
        for position in range(low_pos + min_rally_day, latest_pos + 1):
            gain = daily_return.iloc[position]
            if pd.isna(gain):
                continue
            if (
                float(gain) >= self.config.index_state_ftd_min_gain_pct
                and volume.iloc[position] > previous_volume.iloc[position]
                and close.iloc[position] > close.iloc[low_pos]
            ):
                ftd_pos = position
        ftd_flag = 1.0 if ftd_pos is not None else 0.0
        ftd_age = float(latest_pos - ftd_pos) if ftd_pos is not None else -1.0
        under_pressure = 1.0 if distribution_count >= self.config.index_state_distribution_pressure_count else 0.0
        return {
            "RALLY ATTEMPT DAY": rally_attempt_day,
            "FTD FLAG": ftd_flag,
            "FTD AGE DAYS": ftd_age,
            "DISTRIBUTION DAY COUNT": distribution_count,
            "UNDER PRESSURE FLAG": under_pressure,
        }

    def _ratio_diagnostic_summary(
        self,
        market_histories: dict[str, pd.DataFrame],
        *,
        numerator_symbol: str,
        denominator_symbol: str,
        offset: int = 0,
    ) -> dict[str, float]:
        numerator_history = market_histories.get(numerator_symbol, pd.DataFrame())
        denominator_history = market_histories.get(denominator_symbol, pd.DataFrame())
        if numerator_history.empty or denominator_history.empty:
            return {}
        if "close" not in numerator_history.columns or "close" not in denominator_history.columns:
            return {}
        aligned = pd.concat(
            [
                numerator_history["close"].astype(float),
                denominator_history["close"].astype(float),
            ],
            axis=1,
            join="inner",
        ).dropna()
        if aligned.empty:
            return {}
        aligned = aligned.loc[aligned.iloc[:, 1] != 0]
        if aligned.empty or len(aligned) <= offset:
            return {}
        ratio = aligned.iloc[:, 0] / aligned.iloc[:, 1]
        ratio = ratio.iloc[: len(ratio) - offset]
        if ratio.empty:
            return {}
        latest_ratio = ratio.iloc[-1]
        if pd.isna(latest_ratio):
            return {}
        return {
            "RATIO": float(latest_ratio),
            "REL 1W %": self._ratio_return(ratio, 5),
            "REL 1M %": self._ratio_return(ratio, 21),
            "REL 3M %": self._ratio_return(ratio, 63),
        }

    def _sector_relative_strength(
        self,
        market_histories: dict[str, pd.DataFrame],
        benchmark_history: pd.DataFrame,
    ) -> pd.DataFrame:
        if benchmark_history.empty or "close" not in benchmark_history.columns:
            return pd.DataFrame()
        rows: list[dict[str, object]] = []
        for item in self.config.condition_etfs:
            if item.ticker not in SECTOR_ROTATION_TICKERS:
                continue
            history = market_histories.get(item.ticker, pd.DataFrame())
            if history.empty or "close" not in history.columns:
                continue
            rows.append(
                {
                    "TICKER": item.ticker,
                    "NAME": item.name,
                    "REL 1W %": self._relative_return_at_offset(history, benchmark_history, 5, 0),
                    "REL 1M %": self._relative_return_at_offset(history, benchmark_history, 21, 0),
                    "REL 3M %": self._relative_return_at_offset(history, benchmark_history, 63, 0),
                    "REL 1M 1W AGO %": self._relative_return_at_offset(history, benchmark_history, 21, 5),
                    "REL 1M 1M AGO %": self._relative_return_at_offset(history, benchmark_history, 21, 21),
                }
            )
        frame = pd.DataFrame(rows)
        if frame.empty:
            return frame
        current_rank = frame["REL 1M %"].rank(ascending=False, method="min")
        prior_1w_rank = frame["REL 1M 1W AGO %"].rank(ascending=False, method="min")
        prior_1m_rank = frame["REL 1M 1M AGO %"].rank(ascending=False, method="min")
        frame["RANK 1M"] = current_rank
        frame["RANK DELTA 1W"] = prior_1w_rank - current_rank
        frame["RANK DELTA 1M"] = prior_1m_rank - current_rank
        for column in ["REL 1W %", "REL 1M %", "REL 3M %", "REL 1M 1W AGO %", "REL 1M 1M AGO %", "RANK 1M", "RANK DELTA 1W", "RANK DELTA 1M"]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").round(3)
        return frame.sort_values(["REL 1M %", "REL 1W %"], ascending=[False, False]).reset_index(drop=True)

    def _style_pair_summary(self, market_histories: dict[str, pd.DataFrame]) -> pd.DataFrame:
        rows: list[dict[str, object]] = []
        for numerator, denominator, name in STYLE_RATIO_PAIRS:
            summary = self._pair_ratio_summary(market_histories, numerator, denominator)
            if not summary:
                continue
            rows.append({"PAIR": f"{numerator}/{denominator}", "NAME": name, **summary})
        frame = pd.DataFrame(rows)
        if frame.empty:
            return frame
        for column in ["REL 1W %", "REL 1M %", "REL 3M %", "ABOVE MA COUNT", "MA COUNT"]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").round(3)
        return frame.sort_values(["REL 1M %", "REL 1W %"], ascending=[False, False]).reset_index(drop=True)

    def _pair_ratio_summary(self, market_histories: dict[str, pd.DataFrame], numerator: str, denominator: str) -> dict[str, float]:
        numerator_history = market_histories.get(numerator, pd.DataFrame())
        denominator_history = market_histories.get(denominator, pd.DataFrame())
        if numerator_history.empty or denominator_history.empty:
            return {}
        if "close" not in numerator_history.columns or "close" not in denominator_history.columns:
            return {}
        aligned = pd.concat(
            [numerator_history["close"].astype(float), denominator_history["close"].astype(float)],
            axis=1,
            join="inner",
        ).dropna()
        if aligned.empty:
            return {}
        aligned = aligned.loc[aligned.iloc[:, 1] != 0]
        if aligned.empty:
            return {}
        ratio = aligned.iloc[:, 0] / aligned.iloc[:, 1]
        above_count = 0
        available_ma_count = 0
        for window in self.config.risk_on_ratio_ma_windows:
            if len(ratio) < window:
                continue
            moving_average = ratio.rolling(window).mean().iloc[-1]
            if pd.isna(moving_average):
                continue
            available_ma_count += 1
            if float(ratio.iloc[-1]) >= float(moving_average):
                above_count += 1
        return {
            "REL 1W %": self._ratio_return(ratio, 5),
            "REL 1M %": self._ratio_return(ratio, 21),
            "REL 3M %": self._ratio_return(ratio, 63),
            "ABOVE MA COUNT": float(above_count),
            "MA COUNT": float(available_ma_count),
        }

    def _defensive_cyclical_summary(self, market_histories: dict[str, pd.DataFrame]) -> dict[str, float]:
        summary: dict[str, float] = {}
        for periods, label in [(5, "REL 1W %"), (21, "REL 1M %"), (63, "REL 3M %")]:
            defensive = self._basket_return(market_histories, DEFENSIVE_SECTOR_TICKERS, periods)
            cyclical = self._basket_return(market_histories, CYCLICAL_GROWTH_SECTOR_TICKERS, periods)
            if defensive is None or cyclical is None:
                continue
            summary[label] = cyclical - defensive
        return summary

    def _basket_return(self, market_histories: dict[str, pd.DataFrame], tickers: tuple[str, ...], periods: int) -> float | None:
        returns = [
            value
            for ticker in tickers
            if (value := self._return_at_offset(market_histories.get(ticker, pd.DataFrame()), periods, 0)) is not None
        ]
        if not returns:
            return None
        return float(np.mean(returns))

    def _relative_return_at_offset(
        self,
        asset_history: pd.DataFrame,
        benchmark_history: pd.DataFrame,
        periods: int,
        offset: int,
    ) -> float:
        if asset_history.empty or benchmark_history.empty:
            return float("nan")
        if "close" not in asset_history.columns or "close" not in benchmark_history.columns:
            return float("nan")
        aligned = pd.concat(
            [asset_history["close"].astype(float), benchmark_history["close"].astype(float)],
            axis=1,
            join="inner",
        ).dropna()
        if len(aligned) <= periods + offset:
            return float("nan")
        aligned = aligned.iloc[: len(aligned) - offset] if offset > 0 else aligned
        asset_return = aligned.iloc[:, 0].pct_change(periods, fill_method=None).iloc[-1] * 100.0
        benchmark_return = aligned.iloc[:, 1].pct_change(periods, fill_method=None).iloc[-1] * 100.0
        if pd.isna(asset_return) or pd.isna(benchmark_return):
            return float("nan")
        return float(asset_return - benchmark_return)

    def _ratio_return(self, ratio: pd.Series, periods: int) -> float:
        if len(ratio) <= periods:
            return float("nan")
        previous = ratio.iloc[-1 - periods]
        latest = ratio.iloc[-1]
        if pd.isna(previous) or pd.isna(latest) or float(previous) == 0.0:
            return float("nan")
        return float((float(latest) / float(previous) - 1.0) * 100.0)

    def _score_from_components(self, components: dict[str, float]) -> float:
        return float(sum(components.get(name, 50.0) * weight for name, weight in self.config.component_weights.items()))

    def _rounded_score_at_offset(
        self,
        stock_histories: dict[str, pd.DataFrame],
        market_histories: dict[str, pd.DataFrame],
        offset: int,
    ) -> float | None:
        raw_components = self._raw_component_values_at_offset(stock_histories, market_histories, offset)
        components = self._score_components(raw_components, market_histories, offset)
        if not components:
            return None
        return round(self._score_from_components(components), 2)

    def _label_for_optional_score(self, score: float | None) -> str | None:
        if score is None:
            return None
        return self._label(float(score))

    def _performance_overview(self, benchmark_history: pd.DataFrame) -> dict[str, float]:
        close = benchmark_history["close"].astype(float)
        latest_date = close.index[-1]
        return {
            "% YTD": self._return_for_period(close, self._ytd_period_index(close, latest_date)),
            "% 1W": self._return_for_period(close, 5),
            "% 1M": self._return_for_period(close, 21),
            "% 1Y": self._return_for_period(close, 252),
        }

    def _ytd_period_index(self, close: pd.Series, current_date: pd.Timestamp) -> int:
        year_mask = (close.index.year == current_date.year) & (close.index <= current_date)
        year_slice = close.loc[year_mask]
        return len(year_slice) - 1 if len(year_slice) > 1 else 0

    def _return_for_period(self, close: pd.Series, periods: int) -> float:
        if periods <= 0 or len(close) <= periods:
            return 0.0
        value = close.pct_change(periods, fill_method=None).iloc[-1] * 100.0
        return float(value) if pd.notna(value) else 0.0

    def _return_at_offset(self, history: pd.DataFrame, periods: int, offset: int) -> float | None:
        if history.empty or "close" not in history.columns:
            return None
        close = history["close"].astype(float)
        if len(close) <= (periods + offset):
            return None
        value = close.pct_change(periods, fill_method=None).iloc[-1 - offset] * 100.0
        if pd.isna(value):
            return None
        return float(value)

    def _build_s5th_series(self, stock_histories: dict[str, pd.DataFrame]) -> pd.DataFrame:
        signals: list[pd.Series] = []
        for history in stock_histories.values():
            if history.empty or "close" not in history.columns or "sma200" not in history.columns:
                continue
            signal = (history["close"] >= history["sma200"]).astype(float)
            signals.append(signal.rename(None))
        if not signals:
            return pd.DataFrame(columns=["date", "pct_above_sma200"])
        frame = pd.concat(signals, axis=1)
        s5th = frame.mean(axis=1) * 100.0
        result = s5th.reset_index()
        result.columns = ["date", "pct_above_sma200"]
        result["pct_above_sma200"] = result["pct_above_sma200"].round(2)
        return result

    def _breadth_keys(self) -> tuple[str, ...]:
        return (
            "pct_above_sma10",
            "pct_above_sma20",
            "pct_above_sma50",
            "pct_above_sma200",
            "pct_sma20_gt_sma50",
            "pct_sma50_gt_sma200",
        )

    def _participation_keys(self) -> tuple[str, ...]:
        return (
            "pct_positive_1w",
            "pct_positive_1m",
            "pct_positive_3m",
            "pct_positive_1y",
            "pct_positive_ytd",
        )

    def _latest_close(self, history: pd.DataFrame) -> float | None:
        return self._close_at_offset(history, 0)

    def _close_at_offset(self, history: pd.DataFrame, offset: int) -> float | None:
        if history.empty or "close" not in history.columns or len(history) <= offset:
            return None
        value = history["close"].iloc[-1 - offset]
        if pd.isna(value):
            return None
        return float(value)

    def _latest_trade_date(self, benchmark_history: pd.DataFrame) -> pd.Timestamp | None:
        if benchmark_history.empty:
            return None
        return pd.to_datetime(benchmark_history.index[-1])

    def _label(self, score: float) -> str:
        if score >= self.config.bullish_threshold:
            return "Bullish"
        if score >= self.config.positive_threshold:
            return "Positive"
        if score >= self.config.neutral_threshold:
            return "Neutral"
        if score >= self.config.negative_threshold:
            return "Negative"
        return "Bearish"
