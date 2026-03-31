from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd

from src.data.models import FundamentalSnapshot, SymbolProfile
from src.data.providers import UniverseDiscoveryResult
from src.data.results import FetchStatus, FundamentalBatchResult, ProfileBatchResult

try:
    from finvizfinance.screener.custom import Custom
except ImportError:  # pragma: no cover
    Custom = None


@dataclass(slots=True)
class FinvizScreenerConfig:
    allowed_exchanges: tuple[str, ...] = ("NASDAQ", "NYSE", "AMEX")
    excluded_sectors: tuple[str, ...] = ("Healthcare",)
    max_symbols: int = 2500
    min_market_cap: float = 1_000_000_000.0

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "FinvizScreenerConfig":
        return cls(
            allowed_exchanges=tuple(
                str(value).strip().upper()
                for value in payload.get("allowed_exchanges", ["NASDAQ", "NYSE", "AMEX"])
                if str(value).strip()
            ),
            excluded_sectors=tuple(str(value) for value in payload.get("excluded_sectors", ["Healthcare"])),
            max_symbols=max(1, int(payload.get("max_symbols", 2500))),
            min_market_cap=float(payload.get("min_market_cap", 1_000_000_000.0)),
        )


class FinvizScreenerProvider:
    COLUMN_IDS = [1, 2, 3, 4, 5, 6, 22, 23, 68]
    RENAME_MAP = {
        "Ticker": "ticker",
        "Company": "name",
        "Sector": "sector",
        "Industry": "industry",
        "Country": "country",
        "Market Cap": "market_cap",
        "Market Cap.": "market_cap",
        "EPS Q/Q": "eps_growth",
        "EPS growth qtr over qtr": "eps_growth",
        "Sales Q/Q": "revenue_growth",
        "Sales growth qtr over qtr": "revenue_growth",
        "Earnings": "earnings_date",
        "Earnings Date": "earnings_date",
    }
    REQUIRED_COLUMNS = [
        "ticker",
        "name",
        "sector",
        "industry",
        "country",
        "market_cap",
        "eps_growth",
        "revenue_growth",
        "earnings_date",
    ]

    def __init__(self, config: FinvizScreenerConfig) -> None:
        self.config = config

    def discover(self) -> UniverseDiscoveryResult:
        if Custom is None:
            raise RuntimeError("finvizfinance is not installed.")

        fetched_at = datetime.now()
        frames: list[pd.DataFrame] = []
        exchange_rows: list[dict[str, object]] = []
        for exchange in self.config.allowed_exchanges:
            raw = self._fetch_exchange_frame(exchange)
            if raw is None or raw.empty:
                continue
            normalized = self._normalize_frame(raw, exchange, fetched_at)
            if normalized.empty:
                continue
            frames.append(normalized)
            exchange_rows.append({"exchange": exchange, "row_count": int(len(normalized))})

        if not frames:
            return UniverseDiscoveryResult(
                snapshot=pd.DataFrame(),
                source="live",
                metadata={"provider": "finviz", "exchanges": exchange_rows},
            )

        snapshot = pd.concat(frames, ignore_index=True)
        snapshot = snapshot.drop_duplicates(subset=["ticker"]).copy()
        snapshot = snapshot.loc[snapshot["market_cap"].fillna(0) >= self.config.min_market_cap].copy()
        if self.config.excluded_sectors:
            snapshot = snapshot.loc[~snapshot["sector"].fillna("").isin(self.config.excluded_sectors)].copy()
        snapshot = (
            snapshot.sort_values(["market_cap", "ticker"], ascending=[False, True])
            .head(self.config.max_symbols)
            .reset_index(drop=True)
        )
        snapshot["source"] = "finviz"
        snapshot["discovered_at"] = fetched_at.isoformat(timespec="seconds")
        return UniverseDiscoveryResult(
            snapshot=snapshot,
            source="live",
            metadata={"provider": "finviz", "exchanges": exchange_rows, "row_count": int(len(snapshot))},
        )

    def _fetch_exchange_frame(self, exchange: str) -> pd.DataFrame | None:
        screener = Custom()
        screener.set_filter(filters_dict={"Exchange": exchange, "Market Cap.": "+Small (over $300mln)"})
        return screener.screener_view(
            order="Market Cap.",
            limit=self.config.max_symbols,
            verbose=0,
            ascend=False,
            columns=self.COLUMN_IDS,
            sleep_sec=0,
        )

    def _normalize_frame(self, frame: pd.DataFrame, exchange: str, fetched_at: datetime) -> pd.DataFrame:
        normalized = frame.rename(columns=self.RENAME_MAP).copy()
        for column in self.REQUIRED_COLUMNS:
            if column not in normalized.columns:
                normalized[column] = None

        normalized["ticker"] = normalized["ticker"].astype(str).str.strip().str.upper()
        normalized = normalized.loc[normalized["ticker"].ne("")].copy()
        normalized["name"] = normalized["name"].apply(_string_or_none)
        normalized["sector"] = normalized["sector"].apply(_string_or_none)
        normalized["industry"] = normalized["industry"].apply(_string_or_none)
        normalized["country"] = normalized["country"].apply(_string_or_none)
        normalized["market_cap"] = normalized["market_cap"].apply(_parse_market_cap)
        normalized["eps_growth"] = normalized["eps_growth"].apply(_parse_percent)
        normalized["revenue_growth"] = normalized["revenue_growth"].apply(_parse_percent)
        normalized["earnings_date"] = normalized["earnings_date"].apply(lambda value: _parse_earnings_date(value, fetched_at))
        normalized["exchange"] = exchange
        return normalized[
            [
                "ticker",
                "name",
                "sector",
                "industry",
                "country",
                "exchange",
                "market_cap",
                "eps_growth",
                "revenue_growth",
                "earnings_date",
            ]
        ]


def build_profile_batch_from_snapshot(
    snapshot: pd.DataFrame | None,
    symbols: list[str],
    source: str,
    default_fetched_at: datetime | None = None,
) -> ProfileBatchResult:
    if snapshot is None or snapshot.empty or "ticker" not in snapshot.columns:
        return ProfileBatchResult(profiles=[], statuses={})
    lookup = snapshot.copy()
    lookup["ticker"] = lookup["ticker"].astype(str).str.strip().str.upper()
    lookup = lookup.drop_duplicates(subset=["ticker"]).set_index("ticker")
    profiles: list[SymbolProfile] = []
    statuses: dict[str, FetchStatus] = {}
    for symbol in symbols:
        if symbol not in lookup.index:
            continue
        row = lookup.loc[symbol]
        name = _string_or_none(row.get("name"))
        market_cap = _float_or_none(row.get("market_cap"))
        sector = _string_or_none(row.get("sector"))
        industry = _string_or_none(row.get("industry"))
        if all(value is None for value in [name, market_cap, sector, industry]):
            continue
        fetched_at = _row_timestamp(row, default_fetched_at)
        profiles.append(
            SymbolProfile(
                ticker=symbol,
                name=name,
                market_cap=market_cap,
                sector=sector,
                industry=industry,
                last_profile_update=fetched_at,
                data_source=source,
            )
        )
        statuses[symbol] = FetchStatus(
            symbol=symbol,
            dataset="profile",
            source=source,
            has_data=True,
            fetched_at=fetched_at,
            note="universe snapshot",
        )
    return ProfileBatchResult(profiles=profiles, statuses=statuses)


def build_fundamental_batch_from_snapshot(
    snapshot: pd.DataFrame | None,
    symbols: list[str],
    source: str,
    default_fetched_at: datetime | None = None,
) -> FundamentalBatchResult:
    if snapshot is None or snapshot.empty or "ticker" not in snapshot.columns:
        return FundamentalBatchResult(fundamentals=[], statuses={})
    lookup = snapshot.copy()
    lookup["ticker"] = lookup["ticker"].astype(str).str.strip().str.upper()
    lookup = lookup.drop_duplicates(subset=["ticker"]).set_index("ticker")
    fundamentals: list[FundamentalSnapshot] = []
    statuses: dict[str, FetchStatus] = {}
    for symbol in symbols:
        if symbol not in lookup.index:
            continue
        row = lookup.loc[symbol]
        eps_growth = _float_or_none(row.get("eps_growth"))
        revenue_growth = _float_or_none(row.get("revenue_growth"))
        earnings_date = _date_or_none(row.get("earnings_date"))
        if all(value is None for value in [eps_growth, revenue_growth, earnings_date]):
            continue
        fetched_at = _row_timestamp(row, default_fetched_at)
        fundamentals.append(
            FundamentalSnapshot(
                ticker=symbol,
                eps_growth=eps_growth,
                revenue_growth=revenue_growth,
                earnings_date=earnings_date,
                last_fundamental_update=fetched_at,
                data_source=source,
            )
        )
        statuses[symbol] = FetchStatus(
            symbol=symbol,
            dataset="fundamental",
            source=source,
            has_data=True,
            fetched_at=fetched_at,
            note="universe snapshot",
        )
    return FundamentalBatchResult(fundamentals=fundamentals, statuses=statuses)


def _parse_market_cap(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text or text == "-":
        return None
    suffixes = {"K": 1_000.0, "M": 1_000_000.0, "B": 1_000_000_000.0, "T": 1_000_000_000_000.0}
    suffix = text[-1].upper()
    try:
        if suffix in suffixes:
            return float(text[:-1]) * suffixes[suffix]
        return float(text)
    except ValueError:
        return None


def _parse_percent(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric * 100.0 if abs(numeric) <= 1.5 else numeric
    text = str(value).strip().replace(",", "")
    if not text or text == "-":
        return None
    has_percent_suffix = text.endswith("%")
    if has_percent_suffix:
        text = text[:-1]
    try:
        numeric = float(text)
    except ValueError:
        return None
    if has_percent_suffix:
        return numeric
    return numeric * 100.0 if abs(numeric) <= 1.5 else numeric


def _parse_earnings_date(value: object, fetched_at: datetime) -> date | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text == "-":
        return None

    lowered = text.lower()
    if lowered == "today":
        return fetched_at.date()
    if lowered == "tomorrow":
        return (fetched_at + timedelta(days=1)).date()

    cleaned = text.replace("/a", "").replace("/b", "").replace("*", "").strip()
    parts = cleaned.replace("-", " ").split()
    candidate_tokens: list[str] = []
    if len(parts) >= 2 and parts[0].isalpha():
        candidate_tokens.append(f"{parts[0]} {parts[1]}")
    candidate_tokens.append(cleaned)
    candidate_tokens.append(cleaned.replace(" ", "-"))

    seen: set[str] = set()
    for token in candidate_tokens:
        token = token.strip()
        if not token or token in seen:
            continue
        seen.add(token)
        for fmt in ("%b-%d-%y", "%b-%d-%Y", "%Y-%m-%d", "%b-%d", "%b %d"):
            try:
                parsed = datetime.strptime(token, fmt)
                if fmt in {"%b-%d", "%b %d"}:
                    parsed = parsed.replace(year=fetched_at.year)
                    if parsed.date() < fetched_at.date() - timedelta(days=30):
                        parsed = parsed.replace(year=fetched_at.year + 1)
                return parsed.date()
            except ValueError:
                continue
    return None


def _float_or_none(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string_or_none(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _date_or_none(value: object) -> date | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _row_timestamp(row: pd.Series, default_fetched_at: datetime | None) -> datetime | None:
    for key in ["discovered_at", "saved_at"]:
        if key in row and pd.notna(row[key]):
            parsed = pd.to_datetime(row[key], errors="coerce")
            if not pd.isna(parsed):
                return parsed.to_pydatetime()
    return default_fetched_at