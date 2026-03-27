from __future__ import annotations

import pandas as pd


SOURCE_SCORES: dict[str, float] = {
    "live": 100.0,
    "cache_fresh": 85.0,
    "cache_stale": 65.0,
    "sample": 20.0,
    "missing": 0.0,
}


def source_score(source: object) -> float:
    """Map a source label to a 0-100 quality score."""
    return SOURCE_SCORES.get(str(source), 0.0)


def append_data_quality(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Append data lineage and quality fields to the latest symbol snapshot."""
    result = snapshot.copy()
    profile_fields = [column for column in ["name", "market_cap", "sector", "industry", "ipo_date"] if column in result.columns]
    fundamental_fields = [column for column in ["eps_growth", "revenue_growth", "earnings_date"] if column in result.columns]

    profile_coverage = result[profile_fields].notna().mean(axis=1) * 100.0 if profile_fields else pd.Series(0.0, index=result.index)
    fundamental_coverage = (
        result[fundamental_fields].notna().mean(axis=1) * 100.0 if fundamental_fields else pd.Series(0.0, index=result.index)
    )

    price_source_score = result.get("price_data_source", pd.Series("missing", index=result.index)).map(source_score)
    profile_source_score = result.get("profile_data_source", pd.Series("missing", index=result.index)).map(source_score)
    fundamental_source_score = result.get("fundamental_data_source", pd.Series("missing", index=result.index)).map(source_score)

    coverage_score = (profile_coverage + fundamental_coverage) / 2.0
    result["profile_data_coverage_pct"] = profile_coverage.round(2)
    result["fundamental_data_coverage_pct"] = fundamental_coverage.round(2)
    result["data_quality_score"] = (
        price_source_score * 0.50
        + profile_source_score * 0.20
        + fundamental_source_score * 0.20
        + coverage_score * 0.10
    ).round(2)
    result["data_quality_label"] = result.apply(_quality_label, axis=1)
    result["data_warning"] = result.apply(_warning_message, axis=1)
    return result


def summarize_data_health(fetch_status_frame: pd.DataFrame) -> dict[str, float | int]:
    """Build a small aggregate health summary for the UI."""
    if fetch_status_frame.empty:
        return {
            "live_price_coverage_pct": 0.0,
            "real_price_coverage_pct": 0.0,
            "stale_cache_count": 0,
            "sample_count": 0,
            "missing_count": 0,
        }

    price_rows = fetch_status_frame.loc[fetch_status_frame["dataset"] == "price"]
    live_price_coverage = float((price_rows["source"] == "live").mean() * 100.0) if not price_rows.empty else 0.0
    real_price_coverage = float(price_rows["source"].isin(["live", "cache_fresh", "cache_stale"]).mean() * 100.0) if not price_rows.empty else 0.0
    return {
        "live_price_coverage_pct": round(live_price_coverage, 2),
        "real_price_coverage_pct": round(real_price_coverage, 2),
        "stale_cache_count": int((fetch_status_frame["source"] == "cache_stale").sum()),
        "sample_count": int((fetch_status_frame["source"] == "sample").sum()),
        "missing_count": int((fetch_status_frame["source"] == "missing").sum()),
    }


def summarize_data_source_label(fetch_status_frame: pd.DataFrame) -> str:
    """Collapse detailed statuses into one short label for the app header."""
    if fetch_status_frame.empty:
        return "no data"
    sources = set(fetch_status_frame["source"].dropna().astype(str))
    if sources == {"live"}:
        return "live"
    if "sample" in sources:
        return "live + sample fallback" if len(sources) > 1 else "sample fallback"
    if sources <= {"live", "cache_fresh", "cache_stale"}:
        return "live + cache"
    if sources == {"missing"}:
        return "missing"
    return "mixed"


def _quality_label(row: pd.Series) -> str:
    if row.get("price_data_source") == "sample":
        return "sample"
    score = float(row.get("data_quality_score", 0.0))
    if row.get("price_data_source") == "missing":
        return "missing"
    if score >= 90.0:
        return "live"
    if score >= 70.0:
        return "mixed"
    if score >= 40.0:
        return "weak"
    return "missing"


def _warning_message(row: pd.Series) -> str:
    warnings: list[str] = []
    if row.get("price_data_source") == "cache_stale":
        warnings.append("stale price cache")
    if row.get("profile_data_source") == "cache_stale":
        warnings.append("stale profile cache")
    if row.get("fundamental_data_source") == "cache_stale":
        warnings.append("stale fundamental cache")
    if row.get("price_data_source") == "sample":
        warnings.append("sample price data")
    if row.get("fundamental_data_source") == "missing":
        warnings.append("missing fundamentals")
    if row.get("profile_data_source") == "missing":
        warnings.append("missing profile")
    return ", ".join(warnings)
