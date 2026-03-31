from __future__ import annotations

import html
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.pipeline import PlatformArtifacts, ResearchPlatform


st.set_page_config(page_title="Growth Trading Screener", layout="wide")

GLOBAL_CSS = """
<style>
:root { --bg:#f3f5fb; --panel:#ffffff; --panel-border:#dbe4f3; --text:#223045; --muted:#6f7f98; }
html, body, [class*="css"] { font-family:"Aptos","Segoe UI","Yu Gothic UI",sans-serif; }
[data-testid="stAppViewContainer"] { background:radial-gradient(circle at top left, rgba(86,138,237,.12), transparent 26%), linear-gradient(180deg, #f8fbff 0%, var(--bg) 100%); color:var(--text); }
.block-container { max-width:1440px; padding-top:1.6rem; padding-bottom:2.3rem; }
section[data-testid="stSidebar"] { background:linear-gradient(180deg, #fbfdff 0%, #f4f8ff 100%); border-right:1px solid var(--panel-border); }
div.stButton > button { background:linear-gradient(135deg, #2d6cdf 0%, #528eee 100%); color:#fff; border:none; border-radius:14px; font-weight:700; box-shadow:0 12px 24px rgba(45,108,223,.18); }
div[data-testid="stDataFrame"], div[data-testid="stExpander"] { background:rgba(255,255,255,.9); border:1px solid var(--panel-border); border-radius:18px; overflow:hidden; box-shadow:0 16px 34px rgba(34,48,69,.05); }
[data-testid="stAlert"] { border-radius:16px; }
.oratek-sidebar-title { font-size:1.3rem; font-weight:800; letter-spacing:-.02em; color:var(--text); }
.oratek-sidebar-caption { margin:.35rem 0 1.1rem; color:var(--muted); line-height:1.5; font-size:.92rem; }
.oratek-page-title { font-size:2.05rem; font-weight:800; letter-spacing:-.03em; color:var(--text); margin-bottom:.15rem; }
.oratek-page-title.centered, .oratek-page-subtitle.centered { text-align:center; }
.oratek-page-subtitle { color:var(--muted); font-size:.96rem; }
.oratek-page-meta { text-align:right; color:var(--muted); font-size:.9rem; font-weight:700; padding-top:.55rem; }
.oratek-context-strip { display:flex; flex-wrap:wrap; gap:.6rem; margin:.2rem 0 1.05rem; }
.oratek-context-pill { background:rgba(255,255,255,.82); border:1px solid var(--panel-border); border-radius:999px; padding:.45rem .8rem; color:var(--muted); font-size:.82rem; font-weight:600; }
.oratek-stat-card { background:rgba(255,255,255,.94); border:1px solid var(--panel-border); border-radius:20px; padding:.95rem 1rem; box-shadow:0 16px 34px rgba(34,48,69,.05); margin-bottom:.85rem; min-height:96px; }
.oratek-stat-card.positive { border-color:rgba(33,164,111,.3); }
.oratek-stat-card.negative { border-color:rgba(223,91,91,.3); }
.oratek-stat-label { color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.06em; font-weight:700; }
.oratek-stat-value { color:var(--text); font-size:1.42rem; line-height:1.15; font-weight:800; margin-top:.35rem; }
.oratek-stat-note { color:var(--muted); font-size:.8rem; margin-top:.2rem; }
.oratek-section-head { display:flex; gap:.75rem; align-items:flex-start; margin-bottom:.55rem; }
.oratek-section-bar { width:4px; min-height:1.3rem; border-radius:999px; margin-top:.22rem; background:linear-gradient(180deg, #2d6cdf 0%, #6aaeff 100%); }
.oratek-section-title { color:var(--text); font-size:1rem; font-weight:800; line-height:1.2; }
.oratek-section-caption { color:var(--muted); font-size:.82rem; margin-top:.18rem; }
.oratek-hero-card { background:rgba(255,255,255,.94); border:1px solid var(--panel-border); border-radius:22px; padding:1rem 1.1rem; box-shadow:0 18px 36px rgba(34,48,69,.06); }
.oratek-hero-copy { color:var(--muted); line-height:1.55; font-size:.92rem; }
.oratek-hero-badge { display:inline-flex; gap:.55rem; align-items:baseline; border-radius:18px; padding:.8rem 1rem; margin-top:1rem; font-weight:800; }
.oratek-hero-badge.positive { background:rgba(33,164,111,.13); color:#21a46f; }
.oratek-hero-badge.negative { background:rgba(223,91,91,.13); color:#df5b5b; }
.oratek-hero-badge.neutral { background:rgba(127,140,166,.12); color:#7f8ca6; }
.oratek-hero-score { font-size:1.42rem; }
.oratek-page-submeta { color:var(--muted); font-size:.8rem; line-height:1.45; margin-top:.22rem; text-align:right; }
.oratek-ticker-card { background:rgba(255,255,255,.94); border:1px solid var(--panel-border); border-radius:22px; overflow:hidden; box-shadow:0 18px 36px rgba(34,48,69,.06); min-height:220px; margin-bottom:1rem; }
.oratek-ticker-card-head { display:flex; justify-content:space-between; gap:.8rem; align-items:center; padding:.9rem 1rem; background:linear-gradient(180deg, #eef4ff 0%, #e7f0ff 100%); border-bottom:1px solid var(--panel-border); }
.oratek-ticker-card-title { color:var(--text); font-size:.98rem; font-weight:800; }
.oratek-ticker-card-count { color:var(--muted); font-size:.8rem; font-weight:700; white-space:nowrap; }
.oratek-ticker-grid { display:grid; grid-template-columns:repeat(5, minmax(0,1fr)); gap:.65rem 1rem; padding:1rem 1.1rem 1.15rem; }
.oratek-ticker-item { color:var(--text); font-size:.95rem; font-weight:800; }
.oratek-empty-state { color:var(--muted); font-size:.85rem; padding:1rem 1.1rem 1.15rem; }
.oratek-mover-panel { background:rgba(255,255,255,.94); border:1px solid var(--panel-border); border-radius:22px; box-shadow:0 18px 36px rgba(34,48,69,.06); padding:1rem 1.1rem; margin-bottom:1rem; }
.oratek-mover-stack { display:grid; gap:.75rem; margin-top:.85rem; }
.oratek-mover-row { display:grid; grid-template-columns:54px minmax(0,1fr) auto; gap:.8rem; align-items:center; background:#fbfcff; border:1px solid #e6edf9; border-radius:16px; padding:.78rem .85rem; }
.oratek-mover-rs { background:linear-gradient(180deg, #eef7ec 0%, #e5f7e2 100%); color:#3d7850; border-radius:12px; text-align:center; font-weight:800; padding:.48rem .25rem; }
.oratek-mover-body { min-width:0; }
.oratek-mover-ticker { color:var(--text); font-size:.98rem; font-weight:800; }
.oratek-mover-name { color:var(--muted); font-size:.76rem; margin-top:.12rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.oratek-mover-side { text-align:right; }
.oratek-mover-price { color:var(--text); font-size:.98rem; font-weight:800; }
.oratek-mover-metric { font-size:.78rem; font-weight:800; margin-top:.18rem; }
.oratek-positive { color:#21a46f; }
.oratek-negative { color:#df5b5b; }
.oratek-neutral { color:#7f8ca6; }
.oratek-priority-band { background:linear-gradient(135deg, rgba(45,108,223,.12) 0%, rgba(106,174,255,.08) 100%); border:1px solid rgba(45,108,223,.22); border-radius:24px; box-shadow:0 18px 36px rgba(34,48,69,.06); padding:1rem 1.15rem 1.15rem; margin:.45rem 0 1rem; }
.oratek-priority-head { display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; }
.oratek-priority-kicker { color:#2d6cdf; font-size:.76rem; font-weight:800; text-transform:uppercase; letter-spacing:.08em; }
.oratek-priority-title { color:var(--text); font-size:1.28rem; font-weight:800; margin-top:.15rem; }
.oratek-priority-note { color:var(--muted); font-size:.86rem; margin-top:.2rem; line-height:1.45; }
.oratek-priority-count { color:#2d6cdf; font-size:.9rem; font-weight:800; white-space:nowrap; padding-top:.25rem; }
.oratek-priority-grid { display:grid; grid-template-columns:repeat(8, minmax(0,1fr)); gap:.7rem 1rem; margin-top:.95rem; }
.oratek-priority-item { background:rgba(255,255,255,.78); border:1px solid rgba(45,108,223,.12); border-radius:14px; padding:.72rem .75rem; color:var(--text); font-size:.98rem; font-weight:800; text-align:center; }
@media (max-width:768px) { .oratek-page-meta, .oratek-page-submeta { text-align:left; padding-top:.15rem; } .oratek-ticker-grid { grid-template-columns:repeat(3, minmax(0,1fr)); } .oratek-priority-grid { grid-template-columns:repeat(4, minmax(0,1fr)); } .oratek-mover-row { grid-template-columns:1fr; } .oratek-mover-side { text-align:left; } }
</style>
"""

def inject_global_styles() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def _coerce_number(value: object) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
    except TypeError:
        if value is None:
            return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text.lower() in {"n/a", "nan", "none"}:
        return None
    cleaned = text.replace("%", "").replace("$", "").replace(",", "").replace("+", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _tone_class(value: object) -> str:
    number = _coerce_number(value)
    if number is not None:
        if number > 0:
            return "positive"
        if number < 0:
            return "negative"
        return "neutral"
    text = str(value).strip().lower()
    if any(token in text for token in ["positive", "bull", "high", "above"]):
        return "positive"
    if any(token in text for token in ["negative", "bear", "low", "below"]):
        return "negative"
    return "neutral"


def render_page_header(title: str, subtitle: str = "", meta: str = "", centered: bool = False) -> None:
    if centered:
        _, meta_col = st.columns([5, 1])
        with meta_col:
            if meta:
                st.markdown(f"<div class='oratek-page-meta'>{html.escape(meta)}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='oratek-page-title centered'>{html.escape(title)}</div>", unsafe_allow_html=True)
        if subtitle:
            st.markdown(f"<div class='oratek-page-subtitle centered'>{html.escape(subtitle)}</div>", unsafe_allow_html=True)
        return
    left_col, right_col = st.columns([4.2, 1.3])
    with left_col:
        st.markdown(f"<div class='oratek-page-title'>{html.escape(title)}</div>", unsafe_allow_html=True)
        if subtitle:
            st.markdown(f"<div class='oratek-page-subtitle'>{html.escape(subtitle)}</div>", unsafe_allow_html=True)
    with right_col:
        if meta:
            st.markdown(f"<div class='oratek-page-meta'>{html.escape(meta)}</div>", unsafe_allow_html=True)


def render_context_strip(items: list[str]) -> None:
    pills = "".join(f"<span class='oratek-context-pill'>{html.escape(item)}</span>" for item in items if item)
    if pills:
        st.markdown(f"<div class='oratek-context-strip'>{pills}</div>", unsafe_allow_html=True)


def render_section_heading(title: str, caption: str = "") -> None:
    caption_html = f"<div class='oratek-section-caption'>{html.escape(caption)}</div>" if caption else ""
    st.markdown("<div class='oratek-section-head'><span class='oratek-section-bar'></span>" f"<div><div class='oratek-section-title'>{html.escape(title)}</div>{caption_html}</div></div>", unsafe_allow_html=True)


def render_stat_cards(items: list[tuple[str, str, str, str]]) -> None:
    columns = st.columns(len(items))
    for column, (label, value, note, tone) in zip(columns, items):
        note_html = f"<div class='oratek-stat-note'>{html.escape(note)}</div>" if note else ""
        column.markdown(f"<div class='oratek-stat-card {html.escape(tone)}'><div class='oratek-stat-label'>{html.escape(label)}</div><div class='oratek-stat-value'>{html.escape(value)}</div>{note_html}</div>", unsafe_allow_html=True)


def _to_ticker_list(frame: pd.DataFrame, sort_column: str | None = None) -> list[str]:
    if frame is None or frame.empty:
        return []
    working = frame.copy()
    if sort_column and sort_column in working.columns:
        working = working.sort_values(sort_column, ascending=False)
    ticker_column = "Ticker" if "Ticker" in working.columns else "TICKER" if "TICKER" in working.columns else None
    if not ticker_column:
        return []
    return [str(value).strip().upper() for value in working[ticker_column].tolist() if str(value).strip()]


def render_ticker_card(title: str, tickers: list[str], empty_text: str) -> None:
    count = len(tickers)
    body = "".join(f"<div class='oratek-ticker-item'>{html.escape(ticker)}</div>" for ticker in tickers)
    if not body:
        body = f"<div class='oratek-empty-state'>{html.escape(empty_text)}</div>"
    else:
        body = f"<div class='oratek-ticker-grid'>{body}</div>"
    st.markdown(
        f"<div class='oratek-ticker-card'><div class='oratek-ticker-card-head'><div class='oratek-ticker-card-title'>{html.escape(title)}</div><div class='oratek-ticker-card-count'>{count} tickers</div></div>{body}</div>",
        unsafe_allow_html=True,
    )


def render_priority_ticker_band(title: str, tickers: list[str], note: str, empty_text: str) -> None:
    count = len(tickers)
    body = "".join(f"<div class='oratek-priority-item'>{html.escape(ticker)}</div>" for ticker in tickers)
    if not body:
        body = f"<div class='oratek-empty-state'>{html.escape(empty_text)}</div>"
    else:
        body = f"<div class='oratek-priority-grid'>{body}</div>"
    st.markdown(
        f"<div class='oratek-priority-band'><div class='oratek-priority-head'><div><div class='oratek-priority-kicker'>Priority Focus</div><div class='oratek-priority-title'>{html.escape(title)}</div><div class='oratek-priority-note'>{html.escape(note)}</div></div><div class='oratek-priority-count'>{count} tickers</div></div>{body}</div>",
        unsafe_allow_html=True,
    )


def _format_radar_value(column: str, value: object) -> str:
    number = _coerce_number(value)
    if number is None:
        return "" if value is None else str(value)
    if column == "PRICE":
        return f"${number:,.2f}"
    if column in {"DAY %", "WK %", "MTH %", "RS DAY%", "RS WK%", "RS MTH%", "52W HIGH"}:
        return f"{number:+.2f}%"
    if column in {"RS", "1D", "1W", "1M"}:
        return f"{number:.0f}"
    return f"{number:.2f}"


def _signed_style(value: object) -> str:
    text = str(value).strip()
    if text == "Yes":
        return "color:#21a46f;font-weight:700;"
    number = _coerce_number(value)
    if number is None:
        return ""
    if number > 0:
        return "color:#21a46f;font-weight:700;"
    if number < 0:
        return "color:#df5b5b;font-weight:700;"
    return ""


def build_radar_styler(frame: pd.DataFrame):
    if frame.empty:
        return frame
    formatters = {column: (lambda value, column=column: _format_radar_value(column, value)) for column in frame.columns}
    styler = frame.style.format(formatters, na_rep="")
    for column in ["DAY %", "WK %", "MTH %", "RS DAY%", "RS WK%", "RS MTH%", "52W HIGH"]:
        if column in frame.columns:
            styler = styler.map(_signed_style, subset=[column])
    if "TICKER" in frame.columns:
        styler = styler.map(lambda _: "color:#2d6cdf;font-weight:800;", subset=["TICKER"])
    return styler


def render_top_movers_panel(title: str, frame: pd.DataFrame, perf_col: str, rs_col: str) -> None:
    if frame.empty:
        body = "<div class='oratek-empty-state'>No movers available.</div>"
    else:
        rows = []
        for _, row in frame.iterrows():
            perf_text = _format_radar_value(perf_col, row.get(perf_col))
            rs_text = _format_radar_value(rs_col, row.get(rs_col))
            rows.append(
                f"<div class='oratek-mover-row'><div class='oratek-mover-rs'>{_format_radar_value('RS', row.get('RS'))}</div><div class='oratek-mover-body'><div class='oratek-mover-ticker'>{html.escape(str(row.get('TICKER', '')))}</div><div class='oratek-mover-name'>{html.escape(str(row.get('NAME', '')))}</div></div><div class='oratek-mover-side'><div class='oratek-mover-price'>{html.escape(_format_radar_value('PRICE', row.get('PRICE')))}</div><div class='oratek-mover-metric oratek-{_tone_class(perf_text)}'>{html.escape(perf_col.replace('%', '').strip())} {html.escape(perf_text)}</div><div class='oratek-mover-metric oratek-{_tone_class(rs_text)}'>{html.escape(rs_col.replace('%', '').strip())} {html.escape(rs_text)}</div></div></div>"
            )
        body = f"<div class='oratek-mover-stack'>{''.join(rows)}</div>"
    st.markdown(f"<div class='oratek-mover-panel'>{_section_header_html(title)}{body}</div>", unsafe_allow_html=True)


def _section_header_html(title: str, caption: str = "") -> str:
    caption_html = f"<div class='oratek-section-caption'>{html.escape(caption)}</div>" if caption else ""
    return f"<div class='oratek-section-head'><span class='oratek-section-bar'></span><div><div class='oratek-section-title'>{html.escape(title)}</div>{caption_html}</div></div>"

def parse_symbols(raw_value: str) -> list[str]:
    normalized = raw_value.replace(chr(10), ",")
    return [part.strip().upper() for part in normalized.split(",") if part.strip()]


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
        st.dataframe(artifacts.fetch_status, width="stretch", hide_index=True)
        if artifacts.universe_snapshot_path:
            st.caption(f"Universe snapshot: {artifacts.universe_snapshot_path}")
        if artifacts.run_directory:
            st.caption(f"Run snapshot saved to: {artifacts.run_directory}")


def _format_trade_date(artifacts: PlatformArtifacts) -> str:
    if artifacts.snapshot.empty or "trade_date" not in artifacts.snapshot.columns:
        return "Unknown date"
    trade_date = pd.to_datetime(artifacts.snapshot["trade_date"], errors="coerce").max()
    if pd.isna(trade_date):
        return "Unknown date"
    return trade_date.strftime("%B %d, %Y")


def render_watchlist(artifacts: PlatformArtifacts) -> None:
    title_col, meta_col = st.columns([4.2, 1.8])
    with title_col:
        st.markdown("<div class='oratek-page-title'>Today's Watchlist</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='oratek-page-subtitle'>{html.escape(_format_trade_date(artifacts))}</div>", unsafe_allow_html=True)
    with meta_col:
        st.markdown(
            f"<div class='oratek-page-meta'>Sorted by Hybrid-RS</div><div class='oratek-page-submeta'>Universe Mode: {html.escape(str(artifacts.universe_mode))}<br>Universe Size: {len(artifacts.resolved_symbols)}</div>",
            unsafe_allow_html=True,
        )

    cards: list[tuple[str, list[str], str]] = [
        (card.display_name, _to_ticker_list(card.rows), "No tickers matched this scan.")
        for card in artifacts.watchlist_cards
    ]

    duplicate_frame = artifacts.duplicate_tickers.copy()
    duplicate_tickers = _to_ticker_list(duplicate_frame)

    render_priority_ticker_band(
        "Duplicate Tickers",
        duplicate_tickers,
        "Overlap count and Hybrid-RS priority are already resolved upstream. This band highlights the strongest names repeated across multiple scan cards.",
        "No duplicate tickers in the current watchlist.",
    )

    earnings_frame = artifacts.earnings_today.sort_values("Hybrid-RS", ascending=False) if not artifacts.earnings_today.empty and "Hybrid-RS" in artifacts.earnings_today.columns else artifacts.earnings_today

    if not cards:
        st.caption("No scan cards are configured or no scan rules matched the current universe.")
    else:
        for start in range(0, len(cards), 3):
            batch = cards[start : start + 3]
            columns = st.columns(3)
            for column, (title, tickers, empty_text) in zip(columns, batch):
                with column:
                    render_ticker_card(title, tickers, empty_text)

    st.markdown("<div style='margin-top:.2rem;'></div>", unsafe_allow_html=True)
    render_ticker_card(
        "Earnings for today (liquid)",
        _to_ticker_list(earnings_frame),
        "No same-day earnings names in the current eligible universe.",
    )
    render_data_health_table(artifacts)


def render_rs_radar(artifacts: PlatformArtifacts) -> None:
    result = artifacts.radar_result
    render_page_header(
        "RS Radar",
        subtitle="ETF-based radar using configured sector and industry universes.",
        meta=f"Updated: {result.update_time.split('T')[-1]}" if result.update_time else "Updated: N/A",
    )

    left_col, right_col = st.columns([1.0, 2.1])
    with left_col:
        render_top_movers_panel("Top 3 RS% Change (Daily)", result.top_daily, "DAY %", "RS DAY%")
        render_top_movers_panel("Top 3 RS% Change (Weekly)", result.top_weekly, "WK %", "RS WK%")
    with right_col:
        with st.container(border=True):
            render_section_heading("Sector Leaders", "Configured sector ETF leaders")
            if result.sector_leaders.empty:
                st.caption("No sector summary available.")
            else:
                st.dataframe(build_radar_styler(result.sector_leaders), width="stretch", hide_index=True, height=110 + len(result.sector_leaders) * 35)

    with st.container(border=True):
        render_section_heading("Industry Leaders", "Configured industry ETF leaders and major stock references")
        if result.industry_leaders.empty:
            st.caption("No industry summary available.")
        else:
            st.dataframe(build_radar_styler(result.industry_leaders), width="stretch", hide_index=True, height=min(760, 110 + len(result.industry_leaders) * 35))
    render_data_health_table(artifacts)


def _breadth_label(value: float) -> str:
    if value >= 60.0:
        return "Positive"
    if value <= 40.0:
        return "Negative"
    return "Neutral"


def _performance_label(value: float) -> str:
    if value > 0:
        return "Positive"
    if value < 0:
        return "Negative"
    return "Neutral"


def render_market_dashboard(artifacts: PlatformArtifacts) -> None:
    result = artifacts.market_result
    render_page_header("Market Dashboard", meta=result.update_time.split("T")[-1] if result.update_time else "N/A", centered=True)
    render_stat_cards(
        [
            ("Market Score", f"{result.score:.2f}", "current composite", _tone_class(result.label)),
            ("Label", str(result.label), "current regime", _tone_class(result.label)),
            ("1W Ago", f"{result.score_1w_ago:.2f}" if result.score_1w_ago is not None else "N/A", "prior score", "neutral"),
            ("1M Ago", f"{result.score_1m_ago:.2f}" if result.score_1m_ago is not None else "N/A", "prior score", "neutral"),
            ("VIX", f"{result.vix_close:.2f}" if result.vix_close is not None else "N/A", "latest close", "neutral"),
        ]
    )

    time_axis = pd.DataFrame(
        [
            {"Point": "Now", "Score": result.score},
            {"Point": "1D Ago", "Score": result.score_1d_ago},
            {"Point": "1W Ago", "Score": result.score_1w_ago},
            {"Point": "1M Ago", "Score": result.score_1m_ago},
            {"Point": "3M Ago", "Score": result.score_3m_ago},
        ]
    )
    breadth_frame = pd.DataFrame(
        [
            {"Metric": key, "Value": value, "Label": _breadth_label(float(value))}
            for key, value in result.breadth_summary.items()
        ]
    )
    performance_frame = pd.DataFrame(
        [
            {"Metric": key, "Value": value, "Label": _performance_label(float(value))}
            for key, value in result.performance_overview.items()
        ]
    )

    hero_col, summary_col = st.columns([1.0, 1.8])
    with hero_col:
        score_class = _tone_class(result.label)
        with st.container(border=True):
            render_section_heading("Market Conditions", "Composite score from breadth, trend, performance, highs, and VIX")
            st.markdown(
                f"<div class='oratek-hero-card'><div class='oratek-hero-copy'>Market conditions are determined by the configured breadth, performance, and volatility inputs. The underlying scoring logic is unchanged.</div><div class='oratek-hero-badge {score_class}'>{html.escape(str(result.label))}<span class='oratek-hero-score'>{result.score:.2f}</span></div></div>",
                unsafe_allow_html=True,
            )
            st.progress(min(max(result.score / 100.0, 0.0), 1.0))
        with st.container(border=True):
            render_section_heading("Score Timeline")
            st.dataframe(time_axis, width="stretch", hide_index=True)
    with summary_col:
        upper_left, upper_right = st.columns([1.2, 1.0])
        with upper_left:
            with st.container(border=True):
                render_section_heading("Breadth & Trend Metrics")
                st.dataframe(breadth_frame, width="stretch", hide_index=True)
        with upper_right:
            with st.container(border=True):
                render_section_heading("Performance Overview")
                st.dataframe(performance_frame, width="stretch", hide_index=True)
        lower_left, lower_right = st.columns([0.9, 1.1])
        with lower_left:
            with st.container(border=True):
                render_section_heading("High & VIX")
                st.dataframe(pd.DataFrame([{"Metric": key, "Value": value} for key, value in result.high_vix_summary.items()]), width="stretch", hide_index=True)
        with lower_right:
            with st.container(border=True):
                render_section_heading("Component Scores")
                st.dataframe(pd.DataFrame([{"Component": key, "Score": value} for key, value in result.component_scores.items()]), width="stretch", hide_index=True, height=min(460, 110 + len(result.component_scores) * 35))

    snapshot_col, factor_col = st.columns([2.0, 1.05])
    with snapshot_col:
        with st.container(border=True):
            render_section_heading("Market Snapshot", "Vol % is versus the 50-day average")
            if result.market_snapshot.empty:
                st.caption("No market snapshot rows available.")
            else:
                st.dataframe(result.market_snapshot, width="stretch", hide_index=True, height=min(360, 110 + len(result.market_snapshot) * 35))
    with factor_col:
        with st.container(border=True):
            render_section_heading("Factors vs SP500", "Relative performance versus the S&P 500")
            if result.factors_vs_sp500.empty:
                st.caption("No factor-relative-strength rows available.")
            else:
                st.dataframe(result.factors_vs_sp500, width="stretch", hide_index=True, height=min(360, 110 + len(result.factors_vs_sp500) * 35))

    with st.container(border=True):
        render_section_heading("S&P 500 Stocks > 200-Day Moving Average (S5TH)")
        if result.s5th_series.empty:
            st.caption("No S5TH series available.")
        else:
            chart_source = result.s5th_series.set_index("date")
            st.line_chart(chart_source[["pct_above_sma200"]], width="stretch")
    render_data_health_table(artifacts)


def main() -> None:
    inject_global_styles()
    default_config = ROOT / "config" / "default.yaml"

    with st.sidebar:
        st.markdown("<div class='oratek-sidebar-title'>Growth Trading Screener</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='oratek-sidebar-caption'>Refresh cached universes and inspect watchlist, radar, and market conditions without changing the underlying pipeline.</div>",
            unsafe_allow_html=True,
        )
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
    render_context_strip([f"Data source: {artifacts.data_source_label}"])
    render_data_health_banner(artifacts)

    if page == "Today's Watchlist":
        render_watchlist(artifacts)
    elif page == "RS Radar":
        render_rs_radar(artifacts)
    else:
        render_market_dashboard(artifacts)


if __name__ == "__main__":
    main()
