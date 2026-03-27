from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from src.data.models import FundamentalSnapshot, SymbolProfile
from src.utils import deterministic_seed


class SampleDataFactory:
    """Generate deterministic sample data when live downloads are unavailable."""

    def __init__(self, periods: int = 320) -> None:
        self.periods = periods

    def build_price_history(self, symbols: list[str]) -> dict[str, pd.DataFrame]:
        dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=self.periods)
        histories: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            rng = np.random.default_rng(deterministic_seed(symbol))
            start_price = float(rng.integers(20, 220))
            drift = rng.uniform(0.0004, 0.0014)
            volatility = rng.uniform(0.012, 0.03)
            daily_returns = rng.normal(drift, volatility, size=len(dates))
            close = start_price * np.exp(np.cumsum(daily_returns))
            open_price = close * (1 + rng.normal(0.0, 0.004, size=len(dates)))
            high = np.maximum(open_price, close) * (1 + rng.uniform(0.002, 0.02, size=len(dates)))
            low = np.minimum(open_price, close) * (1 - rng.uniform(0.002, 0.02, size=len(dates)))
            volume = rng.integers(900_000, 7_000_000, size=len(dates))
            frame = pd.DataFrame(
                {
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "adjusted_close": close,
                    "volume": volume.astype(float),
                },
                index=dates,
            )
            frame.index.name = "date"
            histories[symbol] = frame.round(4)
        return histories

    def build_profiles(self, symbols: list[str]) -> list[SymbolProfile]:
        sectors = [
            ("Technology", "Software"),
            ("Communication Services", "Internet Content"),
            ("Consumer Cyclical", "Retail"),
            ("Industrials", "Electrical Equipment"),
        ]
        profiles: list[SymbolProfile] = []
        for index, symbol in enumerate(symbols):
            sector, industry = sectors[index % len(sectors)]
            seed = deterministic_seed(symbol)
            market_cap = float(1_500_000_000 + (seed % 80) * 250_000_000)
            ipo_date = date.today() - timedelta(days=600 + seed % 2500)
            profiles.append(
                SymbolProfile(
                    ticker=symbol,
                    name=f"{symbol} Demo Corp",
                    market_cap=market_cap,
                    sector=sector,
                    industry=industry,
                    ipo_date=ipo_date,
                )
            )
        return profiles

    def build_fundamentals(self, symbols: list[str]) -> list[FundamentalSnapshot]:
        fundamentals: list[FundamentalSnapshot] = []
        for symbol in symbols:
            seed = deterministic_seed(f"{symbol}_fund")
            eps_growth = float(15 + (seed % 70))
            revenue_growth = float(10 + (seed % 45))
            earnings_date = date.today() + timedelta(days=int(seed % 20))
            fundamentals.append(
                FundamentalSnapshot(
                    ticker=symbol,
                    eps_growth=eps_growth,
                    revenue_growth=revenue_growth,
                    earnings_date=earnings_date,
                )
            )
        return fundamentals
