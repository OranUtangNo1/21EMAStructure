from __future__ import annotations

import pandas as pd

from src.dashboard.stock_card import StockCardMetadata


SECTOR_NAME_TO_ETF = {
    "basic materials": "XLB",
    "communication services": "XLC",
    "communications": "XLC",
    "consumer cyclical": "XLY",
    "consumer defensive": "XLP",
    "consumer discretionary": "XLY",
    "consumer staples": "XLP",
    "energy": "XLE",
    "financial": "XLF",
    "financial services": "XLF",
    "financials": "XLF",
    "health care": "XLV",
    "healthcare": "XLV",
    "industrial goods": "XLI",
    "industrials": "XLI",
    "real estate": "XLRE",
    "technology": "XLK",
    "utilities": "XLU",
}


INDUSTRY_NAME_TO_ETF = {
    "semiconductor": "SMH",
    "semiconductors": "SMH",
    "semiconductor equipment & materials": "SMH",
    "semiconductor equipment and materials": "SMH",
}


def build_stock_card_metadata_lookup(settings: dict[str, object], artifacts: object) -> dict[str, StockCardMetadata]:
    radar_config = settings.get("radar", {})
    industry_map: dict[str, str] = {}
    industry_name_map: dict[str, str] = dict(INDUSTRY_NAME_TO_ETF)
    for item in radar_config.get("industry_etfs", []) if isinstance(radar_config, dict) else []:
        if not isinstance(item, dict):
            continue
        etf = str(item.get("ticker", "")).strip().upper()
        name = str(item.get("name", "")).strip().lower()
        if etf and name:
            industry_name_map.setdefault(name, etf)
        for symbol in item.get("major_stocks", []) or []:
            if etf and str(symbol).strip():
                industry_map[str(symbol).strip().upper()] = etf

    industry_rank: dict[str, int] = {}
    industry_leaders = getattr(getattr(artifacts, "radar_result", None), "industry_leaders", pd.DataFrame())
    if isinstance(industry_leaders, pd.DataFrame) and not industry_leaders.empty and "TICKER" in industry_leaders.columns:
        for index, ticker in enumerate(industry_leaders["TICKER"].astype(str).str.upper().tolist(), start=1):
            industry_rank[ticker] = index

    source_frames = [
        getattr(artifacts, "eligible_snapshot", pd.DataFrame()),
        getattr(artifacts, "snapshot", pd.DataFrame()),
        getattr(artifacts, "watchlist", pd.DataFrame()),
    ]
    rows: dict[str, pd.Series] = {}
    for frame in source_frames:
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            for ticker, row in frame.iterrows():
                rows.setdefault(str(ticker).strip().upper(), row)

    lookup: dict[str, StockCardMetadata] = {}
    for ticker, row in rows.items():
        sector_raw = str(row.get("sector", "")).strip().lower() if isinstance(row, pd.Series) else ""
        sector_etf = SECTOR_NAME_TO_ETF.get(sector_raw, "NA")
        industry_etf = industry_map.get(ticker, "NA")
        if industry_etf == "NA" and isinstance(row, pd.Series):
            industry_etf = stock_card_industry_etf_from_row(row, industry_name_map)
        rs_pctl = next(
            (
                row.get(column)
                for column in ("rs_pctl", "rs_percentile", "rs_percentile_12_1", "rs12_1_pctl")
                if isinstance(row, pd.Series) and column in row.index and pd.notna(row.get(column))
            ),
            None,
        )
        lookup[ticker] = StockCardMetadata(
            sector_etf=sector_etf,
            industry_etf=industry_etf,
            industry_rs_rank=industry_rank.get(industry_etf),
            rs_pctl=float(rs_pctl) if rs_pctl is not None and pd.notna(rs_pctl) else None,
        )
    return lookup


def stock_card_industry_etf_from_row(row: pd.Series, industry_name_map: dict[str, str]) -> str:
    raw = str(row.get("industry", "")).strip().lower()
    if not raw or raw in {"nan", "none", "na"}:
        return "NA"
    if raw in industry_name_map:
        return industry_name_map[raw]
    for name, etf in industry_name_map.items():
        if len(name) >= 4 and (name in raw or raw in name):
            return etf
    return "NA"
