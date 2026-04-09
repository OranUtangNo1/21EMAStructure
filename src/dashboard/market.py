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

DEFAULT_LEADERSHIP_ETFS = (
    MarketUniverseItem("SMH", "Semiconductors"),
    MarketUniverseItem("SOXX", "Semiconductors Broad"),
    MarketUniverseItem("IGV", "Software"),
    MarketUniverseItem("FDN", "Internet"),
    MarketUniverseItem("HACK", "Cybersecurity"),
    MarketUniverseItem("XBI", "Biotech"),
    MarketUniverseItem("IBB", "Biotech Large Cap"),
    MarketUniverseItem("ITA", "Aerospace and Defense"),
    MarketUniverseItem("KRE", "Regional Banks"),
    MarketUniverseItem("XRT", "Retail"),
    MarketUniverseItem("XOP", "Oil and Gas Exploration"),
    MarketUniverseItem("TAN", "Solar"),
    MarketUniverseItem("IYT", "Transportation"),
    MarketUniverseItem("IPO", "IPOs"),
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
    leadership_etfs: tuple[MarketUniverseItem, ...] = field(default_factory=lambda: DEFAULT_LEADERSHIP_ETFS)
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

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "MarketConditionConfig":
        condition_payload = payload.get("market_condition_etf_universe", payload.get("condition_etfs", []))
        leadership_payload = payload.get("leadership_etfs", [])
        external_payload = payload.get("external_etfs", [])
        factor_payload = payload.get("factor_etfs", [])
        condition_items = tuple(MarketUniverseItem.from_payload(item) for item in condition_payload) if condition_payload else DEFAULT_MARKET_CONDITION_ETFS
        leadership_items = tuple(MarketUniverseItem.from_payload(item) for item in leadership_payload) if leadership_payload else DEFAULT_LEADERSHIP_ETFS
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
    performance_overview: dict[str, float]
    high_vix_summary: dict[str, float]
    market_snapshot: pd.DataFrame
    leadership_snapshot: pd.DataFrame
    external_snapshot: pd.DataFrame
    factors_vs_sp500: pd.DataFrame
    s5th_series: pd.DataFrame
    vix_close: float | None
    update_time: str


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
            for item in [*self.config.condition_etfs, *self.config.leadership_etfs, *self.config.external_etfs, *self.config.factor_etfs]
        ]
        symbols.extend(["^VIX", self.config.safe_haven_risk_on_symbol, self.config.safe_haven_risk_off_symbol])
        return list(dict.fromkeys(symbols))

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
        leadership_snapshot = self.snapshot_builder.build(market_histories, self.config.leadership_etfs)
        external_snapshot = self.snapshot_builder.build(market_histories, self.config.external_etfs)
        factors_vs_sp500 = self.factor_calculator.build(market_histories, benchmark_history)
        s5th_series = self._build_s5th_series(stock_histories)

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
            performance_overview={key: round(value, 2) for key, value in performance_overview.items()},
            high_vix_summary={
                "S2W HIGH %": round(latest_raw_components.get("pct_2w_high", 0.0), 2),
                "VIX": round(vix_close, 2) if vix_close is not None else np.nan,
                "SAFE HAVEN %": round(self._safe_haven_spread(market_histories, 0), 2),
            },
            market_snapshot=market_snapshot,
            leadership_snapshot=leadership_snapshot,
            external_snapshot=external_snapshot,
            factors_vs_sp500=factors_vs_sp500,
            s5th_series=s5th_series,
            vix_close=round(vix_close, 2) if vix_close is not None else None,
            update_time=datetime.now().isoformat(timespec="seconds"),
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
            performance_overview={},
            high_vix_summary={},
            market_snapshot=empty,
            leadership_snapshot=empty,
            external_snapshot=empty,
            factors_vs_sp500=empty,
            s5th_series=empty,
            vix_close=None,
            update_time=datetime.now().isoformat(timespec="seconds"),
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
