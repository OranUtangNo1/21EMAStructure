from __future__ import annotations

import html
import importlib
import inspect
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from pandas.tseries.offsets import BDay

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.configuration import load_settings
from src.dashboard.effectiveness import sync_preset_effectiveness_logs
from src.dashboard.watchlist import WatchlistViewModelBuilder
from src.data.cache import CacheLayer
from src.data.providers import YFinancePriceDataProvider
from src.data.tracking_repository import read_detection_detail, read_preset_horizon_performance
from src.pipeline import PlatformArtifacts, ResearchPlatform
from src.scan.rules import DuplicateRuleConfig, ScanConfig, WatchlistPresetConfig
from src.signals.rules import ENTRY_SIGNAL_REGISTRY, EntrySignalConfig
from src.signals.runner import (
    ENTRY_SIGNAL_UNIVERSE_MODE_BOTH,
    ENTRY_SIGNAL_UNIVERSE_MODE_CURRENT,
    ENTRY_SIGNAL_UNIVERSE_MODE_ELIGIBLE,
    ENTRY_SIGNAL_UNIVERSE_MODE_PRESETS,
    ENTRY_SIGNAL_UNIVERSE_MODE_WATCHLIST,
    EntrySignalRunner,
)
from src.ui_preferences import UserPreferenceStore


st.set_page_config(
    page_title="Growth Trading Screener",
    layout="wide",
    initial_sidebar_state="collapsed",
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
header[data-testid="stHeader"] { background:transparent; box-shadow:none; }
.block-container { max-width:1440px; padding-top:.9rem; padding-bottom:2.3rem; }
section[data-testid="stSidebar"] { background:linear-gradient(180deg, #fbfdff 0%, #f4f8ff 100%); border-right:1px solid var(--panel-border); }
div.stButton { width:100%; }
div.stButton > button { width:100%; min-height:44px; display:flex; align-items:center; justify-content:center; background:linear-gradient(135deg, #2d6cdf 0%, #528eee 100%); color:#fff; border:none; border-radius:8px; font-weight:700; box-shadow:0 12px 24px rgba(45,108,223,.18); cursor:pointer; }
div.stButton > button * { pointer-events:none; }
div.stButton > button:disabled { cursor:not-allowed; opacity:.62; }
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
.oratek-ticker-card.role-required { border-color:#2d6cdf; box-shadow:0 18px 36px rgba(45,108,223,.13); }
.oratek-ticker-card.role-optional { border-color:#21a46f; box-shadow:0 18px 36px rgba(33,164,111,.12); }
.oratek-ticker-card-head { display:flex; justify-content:space-between; gap:.8rem; align-items:center; padding:.9rem 1rem; background:linear-gradient(180deg, #eef4ff 0%, #e7f0ff 100%); border-bottom:1px solid var(--panel-border); }
.oratek-ticker-card.role-required .oratek-ticker-card-head { background:linear-gradient(180deg, #edf4ff 0%, #e3efff 100%); border-bottom-color:rgba(45,108,223,.24); }
.oratek-ticker-card.role-optional .oratek-ticker-card-head { background:linear-gradient(180deg, #edf8f2 0%, #e4f4eb 100%); border-bottom-color:rgba(33,164,111,.24); }
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
class WatchlistControlState:
    scan_config: ScanConfig
    selected_scan_names: list[str]
    required_scan_names: list[str]
    optional_scan_names: list[str]
    optional_scan_groups: list[dict[str, object]]
    selected_annotation_filters: list[str]
    selected_duplicate_subfilters: list[str]
    duplicate_threshold: int
    duplicate_rule: dict[str, object] | None = None
    selected_preset_export_name: str | None = None
    selected_preset_export_values: dict[str, object] | None = None


@dataclass(frozen=True)
class WatchlistPresetDefinition:
    preset_name: str
    source: str
    values: dict[str, object]


@dataclass(frozen=True)
class EntrySignalPageState:
    signal_config: EntrySignalConfig
    selected_signal_names: list[str]


ENTRY_SIGNAL_UNIVERSE_LABELS: dict[str, str] = {
    ENTRY_SIGNAL_UNIVERSE_MODE_BOTH: "Preset + Current Duplicates",
    ENTRY_SIGNAL_UNIVERSE_MODE_PRESETS: "Preset Duplicates",
    ENTRY_SIGNAL_UNIVERSE_MODE_CURRENT: "Current Selection Duplicates",
    ENTRY_SIGNAL_UNIVERSE_MODE_WATCHLIST: "Today's Watchlist",
    ENTRY_SIGNAL_UNIVERSE_MODE_ELIGIBLE: "Eligible Universe",
}


APP_PAGES: tuple[AppPageDefinition, ...] = (
    AppPageDefinition("watchlist", "Watchlist"),
    AppPageDefinition("entry_signals", "Entry Signal"),
    AppPageDefinition("market_dashboard", "Market Dashboard"),
    AppPageDefinition("rs_radar", "RS"),
    AppPageDefinition("analysis", "Analysis"),
    AppPageDefinition("setting", "Setting"),
)
APP_PAGE_KEYS = tuple(page.key for page in APP_PAGES)
APP_PAGE_LABELS = {page.key: page.label for page in APP_PAGES}
DEFAULT_PAGE_KEY = APP_PAGES[0].key
TRACKING_HORIZON_OPTIONS = (1, 5, 10, 20)
TRACKING_MARKET_ENV_OPTIONS = ("bull", "neutral", "weak", "bear")
TRACKING_BENCHMARK_OPTIONS = ("SPY", "QQQ", "IWM")

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


def render_ticker_card(title: str, tickers: list[str], empty_text: str, role: str | None = None) -> None:
    count = len(tickers)
    body = "".join(f"<div class='oratek-ticker-item'>{html.escape(ticker)}</div>" for ticker in tickers)
    if not body:
        body = f"<div class='oratek-empty-state'>{html.escape(empty_text)}</div>"
    else:
        body = f"<div class='oratek-ticker-grid'>{body}</div>"
    role_class = f" role-{html.escape(role)}" if role in {"required", "optional"} else ""
    st.markdown(
        f"<div class='oratek-ticker-card{role_class}'><div class='oratek-ticker-card-head'><div class='oratek-ticker-card-title'>{html.escape(title)}</div><div class='oratek-ticker-card-count'>{count} tickers</div></div>{body}</div>",
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


def get_research_platform_class() -> type[ResearchPlatform]:
    global PlatformArtifacts, ResearchPlatform

    if "force_price_refresh" in inspect.signature(ResearchPlatform.run).parameters:
        return ResearchPlatform

    pipeline_module = importlib.import_module("src.pipeline")
    pipeline_module = importlib.reload(pipeline_module)
    PlatformArtifacts = pipeline_module.PlatformArtifacts
    ResearchPlatform = pipeline_module.ResearchPlatform
    return ResearchPlatform


def load_artifacts(
    config_path: str,
    symbols: list[str],
    force_universe_refresh: bool,
    force_price_refresh: bool,
    *,
    prefer_saved_run: bool = True,
) -> PlatformArtifacts:
    platform = get_research_platform_class()(config_path)
    if prefer_saved_run and not force_universe_refresh and not force_price_refresh:
        saved = platform.load_latest_run_artifacts(
            symbols or None,
            force_universe_refresh=force_universe_refresh,
        )
        if saved is not None:
            return saved
    return platform.run(
        symbols or None,
        force_universe_refresh=force_universe_refresh,
        force_price_refresh=force_price_refresh,
    )


def load_scan_config(config_path: str) -> ScanConfig:
    settings = load_settings(config_path)
    return ScanConfig.from_dict(settings.get("scan", {}))


def load_entry_signal_config(config_path: str) -> EntrySignalConfig:
    settings = load_settings(config_path)
    return EntrySignalConfig.from_dict(settings.get("entry_signals", {}))


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


def export_watchlist_preset_csvs(
    config_path: str,
    artifacts: PlatformArtifacts,
    *,
    respect_config: bool = True,
) -> Path | None:
    scan_config = load_scan_config(config_path)
    export_config = scan_config.preset_csv_export
    if respect_config and not export_config.enabled:
        return None

    preset_definitions = load_watchlist_preset_definitions(config_path, scan_config)
    if not preset_definitions:
        return None

    builder = WatchlistViewModelBuilder(scan_config)
    trade_date = _latest_trade_date_for_export(artifacts)
    output_date = datetime.now().strftime("%Y-%m-%d")
    export_dir = _resolve_preset_export_directory(config_path, export_config.output_dir, artifacts)
    export_dir.mkdir(parents=True, exist_ok=True)

    summary_frame, hits_frame = build_watchlist_preset_hit_exports(
        preset_definitions,
        artifacts,
        builder,
        trade_date=trade_date,
        output_date=output_date,
    )
    summary_frame.to_csv(export_dir / "preset_summary.csv", index=False)
    hits_frame.to_csv(export_dir / "preset_hits.csv", index=False)

    if export_config.write_details:
        detail_presets = [
            _watchlist_preset_config_from_definition(definition)
            for definition in preset_definitions
        ]
        details_frame = builder.build_preset_detail_exports(
            detail_presets,
            artifacts.watchlist,
            artifacts.scan_hits,
        )
        details_frame.to_csv(export_dir / "preset_details.csv", index=False)

    return export_dir


def build_watchlist_preset_hit_exports(
    preset_definitions: list[WatchlistPresetDefinition],
    artifacts: PlatformArtifacts,
    builder: WatchlistViewModelBuilder,
    *,
    trade_date: str,
    output_date: str,
    export_target: str = "Today's Watchlist",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    hit_columns = [
        "Output Target",
        "trade_date",
        "output_date",
        "preset_name",
        "preset_source",
        "ticker",
        "scan_hit_count",
        "matched_scans",
        "selected_scan_names",
        "selected_annotation_filters",
        "duplicate_threshold",
        "duplicate_rule_mode",
        "hybrid_score",
        "vcs",
    ]
    summary_columns = [
        "Output Target",
        "trade_date",
        "output_date",
        "ticker",
        "hit_presets",
        "hit_preset_count",
        "builtin_presets",
        "custom_presets",
        "matched_scans",
        "selected_scan_names",
        "selected_annotation_filters",
        "duplicate_thresholds",
        "duplicate_rule_modes",
    ]
    hit_rows: list[dict[str, object]] = []
    scan_hits = artifacts.scan_hits.copy() if not artifacts.scan_hits.empty else pd.DataFrame(columns=["ticker", "name", "kind"])
    if not scan_hits.empty and "ticker" in scan_hits.columns:
        scan_hits["ticker"] = scan_hits["ticker"].astype(str).str.upper()
    if "kind" in scan_hits.columns:
        scan_hits = scan_hits.loc[scan_hits["kind"] == "scan"].copy()

    for definition in preset_definitions:
        preset = _watchlist_preset_config_from_definition(definition)
        duplicate_frame, _ = builder._build_preset_frames(preset, artifacts.watchlist, artifacts.scan_hits)
        if duplicate_frame.empty or "Ticker" not in duplicate_frame.columns:
            continue
        for row in duplicate_frame.to_dict("records"):
            ticker = str(row.get("Ticker", "")).strip().upper()
            if not ticker:
                continue
            matched_scans = sorted(
                {
                    str(name)
                    for name in scan_hits.loc[
                        (scan_hits["ticker"] == ticker)
                        & (scan_hits["name"].isin(preset.selected_scan_names)),
                        "name",
                    ].tolist()
                }
            )
            hit_rows.append(
                {
                    "Output Target": str(export_target).strip(),
                    "trade_date": str(trade_date).strip(),
                    "output_date": str(output_date).strip(),
                    "preset_name": preset.preset_name,
                    "preset_source": definition.source,
                    "ticker": ticker,
                    "scan_hit_count": int(row.get("Scan Hits", len(matched_scans)) or 0),
                    "matched_scans": ", ".join(matched_scans),
                    "selected_scan_names": ", ".join(preset.selected_scan_names),
                    "selected_annotation_filters": ", ".join(preset.selected_annotation_filters),
                    "duplicate_threshold": int(preset.duplicate_threshold),
                    "duplicate_rule_mode": preset.duplicate_rule.mode,
                    "hybrid_score": row.get("Hybrid-RS", ""),
                    "vcs": row.get("VCS", ""),
                }
            )

    hits_frame = pd.DataFrame(hit_rows, columns=hit_columns)

    grouped: dict[str, dict[str, object]] = {}
    for row in hits_frame.to_dict("records"):
        ticker = str(row["ticker"])
        grouped_row = grouped.setdefault(
            ticker,
            {
                "Output Target": row["Output Target"],
                "trade_date": row["trade_date"],
                "output_date": row["output_date"],
                "ticker": ticker,
                "hit_presets": [],
                "builtin_presets": [],
                "custom_presets": [],
                "matched_scans": [],
                "selected_scan_names": [],
                "selected_annotation_filters": [],
                "duplicate_thresholds": [],
                "duplicate_rule_modes": [],
            },
        )
        preset_name = str(row["preset_name"])
        _extend_unique_text(grouped_row["hit_presets"], [preset_name])
        if str(row["preset_source"]) == "Custom":
            _extend_unique_text(grouped_row["custom_presets"], [preset_name])
        else:
            _extend_unique_text(grouped_row["builtin_presets"], [preset_name])
        _extend_unique_text(grouped_row["matched_scans"], str(row["matched_scans"]).split(", "))
        _extend_unique_text(grouped_row["selected_scan_names"], str(row["selected_scan_names"]).split(", "))
        _extend_unique_text(grouped_row["selected_annotation_filters"], str(row["selected_annotation_filters"]).split(", "))
        _extend_unique_text(grouped_row["duplicate_thresholds"], [str(row["duplicate_threshold"])])
        _extend_unique_text(grouped_row["duplicate_rule_modes"], [str(row["duplicate_rule_mode"])])

    summary_rows: list[dict[str, object]] = []
    for row in grouped.values():
        hit_presets = row["hit_presets"]
        summary_rows.append(
            {
                "Output Target": row["Output Target"],
                "trade_date": row["trade_date"],
                "output_date": row["output_date"],
                "ticker": row["ticker"],
                "hit_presets": ", ".join(hit_presets),
                "hit_preset_count": len(hit_presets),
                "builtin_presets": ", ".join(row["builtin_presets"]),
                "custom_presets": ", ".join(row["custom_presets"]),
                "matched_scans": ", ".join(row["matched_scans"]),
                "selected_scan_names": ", ".join(row["selected_scan_names"]),
                "selected_annotation_filters": ", ".join(row["selected_annotation_filters"]),
                "duplicate_thresholds": ", ".join(row["duplicate_thresholds"]),
                "duplicate_rule_modes": ", ".join(row["duplicate_rule_modes"]),
            }
        )
    summary_frame = pd.DataFrame(summary_rows, columns=summary_columns)
    if not summary_frame.empty:
        summary_frame = summary_frame.sort_values(["hit_preset_count", "ticker"], ascending=[False, True]).reset_index(drop=True)
    if not hits_frame.empty:
        hits_frame = hits_frame.sort_values(["ticker", "preset_source", "preset_name"]).reset_index(drop=True)
    return summary_frame, hits_frame


def _watchlist_preset_config_from_definition(definition: WatchlistPresetDefinition) -> WatchlistPresetConfig:
    values = definition.values
    duplicate_threshold = int(values.get("duplicate_threshold", 1))
    return WatchlistPresetConfig(
        preset_name=definition.preset_name,
        selected_scan_names=tuple(str(name) for name in values.get("selected_scan_names", [])),
        selected_annotation_filters=tuple(str(name) for name in values.get("selected_annotation_filters", [])),
        selected_duplicate_subfilters=tuple(str(name) for name in values.get("selected_duplicate_subfilters", [])),
        duplicate_threshold=duplicate_threshold,
        duplicate_rule=DuplicateRuleConfig.from_dict(values.get("duplicate_rule"), default_min_count=duplicate_threshold),
    )


def _extend_unique_text(target: list[str], values: list[object]) -> None:
    existing = set(target)
    for value in values:
        text = str(value).strip()
        if text and text not in existing:
            target.append(text)
            existing.add(text)


def _load_builtin_watchlist_preset_definitions(scan_config: ScanConfig, *, visible_only: bool) -> list[WatchlistPresetDefinition]:
    definitions: list[WatchlistPresetDefinition] = []
    available_scan_names = [section.scan_name for section in scan_config.card_sections]
    for preset in scan_config.watchlist_presets:
        if not preset.export_enabled:
            continue
        if visible_only and not preset.visible_in_ui:
            continue
        preset_name = _normalize_watchlist_preset_name(preset.preset_name)
        if not preset_name:
            continue
        values = preset.to_control_values()
        required_scan_names, optional_scan_groups, _ = _resolve_duplicate_role_controls(
            values.get("selected_scan_names", []),
            values.get("duplicate_rule"),
            int(values.get("duplicate_threshold", 1)),
            available_scan_names,
            return_groups=True,
        )
        optional_scan_names = _flatten_optional_scan_groups(optional_scan_groups)
        definitions.append(
            WatchlistPresetDefinition(
                preset_name=preset_name,
                source="Built-in",
                values=_build_watchlist_control_values(
                    list(values.get("selected_scan_names", [])),
                    list(values.get("selected_annotation_filters", [])),
                    list(values.get("selected_duplicate_subfilters", [])),
                    int(values.get("duplicate_threshold", 1)),
                    values.get("duplicate_rule"),
                    required_scan_names,
                    optional_scan_names,
                    optional_scan_groups,
                ),
            )
        )
    return definitions


def load_watchlist_preset_definitions(config_path: str, scan_config: ScanConfig | None = None) -> list[WatchlistPresetDefinition]:
    scan_config = scan_config or load_scan_config(config_path)
    definitions = _load_builtin_watchlist_preset_definitions(scan_config, visible_only=False)
    available_scan_names = [section.scan_name for section in scan_config.card_sections]
    available_annotation_names = [section.filter_name for section in scan_config.annotation_filters]
    available_duplicate_subfilters = list(WatchlistViewModelBuilder(scan_config).available_duplicate_subfilters())
    preference_store = load_user_preference_store(config_path)
    raw_presets = preference_store.load_collection(WATCHLIST_PRESET_GROUP, watchlist_preference_namespace(config_path))
    for raw_name, raw_record in raw_presets.items():
        preset_name = _normalize_watchlist_preset_name(raw_name)
        if not preset_name:
            continue
        values = _read_watchlist_preset_values(
            raw_record,
            available_scan_names=available_scan_names,
            available_annotation_names=available_annotation_names,
            available_duplicate_subfilters=available_duplicate_subfilters,
            default_duplicate_threshold=scan_config.duplicate_min_count,
        )
        if values is None:
            continue
        definitions.append(
            WatchlistPresetDefinition(
                preset_name=preset_name,
                source="Custom",
                values=values,
            )
        )
    return definitions


def build_watchlist_preset_hit_frames(
    config_path: str,
    artifacts: PlatformArtifacts,
    scan_config: ScanConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    scan_config = scan_config or load_scan_config(config_path)
    definitions = load_watchlist_preset_definitions(config_path, scan_config)
    builder = WatchlistViewModelBuilder(scan_config)
    return build_watchlist_preset_hit_exports(
        definitions,
        artifacts,
        builder,
        trade_date=_latest_trade_date_for_export(artifacts),
        output_date=datetime.now().strftime("%Y-%m-%d"),
    )


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
    selected_page = page_key
    columns = st.columns(len(APP_PAGES), gap="small")
    for column, page in zip(columns, APP_PAGES):
        with column:
            if st.button(
                page.label,
                key=f"page_tab_{page.key}",
                type="primary" if page.key == page_key else "secondary",
                use_container_width=True,
            ):
                if page.key != page_key:
                    st.session_state[PAGE_SELECTION_KEY] = page.key
                    st.rerun()
                selected_page = page.key
    return selected_page


def _normalize_watchlist_preset_name(raw_value: object) -> str:
    return str(raw_value).strip()


def _resolve_selected_watchlist_preset_name(raw_value: object, presets: dict[str, dict[str, object]]) -> str:
    preset_name = _normalize_watchlist_preset_name(raw_value)
    return preset_name if preset_name in presets else ""


def _build_watchlist_control_values(
    selected_scan_names: list[str],
    selected_annotation_filters: list[str],
    selected_duplicate_subfilters: list[str],
    duplicate_threshold: int,
    duplicate_rule: dict[str, object] | None = None,
    required_scan_names: list[str] | None = None,
    optional_scan_names: list[str] | None = None,
    optional_scan_groups: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "selected_scan_names": list(selected_scan_names),
        "required_scan_names": list(required_scan_names or []),
        "optional_scan_names": list(optional_scan_names or []),
        "optional_scan_groups": list(optional_scan_groups or []),
        "selected_annotation_filters": list(selected_annotation_filters),
        "selected_duplicate_subfilters": list(selected_duplicate_subfilters),
        "duplicate_threshold": int(duplicate_threshold),
        "duplicate_rule": dict(duplicate_rule) if isinstance(duplicate_rule, dict) else DuplicateRuleConfig(min_count=int(duplicate_threshold)).to_dict(),
    }


def _filter_available_scan_names(raw_names: object, available_scan_names: list[str]) -> list[str]:
    if not isinstance(raw_names, (list, tuple, set)):
        return []
    available = set(available_scan_names)
    return list(
        dict.fromkeys(
            str(name)
            for name in raw_names
            if str(name) in available
        )
    )


def _merge_scan_role_names(required_scan_names: list[str], optional_scan_names: list[str]) -> list[str]:
    return list(dict.fromkeys([*required_scan_names, *optional_scan_names]))


def _normalize_optional_scan_groups(raw_groups: object, available_scan_names: list[str]) -> list[dict[str, object]]:
    if not isinstance(raw_groups, (list, tuple)):
        return []
    normalized_groups: list[dict[str, object]] = []
    used_names: set[str] = set()
    for index, raw_group in enumerate(raw_groups, start=1):
        if not isinstance(raw_group, dict):
            continue
        group_name = str(raw_group.get("group_name", raw_group.get("name", f"Optional Condition {index}"))).strip()
        if not group_name:
            group_name = f"Optional Condition {index}"
        scans = [
            name
            for name in _filter_available_scan_names(raw_group.get("scans", []), available_scan_names)
            if name not in used_names
        ]
        if not scans:
            continue
        used_names.update(scans)
        try:
            min_hits = int(raw_group.get("min_hits", 1))
        except (TypeError, ValueError):
            min_hits = 1
        min_hits = max(1, min(min_hits, len(scans)))
        normalized_groups.append(
            {
                "group_name": group_name,
                "scans": scans,
                "min_hits": min_hits,
            }
        )
    return normalized_groups


def _flatten_optional_scan_groups(optional_scan_groups: list[dict[str, object]]) -> list[str]:
    names: list[str] = []
    for group in optional_scan_groups:
        names.extend(str(name) for name in group.get("scans", []) if str(name).strip())
    return list(dict.fromkeys(names))


def _resolve_duplicate_role_controls(
    selected_scan_names: object,
    duplicate_rule: object,
    duplicate_threshold: int,
    available_scan_names: list[str],
    required_scan_names: object = None,
    optional_scan_names: object = None,
    optional_scan_groups: object = None,
    *,
    return_groups: bool = False,
) -> tuple[list[str], list[object], int]:
    def result(
        required_names: list[str],
        groups: list[dict[str, object]],
        threshold: int,
    ) -> tuple[list[str], list[object], int]:
        if return_groups:
            return required_names, groups, threshold
        return required_names, _flatten_optional_scan_groups(groups), threshold

    selected_names = _filter_available_scan_names(selected_scan_names, available_scan_names)
    try:
        rule = DuplicateRuleConfig.from_dict(
            duplicate_rule if isinstance(duplicate_rule, dict) else None,
            default_min_count=int(duplicate_threshold),
        )
    except ValueError:
        rule = DuplicateRuleConfig(min_count=int(duplicate_threshold))

    explicit_required_scan_names = _filter_available_scan_names(required_scan_names, available_scan_names)
    explicit_optional_groups = _normalize_optional_scan_groups(optional_scan_groups, available_scan_names)
    if not explicit_optional_groups:
        explicit_optional_scan_names = [
            name
            for name in _filter_available_scan_names(optional_scan_names, available_scan_names)
            if name not in explicit_required_scan_names
        ]
        if explicit_optional_scan_names:
            explicit_optional_groups = [
                {
                    "group_name": "Optional Condition 1",
                    "scans": explicit_optional_scan_names,
                    "min_hits": max(1, min(int(rule.optional_min_hits), len(explicit_optional_scan_names)))
                    if rule.mode == "required_plus_optional_min"
                    else max(1, min(int(duplicate_threshold), len(explicit_optional_scan_names))),
                }
            ]
    if explicit_required_scan_names or explicit_optional_groups:
        selected_name_set = set(selected_names)
        if selected_name_set:
            explicit_required_scan_names = [
                name for name in explicit_required_scan_names if name in selected_name_set
            ]
            explicit_optional_groups = [
                {
                    **group,
                    "scans": [name for name in group.get("scans", []) if name in selected_name_set],
                }
                for group in explicit_optional_groups
            ]
            explicit_optional_groups = [
                {**group, "min_hits": max(1, min(int(group.get("min_hits", 1)), len(group.get("scans", []))))}
                for group in explicit_optional_groups
                if group.get("scans")
            ]
        if not explicit_required_scan_names and not explicit_optional_groups:
            optional_threshold = max(1, min(int(rule.min_count), len(selected_names))) if selected_names else 1
            return result([], [{"group_name": "Optional Condition 1", "scans": selected_names, "min_hits": optional_threshold}], optional_threshold)
        optional_threshold = int(explicit_optional_groups[0].get("min_hits", 1)) if explicit_optional_groups else 1
        return result(explicit_required_scan_names, explicit_optional_groups, optional_threshold)

    if rule.mode == "grouped_threshold":
        required_scan_names = _filter_available_scan_names(rule.required_scans, available_scan_names)
        optional_groups = [
            {
                "group_name": group.group_name,
                "scans": [
                    name for name in _filter_available_scan_names(group.scans, available_scan_names)
                    if name not in required_scan_names
                ],
                "min_hits": int(group.min_hits),
            }
            for group in rule.optional_groups
        ]
        optional_groups = [
            {**group, "min_hits": max(1, min(int(group["min_hits"]), len(group["scans"])))}
            for group in optional_groups
            if group["scans"]
        ]
        if required_scan_names or optional_groups:
            optional_threshold = int(optional_groups[0].get("min_hits", 1)) if optional_groups else 1
            return result(required_scan_names, optional_groups, optional_threshold)

    if rule.mode == "required_plus_optional_min":
        required_scan_names = _filter_available_scan_names(rule.required_scans, available_scan_names)
        optional_scan_names = [
            name
            for name in _filter_available_scan_names(rule.optional_scans, available_scan_names)
            if name not in required_scan_names
        ]
        if required_scan_names and optional_scan_names:
            optional_threshold = max(1, min(int(rule.optional_min_hits), len(optional_scan_names)))
            return result(required_scan_names, [{"group_name": "Optional Condition 1", "scans": optional_scan_names, "min_hits": optional_threshold}], optional_threshold)

    optional_threshold = max(1, min(int(rule.min_count), len(selected_names))) if selected_names else 1
    return result([], [{"group_name": "Optional Condition 1", "scans": selected_names, "min_hits": optional_threshold}] if selected_names else [], optional_threshold)


def _build_duplicate_role_state(
    required_scan_names: list[str],
    optional_scan_names: list[str],
    optional_threshold: int,
    optional_scan_groups: list[dict[str, object]] | None = None,
) -> tuple[list[str], int, dict[str, object]]:
    if optional_scan_groups is None and not required_scan_names and optional_scan_names:
        threshold = max(1, min(int(optional_threshold), len(optional_scan_names)))
        rule = DuplicateRuleConfig(min_count=threshold)
        return list(dict.fromkeys(optional_scan_names)), threshold, rule.to_dict()
    normalized_groups = _normalize_optional_scan_groups(optional_scan_groups, [*required_scan_names, *optional_scan_names])
    if not normalized_groups and optional_scan_names:
        threshold = max(1, min(int(optional_threshold), len(optional_scan_names)))
        normalized_groups = [{"group_name": "Optional Condition 1", "scans": list(optional_scan_names), "min_hits": threshold}]
    grouped_optional_scan_names = _flatten_optional_scan_groups(normalized_groups)
    selected_scan_names = _merge_scan_role_names(required_scan_names, grouped_optional_scan_names)
    if normalized_groups:
        threshold = int(normalized_groups[0].get("min_hits", 1))
        rule = DuplicateRuleConfig.from_dict(
            {
                "mode": "grouped_threshold",
                "min_count": threshold,
                "required_scans": list(required_scan_names),
                "optional_scans": list(grouped_optional_scan_names),
                "optional_min_hits": threshold,
                "optional_groups": normalized_groups,
            },
            default_min_count=threshold,
        )
        return selected_scan_names, threshold, rule.to_dict()

    threshold = max(1, len(required_scan_names)) if required_scan_names else max(1, int(optional_threshold))
    rule = DuplicateRuleConfig(min_count=threshold)
    return selected_scan_names, threshold, rule.to_dict()


def _watchlist_controls_equal(left: dict[str, object] | None, right: dict[str, object] | None) -> bool:
    if left is None or right is None:
        return False
    return _build_watchlist_control_values(
        list(left.get("selected_scan_names", [])),
        list(left.get("selected_annotation_filters", [])),
        list(left.get("selected_duplicate_subfilters", [])),
        int(left.get("duplicate_threshold", 1)),
        left.get("duplicate_rule"),
        list(left.get("required_scan_names", [])),
        list(left.get("optional_scan_names", [])),
        list(left.get("optional_scan_groups", [])),
    ) == _build_watchlist_control_values(
        list(right.get("selected_scan_names", [])),
        list(right.get("selected_annotation_filters", [])),
        list(right.get("selected_duplicate_subfilters", [])),
        int(right.get("duplicate_threshold", 1)),
        right.get("duplicate_rule"),
        list(right.get("required_scan_names", [])),
        list(right.get("optional_scan_names", [])),
        list(right.get("optional_scan_groups", [])),
    )


def _build_watchlist_preset_record(values: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": WATCHLIST_PRESET_SCHEMA_VERSION,
        "kind": WATCHLIST_PRESET_KIND,
        "values": values,
    }


def _build_builtin_watchlist_presets(scan_config: ScanConfig) -> dict[str, dict[str, object]]:
    presets: dict[str, dict[str, object]] = {}
    available_scan_names = [section.scan_name for section in scan_config.card_sections]
    for preset in scan_config.watchlist_presets:
        if not preset.visible_in_ui:
            continue
        preset_name = _normalize_watchlist_preset_name(preset.preset_name)
        if not preset_name:
            continue
        values = preset.to_control_values()
        required_scan_names, optional_scan_groups, _ = _resolve_duplicate_role_controls(
            values.get("selected_scan_names", []),
            values.get("duplicate_rule"),
            int(values.get("duplicate_threshold", 1)),
            available_scan_names,
            return_groups=True,
        )
        optional_scan_names = _flatten_optional_scan_groups(optional_scan_groups)
        presets[preset_name] = _build_watchlist_control_values(
            list(values.get("selected_scan_names", [])),
            list(values.get("selected_annotation_filters", [])),
            list(values.get("selected_duplicate_subfilters", [])),
            int(values.get("duplicate_threshold", 1)),
            values.get("duplicate_rule"),
            required_scan_names,
            optional_scan_names,
            optional_scan_groups,
        )
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

    required_scan_names, optional_scan_groups, _ = _resolve_duplicate_role_controls(
        selected_scan_names,
        parsed_duplicate_rule,
        duplicate_threshold,
        available_scan_names,
        values.get("required_scan_names"),
        values.get("optional_scan_names"),
        values.get("optional_scan_groups"),
        return_groups=True,
    )
    optional_scan_names = _flatten_optional_scan_groups(optional_scan_groups)
    return _build_watchlist_control_values(
        selected_scan_names,
        selected_annotation_filters,
        selected_duplicate_subfilters,
        duplicate_threshold,
        parsed_duplicate_rule,
        required_scan_names,
        optional_scan_names,
        optional_scan_groups,
    )


def _apply_watchlist_preset_to_session_state(
    values: dict[str, object],
    *,
    selection_key: str,
    annotation_key: str,
    duplicate_subfilter_key: str,
    threshold_key: str,
    duplicate_rule_key: str,
    optional_groups_key: str,
) -> None:
    st.session_state[selection_key] = list(values.get("selected_scan_names", []))
    st.session_state[annotation_key] = list(values.get("selected_annotation_filters", []))
    st.session_state[duplicate_subfilter_key] = list(values.get("selected_duplicate_subfilters", []))
    st.session_state[threshold_key] = int(values.get("duplicate_threshold", 1))
    st.session_state[duplicate_rule_key] = values.get("duplicate_rule")
    st.session_state[optional_groups_key] = list(values.get("optional_scan_groups", []))


def _build_watchlist_preset_export_filename(preset_name: str) -> str:
    safe_name = "".join(char if char.isalnum() else "_" for char in str(preset_name).strip())
    safe_name = safe_name.strip("_") or "preset"
    return f"watchlist_preset_{safe_name.lower()}.csv"


def _dataframe_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")


def render_watchlist_controls(config_path: str) -> WatchlistControlState:
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
    required_scan_key = "watchlist_required_scan_names"
    optional_scan_key = "watchlist_optional_scan_names"
    optional_groups_key = "watchlist_optional_scan_groups"
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
    (
        persisted_required_scan_names,
        persisted_optional_scan_groups,
        persisted_optional_threshold,
    ) = _resolve_duplicate_role_controls(
        persisted_selected_scan_names,
        persisted_duplicate_rule,
        persisted_duplicate_threshold_int,
        available_scan_names,
        watchlist_preferences.get("required_scan_names"),
        watchlist_preferences.get("optional_scan_names"),
        watchlist_preferences.get("optional_scan_groups"),
        return_groups=True,
    )
    persisted_optional_scan_names = _flatten_optional_scan_groups(persisted_optional_scan_groups)

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
    preset_columns = st.columns([2.4, 0.9, 0.9])
    with preset_columns[0]:
        selected_preset_name = st.selectbox(
            "Saved preset",
            options=preset_options,
            key=preset_select_key,
            format_func=lambda name: name if name else "Select a preset",
        )
    selected_preset_name = _resolve_selected_watchlist_preset_name(
        st.session_state.get(preset_select_key, selected_preset_name),
        watchlist_presets,
    )
    selected_preset_is_builtin = bool(selected_preset_name and selected_preset_name in builtin_watchlist_presets)
    selected_preset_export_name = selected_preset_name or None
    selected_preset_export_values = watchlist_presets.get(selected_preset_name) if selected_preset_name else None
    with preset_columns[1]:
        st.caption(" ")
        load_preset = st.button(
            "Load Preset",
            use_container_width=True,
            disabled=not bool(watchlist_presets),
        )
    with preset_columns[2]:
        st.caption(" ")
        delete_preset = st.button(
            "Delete Preset",
            use_container_width=True,
            disabled=not selected_preset_name or selected_preset_is_builtin,
        )

    if load_preset:
        selected_preset_name = _resolve_selected_watchlist_preset_name(
            st.session_state.get(preset_select_key, selected_preset_name),
            watchlist_presets,
        )
        loaded_values = watchlist_presets.get(selected_preset_name)
        if not selected_preset_name or loaded_values is None:
            st.warning("Select a preset before loading.")
        else:
            _apply_watchlist_preset_to_session_state(
                loaded_values,
                selection_key=selection_key,
                annotation_key=annotation_key,
                duplicate_subfilter_key=duplicate_subfilter_key,
                threshold_key=threshold_key,
                duplicate_rule_key=duplicate_rule_key,
                optional_groups_key=optional_groups_key,
            )
            st.session_state[selection_defaults_key] = selection_defaults_signature
            st.session_state[annotation_defaults_key] = annotation_defaults_signature
            st.session_state[duplicate_subfilter_defaults_key] = duplicate_subfilter_defaults_signature
            st.session_state[threshold_defaults_key] = (
                watchlist_preferences_namespace,
                max(1, len(loaded_values["selected_scan_names"])) if loaded_values["selected_scan_names"] else 1,
            )
            loaded_required_scan_names, loaded_optional_scan_groups, loaded_optional_threshold = _resolve_duplicate_role_controls(
                loaded_values.get("selected_scan_names", []),
                loaded_values.get("duplicate_rule"),
                int(loaded_values.get("duplicate_threshold", 1)),
                available_scan_names,
                loaded_values.get("required_scan_names"),
                loaded_values.get("optional_scan_names"),
                loaded_values.get("optional_scan_groups"),
                return_groups=True,
            )
            loaded_optional_scan_names = _flatten_optional_scan_groups(loaded_optional_scan_groups)
            st.session_state[required_scan_key] = loaded_required_scan_names
            st.session_state[optional_scan_key] = loaded_optional_scan_names
            st.session_state[optional_groups_key] = loaded_optional_scan_groups
            st.session_state["watchlist_condition_group_count"] = max(1, len(loaded_optional_scan_groups) or 1)
            st.session_state[threshold_key] = loaded_optional_threshold
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
        st.session_state[required_scan_key] = persisted_required_scan_names
        st.session_state[optional_scan_key] = persisted_optional_scan_names
        st.session_state[optional_groups_key] = persisted_optional_scan_groups
        st.session_state[selection_key] = _merge_scan_role_names(
            persisted_required_scan_names,
            persisted_optional_scan_names,
        )
        st.session_state[threshold_key] = persisted_optional_threshold
        st.session_state[selection_defaults_key] = selection_defaults_signature
    else:
        st.session_state[required_scan_key] = [
            name
            for name in st.session_state.get(required_scan_key, [])
            if name in available_scan_names
        ]
        st.session_state[optional_scan_key] = [
            name
            for name in st.session_state.get(optional_scan_key, current_selected_scan_names)
            if name in available_scan_names and name not in st.session_state[required_scan_key]
        ]
        st.session_state[optional_groups_key] = _normalize_optional_scan_groups(
            st.session_state.get(optional_groups_key, []),
            available_scan_names,
        )
        if not st.session_state[optional_groups_key] and st.session_state[optional_scan_key]:
            st.session_state[optional_groups_key] = [
                {
                    "group_name": "Optional Condition 1",
                    "scans": list(st.session_state[optional_scan_key]),
                    "min_hits": max(1, min(int(st.session_state.get(threshold_key, 1)), len(st.session_state[optional_scan_key]))),
                }
            ]
        st.session_state[selection_key] = _merge_scan_role_names(
            st.session_state[required_scan_key],
            st.session_state[optional_scan_key],
        )

    st.caption("Required scans must all hit. Each optional condition must meet its own minimum hit count.")
    selected_required_scans = st.multiselect(
        "Required scans",
        options=available_scan_names,
        format_func=lambda name: display_names.get(name, name),
        key=required_scan_key,
    )
    available_group_scan_names = [
        name for name in available_scan_names if name not in selected_required_scans
    ]
    existing_groups = _normalize_optional_scan_groups(
        st.session_state.get(optional_groups_key, persisted_optional_scan_groups),
        available_group_scan_names,
    )
    group_count_key = "watchlist_condition_group_count"
    max_condition_groups = 5
    if group_count_key not in st.session_state:
        st.session_state[group_count_key] = max(1, len(existing_groups) or 1)
    try:
        condition_group_count = int(st.session_state.get(group_count_key, 1))
    except (TypeError, ValueError):
        condition_group_count = 1
    condition_group_count = max(1, min(condition_group_count, max_condition_groups))
    st.session_state[group_count_key] = condition_group_count
    group_count_columns = st.columns([1.15, 1.15, 2.7])
    with group_count_columns[0]:
        add_condition_group = st.button(
            "Add optional condition",
            key="watchlist_add_condition_group",
            use_container_width=True,
            disabled=condition_group_count >= max_condition_groups,
        )
    with group_count_columns[1]:
        remove_condition_group = st.button(
            "Remove last condition",
            key="watchlist_remove_condition_group",
            use_container_width=True,
            disabled=condition_group_count <= 1,
        )
    if add_condition_group:
        condition_group_count = min(max_condition_groups, condition_group_count + 1)
        st.session_state[group_count_key] = condition_group_count
    if remove_condition_group:
        removed_index = condition_group_count
        condition_group_count = max(1, condition_group_count - 1)
        st.session_state[group_count_key] = condition_group_count
        for suffix in ("name", "scans", "min"):
            st.session_state.pop(f"watchlist_condition_group_{removed_index}_{suffix}", None)
    with group_count_columns[2]:
        st.caption(
            f"{condition_group_count} optional condition group(s). Each group is required, and each group can accept N hits from its own scan set."
        )
    while len(existing_groups) < condition_group_count:
        existing_groups.append(
            {
                "group_name": f"Optional Condition {len(existing_groups) + 1}",
                "scans": [],
                "min_hits": 1,
            }
        )
    existing_groups = existing_groups[:condition_group_count]

    selected_optional_groups: list[dict[str, object]] = []
    used_group_scans: set[str] = set()
    for index, group in enumerate(existing_groups, start=1):
        group_label_key = f"watchlist_condition_group_{index}_name"
        group_scans_key = f"watchlist_condition_group_{index}_scans"
        group_min_key = f"watchlist_condition_group_{index}_min"
        if group_label_key not in st.session_state:
            st.session_state[group_label_key] = str(group.get("group_name", f"Optional Condition {index}"))
        group_scan_options = [
            name
            for name in available_group_scan_names
            if name not in used_group_scans or name in group.get("scans", [])
        ]
        if group_scans_key not in st.session_state:
            st.session_state[group_scans_key] = [
                name for name in group.get("scans", []) if name in group_scan_options
            ]
        else:
            st.session_state[group_scans_key] = [
                name for name in st.session_state.get(group_scans_key, []) if name in group_scan_options
            ]
        with st.container(border=True):
            st.markdown(f"**Optional condition {index}**")
            group_name_columns = st.columns([2.4, 0.8])
            with group_name_columns[0]:
                group_name = st.text_input(
                    f"Optional condition {index} name",
                    key=group_label_key,
                ).strip() or f"Optional Condition {index}"
            group_scans = st.multiselect(
                f"{group_name} scans",
                options=group_scan_options,
                format_func=lambda name: display_names.get(name, name),
                key=group_scans_key,
            )
            used_group_scans.update(group_scans)
            max_group_hits = max(1, len(group_scans)) if group_scans else 1
            if group_min_key not in st.session_state:
                st.session_state[group_min_key] = max(1, min(int(group.get("min_hits", 1)), max_group_hits))
            else:
                st.session_state[group_min_key] = max(1, min(int(st.session_state[group_min_key]), max_group_hits))
            with group_name_columns[1]:
                group_min_hits = int(
                    st.number_input(
                        "Required hits",
                        min_value=1,
                        max_value=max_group_hits,
                        step=1,
                        key=group_min_key,
                        disabled=not group_scans,
                        help=f"Minimum hits required inside {group_name}.",
                    )
                )
            if group_scans:
                selected_optional_groups.append(
                    {
                        "group_name": group_name,
                        "scans": list(group_scans),
                        "min_hits": max(1, min(group_min_hits, len(group_scans))),
                    }
                )

    selected_optional_scans = _flatten_optional_scan_groups(selected_optional_groups)
    st.session_state[optional_scan_key] = selected_optional_scans
    st.session_state[optional_groups_key] = selected_optional_groups
    selected_watchlist_scans, duplicate_threshold, current_duplicate_rule = _build_duplicate_role_state(
        selected_required_scans,
        selected_optional_scans,
        int(st.session_state.get(threshold_key, persisted_optional_threshold)),
        selected_optional_groups,
    )
    st.session_state[selection_key] = selected_watchlist_scans
    st.session_state[duplicate_rule_key] = current_duplicate_rule

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

    selected_duplicate_subfilters: list[str] = []
    st.session_state[duplicate_subfilter_key] = selected_duplicate_subfilters

    st.session_state[threshold_key] = int(duplicate_threshold)
    selected_watchlist_scans, duplicate_threshold, current_duplicate_rule = _build_duplicate_role_state(
        selected_required_scans,
        selected_optional_scans,
        duplicate_threshold,
        selected_optional_groups,
    )
    st.session_state[selection_key] = selected_watchlist_scans
    st.session_state[duplicate_rule_key] = current_duplicate_rule

    current_watchlist_controls = _build_watchlist_control_values(
        selected_watchlist_scans,
        selected_annotation_filters,
        selected_duplicate_subfilters,
        duplicate_threshold,
        st.session_state.get(duplicate_rule_key),
        selected_required_scans,
        selected_optional_scans,
        selected_optional_groups,
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
    preset_editor_columns = st.columns([2.4, 0.9, 0.9])
    with preset_editor_columns[0]:
        st.text_input(
            "Preset name",
            key=preset_name_key,
            placeholder="e.g. Momentum Core",
        )
    with preset_editor_columns[1]:
        st.caption(" ")
        save_preset = st.button("Save Preset", use_container_width=True)
    with preset_editor_columns[2]:
        st.caption(" ")
        update_preset = st.button(
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

    return WatchlistControlState(
        scan_config=watchlist_scan_config,
        selected_scan_names=selected_watchlist_scans,
        required_scan_names=selected_required_scans,
        optional_scan_names=selected_optional_scans,
        optional_scan_groups=selected_optional_groups,
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
    config_path: str,
    artifacts: PlatformArtifacts,
    scan_config: ScanConfig | None = None,
    selected_scan_names: list[str] | None = None,
    required_scan_names: list[str] | None = None,
    optional_scan_names: list[str] | None = None,
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
    required_scan_name_set = set(required_scan_names or [])
    optional_scan_name_set = set(optional_scan_names or [])
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

    render_preset_hits_panel(config_path, artifacts, scan_config)

    cards: list[tuple[str, list[str], str, str | None]] = [
        (
            card.display_name,
            _to_ticker_list(card.rows),
            "No tickers matched this scan.",
            "required" if card.scan_name in required_scan_name_set else "optional" if card.scan_name in optional_scan_name_set else None,
        )
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
        if parsed_duplicate_rule.mode == "grouped_threshold":
            duplicate_note += f". Required scans: {', '.join(parsed_duplicate_rule.required_scans) or 'none'}."
            for group in parsed_duplicate_rule.optional_groups:
                duplicate_note += (
                    f" {group.group_name}: {group.min_hits}+ of "
                    f"{', '.join(group.scans)}."
                )
        elif parsed_duplicate_rule.mode == "required_plus_optional_min":
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
        duplicate_note = "No cards are selected. Choose one or more watchlist cards in the watchlist controls to enable duplicate counting."
        duplicate_empty_text = "No cards selected."

    render_priority_band_from_frame(
        "Duplicate Tickers",
        duplicate_frame,
        duplicate_note,
        duplicate_empty_text,
    )

    with st.expander("Current duplicate rule", expanded=False):
        required_text = ", ".join(required_scan_names or []) if required_scan_names else "None"
        st.caption(f"Required: {required_text}")
        if parsed_duplicate_rule.mode == "grouped_threshold":
            for group in parsed_duplicate_rule.optional_groups:
                st.caption(
                    f"{group.group_name}: {group.min_hits} of {len(group.scans)} required - "
                    + ", ".join(group.scans)
                )
        elif parsed_duplicate_rule.mode == "required_plus_optional_min":
            st.caption(
                f"Optional: {parsed_duplicate_rule.optional_min_hits} of {len(parsed_duplicate_rule.optional_scans)} required - "
                + ", ".join(parsed_duplicate_rule.optional_scans)
            )
        else:
            st.caption(f"Duplicate threshold: {duplicate_threshold} selected scan hit(s).")

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
            for column, (title, tickers, empty_text, role) in zip(columns, batch):
                with column:
                    render_ticker_card(title, tickers, empty_text, role=role)

    render_data_health_table(artifacts)


def render_preset_hits_panel(
    config_path: str,
    artifacts: PlatformArtifacts,
    scan_config: ScanConfig,
) -> None:
    with st.expander("Preset Hits", expanded=True):
        try:
            summary_frame, hits_frame = build_watchlist_preset_hit_frames(config_path, artifacts, scan_config)
        except Exception as exc:
            st.error(f"Preset hit list could not be built: {exc}")
            return

        trade_date = _latest_trade_date_for_export(artifacts)
        preset_count = len(load_watchlist_preset_definitions(config_path, scan_config))
        hit_count = len(summary_frame)
        st.caption(
            f"{hit_count:,} ticker(s) matched preset duplicate rules on {trade_date}. "
            f"Evaluated {preset_count:,} built-in/custom preset(s)."
        )

        if summary_frame.empty:
            st.caption("No preset hits for the current watchlist run.")
        else:
            display = summary_frame.rename(
                columns={
                    "ticker": "Ticker",
                    "hit_presets": "Hit Presets",
                    "hit_preset_count": "Preset Count",
                    "builtin_presets": "Built-in Presets",
                    "custom_presets": "Custom Presets",
                    "matched_scans": "Matched Scans",
                    "duplicate_rule_modes": "Rule Modes",
                }
            )
            display_columns = [
                "Ticker",
                "Preset Count",
                "Hit Presets",
                "Built-in Presets",
                "Custom Presets",
                "Matched Scans",
                "Rule Modes",
            ]
            st.dataframe(
                display[[column for column in display_columns if column in display.columns]],
                width="stretch",
                hide_index=True,
            )

        download_col, write_col = st.columns([1, 1])
        with download_col:
            st.download_button(
                "Download preset hits CSV",
                data=_dataframe_to_csv_bytes(hits_frame),
                file_name=f"preset_hits_{trade_date.replace('-', '')}.csv",
                mime="text/csv",
                use_container_width=True,
                disabled=hits_frame.empty,
            )
        with write_col:
            if st.button("Write preset CSV files", type="secondary", use_container_width=True):
                try:
                    export_dir = export_watchlist_preset_csvs(config_path, artifacts, respect_config=False)
                except Exception as exc:
                    st.error(f"Preset CSV export failed: {exc}")
                else:
                    if export_dir is None:
                        st.warning("No preset definitions were available for export.")
                    else:
                        st.session_state["preset_export_directory"] = str(export_dir)
                        st.success(f"Preset CSV files written to: {export_dir}")

        export_dir = st.session_state.get("preset_export_directory")
        if export_dir:
            st.caption(f"Latest preset CSV output: {export_dir}")
        export_error = st.session_state.get("preset_export_error")
        if export_error:
            st.caption(f"Automatic preset CSV output failed: {export_error}")


def render_entry_signals(
    artifacts: PlatformArtifacts,
    watchlist_state: WatchlistControlState,
    signal_state: EntrySignalPageState,
) -> None:
    render_page_header(
        "Entry Signals",
        subtitle="Entry-timing checks for the selected signal universe.",
        meta=_format_trade_date(artifacts),
    )
    st.caption(
        "Signals are not scans. They evaluate whether a selected candidate universe is at a reasonable entry point today."
    )

    universe_modes = list(ENTRY_SIGNAL_UNIVERSE_LABELS)
    control_col, signal_col = st.columns([1, 2])
    with control_col:
        selected_universe_mode = st.selectbox(
            "Signal universe",
            options=universe_modes,
            index=0,
            format_func=lambda mode: ENTRY_SIGNAL_UNIVERSE_LABELS.get(mode, str(mode)),
            help="Choose which ticker set Entry Signals should evaluate.",
        )
    enabled_signal_names = list(signal_state.signal_config.enabled_signal_names())
    default_selected_signals = [
        name
        for name in signal_state.selected_signal_names
        if name in enabled_signal_names and name in ENTRY_SIGNAL_REGISTRY
    ]
    display_names = {
        name: ENTRY_SIGNAL_REGISTRY[name].display_name
        for name in enabled_signal_names
        if name in ENTRY_SIGNAL_REGISTRY
    }
    with signal_col:
        selected_signal_names = st.multiselect(
            "Entry signal logic",
            options=enabled_signal_names,
            default=default_selected_signals,
            format_func=lambda name: display_names.get(name, str(name)),
            help="Entry timing logic to evaluate against the selected universe.",
        )

    duplicate_threshold = int(watchlist_state.duplicate_threshold)
    parsed_duplicate_rule = DuplicateRuleConfig.from_dict(
        watchlist_state.duplicate_rule,
        default_min_count=duplicate_threshold,
    )
    runner = EntrySignalRunner(signal_state.signal_config, watchlist_state.scan_config)
    signal_watchlist = artifacts.entry_signal_watchlist if artifacts.entry_signal_watchlist is not None else artifacts.watchlist
    universe = runner.build_universe(
        signal_watchlist,
        artifacts.scan_hits,
        selected_scan_names=watchlist_state.selected_scan_names,
        duplicate_threshold=duplicate_threshold,
        selected_annotation_filters=watchlist_state.selected_annotation_filters,
        selected_duplicate_subfilters=watchlist_state.selected_duplicate_subfilters,
        duplicate_rule=parsed_duplicate_rule,
        universe_mode=selected_universe_mode,
        eligible_snapshot=artifacts.eligible_snapshot,
    )
    result = runner.evaluate(universe, selected_signal_names)
    summary_col, signal_col = st.columns([1, 2])
    with summary_col:
        st.metric("Signal Universe", int(len(universe)))
    with signal_col:
        st.caption("Universe source: " + ENTRY_SIGNAL_UNIVERSE_LABELS.get(selected_universe_mode, str(selected_universe_mode)))
        st.caption(
            "Selected signals: "
            + (", ".join(selected_signal_names) if selected_signal_names else "None")
        )

    if not selected_signal_names:
        st.info("Select at least one entry signal.")
    elif result.empty:
        st.caption("No ticker in the selected universe matched the selected entry signals.")
    else:
        st.dataframe(result, width="stretch", hide_index=True, height=min(760, 110 + len(result) * 35))

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


def _tracking_health_value(payload: dict[str, object], key: str) -> int:
    try:
        return int(payload.get(key, 0))
    except (TypeError, ValueError):
        return 0


def render_setting() -> None:
    render_page_header(
        "Setting",
        subtitle="Tracking diagnostics now. Global app settings can be added here.",
    )
    tracking_health = st.session_state.get("tracking_health")
    if not isinstance(tracking_health, dict) or not tracking_health:
        st.caption("Tracking health is available after loading screening artifacts.")
        return
    rows = [
        ("Active detections", _tracking_health_value(tracking_health, "active_detection_count")),
        ("Missing hit close", _tracking_health_value(tracking_health, "missing_hit_close_count")),
        ("Missing 1D close", _tracking_health_value(tracking_health, "missing_close_1d_count")),
        ("Missing 5D close", _tracking_health_value(tracking_health, "missing_close_5d_count")),
        ("Filled 1D returns", _tracking_health_value(tracking_health, "filled_return_1d_count")),
        ("Filled 5D returns", _tracking_health_value(tracking_health, "filled_return_5d_count")),
    ]
    st.dataframe(
        pd.DataFrame(rows, columns=["Metric", "Count"]),
        width="stretch",
        hide_index=True,
    )


@st.cache_data(ttl=1800, show_spinner=False)
def _load_benchmark_price_history(config_path: str, benchmark_ticker: str) -> pd.DataFrame:
    settings = load_settings(config_path)
    app_settings = settings.get("app", {}) if isinstance(settings.get("app", {}), dict) else {}
    data_settings = settings.get("data", {}) if isinstance(settings.get("data", {}), dict) else {}
    cache_dir = Path(str(app_settings.get("cache_dir", "data_cache"))).expanduser()
    if not cache_dir.is_absolute():
        cache_dir = ROOT / cache_dir
    provider = YFinancePriceDataProvider(
        CacheLayer(cache_dir),
        technical_ttl_hours=int(data_settings.get("technical_cache_ttl_hours", 12)),
        allow_stale_cache_on_failure=bool(data_settings.get("allow_stale_cache_on_failure", True)),
        batch_size=int(data_settings.get("price_batch_size", 80)),
        max_retries=int(data_settings.get("price_max_retries", 3)),
        request_sleep_seconds=float(data_settings.get("price_request_sleep_seconds", 2.0)),
        retry_backoff_multiplier=float(data_settings.get("price_retry_backoff_multiplier", 2.0)),
        incremental_period=data_settings.get("price_incremental_period", "5d"),
    )
    period = str(app_settings.get("price_period", "18mo"))
    try:
        result = provider.get_price_history([benchmark_ticker], period=period, force_refresh=False)
    except RuntimeError:
        return pd.DataFrame()
    history = result.histories.get(benchmark_ticker, pd.DataFrame())
    return _normalized_price_history(history)


def _normalized_price_history(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty or "close" not in history.columns:
        return pd.DataFrame()
    working = history.copy()
    working.index = pd.to_datetime(working.index, errors="coerce")
    working = working.loc[working.index.notna()].sort_index()
    return working


def _close_on_or_after(history: pd.DataFrame, target_date: pd.Timestamp) -> float | None:
    if history.empty:
        return None
    normalized_target = pd.Timestamp(target_date).normalize()
    candidates = history.loc[history.index.normalize() >= normalized_target]
    if candidates.empty:
        return None
    try:
        return float(candidates.iloc[0]["close"])
    except (TypeError, ValueError, KeyError):
        return None


def _build_benchmark_return_map(
    history: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    horizon_days: int,
) -> dict[pd.Timestamp, float]:
    if history.empty:
        return {}
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    if end < start:
        return {}
    results: dict[pd.Timestamp, float] = {}
    for current in pd.date_range(start=start, end=end, freq="D"):
        base_close = _close_on_or_after(history, current)
        if base_close is None or base_close == 0:
            continue
        target_close = _close_on_or_after(history, current + BDay(horizon_days))
        if target_close is None:
            continue
        results[current.normalize()] = ((target_close / base_close) - 1.0) * 100.0
    return results


def _build_benchmark_horizon_payload_map(
    history: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    horizon_days: int,
) -> dict[pd.Timestamp, dict[str, float]]:
    if history.empty:
        return {}
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    if end < start:
        return {}
    results: dict[pd.Timestamp, dict[str, float]] = {}
    for current in pd.date_range(start=start, end=end, freq="D"):
        base_close = _close_on_or_after(history, current)
        if base_close is None or base_close == 0:
            continue
        target_close = _close_on_or_after(history, current + BDay(horizon_days))
        if target_close is None:
            continue
        results[current.normalize()] = {
            "benchmark_close_at_hit": base_close,
            "benchmark_close_at_target": target_close,
            "benchmark_return_pct": ((target_close / base_close) - 1.0) * 100.0,
        }
    return results


def _build_tracking_analysis_export_frames(
    scoped_detail: pd.DataFrame,
    *,
    benchmark_ticker: str,
    benchmark_history: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if scoped_detail.empty:
        return pd.DataFrame(), pd.DataFrame()
    working = scoped_detail.copy()
    working["hit_date"] = pd.to_datetime(working["hit_date"], errors="coerce")
    working = working.loc[working["hit_date"].notna()].copy()
    if working.empty:
        return pd.DataFrame(), pd.DataFrame()
    min_hit_date = pd.Timestamp(working["hit_date"].min()).normalize()
    max_hit_date = pd.Timestamp(working["hit_date"].max()).normalize()
    benchmark_maps = {
        horizon: _build_benchmark_horizon_payload_map(benchmark_history, min_hit_date, max_hit_date, horizon)
        for horizon in TRACKING_HORIZON_OPTIONS
    }
    observation_rows: list[dict[str, object]] = []
    for _, row in working.iterrows():
        hit_date = pd.Timestamp(row["hit_date"]).normalize()
        for horizon in TRACKING_HORIZON_OPTIONS:
            return_column = f"return_{horizon}d"
            close_column = f"close_at_{horizon}d"
            return_value = row.get(return_column)
            close_at_target = row.get(close_column)
            if pd.isna(return_value) and pd.isna(close_at_target):
                continue
            benchmark_payload = benchmark_maps[horizon].get(hit_date, {})
            benchmark_return = benchmark_payload.get("benchmark_return_pct")
            observation_rows.append(
                {
                    "detection_id": row.get("detection_id"),
                    "hit_date": hit_date.strftime("%Y-%m-%d"),
                    "preset_name": row.get("preset_name"),
                    "ticker": row.get("ticker"),
                    "status": row.get("status"),
                    "market_env": row.get("market_env"),
                    "horizon_days": horizon,
                    "return_pct": return_value if not pd.isna(return_value) else None,
                    "benchmark_ticker": benchmark_ticker,
                    "benchmark_return_pct": benchmark_return,
                    "excess_return_pct": (
                        (float(return_value) - float(benchmark_return))
                        if (not pd.isna(return_value) and benchmark_return is not None)
                        else None
                    ),
                    "close_at_hit": row.get("close_at_hit"),
                    "close_at_target": close_at_target if not pd.isna(close_at_target) else None,
                    "benchmark_close_at_hit": benchmark_payload.get("benchmark_close_at_hit"),
                    "benchmark_close_at_target": benchmark_payload.get("benchmark_close_at_target"),
                    "hit_scans": row.get("hit_scans"),
                }
            )
    observations = pd.DataFrame(observation_rows)
    scan_bridge_rows: list[dict[str, object]] = []
    for _, row in working.iterrows():
        detection_id = row.get("detection_id")
        if pd.isna(detection_id):
            continue
        hit_scans = str(row.get("hit_scans", "")).strip()
        if not hit_scans:
            continue
        for scan_name in [part.strip() for part in hit_scans.split(",") if part.strip()]:
            scan_bridge_rows.append(
                {
                    "detection_id": int(detection_id),
                    "hit_date": pd.Timestamp(row["hit_date"]).strftime("%Y-%m-%d"),
                    "preset_name": row.get("preset_name"),
                    "ticker": row.get("ticker"),
                    "scan_name": scan_name,
                }
            )
    detection_scans = pd.DataFrame(scan_bridge_rows)
    return observations, detection_scans


def _format_tracking_percent(value: object, *, signed: bool = True) -> str:
    number = _coerce_number(value)
    if number is None:
        return "-"
    sign = "+" if signed else ""
    return f"{number:{sign}.2f}%"


def _format_tracking_price(value: object) -> str:
    number = _coerce_number(value)
    if number is None:
        return "-"
    return f"{number:,.2f}"


def _format_tracking_count(value: object) -> str:
    number = _coerce_number(value)
    if number is None:
        return "-"
    return f"{int(number):,}"


def _format_tracking_metric(value: object) -> str:
    number = _coerce_number(value)
    if number is None:
        return "-"
    return f"{number:.1f}"


def _format_tracking_win_rate(value: object) -> str:
    number = _coerce_number(value)
    if number is None:
        return "-"
    return f"{number * 100.0:.1f}%"


def _tracking_value_until_horizon(row: pd.Series, column_name: str, horizon: int, selected_horizon: int, formatter) -> str:
    if horizon > selected_horizon:
        return "-"
    return formatter(row.get(column_name))


def _build_tracking_ranking_display(ranking: pd.DataFrame) -> pd.DataFrame:
    if ranking.empty:
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "Preset": ranking["preset_name"].astype(str),
            "Market": ranking["market_env"].astype(str),
            "Avg Return (%)": ranking["avg_return_pct"].map(_format_tracking_percent),
            "Excess vs Benchmark (%)": ranking["excess_avg_pct"].map(_format_tracking_percent),
            "Max Return (%)": ranking["max_return_pct"].map(_format_tracking_percent),
            "Min Return (%)": ranking["min_return_pct"].map(_format_tracking_percent),
            "Win Rate (%)": ranking["win_rate"].map(_format_tracking_win_rate),
            "Detections": ranking["detection_count"].map(_format_tracking_count),
        }
    )


def _build_tracking_detail_display(
    detail: pd.DataFrame,
    *,
    selected_horizon: int,
    benchmark_ticker: str,
) -> pd.DataFrame:
    if detail.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for _, row in detail.iterrows():
        display_row: dict[str, object] = {
            "Hit Date": row.get("hit_date"),
            "Preset": row.get("preset_name"),
            "Market": row.get("market_env"),
            "Ticker": row.get("ticker"),
            "Status": row.get("status"),
            "Hit Close": _format_tracking_price(row.get("close_at_hit")),
            "RS21": _format_tracking_metric(row.get("rs21_at_hit")),
            "VCS": _format_tracking_metric(row.get("vcs_at_hit")),
            "Hybrid": _format_tracking_metric(row.get("hybrid_score_at_hit")),
            "Duplicate Hits": _format_tracking_count(row.get("duplicate_hit_count")),
        }
        for horizon in TRACKING_HORIZON_OPTIONS:
            label = f"{horizon}D"
            display_row[f"{label} Close"] = _tracking_value_until_horizon(
                row,
                f"close_at_{horizon}d",
                horizon,
                selected_horizon,
                _format_tracking_price,
            )
            display_row[f"{label} Return (%)"] = _tracking_value_until_horizon(
                row,
                f"return_{horizon}d",
                horizon,
                selected_horizon,
                _format_tracking_percent,
            )
        display_row[f"Excess vs {benchmark_ticker} (%)"] = _format_tracking_percent(row.get("excess_return_pct"))
        display_row["Hit Scans"] = row.get("hit_scans")
        display_row["Matched Filters"] = row.get("matched_filters")
        rows.append(display_row)
    return pd.DataFrame(rows)


def _style_tracking_excess_rows(frame: pd.DataFrame, excess_column: str):
    if frame.empty or excess_column not in frame.columns:
        return frame

    def row_style(row: pd.Series) -> list[str]:
        number = _coerce_number(row.get(excess_column))
        if number is None:
            return ["" for _ in row]
        if number > 0:
            return ["background-color:rgba(33,164,111,.11);" for _ in row]
        if number < 0:
            return ["background-color:rgba(223,91,91,.11);" for _ in row]
        return ["" for _ in row]

    return frame.style.apply(row_style, axis=1)


def render_analysis() -> None:
    render_page_header(
        "Analysis",
        subtitle="Preset-level performance summary with unified filters.",
    )
    detail_frame = read_detection_detail()
    if detail_frame.empty:
        st.caption("No detection rows are available.")
        return

    config_path = str(ROOT / "config" / "default.yaml")
    preset_universe = sorted(
        {
            str(preset.preset_name).strip()
            for preset in load_scan_config(config_path).watchlist_presets
            if str(preset.preset_name).strip()
        }
    )
    if not preset_universe:
        preset_universe = sorted(str(value) for value in detail_frame["preset_name"].dropna().unique().tolist())

    detail_frame = detail_frame.copy()
    detail_frame["hit_date"] = pd.to_datetime(detail_frame["hit_date"], errors="coerce")
    detail_frame["market_env"] = detail_frame["market_env"].astype(str).str.strip().str.lower()
    detail_frame = detail_frame.loc[detail_frame["market_env"].isin(TRACKING_MARKET_ENV_OPTIONS)].copy()
    valid_dates = detail_frame["hit_date"].dropna()
    render_section_heading("Aggregation Scope", "Preset universe / horizon / hit date / market environment.")

    selected_presets_state_key = "tracking_scope_presets_state"
    selected_horizon_state_key = "tracking_scope_horizon_state"
    selected_date_range_state_key = "tracking_scope_date_range_state"
    selected_market_env_state_key = "tracking_scope_market_env_state"
    selected_benchmark_state_key = "tracking_scope_benchmark_state"
    selected_presets_widget_key = "tracking_scope_presets_widget"
    selected_horizon_widget_key = "tracking_scope_horizon_widget"
    selected_date_range_widget_key = "tracking_scope_date_range_widget"
    selected_market_env_widget_key = "tracking_scope_market_env_widget"
    selected_benchmark_widget_key = "tracking_scope_benchmark_widget"

    persisted_presets = st.session_state.get(selected_presets_state_key, preset_universe)
    if not isinstance(persisted_presets, list):
        persisted_presets = list(preset_universe)
    persisted_presets = [name for name in persisted_presets if name in preset_universe]
    if not persisted_presets:
        persisted_presets = list(preset_universe)

    persisted_horizon = st.session_state.get(selected_horizon_state_key, TRACKING_HORIZON_OPTIONS[0])
    if persisted_horizon not in TRACKING_HORIZON_OPTIONS:
        persisted_horizon = TRACKING_HORIZON_OPTIONS[0]

    default_date_range: tuple[object, object] | tuple[()] = ()
    if not valid_dates.empty:
        fallback_start = valid_dates.min().date()
        fallback_end = valid_dates.max().date()
        persisted_date_range = st.session_state.get(selected_date_range_state_key, (fallback_start, fallback_end))
        if not (
            isinstance(persisted_date_range, tuple)
            and len(persisted_date_range) == 2
            and persisted_date_range[0] is not None
            and persisted_date_range[1] is not None
        ):
            persisted_date_range = (fallback_start, fallback_end)
        default_date_range = persisted_date_range

    persisted_market_envs = st.session_state.get(selected_market_env_state_key, list(TRACKING_MARKET_ENV_OPTIONS))
    if not isinstance(persisted_market_envs, list):
        persisted_market_envs = list(TRACKING_MARKET_ENV_OPTIONS)
    persisted_market_envs = [name for name in persisted_market_envs if name in TRACKING_MARKET_ENV_OPTIONS]
    if not persisted_market_envs:
        persisted_market_envs = list(TRACKING_MARKET_ENV_OPTIONS)

    persisted_benchmark = st.session_state.get(selected_benchmark_state_key, TRACKING_BENCHMARK_OPTIONS[0])
    if persisted_benchmark not in TRACKING_BENCHMARK_OPTIONS:
        persisted_benchmark = TRACKING_BENCHMARK_OPTIONS[0]

    if selected_presets_widget_key not in st.session_state:
        st.session_state[selected_presets_widget_key] = list(persisted_presets)
    else:
        widget_presets = st.session_state.get(selected_presets_widget_key, [])
        if not isinstance(widget_presets, list):
            st.session_state[selected_presets_widget_key] = list(persisted_presets)
        else:
            st.session_state[selected_presets_widget_key] = [name for name in widget_presets if name in preset_universe]

    if selected_horizon_widget_key not in st.session_state:
        st.session_state[selected_horizon_widget_key] = int(persisted_horizon)
    elif st.session_state.get(selected_horizon_widget_key) not in TRACKING_HORIZON_OPTIONS:
        st.session_state[selected_horizon_widget_key] = int(persisted_horizon)

    if valid_dates.empty:
        st.session_state.pop(selected_date_range_widget_key, None)
    elif selected_date_range_widget_key not in st.session_state:
        st.session_state[selected_date_range_widget_key] = default_date_range
    else:
        widget_date_range = st.session_state.get(selected_date_range_widget_key, default_date_range)
        if not (
            isinstance(widget_date_range, tuple)
            and len(widget_date_range) == 2
            and widget_date_range[0] is not None
            and widget_date_range[1] is not None
        ):
            st.session_state[selected_date_range_widget_key] = default_date_range

    if selected_market_env_widget_key not in st.session_state:
        st.session_state[selected_market_env_widget_key] = list(persisted_market_envs)
    else:
        widget_market_envs = st.session_state.get(selected_market_env_widget_key, [])
        if not isinstance(widget_market_envs, list):
            st.session_state[selected_market_env_widget_key] = list(persisted_market_envs)
        else:
            st.session_state[selected_market_env_widget_key] = [
                name for name in widget_market_envs if name in TRACKING_MARKET_ENV_OPTIONS
            ]

    if selected_benchmark_widget_key not in st.session_state:
        st.session_state[selected_benchmark_widget_key] = str(persisted_benchmark)
    elif st.session_state.get(selected_benchmark_widget_key) not in TRACKING_BENCHMARK_OPTIONS:
        st.session_state[selected_benchmark_widget_key] = str(persisted_benchmark)

    p_col, h_col, d_col, e_col, b_col = st.columns([1.5, 0.8, 1.3, 1.1, 0.8])
    with p_col:
        selected_presets = st.multiselect(
            "Preset Universe",
            options=preset_universe,
            key=selected_presets_widget_key,
        )
    with h_col:
        selected_horizon = int(
            st.selectbox(
                "Horizon",
                options=list(TRACKING_HORIZON_OPTIONS),
                format_func=lambda value: f"{value}D",
                key=selected_horizon_widget_key,
            )
        )
    with d_col:
        if valid_dates.empty:
            selected_date_range: tuple[object, object] | tuple[()] = ()
            st.caption("No valid hit dates")
        else:
            selected_date_range = st.date_input(
                "Hit Date Range",
                key=selected_date_range_widget_key,
            )
    with e_col:
        selected_market_envs = st.multiselect(
            "Hit Market Env",
            options=list(TRACKING_MARKET_ENV_OPTIONS),
            key=selected_market_env_widget_key,
        )
    with b_col:
        selected_benchmark = st.selectbox(
            "Benchmark",
            options=list(TRACKING_BENCHMARK_OPTIONS),
            key=selected_benchmark_widget_key,
        )

    st.session_state[selected_presets_state_key] = list(selected_presets)
    st.session_state[selected_horizon_state_key] = int(selected_horizon)
    if isinstance(selected_date_range, tuple) and len(selected_date_range) == 2:
        st.session_state[selected_date_range_state_key] = selected_date_range
    st.session_state[selected_market_env_state_key] = list(selected_market_envs)
    st.session_state[selected_benchmark_state_key] = str(selected_benchmark)

    filtered_detail = detail_frame.copy()
    if (
        isinstance(selected_date_range, tuple)
        and len(selected_date_range) == 2
        and selected_date_range[0] is not None
        and selected_date_range[1] is not None
    ):
        start_date = pd.Timestamp(selected_date_range[0]).normalize()
        end_date = pd.Timestamp(selected_date_range[1]).normalize()
        filtered_detail = filtered_detail.loc[
            (filtered_detail["hit_date"] >= start_date) & (filtered_detail["hit_date"] <= end_date)
        ].copy()
    if selected_presets:
        filtered_detail = filtered_detail.loc[filtered_detail["preset_name"].isin(selected_presets)].copy()
    if selected_market_envs:
        filtered_detail = filtered_detail.loc[filtered_detail["market_env"].isin(selected_market_envs)].copy()

    return_column = f"return_{selected_horizon}d"
    close_column = f"close_at_{selected_horizon}d"
    aggregation_base = filtered_detail.loc[filtered_detail[return_column].notna()].copy()
    aggregation_base["selected_return_pct"] = aggregation_base[return_column]
    benchmark_history = pd.DataFrame()
    benchmark_return_map: dict[pd.Timestamp, float] = {}
    if not aggregation_base.empty:
        hit_dates = aggregation_base["hit_date"].dropna()
        if not hit_dates.empty:
            benchmark_history = _load_benchmark_price_history(config_path, selected_benchmark)
            benchmark_return_map = _build_benchmark_return_map(
                benchmark_history,
                hit_dates.min(),
                hit_dates.max(),
                selected_horizon,
            )
    aggregation_base["benchmark_return_pct"] = aggregation_base["hit_date"].map(
        lambda value: benchmark_return_map.get(pd.Timestamp(value).normalize()) if pd.notna(value) else None
    )
    aggregation_base["excess_return_pct"] = aggregation_base["selected_return_pct"] - aggregation_base["benchmark_return_pct"]

    render_section_heading("Ranking", "Per-preset summary using selected scope and horizon return.")
    if aggregation_base.empty:
        st.caption("No rows matched the selected horizon and filters.")
    else:
        ranking = aggregation_base.groupby(["preset_name", "market_env"], as_index=False).agg(
            detection_count=(return_column, "count"),
            avg_return_pct=(return_column, "mean"),
            max_return_pct=(return_column, "max"),
            min_return_pct=(return_column, "min"),
        )
        win_rate = (
            aggregation_base.assign(is_win=aggregation_base[return_column] > 0)
            .groupby(["preset_name", "market_env"], as_index=False)["is_win"]
            .mean()
            .rename(columns={"is_win": "win_rate"})
        )
        benchmark_stats = aggregation_base.groupby(["preset_name", "market_env"], as_index=False).agg(
            benchmark_avg_pct=("benchmark_return_pct", "mean"),
            excess_avg_pct=("excess_return_pct", "mean"),
        )
        ranking = ranking.merge(win_rate, on=["preset_name", "market_env"], how="left")
        ranking = ranking.merge(benchmark_stats, on=["preset_name", "market_env"], how="left")
        ranking["avg_return_pct"] = ranking["avg_return_pct"].round(2)
        ranking["max_return_pct"] = ranking["max_return_pct"].round(2)
        ranking["min_return_pct"] = ranking["min_return_pct"].round(2)
        ranking["win_rate"] = ranking["win_rate"].round(3)
        ranking["excess_avg_pct"] = ranking["excess_avg_pct"].round(2)
        ranking = ranking.sort_values(["avg_return_pct", "detection_count"], ascending=[False, False]).reset_index(drop=True)
        st.caption(f"{len(ranking):,} rows")
        ranking_display = _build_tracking_ranking_display(ranking)
        st.dataframe(
            _style_tracking_excess_rows(ranking_display, "Excess vs Benchmark (%)"),
            width="stretch",
            hide_index=True,
            height=min(620, 110 + max(1, len(ranking)) * 32),
        )

    render_section_heading(
        "Detail",
        f"Scope-matched rows with returns through the selected {selected_horizon}D horizon. Later horizons are shown as '-'.",
    )
    filtered_detail["selected_return_pct"] = filtered_detail[return_column]
    filtered_detail["selected_close_at_target"] = filtered_detail[close_column]
    filtered_detail["benchmark_return_pct"] = filtered_detail["hit_date"].map(
        lambda value: benchmark_return_map.get(pd.Timestamp(value).normalize()) if pd.notna(value) else None
    )
    filtered_detail["excess_return_pct"] = filtered_detail["selected_return_pct"] - filtered_detail["benchmark_return_pct"]
    export_detail = filtered_detail.copy()
    observations_export, detection_scans_export = _build_tracking_analysis_export_frames(
        export_detail,
        benchmark_ticker=selected_benchmark,
        benchmark_history=benchmark_history,
    )
    filtered_detail = filtered_detail.sort_values(["hit_date", "preset_name", "ticker"], ascending=[False, True, True])
    filtered_detail["hit_date"] = filtered_detail["hit_date"].dt.strftime("%Y-%m-%d")
    st.caption(f"{len(filtered_detail):,} rows")
    detail_display = _build_tracking_detail_display(
        filtered_detail,
        selected_horizon=selected_horizon,
        benchmark_ticker=selected_benchmark,
    )
    st.dataframe(
        _style_tracking_excess_rows(detail_display, f"Excess vs {selected_benchmark} (%)"),
        width="stretch",
        hide_index=True,
        height=min(760, 110 + max(1, len(filtered_detail)) * 30),
    )
    render_section_heading("Export", "Analysis-oriented normalized CSV output.")
    export_col1, export_col2 = st.columns(2)
    with export_col1:
        st.download_button(
            "Export Observations CSV",
            data=_dataframe_to_csv_bytes(observations_export),
            file_name=f"tracking_observations_h{selected_horizon}_{selected_benchmark.lower()}.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=observations_export.empty,
        )
    with export_col2:
        st.download_button(
            "Export Detection Scans CSV",
            data=_dataframe_to_csv_bytes(detection_scans_export),
            file_name=f"tracking_detection_scans_h{selected_horizon}_{selected_benchmark.lower()}.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=detection_scans_export.empty,
        )
    if observations_export.empty:
        st.caption("No scoped observations were available for export.")
    else:
        st.caption(f"observations: {len(observations_export):,} rows / detection_scans: {len(detection_scans_export):,} rows")
def render_active_page(
    page_key: str,
    config_path: str,
    artifacts: PlatformArtifacts,
    watchlist_state: WatchlistControlState | None,
    signal_state: EntrySignalPageState | None,
) -> None:
    if page_key == "watchlist":
        if watchlist_state is None:
            st.error("Watchlist controls could not be initialized.")
            return
        render_watchlist(
            config_path,
            artifacts,
            scan_config=watchlist_state.scan_config,
            selected_scan_names=watchlist_state.selected_scan_names,
            required_scan_names=watchlist_state.required_scan_names,
            optional_scan_names=watchlist_state.optional_scan_names,
            duplicate_min_count=watchlist_state.duplicate_threshold,
            selected_annotation_filters=watchlist_state.selected_annotation_filters,
            selected_duplicate_subfilters=watchlist_state.selected_duplicate_subfilters,
            duplicate_rule=watchlist_state.duplicate_rule,
        )
        return
    if page_key == "entry_signals":
        if watchlist_state is None or signal_state is None:
            st.error("Entry signal controls could not be initialized.")
            return
        render_entry_signals(artifacts, watchlist_state, signal_state)
        return
    if page_key == "rs_radar":
        render_rs_radar(artifacts)
        return
    if page_key == "analysis":
        render_analysis()
        return
    if page_key == "setting":
        render_setting()
        return
    render_market_dashboard(artifacts)


def main() -> None:
    inject_global_styles()
    default_config = ROOT / "config" / "default.yaml"
    page_key = current_page_key()
    watchlist_state: WatchlistControlState | None = None
    signal_state: EntrySignalPageState | None = None

    config_path = str(default_config)
    symbols: list[str] = []
    with st.expander("Run options", expanded=False):
        force_universe_refresh = st.checkbox("Force weekly universe refresh", value=False)
        force_price_refresh = st.checkbox(
            "Force price data refresh",
            value=False,
            help="Bypass the price-cache TTL and fetch the latest OHLCV data while keeping cached rows as fallback.",
        )
        refresh = st.button("Refresh data", type="secondary")

    cache_key = (config_path, tuple(symbols), force_universe_refresh, force_price_refresh)
    if refresh or st.session_state.get("artifacts_key") != cache_key:
        with st.spinner("Loading screening artifacts..."):
            artifacts = load_artifacts(
                config_path,
                symbols,
                force_universe_refresh,
                force_price_refresh,
                prefer_saved_run=not refresh,
            )
            st.session_state["artifacts"] = artifacts
            if artifacts.artifact_origin == "pipeline_recomputed":
                try:
                    preset_export_dir = export_watchlist_preset_csvs(config_path, artifacts)
                except Exception as exc:
                    preset_export_dir = None
                    st.session_state["preset_export_error"] = str(exc)
                else:
                    st.session_state["preset_export_error"] = ""
                st.session_state["preset_export_directory"] = str(preset_export_dir) if preset_export_dir is not None else ""
                effectiveness_sync = sync_preset_effectiveness_logs(
                    config_path,
                    artifacts,
                    register_detections=True,
                )
            else:
                st.session_state["preset_export_directory"] = ""
                st.session_state["preset_export_error"] = ""
                effectiveness_sync = sync_preset_effectiveness_logs(
                    config_path,
                    artifacts,
                    register_detections=False,
                )
            st.session_state["preset_effectiveness_directory"] = (
                effectiveness_sync.tracking_db_path if effectiveness_sync is not None else ""
            )
            st.session_state["tracking_health"] = (
                {
                    "active_detection_count": effectiveness_sync.active_detection_count,
                    "missing_hit_close_count": effectiveness_sync.missing_hit_close_count,
                    "missing_close_1d_count": effectiveness_sync.missing_close_1d_count,
                    "missing_close_5d_count": effectiveness_sync.missing_close_5d_count,
                    "filled_return_1d_count": effectiveness_sync.filled_return_1d_count,
                    "filled_return_5d_count": effectiveness_sync.filled_return_5d_count,
                }
                if effectiveness_sync is not None
                else {}
            )
            st.session_state["artifacts_key"] = cache_key

    artifacts: PlatformArtifacts = st.session_state["artifacts"]
    page_key = render_page_tabs()
    render_context_strip([f"Data source: {artifacts.data_source_label}"])
    render_data_health_banner(artifacts)
    if page_key in {"watchlist", "entry_signals"} and watchlist_state is None:
        with st.expander("Watchlist presets and controls", expanded=False):
            watchlist_state = render_watchlist_controls(config_path)

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
        with st.expander("Preset export", expanded=False):
            st.markdown("**Preset Export**")
            st.download_button(
                "Export Preset CSV",
                data=_dataframe_to_csv_bytes(preset_export_frame),
                file_name=_build_watchlist_preset_export_filename(watchlist_state.selected_preset_export_name),
                mime="text/csv",
                use_container_width=True,
            )
            st.caption("Exports the selected preset's duplicate tickers and each selected scan card's hit tickers.")

    if page_key == "entry_signals" and signal_state is None:
        signal_state = EntrySignalPageState(
            signal_config=load_entry_signal_config(config_path),
            selected_signal_names=list(load_entry_signal_config(config_path).startup_selected_signal_names()),
        )
    if page_key == "entry_signals" and watchlist_state is None:
        scan_config = load_scan_config(config_path)
        startup_scan_names = list(scan_config.startup_selected_scan_names())
        watchlist_state = WatchlistControlState(
            scan_config=scan_config,
            selected_scan_names=startup_scan_names,
            required_scan_names=[],
            optional_scan_names=startup_scan_names,
            optional_scan_groups=[{"group_name": "Optional Condition 1", "scans": startup_scan_names, "min_hits": scan_config.duplicate_min_count}],
            selected_annotation_filters=list(scan_config.enabled_annotation_filters),
            selected_duplicate_subfilters=[],
            duplicate_threshold=scan_config.duplicate_min_count,
            duplicate_rule=DuplicateRuleConfig(min_count=scan_config.duplicate_min_count).to_dict(),
        )

    render_active_page(page_key, config_path, artifacts, watchlist_state, signal_state)


if __name__ == "__main__":
    main()
