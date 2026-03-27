from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.pipeline import PlatformArtifacts, ResearchPlatform


st.set_page_config(page_title="Growth Trading Screener", layout="wide")


def parse_symbols(raw_value: str) -> list[str]:
    return [part.strip().upper() for part in raw_value.replace("\n", ",").split(",") if part.strip()]


def load_artifacts(config_path: str, symbols: list[str], force_universe_refresh: bool) -> PlatformArtifacts:
    platform = ResearchPlatform(config_path)
    return platform.run(symbols or None, force_universe_refresh=force_universe_refresh)


def render_data_health_banner(artifacts: PlatformArtifacts) -> None:
    summary = artifacts.data_health_summary
    if summary.get("sample_count", 0) > 0:
        st.warning("Some datasets are using sample fallback. Treat scores and rankings as non-live.")
    elif summary.get("stale_cache_count", 0) > 0 or summary.get("missing_count", 0) > 0:
        st.info("Some datasets came from stale cache or are missing. Check Data Health below before acting.")


def render_data_health_table(artifacts: PlatformArtifacts) -> None:
    with st.expander("Data Health", expanded=False):
        st.dataframe(artifacts.fetch_status, use_container_width=True, hide_index=True)
        if artifacts.universe_snapshot_path:
            st.caption(f"Universe snapshot: {artifacts.universe_snapshot_path}")
        if artifacts.run_directory:
            st.caption(f"Run snapshot saved to: {artifacts.run_directory}")


def render_watchlist(artifacts: PlatformArtifacts) -> None:
    st.subheader("Today's Watchlist")
    metric_columns = st.columns(5)
    overlap_series = artifacts.watchlist.get("overlap_count", pd.Series(dtype=int)) if not artifacts.watchlist.empty else pd.Series(dtype=int)
    metric_columns[0].metric("Cards", len(artifacts.watchlist_cards))
    metric_columns[1].metric("Candidates", len(artifacts.watchlist))
    metric_columns[2].metric("Duplicate Tickers", int(overlap_series.ge(3).sum()))
    metric_columns[3].metric("Universe Mode", artifacts.universe_mode)
    metric_columns[4].metric("Universe Size", len(artifacts.resolved_symbols))
    st.caption("Scan-based card grid. Rows inside each card are sorted by Hybrid-RS.")

    if not artifacts.watchlist_cards:
        st.info("No scan hits were produced. Try expanding the universe or adjusting thresholds.")
    else:
        cards = artifacts.watchlist_cards
        for start in range(0, len(cards), 3):
            batch = cards[start : start + 3]
            columns = st.columns(len(batch))
            for column, card in zip(columns, batch):
                with column:
                    with st.container(border=True):
                        st.markdown(f"**{card.display_name}**")
                        st.caption(f"{card.ticker_count} tickers")
                        st.dataframe(card.rows, use_container_width=True, hide_index=True, height=min(320, 75 + len(card.rows) * 35))

    st.markdown("**Earnings for today (liquid)**")
    if artifacts.earnings_today.empty:
        st.caption("No same-day earnings names in the current eligible universe.")
    else:
        st.dataframe(artifacts.earnings_today, use_container_width=True, hide_index=True)
    render_data_health_table(artifacts)


def render_rs_radar(artifacts: PlatformArtifacts) -> None:
    result = artifacts.radar_result
    st.subheader("RS Radar")
    st.caption("ETF-based radar using configured sector and industry universes. MAJOR STOCKS are config-driven reference names.")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Sector ETFs", len(result.sector_leaders))
    metric_columns[1].metric("Industry ETFs", len(result.industry_leaders))
    metric_columns[2].metric("Top Daily", result.top_daily.iloc[0]["TICKER"] if not result.top_daily.empty else "N/A")
    metric_columns[3].metric("Updated", result.update_time.split("T")[-1] if result.update_time else "N/A")

    top_left, top_right = st.columns(2)
    with top_left:
        st.markdown("**Top 3 RS% Change (Daily)**")
        if result.top_daily.empty:
            st.caption("No daily movers available.")
        else:
            st.dataframe(result.top_daily, use_container_width=True, hide_index=True)
    with top_right:
        st.markdown("**Top 3 RS% Change (Weekly)**")
        if result.top_weekly.empty:
            st.caption("No weekly movers available.")
        else:
            st.dataframe(result.top_weekly, use_container_width=True, hide_index=True)

    lower_left, lower_right = st.columns(2)
    with lower_left:
        st.markdown("**Sector Leaders**")
        if result.sector_leaders.empty:
            st.caption("No sector summary available.")
        else:
            st.dataframe(result.sector_leaders, use_container_width=True, hide_index=True)
    with lower_right:
        st.markdown("**Industry Leaders**")
        if result.industry_leaders.empty:
            st.caption("No industry summary available.")
        else:
            st.dataframe(result.industry_leaders, use_container_width=True, hide_index=True)
    render_data_health_table(artifacts)


def render_market_dashboard(artifacts: PlatformArtifacts) -> None:
    result = artifacts.market_result
    st.subheader("Market Dashboard")
    columns = st.columns(5)
    columns[0].metric("Market Score", result.score)
    columns[1].metric("Label", result.label)
    columns[2].metric("VIX", result.vix_close if result.vix_close is not None else "N/A")
    columns[3].metric("Updated", result.update_time.split("T")[-1] if result.update_time else "N/A")
    columns[4].metric("Data Mode", artifacts.data_source_label)

    left, right = st.columns(2)
    with left:
        st.markdown("**Breadth Summary**")
        st.dataframe(
            pd.DataFrame(
                [{"Metric": key, "Value": value} for key, value in result.breadth_summary.items()]
            ),
            use_container_width=True,
            hide_index=True,
        )
    with right:
        st.markdown("**Component Scores**")
        st.dataframe(
            pd.DataFrame(
                [{"Component": key, "Score": value} for key, value in result.component_scores.items()]
            ),
            use_container_width=True,
            hide_index=True,
        )
    render_data_health_table(artifacts)


def main() -> None:
    st.title("Growth Trading Screener")
    default_config = ROOT / "config" / "default.yaml"

    with st.sidebar:
        st.markdown("**Controls**")
        config_path = st.text_input("Config Path", value=str(default_config))
        symbols_raw = st.text_area("Manual Symbols (optional)", value="", height=120, placeholder="Leave blank to use weekly universe snapshot")
        force_universe_refresh = st.checkbox("Force Weekly Universe Refresh", value=False)
        page = st.radio("Page", ["Today's Watchlist", "RS Radar", "Market Dashboard"])
        refresh = st.button("Refresh", type="primary")

    symbols = parse_symbols(symbols_raw)
    cache_key = (config_path, tuple(symbols), force_universe_refresh)
    if refresh or st.session_state.get("artifacts_key") != cache_key:
        with st.spinner("Loading screening artifacts..."):
            st.session_state["artifacts"] = load_artifacts(config_path, symbols, force_universe_refresh)
            st.session_state["artifacts_key"] = cache_key

    artifacts: PlatformArtifacts = st.session_state["artifacts"]
    st.caption(f"Data source: {artifacts.data_source_label} | Universe mode: {artifacts.universe_mode} | Symbols: {len(artifacts.resolved_symbols)}")
    render_data_health_banner(artifacts)

    if page == "Today's Watchlist":
        render_watchlist(artifacts)
    elif page == "RS Radar":
        render_rs_radar(artifacts)
    else:
        render_market_dashboard(artifacts)


if __name__ == "__main__":
    main()
