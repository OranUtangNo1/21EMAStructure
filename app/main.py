from __future__ import annotations

import html
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.configuration import load_settings
from src.dashboard.effectiveness import sync_preset_effectiveness_logs
from src.dashboard.watchlist import WatchlistViewModelBuilder
from src.pipeline import PlatformArtifacts, ResearchPlatform
from src.scan.rules import DuplicateRuleConfig, ScanConfig
from src.ui_preferences import UserPreferenceStore


st.set_page_config(
    page_title="Growth Trading Screener",
    layout="wide",
    initial_sidebar_state="expanded",
)

WATCHLIST_PRESET_GROUP = "watchlist_presets"
WATCHLIST_PRESET_KIND = "watchlist_controls"
WATCHLIST_PRESET_SCHEMA_VERSION = 1
WATCHLIST_PRESET_LIMIT = 10
PAGE_SELECTION_KEY = "active_page"

GLOBAL_CSS = """
<style>
:root { --bg:#f3f5fb; --panel:#ffffff; --panel-border:#dbe4f3; --text:#223045; --muted:#6f7f98; }
html, body, [class*="css"] { font-family:"Aptos","Segoe UI","Yu Gothic UI",sans-serif; }
[data-testid="stAppViewContainer"] { background:radial-gradient(circle at top left, rgba(86,138,237,.12), transparent 26%), linear-gradient(180deg, #f8fbff 0%, var(--bg) 100%); color:var(--text); }
header[data-testid="stHeader"] { display:none; }
.block-container { max-width:1440px; padding-top:.9rem; padding-bottom:2.3rem; }
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
.oratek-priority-item-rs { color:#2d6cdf; font-size:.74rem; font-weight:800; letter-spacing:.04em; text-transform:uppercase; margin-bottom:.18rem; }
.oratek-priority-item-ticker { color:var(--text); font-size:.98rem; font-weight:800; }
.oratek-market-panel { background:rgba(255,255,255,.95); border:1px solid var(--panel-border); border-radius:24px; box-shadow:0 18px 36px rgba(34,48,69,.06); padding:1rem 1.05rem 1.1rem; margin-bottom:1rem; }
.oratek-market-panel-title { color:var(--text); font-size:.82rem; font-weight:800; text-transform:uppercase; letter-spacing:.08em; margin-bottom:.85rem; }
.oratek-market-panel-title.centered { text-align:center; }
.oratek-market-copy-head { color:var(--text); font-size:.88rem; font-weight:800; margin-bottom:.35rem; }
.oratek-market-copy { color:var(--muted); font-size:.84rem; line-height:1.55; }
.oratek-market-score-chip { display:inline-flex; align-items:center; justify-content:center; gap:.45rem; padding:.72rem 1rem; border-radius:16px; margin:1rem 0 .8rem; font-size:1rem; font-weight:800; min-width:136px; }
.oratek-market-score-chip.positive { background:linear-gradient(135deg, #1fb87b 0%, #27c997 100%); color:#fff; }
.oratek-market-score-chip.negative { background:linear-gradient(135deg, #f15050 0%, #ef3d52 100%); color:#fff; }
.oratek-market-score-chip.neutral { background:linear-gradient(135deg, #7f8ca6 0%, #94a1ba 100%); color:#fff; }
.oratek-market-gauge { width:220px; margin:0 auto .2rem; }
.oratek-market-gauge-svg { display:block; width:220px; height:120px; }
.oratek-market-gauge-track { fill:none; stroke:#e8eef8; stroke-width:28; stroke-linecap:round; }
.oratek-market-gauge-value { fill:none; stroke-width:28; stroke-linecap:round; stroke-dasharray:var(--market-score-filled) var(--market-score-remaining); }
.oratek-market-gauge-value.positive { stroke:#21a46f; }
.oratek-market-gauge-value.negative { stroke:#ef4c54; }
.oratek-market-gauge-value.neutral { stroke:#8a97b0; }
.oratek-market-gauge-inner { fill:none; stroke:#dbe4f3; stroke-width:1.5; }
.oratek-market-gauge-core { fill:rgba(255,255,255,.96); stroke:rgba(219,228,243,.9); stroke-width:1.5; }
.oratek-market-gauge-caption { text-align:center; color:var(--muted); font-size:.78rem; margin-top:.2rem; }
.oratek-market-timeline-stack { display:grid; gap:.72rem; }
.oratek-market-mini-card { background:rgba(255,255,255,.95); border:1px solid var(--panel-border); border-radius:20px; box-shadow:0 14px 30px rgba(34,48,69,.05); padding:.88rem .95rem; }
.oratek-market-mini-head { display:flex; justify-content:space-between; gap:.75rem; align-items:flex-start; }
.oratek-market-mini-title { color:var(--text); font-size:.84rem; font-weight:800; text-transform:uppercase; letter-spacing:.04em; }
.oratek-market-mini-state { color:var(--muted); font-size:.78rem; margin-top:.28rem; }
.oratek-market-mini-score { min-width:58px; text-align:center; border-radius:12px; padding:.36rem .55rem; font-size:.92rem; font-weight:800; }
.oratek-market-mini-score.positive { background:rgba(33,164,111,.14); color:#21a46f; }
.oratek-market-mini-score.negative { background:rgba(223,91,91,.14); color:#df5b5b; }
.oratek-market-mini-score.neutral { background:rgba(127,140,166,.14); color:#7f8ca6; }
.oratek-market-metric-grid { display:grid; gap:.75rem; }
.oratek-market-metric-grid.cols-6 { grid-template-columns:repeat(6, minmax(0,1fr)); }
.oratek-market-metric-grid.cols-4 { grid-template-columns:repeat(4, minmax(0,1fr)); }
.oratek-market-metric-grid.cols-2 { grid-template-columns:repeat(2, minmax(0,1fr)); }
.oratek-market-metric-card { background:#fbfcff; border:1px solid #e6edf9; border-radius:18px; padding:.78rem .6rem; text-align:center; min-height:112px; display:flex; flex-direction:column; justify-content:space-between; }
.oratek-market-metric-name { color:var(--muted); font-size:.74rem; font-weight:800; text-transform:uppercase; letter-spacing:.05em; }
.oratek-market-metric-value { color:var(--text); font-size:1.06rem; font-weight:800; margin:.45rem 0 .55rem; }
.oratek-market-pill { display:inline-flex; align-items:center; justify-content:center; border-radius:999px; padding:.34rem .65rem; font-size:.74rem; font-weight:800; }
.oratek-market-pill.positive { background:rgba(33,164,111,.14); color:#21a46f; }
.oratek-market-pill.negative { background:rgba(223,91,91,.14); color:#df5b5b; }
.oratek-market-pill.neutral { background:rgba(127,140,166,.14); color:#7f8ca6; }
.oratek-market-stage-head { margin:.4rem 0 .65rem; }
.oratek-market-stage-title { color:var(--text); font-size:1rem; font-weight:800; text-align:center; }
.oratek-market-stage-caption { color:var(--muted); font-size:.78rem; text-align:center; margin-top:.18rem; }
.oratek-market-snapshot-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:1rem; }
.oratek-market-snapshot-card { background:rgba(255,255,255,.95); border:1px solid var(--panel-border); border-radius:22px; box-shadow:0 18px 36px rgba(34,48,69,.06); padding:.9rem 1rem 1rem; }
.oratek-market-snapshot-head { display:flex; justify-content:space-between; gap:.65rem; align-items:flex-start; }
.oratek-market-snapshot-name { color:var(--muted); font-size:.78rem; font-weight:700; line-height:1.35; max-width:70%; }
.oratek-market-snapshot-ticker { color:var(--text); font-size:1.62rem; font-weight:800; letter-spacing:-.03em; margin-top:.55rem; }
.oratek-market-snapshot-price-row { display:flex; justify-content:space-between; gap:.75rem; align-items:baseline; margin-top:.55rem; }
.oratek-market-snapshot-price { color:var(--text); font-size:1.42rem; font-weight:800; }
.oratek-market-snapshot-day { font-size:1.08rem; font-weight:800; text-align:right; }
.oratek-market-snapshot-volume { color:var(--muted); font-size:.78rem; text-align:right; margin-top:.28rem; }
.oratek-market-factors-panel { background:rgba(255,255,255,.95); border:1px solid var(--panel-border); border-radius:22px; box-shadow:0 18px 36px rgba(34,48,69,.06); padding:.9rem .95rem 1rem; }
.oratek-market-factor-list { display:grid; gap:.72rem; }
.oratek-market-factor-row { background:#fbfcff; border:1px solid #e6edf9; border-radius:18px; padding:.8rem .85rem; }
.oratek-market-factor-head { display:flex; justify-content:space-between; gap:.5rem; align-items:baseline; margin-bottom:.55rem; }
.oratek-market-factor-name { color:var(--text); font-size:.92rem; font-weight:800; }
.oratek-market-factor-ticker { color:var(--muted); font-size:.72rem; font-weight:700; text-transform:uppercase; letter-spacing:.06em; }
.oratek-market-factor-metrics { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:.65rem; }
.oratek-market-factor-metric-head { display:flex; justify-content:space-between; gap:.4rem; align-items:center; font-size:.73rem; font-weight:800; margin-bottom:.28rem; }
.oratek-market-factor-period { color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }
.oratek-market-factor-value { font-weight:800; }
.oratek-market-factor-bar { height:8px; border-radius:999px; background:#edf1f7; overflow:hidden; }
.oratek-market-factor-fill { display:block; height:100%; border-radius:999px; }
.oratek-market-factor-fill.positive { background:linear-gradient(90deg, #39cf9a 0%, #17b07d 100%); }
.oratek-market-factor-fill.negative { background:linear-gradient(90deg, #ff8a7a 0%, #ef4d53 100%); }
.oratek-market-factor-fill.neutral { background:linear-gradient(90deg, #aeb9ca 0%, #8a97b0 100%); }
@media (max-width:768px) { .oratek-page-meta, .oratek-page-submeta { text-align:left; padding-top:.15rem; } .oratek-ticker-grid { grid-template-columns:repeat(3, minmax(0,1fr)); } .oratek-priority-grid { grid-template-columns:repeat(4, minmax(0,1fr)); } .oratek-mover-row { grid-template-columns:1fr; } .oratek-mover-side { text-align:left; } .oratek-market-gauge { width:180px; height:96px; } .oratek-market-metric-grid.cols-6, .oratek-market-metric-grid.cols-4 { grid-template-columns:repeat(2, minmax(0,1fr)); } .oratek-market-metric-grid.cols-2, .oratek-market-factor-metrics { grid-template-columns:repeat(2, minmax(0,1fr)); } .oratek-market-snapshot-grid { grid-template-columns:1fr; } .oratek-market-snapshot-price-row { align-items:flex-start; flex-direction:column; } }
</style>
"""


@dataclass(frozen=True)
class AppPageDefinition:
    key: str
    label: str


@dataclass(frozen=True)
class WatchlistSidebarState:
    scan_config: ScanConfig
    selected_scan_names: list[str]
    selected_annotation_filters: list[str]
    selected_duplicate_subfilters: list[str]
    duplicate_threshold: int
    duplicate_rule: dict[str, object] | None = None
    selected_preset_export_name: str | None = None
    selected_preset_export_values: dict[str, object] | None = None


APP_PAGES: tuple[AppPageDefinition, ...] = (
    AppPageDefinition("watchlist", "Today's Watchlist"),
    AppPageDefinition("rs_radar", "RS Radar"),
    AppPageDefinition("market_dashboard", "Market Dashboard"),
)
APP_PAGE_KEYS = tuple(page.key for page in APP_PAGES)
APP_PAGE_LABELS = {page.key: page.label for page in APP_PAGES}
DEFAULT_PAGE_KEY = APP_PAGES[0].key

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
    body = "".join(f"<div class='oratek-priority-item'><div class='oratek-priority-item-ticker'>{html.escape(ticker)}</div></div>" for ticker in tickers)
    if not body:
        body = f"<div class='oratek-empty-state'>{html.escape(empty_text)}</div>"
    else:
        body = f"<div class='oratek-priority-grid'>{body}</div>"
    st.markdown(
        f"<div class='oratek-priority-band'><div class='oratek-priority-head'><div><div class='oratek-priority-kicker'>Priority Focus</div><div class='oratek-priority-title'>{html.escape(title)}</div><div class='oratek-priority-note'>{html.escape(note)}</div></div><div class='oratek-priority-count'>{count} tickers</div></div>{body}</div>",
        unsafe_allow_html=True,
    )


def render_priority_band_from_frame(
    title: str,
    frame: pd.DataFrame,
    note: str,
    empty_text: str,
    metric_label: str = "RS",
    metric_column: str = "Hybrid-RS",
) -> None:
    count = len(frame.index) if frame is not None else 0
    if frame is None or frame.empty or "Ticker" not in frame.columns:
        body = f"<div class='oratek-empty-state'>{html.escape(empty_text)}</div>"
    else:
        items: list[str] = []
        for _, row in frame.iterrows():
            ticker = str(row.get("Ticker", "")).strip()
            if not ticker:
                continue
            metric_value = row.get(metric_column)
            metric_html = ""
            if pd.notna(metric_value):
                metric_text = _format_metric_value(metric_value)
                metric_html = f"<div class='oratek-priority-item-rs'>{html.escape(metric_label)} {html.escape(metric_text)}</div>"
            items.append(
                f"<div class='oratek-priority-item'>{metric_html}<div class='oratek-priority-item-ticker'>{html.escape(ticker)}</div></div>"
            )
        body = f"<div class='oratek-priority-grid'>{''.join(items)}</div>" if items else f"<div class='oratek-empty-state'>{html.escape(empty_text)}</div>"
    st.markdown(
        f"<div class='oratek-priority-band'><div class='oratek-priority-head'><div><div class='oratek-priority-kicker'>Priority Focus</div><div class='oratek-priority-title'>{html.escape(title)}</div><div class='oratek-priority-note'>{html.escape(note)}</div></div><div class='oratek-priority-count'>{count} tickers</div></div>{body}</div>",
        unsafe_allow_html=True,
    )


def _format_metric_value(value: object) -> str:
    number = _coerce_number(value)
    if number is None:
        return str(value).strip()
    return f"{number:.1f}"


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


def load_scan_config(config_path: str) -> ScanConfig:
    settings = load_settings(config_path)
    return ScanConfig.from_dict(settings.get("scan", {}))


def _latest_trade_date_for_export(artifacts: PlatformArtifacts) -> str:
    if artifacts.snapshot.empty or "trade_date" not in artifacts.snapshot.columns:
        return datetime.now().strftime("%Y-%m-%d")
    trade_date = pd.to_datetime(artifacts.snapshot["trade_date"], errors="coerce").max()
    if pd.isna(trade_date):
        return datetime.now().strftime("%Y-%m-%d")
    return pd.Timestamp(trade_date).strftime("%Y-%m-%d")


def _export_folder_name(artifacts: PlatformArtifacts) -> str:
    trade_date = _latest_trade_date_for_export(artifacts)
    return trade_date.replace("-", "")


def _resolve_preset_export_directory(config_path: str, output_dir: str, artifacts: PlatformArtifacts) -> Path:
    base_dir = Path(output_dir).expanduser()
    if not base_dir.is_absolute():
        base_dir = ROOT / base_dir
    return base_dir / _export_folder_name(artifacts)


def export_watchlist_preset_csvs(config_path: str, artifacts: PlatformArtifacts) -> Path | None:
    scan_config = load_scan_config(config_path)
    export_config = scan_config.preset_csv_export
    if not export_config.enabled:
        return None

    export_presets = [preset for preset in scan_config.watchlist_presets if preset.export_enabled]
    if not export_presets:
        return None

    builder = WatchlistViewModelBuilder(scan_config)
    trade_date = _latest_trade_date_for_export(artifacts)
    output_date = datetime.now().strftime("%Y-%m-%d")
    export_dir = _resolve_preset_export_directory(config_path, export_config.output_dir, artifacts)
    export_dir.mkdir(parents=True, exist_ok=True)

    summary_frame = builder.build_preset_summary_exports(
        export_presets,
        artifacts.watchlist,
        artifacts.scan_hits,
        trade_date=trade_date,
        output_date=output_date,
        top_ticker_limit=export_config.top_ticker_limit,
    )
    summary_frame.to_csv(export_dir / "preset_summary.csv", index=False)

    if export_config.write_details:
        details_frame = builder.build_preset_detail_exports(
            export_presets,
            artifacts.watchlist,
            artifacts.scan_hits,
        )
        details_frame.to_csv(export_dir / "preset_details.csv", index=False)

    return export_dir


def load_user_preference_store(config_path: str) -> UserPreferenceStore:
    settings = load_settings(config_path)
    app_settings = settings.get("app", {}) if isinstance(settings.get("app", {}), dict) else {}
    configured_path = str(app_settings.get("user_preferences_path", "")).strip()
    if configured_path:
        preference_path = Path(configured_path).expanduser()
        if not preference_path.is_absolute():
            preference_path = ROOT / preference_path
    else:
        cache_dir = Path(str(app_settings.get("cache_dir", "data_cache"))).expanduser()
        if not cache_dir.is_absolute():
            cache_dir = ROOT / cache_dir
        preference_path = cache_dir / "user_preferences.yaml"
    return UserPreferenceStore(preference_path)


def watchlist_preference_namespace(config_path: str) -> str:
    return str(Path(config_path).expanduser().resolve(strict=False))


def current_page_key() -> str:
    page_key = str(st.session_state.get(PAGE_SELECTION_KEY, DEFAULT_PAGE_KEY))
    if page_key not in APP_PAGE_LABELS:
        page_key = DEFAULT_PAGE_KEY
        st.session_state[PAGE_SELECTION_KEY] = page_key
    return page_key


def render_page_tabs() -> str:
    page_key = current_page_key()
    selected_page = st.segmented_control(
        "Page",
        options=list(APP_PAGE_KEYS),
        default=page_key,
        format_func=lambda key: APP_PAGE_LABELS.get(key, str(key)),
        selection_mode="single",
        key=PAGE_SELECTION_KEY,
        label_visibility="collapsed",
    )
    if selected_page is None:
        return page_key
    return str(selected_page)


def _normalize_watchlist_preset_name(raw_value: object) -> str:
    return str(raw_value).strip()


def _build_watchlist_control_values(
    selected_scan_names: list[str],
    selected_annotation_filters: list[str],
    selected_duplicate_subfilters: list[str],
    duplicate_threshold: int,
    duplicate_rule: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "selected_scan_names": list(selected_scan_names),
        "selected_annotation_filters": list(selected_annotation_filters),
        "selected_duplicate_subfilters": list(selected_duplicate_subfilters),
        "duplicate_threshold": int(duplicate_threshold),
        "duplicate_rule": dict(duplicate_rule) if isinstance(duplicate_rule, dict) else DuplicateRuleConfig(min_count=int(duplicate_threshold)).to_dict(),
    }


def _watchlist_controls_equal(left: dict[str, object] | None, right: dict[str, object] | None) -> bool:
    if left is None or right is None:
        return False
    return _build_watchlist_control_values(
        list(left.get("selected_scan_names", [])),
        list(left.get("selected_annotation_filters", [])),
        list(left.get("selected_duplicate_subfilters", [])),
        int(left.get("duplicate_threshold", 1)),
        left.get("duplicate_rule"),
    ) == _build_watchlist_control_values(
        list(right.get("selected_scan_names", [])),
        list(right.get("selected_annotation_filters", [])),
        list(right.get("selected_duplicate_subfilters", [])),
        int(right.get("duplicate_threshold", 1)),
        right.get("duplicate_rule"),
    )


def _build_watchlist_preset_record(values: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": WATCHLIST_PRESET_SCHEMA_VERSION,
        "kind": WATCHLIST_PRESET_KIND,
        "values": values,
    }


def _build_builtin_watchlist_presets(scan_config: ScanConfig) -> dict[str, dict[str, object]]:
    presets: dict[str, dict[str, object]] = {}
    for preset in scan_config.watchlist_presets:
        if not preset.visible_in_ui:
            continue
        preset_name = _normalize_watchlist_preset_name(preset.preset_name)
        if not preset_name:
            continue
        presets[preset_name] = preset.to_control_values()
    return presets


def _read_watchlist_preset_values(
    record: object,
    *,
    available_scan_names: list[str],
    available_annotation_names: list[str],
    available_duplicate_subfilters: list[str],
    default_duplicate_threshold: int,
) -> dict[str, object] | None:
    if not isinstance(record, dict):
        return None
    if any(key in record for key in ("schema_version", "kind", "values")):
        schema_version = record.get("schema_version")
        if schema_version not in (None, WATCHLIST_PRESET_SCHEMA_VERSION):
            return None
        kind = str(record.get("kind", WATCHLIST_PRESET_KIND)).strip()
        if kind != WATCHLIST_PRESET_KIND:
            return None
        values = record.get("values", {})
        if not isinstance(values, dict):
            return None
    else:
        values = record

    raw_selected_scan_names = [str(name) for name in values.get("selected_scan_names", [])]
    if any(name not in available_scan_names for name in raw_selected_scan_names):
        return None
    selected_scan_names = raw_selected_scan_names
    selected_annotation_filters = [
        str(name)
        for name in values.get("selected_annotation_filters", [])
        if str(name) in available_annotation_names
    ]
    selected_duplicate_subfilters = [
        str(name)
        for name in values.get("selected_duplicate_subfilters", [])
        if str(name) in available_duplicate_subfilters
    ]

    try:
        duplicate_threshold = int(values.get("duplicate_threshold", default_duplicate_threshold))
    except (TypeError, ValueError):
        duplicate_threshold = int(default_duplicate_threshold)
    max_threshold = max(1, len(selected_scan_names)) if selected_scan_names else 1
    duplicate_threshold = max(1, min(duplicate_threshold, max_threshold))
    duplicate_rule = values.get("duplicate_rule")
    try:
        parsed_duplicate_rule = DuplicateRuleConfig.from_dict(
            duplicate_rule if isinstance(duplicate_rule, dict) else None,
            default_min_count=duplicate_threshold,
        ).to_dict()
    except ValueError:
        return None

    return _build_watchlist_control_values(
        selected_scan_names,
        selected_annotation_filters,
        selected_duplicate_subfilters,
        duplicate_threshold,
        parsed_duplicate_rule,
    )


def _apply_watchlist_preset_to_session_state(
    values: dict[str, object],
    *,
    selection_key: str,
    annotation_key: str,
    duplicate_subfilter_key: str,
    threshold_key: str,
    duplicate_rule_key: str,
) -> None:
    st.session_state[selection_key] = list(values.get("selected_scan_names", []))
    st.session_state[annotation_key] = list(values.get("selected_annotation_filters", []))
    st.session_state[duplicate_subfilter_key] = list(values.get("selected_duplicate_subfilters", []))
    st.session_state[threshold_key] = int(values.get("duplicate_threshold", 1))
    st.session_state[duplicate_rule_key] = values.get("duplicate_rule")


def _build_watchlist_preset_export_filename(preset_name: str) -> str:
    safe_name = "".join(char if char.isalnum() else "_" for char in str(preset_name).strip())
    safe_name = safe_name.strip("_") or "preset"
    return f"watchlist_preset_{safe_name.lower()}.csv"


def _dataframe_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")


def render_watchlist_sidebar_controls(config_path: str) -> WatchlistSidebarState:
    watchlist_scan_config = load_scan_config(config_path)
    watchlist_preference_store = load_user_preference_store(config_path)
    watchlist_preferences_namespace = watchlist_preference_namespace(config_path)
    watchlist_preferences = watchlist_preference_store.load_group("watchlist_controls", watchlist_preferences_namespace)
    raw_watchlist_presets = watchlist_preference_store.load_collection(
        WATCHLIST_PRESET_GROUP,
        watchlist_preferences_namespace,
    )
    builtin_watchlist_presets = _build_builtin_watchlist_presets(watchlist_scan_config)
    card_sections = watchlist_scan_config.card_sections
    annotation_filters = watchlist_scan_config.annotation_filters
    available_duplicate_subfilters = list(WatchlistViewModelBuilder(watchlist_scan_config).available_duplicate_subfilters())
    available_scan_names = [section.scan_name for section in card_sections]
    display_names = {section.scan_name: section.display_name or section.scan_name for section in card_sections}
    available_annotation_names = [section.filter_name for section in annotation_filters]
    annotation_display_names = {
        section.filter_name: section.display_name or section.filter_name
        for section in annotation_filters
    }

    selection_key = "watchlist_selected_scan_names"
    selection_defaults_key = "watchlist_selected_scan_names_defaults"
    annotation_key = "watchlist_selected_annotation_filters"
    annotation_defaults_key = "watchlist_selected_annotation_filters_defaults"
    duplicate_subfilter_key = "watchlist_selected_duplicate_subfilters"
    duplicate_subfilter_defaults_key = "watchlist_selected_duplicate_subfilters_defaults"
    threshold_key = "watchlist_duplicate_threshold"
    threshold_defaults_key = "watchlist_duplicate_threshold_defaults"
    duplicate_rule_key = "watchlist_duplicate_rule"
    preset_select_key = "watchlist_selected_preset_name"
    preset_name_key = "watchlist_preset_name"
    preset_name_pending_key = "watchlist_preset_name_pending"
    preset_feedback_key = "watchlist_preset_feedback"

    default_selected_scan_names = list(watchlist_scan_config.startup_selected_scan_names())
    persisted_selected_scan_names = watchlist_preferences.get("selected_scan_names", default_selected_scan_names)
    if not isinstance(persisted_selected_scan_names, list):
        persisted_selected_scan_names = default_selected_scan_names
    persisted_selected_scan_names = [
        str(name) for name in persisted_selected_scan_names if str(name) in available_scan_names
    ]
    selection_defaults_signature = (
        watchlist_preferences_namespace,
        tuple(available_scan_names),
        tuple(default_selected_scan_names),
    )

    default_annotation_names = [
        name
        for name in watchlist_scan_config.enabled_annotation_filters
        if name in available_annotation_names
    ]
    persisted_annotation_names = watchlist_preferences.get("selected_annotation_filters", default_annotation_names)
    if not isinstance(persisted_annotation_names, list):
        persisted_annotation_names = default_annotation_names
    persisted_annotation_names = [
        str(name) for name in persisted_annotation_names if str(name) in available_annotation_names
    ]
    annotation_defaults_signature = (
        watchlist_preferences_namespace,
        tuple(available_annotation_names),
        tuple(default_annotation_names),
    )

    default_duplicate_subfilters: list[str] = []
    persisted_duplicate_subfilters = watchlist_preferences.get(
        "selected_duplicate_subfilters",
        default_duplicate_subfilters,
    )
    if not isinstance(persisted_duplicate_subfilters, list):
        persisted_duplicate_subfilters = default_duplicate_subfilters
    persisted_duplicate_subfilters = [
        str(name) for name in persisted_duplicate_subfilters if str(name) in available_duplicate_subfilters
    ]
    duplicate_subfilter_defaults_signature = (
        watchlist_preferences_namespace,
        tuple(available_duplicate_subfilters),
        tuple(default_duplicate_subfilters),
    )

    persisted_duplicate_threshold = watchlist_preferences.get(
        "duplicate_threshold",
        int(watchlist_scan_config.duplicate_min_count),
    )
    try:
        persisted_duplicate_threshold_int = int(persisted_duplicate_threshold)
    except (TypeError, ValueError):
        persisted_duplicate_threshold_int = int(watchlist_scan_config.duplicate_min_count)
    persisted_duplicate_threshold_int = max(
        1,
        min(persisted_duplicate_threshold_int, max(1, len(persisted_selected_scan_names)) if persisted_selected_scan_names else 1),
    )
    persisted_duplicate_rule = DuplicateRuleConfig.from_dict(
        watchlist_preferences.get("duplicate_rule"),
        default_min_count=persisted_duplicate_threshold_int,
    ).to_dict()

    saved_watchlist_presets: dict[str, dict[str, object]] = {}
    for raw_name, raw_record in raw_watchlist_presets.items():
        preset_name = _normalize_watchlist_preset_name(raw_name)
        if not preset_name:
            continue
        preset_values = _read_watchlist_preset_values(
            raw_record,
            available_scan_names=available_scan_names,
            available_annotation_names=available_annotation_names,
            available_duplicate_subfilters=available_duplicate_subfilters,
            default_duplicate_threshold=persisted_duplicate_threshold_int,
        )
        if preset_values is None:
            continue
        saved_watchlist_presets[preset_name] = preset_values
    watchlist_presets: dict[str, dict[str, object]] = {
        **builtin_watchlist_presets,
        **saved_watchlist_presets,
    }

    st.markdown("**Watchlist Presets**")
    feedback_message = st.session_state.pop(preset_feedback_key, "")
    if feedback_message:
        st.success(feedback_message)
    if preset_name_pending_key in st.session_state:
        st.session_state[preset_name_key] = st.session_state.pop(preset_name_pending_key)

    preset_options = [""] + list(watchlist_presets)
    selected_preset_name = st.selectbox(
        "Saved preset",
        options=preset_options,
        key=preset_select_key,
        format_func=lambda name: name if name else "Select a preset",
    )
    selected_preset_is_builtin = bool(selected_preset_name and selected_preset_name in builtin_watchlist_presets)
    selected_preset_export_name = selected_preset_name or None
    selected_preset_export_values = watchlist_presets.get(selected_preset_name) if selected_preset_name else None
    preset_action_columns = st.columns(2)
    load_preset = preset_action_columns[0].button(
        "Load Preset",
        use_container_width=True,
        disabled=not selected_preset_name,
    )
    delete_preset = preset_action_columns[1].button(
        "Delete Preset",
        use_container_width=True,
        disabled=not selected_preset_name or selected_preset_is_builtin,
    )

    if load_preset and selected_preset_name:
        loaded_values = watchlist_presets.get(selected_preset_name)
        if loaded_values is not None:
            _apply_watchlist_preset_to_session_state(
                loaded_values,
                selection_key=selection_key,
                annotation_key=annotation_key,
                duplicate_subfilter_key=duplicate_subfilter_key,
                threshold_key=threshold_key,
                duplicate_rule_key=duplicate_rule_key,
            )
            st.session_state[selection_defaults_key] = selection_defaults_signature
            st.session_state[annotation_defaults_key] = annotation_defaults_signature
            st.session_state[duplicate_subfilter_defaults_key] = duplicate_subfilter_defaults_signature
            st.session_state[threshold_defaults_key] = (
                watchlist_preferences_namespace,
                max(1, len(loaded_values["selected_scan_names"])) if loaded_values["selected_scan_names"] else 1,
            )
            st.session_state[preset_name_key] = selected_preset_name
            st.success(f"Loaded preset '{selected_preset_name}'.")

    if delete_preset and selected_preset_name:
        watchlist_preference_store.delete_collection_item(
            WATCHLIST_PRESET_GROUP,
            watchlist_preferences_namespace,
            selected_preset_name,
        )
        st.session_state[preset_select_key] = ""
        st.session_state[preset_name_pending_key] = ""
        st.session_state[preset_feedback_key] = f"Deleted preset '{selected_preset_name}'."
        st.rerun()

    st.caption(
        f"Built-in: {len(builtin_watchlist_presets)} | Saved: {len(saved_watchlist_presets)}/{WATCHLIST_PRESET_LIMIT}"
    )

    st.markdown("**Watchlist Controls**")
    current_selected_scan_names = st.session_state.get(
        selection_key,
        persisted_selected_scan_names,
    )
    if st.session_state.get(selection_defaults_key) != selection_defaults_signature:
        st.session_state[selection_key] = persisted_selected_scan_names
        st.session_state[selection_defaults_key] = selection_defaults_signature
    else:
        st.session_state[selection_key] = [
            name for name in current_selected_scan_names if name in available_scan_names
        ]

    selected_watchlist_scans = st.multiselect(
        "Cards used for display and Duplicate counting",
        options=available_scan_names,
        format_func=lambda name: display_names.get(name, name),
        key=selection_key,
    )

    if st.session_state.get(annotation_defaults_key) != annotation_defaults_signature:
        st.session_state[annotation_key] = persisted_annotation_names
        st.session_state[annotation_defaults_key] = annotation_defaults_signature
    else:
        st.session_state[annotation_key] = [
            name for name in st.session_state.get(annotation_key, persisted_annotation_names)
            if name in available_annotation_names
        ]

    selected_annotation_filters = st.multiselect(
        "Post-scan filters (AND)",
        options=available_annotation_names,
        format_func=lambda name: annotation_display_names.get(name, name),
        key=annotation_key,
        help="Filters are applied after scan eligibility. They narrow displayed cards and Duplicate Tickers without changing the underlying scan candidate set.",
    )

    if st.session_state.get(duplicate_subfilter_defaults_key) != duplicate_subfilter_defaults_signature:
        st.session_state[duplicate_subfilter_key] = persisted_duplicate_subfilters
        st.session_state[duplicate_subfilter_defaults_key] = duplicate_subfilter_defaults_signature
    else:
        st.session_state[duplicate_subfilter_key] = [
            name
            for name in st.session_state.get(duplicate_subfilter_key, persisted_duplicate_subfilters)
            if name in available_duplicate_subfilters
        ]

    selected_duplicate_subfilters = st.multiselect(
        "Duplicate subfilters",
        options=available_duplicate_subfilters,
        key=duplicate_subfilter_key,
        help="Applied only to Duplicate Tickers after duplicate thresholding. Top3 HybridRS keeps the three highest hybrid_score names among duplicate candidates.",
    )

    max_threshold = max(1, len(selected_watchlist_scans)) if selected_watchlist_scans else 1
    threshold_defaults_signature = (watchlist_preferences_namespace, max_threshold)
    if st.session_state.get(threshold_defaults_key) != threshold_defaults_signature:
        st.session_state[threshold_key] = min(persisted_duplicate_threshold_int, max_threshold)
        st.session_state[threshold_defaults_key] = threshold_defaults_signature
    else:
        st.session_state[threshold_key] = max(
            1,
            min(int(st.session_state.get(threshold_key, persisted_duplicate_threshold_int)), max_threshold),
        )

    duplicate_threshold = int(
        st.number_input(
            "Duplicate threshold",
            min_value=1,
            max_value=max_threshold,
            step=1,
            key=threshold_key,
            help="A ticker is shown in Duplicate Tickers only if it appears in at least this many selected scan cards.",
        )
    )
    if duplicate_rule_key not in st.session_state:
        st.session_state[duplicate_rule_key] = persisted_duplicate_rule
    current_duplicate_rule = DuplicateRuleConfig.from_dict(
        st.session_state.get(duplicate_rule_key),
        default_min_count=duplicate_threshold,
    )
    if current_duplicate_rule.mode == "min_count":
        st.session_state[duplicate_rule_key] = DuplicateRuleConfig(min_count=duplicate_threshold).to_dict()

    current_watchlist_controls = _build_watchlist_control_values(
        selected_watchlist_scans,
        selected_annotation_filters,
        selected_duplicate_subfilters,
        duplicate_threshold,
        st.session_state.get(duplicate_rule_key),
    )
    selected_saved_preset_values = (
        saved_watchlist_presets.get(selected_preset_name)
        if selected_preset_name and not selected_preset_is_builtin
        else None
    )
    preset_has_unsaved_changes = not _watchlist_controls_equal(
        current_watchlist_controls,
        selected_saved_preset_values,
    )

    st.markdown("**Preset Editor**")
    st.text_input(
        "Preset name",
        key=preset_name_key,
        placeholder="e.g. Momentum Core",
    )
    preset_editor_columns = st.columns(2)
    save_preset = preset_editor_columns[0].button("Save Preset", use_container_width=True)
    update_preset = preset_editor_columns[1].button(
        "Update Preset",
        use_container_width=True,
        disabled=(
            not selected_preset_name
            or selected_preset_is_builtin
            or not preset_has_unsaved_changes
        ),
    )

    if save_preset:
        preset_name = _normalize_watchlist_preset_name(st.session_state.get(preset_name_key, ""))
        if not preset_name:
            st.warning("Enter a preset name before saving.")
        elif preset_name in watchlist_presets:
            st.warning("That preset already exists. Load it and use Update Preset to overwrite it.")
        elif len(saved_watchlist_presets) >= WATCHLIST_PRESET_LIMIT:
            st.warning(f"You can save up to {WATCHLIST_PRESET_LIMIT} presets.")
        else:
            watchlist_preference_store.save_collection_item(
                WATCHLIST_PRESET_GROUP,
                watchlist_preferences_namespace,
                preset_name,
                _build_watchlist_preset_record(current_watchlist_controls),
            )
            st.session_state[preset_select_key] = preset_name
            st.session_state[preset_name_pending_key] = preset_name
            st.session_state[preset_feedback_key] = f"Saved preset '{preset_name}'."
            st.rerun()

    if update_preset and selected_preset_name:
        watchlist_preference_store.save_collection_item(
            WATCHLIST_PRESET_GROUP,
            watchlist_preferences_namespace,
            selected_preset_name,
            _build_watchlist_preset_record(current_watchlist_controls),
        )
        st.session_state[preset_name_pending_key] = selected_preset_name
        st.session_state[preset_feedback_key] = f"Updated preset '{selected_preset_name}'."
        st.rerun()

    watchlist_preference_store.save_group(
        "watchlist_controls",
        watchlist_preferences_namespace,
        current_watchlist_controls,
    )
    st.caption("Load any preset to apply it. Only saved presets can be updated or deleted; built-in presets are read-only.")
    st.caption("Selected cards drive card display and Duplicate Tickers. Post-scan filters narrow the displayed watchlist after scan hits are computed. Duplicate subfilters apply only inside Duplicate Tickers.")

    return WatchlistSidebarState(
        scan_config=watchlist_scan_config,
        selected_scan_names=selected_watchlist_scans,
        selected_annotation_filters=selected_annotation_filters,
        selected_duplicate_subfilters=selected_duplicate_subfilters,
        duplicate_threshold=duplicate_threshold,
        duplicate_rule=st.session_state.get(duplicate_rule_key),
        selected_preset_export_name=selected_preset_export_name,
        selected_preset_export_values=selected_preset_export_values,
    )


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


def render_watchlist(
    artifacts: PlatformArtifacts,
    scan_config: ScanConfig | None = None,
    selected_scan_names: list[str] | None = None,
    duplicate_min_count: int | None = None,
    selected_annotation_filters: list[str] | None = None,
    selected_duplicate_subfilters: list[str] | None = None,
    duplicate_rule: dict[str, object] | None = None,
) -> None:
    scan_config = scan_config or ScanConfig()
    watchlist_builder = WatchlistViewModelBuilder(scan_config)
    configured_scan_names = [section.scan_name for section in watchlist_builder.available_card_sections()]
    effective_selected_scan_names = selected_scan_names if selected_scan_names is not None else configured_scan_names
    effective_selected_annotation_filters = (
        selected_annotation_filters
        if selected_annotation_filters is not None
        else list(scan_config.enabled_annotation_filters)
    )
    effective_selected_duplicate_subfilters = (
        selected_duplicate_subfilters if selected_duplicate_subfilters is not None else []
    )
    selected_scan_name_set = set(effective_selected_scan_names)
    duplicate_threshold = int(duplicate_min_count if duplicate_min_count is not None else scan_config.duplicate_min_count)
    parsed_duplicate_rule = DuplicateRuleConfig.from_dict(duplicate_rule, default_min_count=duplicate_threshold)

    filtered_watchlist = watchlist_builder.filter_by_annotation_filters(
        artifacts.watchlist,
        effective_selected_annotation_filters,
    )
    display_watchlist = watchlist_builder.apply_selected_scan_metrics(
        filtered_watchlist,
        artifacts.scan_hits,
        min_count=duplicate_threshold,
        selected_scan_names=effective_selected_scan_names,
        duplicate_rule=parsed_duplicate_rule,
    )
    display_cards = watchlist_builder.build_scan_cards(
        display_watchlist,
        artifacts.scan_hits,
        selected_scan_names=effective_selected_scan_names,
    )

    st.markdown("<div class='oratek-page-title'>Today's Watchlist</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='oratek-page-subtitle'>{html.escape(_format_trade_date(artifacts))}</div>", unsafe_allow_html=True)

    cards: list[tuple[str, list[str], str]] = [
        (card.display_name, _to_ticker_list(card.rows), "No tickers matched this scan.")
        for card in display_cards
        if card.scan_name in selected_scan_name_set
    ]

    duplicate_frame = watchlist_builder.build_duplicate_tickers(
        display_watchlist,
        artifacts.scan_hits,
        min_count=duplicate_threshold,
        selected_scan_names=effective_selected_scan_names,
        selected_duplicate_subfilters=effective_selected_duplicate_subfilters,
        duplicate_rule=parsed_duplicate_rule,
    )
    if effective_selected_scan_names:
        duplicate_note = f"Counted from {len(effective_selected_scan_names)} selected cards"
        if effective_selected_annotation_filters:
            duplicate_note += f" after {len(effective_selected_annotation_filters)} post-scan filter(s)"
        if parsed_duplicate_rule.mode == "required_plus_optional_min":
            duplicate_note += (
                f". Required scans: {', '.join(parsed_duplicate_rule.required_scans)}."
                f" Optional scans: {', '.join(parsed_duplicate_rule.optional_scans)} with "
                f"{parsed_duplicate_rule.optional_min_hits}+ hits."
            )
        else:
            duplicate_note += f". A ticker must appear in {duplicate_threshold}+ selected scans."
        if effective_selected_duplicate_subfilters:
            duplicate_note += f" Duplicate subfilters: {', '.join(effective_selected_duplicate_subfilters)}."
        duplicate_empty_text = "No duplicate tickers in the current watchlist for the selected cards."
    else:
        duplicate_note = "No cards are selected. Choose one or more watchlist cards in the sidebar to enable duplicate counting."
        duplicate_empty_text = "No cards selected."

    render_priority_band_from_frame(
        "Duplicate Tickers",
        duplicate_frame,
        duplicate_note,
        duplicate_empty_text,
    )

    earnings_frame = artifacts.earnings_today.sort_values("Hybrid-RS", ascending=False) if not artifacts.earnings_today.empty and "Hybrid-RS" in artifacts.earnings_today.columns else artifacts.earnings_today

    if not effective_selected_scan_names:
        st.caption("No watchlist cards are selected.")
    elif display_watchlist.empty and effective_selected_annotation_filters:
        st.caption("No watchlist names passed the selected post-scan filters.")
    elif not cards:
        st.caption("None of the selected cards matched the current universe.")
    else:
        for start_offset in range(0, len(cards), 3):
            batch = cards[start_offset : start_offset + 3]
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


def _vix_label_from_score(score: float | None) -> str:
    if score is None or pd.isna(score):
        return "Neutral"
    return _breadth_label(float(score))


def _safe_haven_label_from_score(score: float | None) -> str:
    if score is None or pd.isna(score):
        return "Neutral"
    return _breadth_label(float(score))


def _format_market_number(value: float | None, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.{decimals}f}"


def _format_market_percent(value: float | None, signed: bool = False, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    prefix = "+" if signed else ""
    return f"{float(value):{prefix}.{decimals}f}%"


def _format_market_price(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    amount = float(value)
    if abs(amount) >= 1000.0:
        return f"${amount:,.0f}"
    return f"${amount:,.2f}"


def _market_display_ticker(value: object) -> str:
    text = str(value).strip().upper()
    return text.removeprefix("^").replace("-USD", "")


def _market_ema_badge(label: object) -> tuple[str, str]:
    text = str(label).strip()
    if text == "above 21EMA High":
        return "> 21EMA High", "positive"
    if text == "below 21EMA Low":
        return "< 21EMA Low", "negative"
    if text == "inside 21EMA Cloud":
        return "Inside 21EMA", "neutral"
    return "21EMA Unknown", "neutral"


def render_market_conditions_panel(result) -> None:
    tone = _tone_class(result.label)
    score_pct = max(0.0, min(float(result.score), 100.0))
    arc_length = 282.743
    filled = arc_length * (score_pct / 100.0)
    remaining = max(arc_length - filled, 0.0)
    st.markdown(
        f"<div class='oratek-market-panel'><div class='oratek-market-panel-title'>Market Conditions</div><div class='oratek-market-score-chip {tone}'>{html.escape(str(result.label))} {_format_market_number(result.score, 0)}</div><div class='oratek-market-gauge'><svg class='oratek-market-gauge-svg' viewBox='0 0 220 120' aria-hidden='true'><path class='oratek-market-gauge-track' d='M20 110 A90 90 0 0 1 200 110'></path><path class='oratek-market-gauge-value {tone}' d='M20 110 A90 90 0 0 1 200 110' style='--market-score-filled:{filled:.3f}; --market-score-remaining:{remaining:.3f};'></path><path class='oratek-market-gauge-inner' d='M49 110 A61 61 0 0 1 171 110'></path><path class='oratek-market-gauge-core' d='M67 110 A43 43 0 0 1 153 110 L153 110 L67 110 Z'></path></svg></div><div class='oratek-market-gauge-caption'>Composite score (0-100)</div></div>",
        unsafe_allow_html=True,
    )


def render_market_history_stack(result) -> None:
    rows = [
        ("1D ago", result.score_1d_ago, result.label_1d_ago),
        ("1W ago", result.score_1w_ago, result.label_1w_ago),
        ("1M ago", result.score_1m_ago, result.label_1m_ago),
        ("3M ago", result.score_3m_ago, result.label_3m_ago),
    ]
    cards: list[str] = []
    for title, score, label in rows:
        tone = _tone_class(label or "neutral")
        cards.append(
            f"<div class='oratek-market-mini-card'><div class='oratek-market-mini-head'><div><div class='oratek-market-mini-title'>{html.escape(title)}</div><div class='oratek-market-mini-state'>{html.escape(label or 'N/A')}</div></div><div class='oratek-market-mini-score {tone}'>{html.escape(_format_market_number(score, 1))}</div></div></div>"
        )
    st.markdown("<div class='oratek-market-timeline-stack'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def render_market_metric_panel(title: str, items: list[tuple[str, str, str, str]], columns: int, empty_text: str) -> None:
    if not items:
        st.markdown(
            f"<div class='oratek-market-panel'><div class='oratek-market-panel-title centered'>{html.escape(title)}</div><div class='oratek-empty-state'>{html.escape(empty_text)}</div></div>",
            unsafe_allow_html=True,
        )
        return
    cards = "".join(
        f"<div class='oratek-market-metric-card'><div class='oratek-market-metric-name'>{html.escape(name)}</div><div class='oratek-market-metric-value'>{html.escape(value)}</div><div class='oratek-market-pill {tone}'>{html.escape(status)}</div></div>"
        for name, value, status, tone in items
    )
    st.markdown(
        f"<div class='oratek-market-panel'><div class='oratek-market-panel-title centered'>{html.escape(title)}</div><div class='oratek-market-metric-grid cols-{columns}'>{cards}</div></div>",
        unsafe_allow_html=True,
    )


def _market_metric_items(result) -> tuple[list[tuple[str, str, str, str]], list[tuple[str, str, str, str]], list[tuple[str, str, str, str]]]:
    breadth_keys = (
        ("pct_above_sma10", "SMA 10"),
        ("pct_above_sma20", "SMA 20"),
        ("pct_above_sma50", "SMA 50"),
        ("pct_above_sma200", "SMA 200"),
        ("pct_sma20_gt_sma50", "20 > 50"),
        ("pct_sma50_gt_sma200", "50 > 200"),
    )
    breadth_items = []
    for key, label in breadth_keys:
        value = result.breadth_summary.get(key)
        status = _breadth_label(float(value)) if value is not None and not pd.isna(value) else "Neutral"
        breadth_items.append((label, _format_market_percent(value, signed=False, decimals=2), status, _tone_class(status)))

    performance_keys = ("% YTD", "% 1W", "% 1M", "% 1Y")
    performance_items = []
    for key in performance_keys:
        value = result.performance_overview.get(key)
        status = _performance_label(float(value)) if value is not None and not pd.isna(value) else "Neutral"
        performance_items.append((key, _format_market_percent(value, signed=True, decimals=2), status, _tone_class(status)))

    high_value = result.high_vix_summary.get("S2W HIGH %")
    high_status = _breadth_label(float(high_value)) if high_value is not None and not pd.isna(high_value) else "Neutral"
    vix_value = result.high_vix_summary.get("VIX")
    vix_status = _vix_label_from_score(result.component_scores.get("vix_score"))
    safe_haven_value = result.high_vix_summary.get("SAFE HAVEN %")
    safe_haven_status = _safe_haven_label_from_score(result.component_scores.get("safe_haven_score"))
    high_vix_items = [
        ("S2W High", _format_market_percent(high_value, signed=False, decimals=2), high_status, _tone_class(high_status)),
        ("VIX", _format_market_number(vix_value, 2), vix_status, _tone_class(vix_status)),
        ("Safe Haven", _format_market_percent(safe_haven_value, signed=True, decimals=2), safe_haven_status, _tone_class(safe_haven_status)),
    ]
    return breadth_items, performance_items, high_vix_items


def render_market_snapshot_panel(frame: pd.DataFrame) -> None:
    if frame.empty:
        st.caption("No market snapshot rows available.")
        return
    cards: list[str] = []
    for _, row in frame.iterrows():
        badge_text, badge_tone = _market_ema_badge(row.get("21EMA POS"))
        cards.append(
            f"<div class='oratek-market-snapshot-card'><div class='oratek-market-snapshot-head'><div class='oratek-market-snapshot-name'>{html.escape(str(row.get('NAME', '')))}</div><div class='oratek-market-pill {badge_tone}'>{html.escape(badge_text)}</div></div><div class='oratek-market-snapshot-ticker'>{html.escape(_market_display_ticker(row.get('TICKER', '')))}</div><div class='oratek-market-snapshot-price-row'><div class='oratek-market-snapshot-price'>{html.escape(_format_market_price(row.get('PRICE')))}</div><div><div class='oratek-market-snapshot-day oratek-{_tone_class(row.get('DAY %'))}'>{html.escape(_format_market_percent(row.get('DAY %'), signed=True, decimals=2))}</div><div class='oratek-market-snapshot-volume'>volume % {html.escape(_format_market_percent(row.get('VOL vs 50D %'), signed=True, decimals=1))}</div></div></div></div>"
        )
    st.markdown("<div class='oratek-market-snapshot-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def render_market_factors_panel(frame: pd.DataFrame) -> None:
    if frame.empty:
        st.caption("No factor-relative-strength rows available.")
        return
    scale_values: list[float] = []
    for column in ["REL 1W %", "REL 1M %"]:
        scale_values.extend(abs(float(value)) for value in frame[column].dropna().tolist())
    scale = max(scale_values) if scale_values else 1.0
    scale = max(scale, 0.25)

    rows_html: list[str] = []
    for _, row in frame.iterrows():
        metric_html: list[str] = []
        for period, column in (("1W", "REL 1W %"), ("1M", "REL 1M %")):
            value = row.get(column)
            tone = _tone_class(value)
            width = 0.0
            if value is not None and not pd.isna(value):
                width = min(abs(float(value)) / scale * 100.0, 100.0)
            metric_html.append(
                f"<div><div class='oratek-market-factor-metric-head'><span class='oratek-market-factor-period'>{period}</span><span class='oratek-market-factor-value oratek-{tone}'>{html.escape(_format_market_percent(value, signed=True, decimals=2))}</span></div><div class='oratek-market-factor-bar'><span class='oratek-market-factor-fill {tone}' style='width:{width:.1f}%'></span></div></div>"
            )
        rows_html.append(
            f"<div class='oratek-market-factor-row'><div class='oratek-market-factor-head'><div class='oratek-market-factor-name'>{html.escape(str(row.get('NAME', '')))}</div><div class='oratek-market-factor-ticker'>{html.escape(_market_display_ticker(row.get('TICKER', '')))}</div></div><div class='oratek-market-factor-metrics'>{''.join(metric_html)}</div></div>"
        )
    st.markdown(f"<div class='oratek-market-factors-panel'><div class='oratek-market-factor-list'>{''.join(rows_html)}</div></div>", unsafe_allow_html=True)


def render_market_dashboard(artifacts: PlatformArtifacts) -> None:
    result = artifacts.market_result
    updated_meta = f"Updated: {result.update_time.split('T')[-1]}" if result.update_time else "Updated: N/A"
    render_page_header("Market Dashboard", meta=updated_meta, centered=True)

    breadth_items, performance_items, high_vix_items = _market_metric_items(result)

    left_col, middle_col, right_col = st.columns([1.15, 1.0, 2.35])
    with left_col:
        render_market_conditions_panel(result)
    with middle_col:
        render_market_history_stack(result)
    with right_col:
        render_market_metric_panel("Breadth & Trend Metrics", breadth_items, 6, "No breadth metrics available.")
        performance_col, high_vix_col = st.columns([2.2, 1.0])
        with performance_col:
            render_market_metric_panel("Performance Overview", performance_items, 4, "No performance metrics available.")
        with high_vix_col:
            render_market_metric_panel("High, VIX & Safe Haven", high_vix_items, 3, "No High, VIX & Safe Haven metrics available.")

    snapshot_col, factor_col = st.columns([2.3, 1.1])
    with snapshot_col:
        st.markdown("<div class='oratek-market-stage-head'><div class='oratek-market-stage-title'>Core</div><div class='oratek-market-stage-caption'>Used for Market Score. Vol % vs 50D Avg.</div></div>", unsafe_allow_html=True)
        render_market_snapshot_panel(result.market_snapshot)
        st.markdown("<div class='oratek-market-stage-head'><div class='oratek-market-stage-title'>Leadership</div><div class='oratek-market-stage-caption'>Display-only leadership universe.</div></div>", unsafe_allow_html=True)
        render_market_snapshot_panel(result.leadership_snapshot)
        st.markdown("<div class='oratek-market-stage-head'><div class='oratek-market-stage-title'>External</div><div class='oratek-market-stage-caption'>Display-only external universe.</div></div>", unsafe_allow_html=True)
        render_market_snapshot_panel(result.external_snapshot)
    with factor_col:
        st.markdown("<div class='oratek-market-stage-head'><div class='oratek-market-stage-title'>Factors vs SP500</div><div class='oratek-market-stage-caption'>Factors-only universe. Relative performance vs S&P 500 (1W, 1M).</div></div>", unsafe_allow_html=True)
        render_market_factors_panel(result.factors_vs_sp500)

    render_data_health_table(artifacts)


def render_active_page(
    page_key: str,
    artifacts: PlatformArtifacts,
    watchlist_state: WatchlistSidebarState | None,
) -> None:
    if page_key == "watchlist":
        if watchlist_state is None:
            st.error("Watchlist controls could not be initialized.")
            return
        render_watchlist(
            artifacts,
            scan_config=watchlist_state.scan_config,
            selected_scan_names=watchlist_state.selected_scan_names,
            duplicate_min_count=watchlist_state.duplicate_threshold,
            selected_annotation_filters=watchlist_state.selected_annotation_filters,
            selected_duplicate_subfilters=watchlist_state.selected_duplicate_subfilters,
            duplicate_rule=watchlist_state.duplicate_rule,
        )
        return
    if page_key == "rs_radar":
        render_rs_radar(artifacts)
        return
    render_market_dashboard(artifacts)


def main() -> None:
    inject_global_styles()
    default_config = ROOT / "config" / "default.yaml"
    page_key = current_page_key()
    watchlist_state: WatchlistSidebarState | None = None

    with st.sidebar:
        st.markdown("<div class='oratek-sidebar-title'>Growth Trading Screener</div>", unsafe_allow_html=True)
        st.markdown("**Controls**")
        config_path = str(default_config)
        symbols_raw = st.text_area("Manual Symbols (optional)", value="", height=120, placeholder="Leave blank to use weekly universe snapshot")
        force_universe_refresh = st.checkbox("Force Weekly Universe Refresh", value=False)

        if page_key == "watchlist":
            watchlist_state = render_watchlist_sidebar_controls(config_path)

        refresh = st.button("Refresh", type="primary")

    symbols = parse_symbols(symbols_raw)
    cache_key = (config_path, tuple(symbols), force_universe_refresh)
    if refresh or st.session_state.get("artifacts_key") != cache_key:
        with st.spinner("Loading screening artifacts..."):
            st.session_state["artifacts"] = load_artifacts(config_path, symbols, force_universe_refresh)
            st.session_state["preset_export_directory"] = (
                str(export_watchlist_preset_csvs(config_path, st.session_state["artifacts"]) or "")
            )
            effectiveness_sync = sync_preset_effectiveness_logs(config_path, st.session_state["artifacts"])
            st.session_state["preset_effectiveness_directory"] = (
                effectiveness_sync.output_dir if effectiveness_sync is not None else ""
            )
            st.session_state["artifacts_key"] = cache_key

    artifacts: PlatformArtifacts = st.session_state["artifacts"]
    page_key = render_page_tabs()
    render_context_strip([f"Data source: {artifacts.data_source_label}"])
    render_data_health_banner(artifacts)

    if (
        page_key == "watchlist"
        and watchlist_state is not None
        and watchlist_state.selected_preset_export_name
        and watchlist_state.selected_preset_export_values is not None
    ):
        preset_export_frame = WatchlistViewModelBuilder(watchlist_state.scan_config).build_preset_export(
            watchlist_state.selected_preset_export_name,
            artifacts.watchlist,
            artifacts.scan_hits,
            selected_scan_names=list(watchlist_state.selected_preset_export_values.get("selected_scan_names", [])),
            min_count=int(watchlist_state.selected_preset_export_values.get("duplicate_threshold", watchlist_state.scan_config.duplicate_min_count)),
            selected_annotation_filters=list(watchlist_state.selected_preset_export_values.get("selected_annotation_filters", [])),
            selected_duplicate_subfilters=list(watchlist_state.selected_preset_export_values.get("selected_duplicate_subfilters", [])),
            duplicate_rule=DuplicateRuleConfig.from_dict(
                watchlist_state.selected_preset_export_values.get("duplicate_rule"),
                default_min_count=int(
                    watchlist_state.selected_preset_export_values.get("duplicate_threshold", watchlist_state.scan_config.duplicate_min_count)
                ),
            ),
        )
        with st.sidebar:
            st.markdown("**Preset Export**")
            st.download_button(
                "Export Preset CSV",
                data=_dataframe_to_csv_bytes(preset_export_frame),
                file_name=_build_watchlist_preset_export_filename(watchlist_state.selected_preset_export_name),
                mime="text/csv",
                use_container_width=True,
            )
            st.caption("Exports the selected preset's duplicate tickers and each selected scan card's hit tickers.")

    render_active_page(page_key, artifacts, watchlist_state)


if __name__ == "__main__":
    main()
