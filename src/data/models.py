from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(slots=True)
class SymbolProfile:
    """Static profile information for a symbol."""

    ticker: str
    name: str | None = None
    market_cap: float | None = None
    sector: str | None = None
    industry: str | None = None
    ipo_date: date | None = None
    last_profile_update: datetime | None = None
    data_source: str | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "market_cap": self.market_cap,
            "sector": self.sector,
            "industry": self.industry,
            "ipo_date": self.ipo_date.isoformat() if self.ipo_date else None,
            "last_profile_update": self.last_profile_update.isoformat() if self.last_profile_update else None,
            "data_source": self.data_source,
        }

    @classmethod
    def from_record(cls, payload: dict[str, Any]) -> "SymbolProfile":
        ipo_date = date.fromisoformat(payload["ipo_date"]) if payload.get("ipo_date") else None
        last_profile_update = (
            datetime.fromisoformat(payload["last_profile_update"])
            if payload.get("last_profile_update")
            else None
        )
        return cls(
            ticker=payload["ticker"],
            name=payload.get("name"),
            market_cap=payload.get("market_cap"),
            sector=payload.get("sector"),
            industry=payload.get("industry"),
            ipo_date=ipo_date,
            last_profile_update=last_profile_update,
            data_source=payload.get("data_source"),
        )


@dataclass(slots=True)
class FundamentalSnapshot:
    """Fundamental snapshot used for research scoring."""

    ticker: str
    eps_growth: float | None = None
    revenue_growth: float | None = None
    earnings_date: date | None = None
    last_fundamental_update: datetime | None = None
    data_source: str | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "eps_growth": self.eps_growth,
            "revenue_growth": self.revenue_growth,
            "earnings_date": self.earnings_date.isoformat() if self.earnings_date else None,
            "last_fundamental_update": (
                self.last_fundamental_update.isoformat() if self.last_fundamental_update else None
            ),
            "data_source": self.data_source,
        }

    @classmethod
    def from_record(cls, payload: dict[str, Any]) -> "FundamentalSnapshot":
        earnings_date = date.fromisoformat(payload["earnings_date"]) if payload.get("earnings_date") else None
        last_fundamental_update = (
            datetime.fromisoformat(payload["last_fundamental_update"])
            if payload.get("last_fundamental_update")
            else None
        )
        return cls(
            ticker=payload["ticker"],
            eps_growth=payload.get("eps_growth"),
            revenue_growth=payload.get("revenue_growth"),
            earnings_date=earnings_date,
            last_fundamental_update=last_fundamental_update,
            data_source=payload.get("data_source"),
        )
