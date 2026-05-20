from __future__ import annotations

from src.dashboard.market_report import MarketReportBuilder, MarketReportMarkdownRenderer


def _sample_summary() -> dict[str, object]:
    return {
        "trade_date": "2026-05-14T00:00:00",
        "score": 65.84,
        "label": "Positive",
        "score_1d_ago": 65.33,
        "score_1w_ago": 66.25,
        "score_1m_ago": 65.21,
        "score_3m_ago": 52.25,
        "label_1d_ago": "Positive",
        "label_1w_ago": "Positive",
        "label_1m_ago": "Positive",
        "label_3m_ago": "Neutral",
        "component_scores": {
            "pct_above_sma10": 57.89,
            "pct_above_sma20": 61.05,
            "vix_score": 48.7,
            "safe_haven_score": 82.82,
        },
        "breadth_summary": {
            "pct_above_sma10": 63.16,
            "pct_above_sma20": 68.42,
            "pct_above_sma50": 89.47,
            "pct_above_sma200": 89.47,
        },
        "participation_summary": {
            "pct_positive_1w": 63.16,
            "pct_positive_1m": 78.95,
            "pct_positive_3m": 73.68,
        },
        "metric_deltas": {
            "pct_above_sma20": {"1D": -10.526, "1W": -5.263, "1M": -15.789},
            "pct_above_sma50": {"1D": 5.263, "1W": 5.263, "1M": 5.263},
            "pct_positive_1w": {"1D": 26.316, "1W": 10.526, "1M": -10.526},
            "VIX": {"1D": -0.61, "1W": 0.18, "1M": -0.91},
            "SAFE HAVEN %": {"1D": -0.186, "1W": -0.606, "1M": 3.15},
            "safe_haven_score": {"1D": -0.746, "1W": -2.423, "1M": 12.601},
            "risk_on:REL 1M %": {"1D": -0.246, "1W": -1.711, "1M": 1.143},
        },
        "performance_overview": {"% YTD": 9.51, "% 1W": 2.27, "% 1M": 6.89},
        "high_vix_summary": {"S2W HIGH %": 26.32, "VIX": 17.26, "SAFE HAVEN %": 8.2},
        "risk_on_ratio_summary": {
            "RATIO": 1.773,
            "REL 1W %": 1.602,
            "REL 1M %": 2.871,
            "REL 3M %": 5.56,
            "HIGH DIST %": -5.045,
            "ABOVE MA COUNT": 3.0,
            "MA COUNT": 3.0,
        },
        "vix_close": 17.26,
        "market_snapshot": [
            {"TICKER": "SPY", "NAME": "S&P 500", "DAY %": 0.79, "VOL vs 50D %": -38.38, "21EMA POS": "above 21EMA High"},
            {"TICKER": "XLU", "NAME": "Utilities", "DAY %": 0.51, "VOL vs 50D %": -22.24, "21EMA POS": "below 21EMA Low"},
        ],
        "leadership_snapshot": [
            {"TICKER": "SMH", "NAME": "Semiconductors", "DAY %": 1.03, "VOL vs 50D %": -12.68, "21EMA POS": "above 21EMA High"}
        ],
        "external_snapshot": [
            {"TICKER": "KWEB", "NAME": "China Internet", "DAY %": -4.54, "VOL vs 50D %": 116.77, "21EMA POS": "inside 21EMA Cloud"}
        ],
        "factors_vs_sp500": [
            {"TICKER": "MTUM", "NAME": "Momentum", "REL 1W %": 2.27, "REL 1M %": 6.91, "REL 1Y %": 7.58},
            {"TICKER": "VTV", "NAME": "Value", "REL 1W %": -0.76, "REL 1M %": -3.44, "REL 1Y %": -5.05},
        ],
        "sector_relative_strength": [
            {"TICKER": "XLK", "NAME": "Technology", "REL 1W %": 1.2, "REL 1M %": 3.5, "REL 3M %": 4.1, "RANK 1M": 1.0, "RANK DELTA 1W": 1.0},
            {"TICKER": "XLE", "NAME": "Energy", "REL 1W %": -0.8, "REL 1M %": 2.1, "REL 3M %": 3.2, "RANK 1M": 2.0, "RANK DELTA 1W": -3.0},
            {"TICKER": "XLU", "NAME": "Utilities", "REL 1W %": -1.1, "REL 1M %": -2.2, "REL 3M %": -3.1, "RANK 1M": 9.0, "RANK DELTA 1W": -1.0},
        ],
        "style_pair_summary": [
            {"PAIR": "VUG/VTV", "NAME": "Growth vs Value", "REL 1W %": 0.7, "REL 1M %": 2.1, "REL 3M %": 4.0, "ABOVE MA COUNT": 3.0, "MA COUNT": 3.0}
        ],
        "defensive_cyclical_summary": {"REL 1W %": 0.4, "REL 1M %": 1.8, "REL 3M %": 2.5},
        "unknown_future_field": {"should": "not be inferred"},
    }


def test_market_report_builder_creates_evidence_first_sections() -> None:
    previous = {**_sample_summary(), "trade_date": "2026-05-13T00:00:00", "score": 62.0, "label": "Positive"}
    report = MarketReportBuilder().build(
        _sample_summary(),
        source_summary_path="market_summary/20260514.json",
        history_summaries=[previous],
    )

    assert report.trade_date == "2026-05-14"
    assert report.overall_label == "Positive"
    assert report.schema_version == "market_document.v1"
    assert report.document_type == "ai_market_report_input"
    assert report.sections
    assert {section.key for section in report.sections} >= {
        "market_regime",
        "recommendation_inputs",
        "breadth_participation",
        "volatility_safe_haven",
        "risk_on_ratio",
        "sector_rotation",
        "factor_style",
    }
    assert any(section.trajectory for section in report.sections if section.key == "market_regime")
    assert report.watchpoint_candidates
    assert report.analysis_boundary["prohibited_sources"]
    assert all(evidence.source_field for evidence in report.data_appendix)
    assert not any("unknown_future_field" in evidence.source_field for evidence in report.data_appendix)
    assert any(item.key == "credit_proxy" for item in report.missing_inputs)
    assert report.report_generation_contract["final_report_owner"] == "skill"


def test_market_report_markdown_uses_structured_result_without_trade_management_terms() -> None:
    report = MarketReportBuilder().build(_sample_summary())
    markdown = MarketReportMarkdownRenderer().render(report)

    assert "# AI入力用マーケットドキュメント" in markdown
    assert "## analysis_boundary" in markdown
    assert "## watchpoint_candidates" in markdown
    assert "### recommendation_inputs" in markdown
    assert "priority_sectors" in markdown
    assert "profit_taking_exit_watch" in markdown
    assert "source=score" in markdown
    assert "## データ付録" not in markdown
    assert report.data_appendix
    assert "must_not_do" in markdown
    assert "トレーリングストップ" not in markdown
