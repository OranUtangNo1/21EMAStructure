from __future__ import annotations

from src.dashboard.market_context import MarketContextBuilder, MarketContextConfig, MarketContextMarkdownRenderer


def _summary() -> dict[str, object]:
    return {
        "trade_date": "2026-06-10T00:00:00",
        "score": 68.0,
        "component_scores": {"safe_haven_score": 63.0},
        "breadth_summary": {"pct_above_sma20": 58.0, "pct_above_sma50": 54.0, "pct_above_sma200": 61.0},
        "breadth_momentum_summary": {"A20": 58.0, "A20 DELTA 5D": 6.0, "A20 DELTA 10D": 11.0, "A20 MOMENTUM FLAG": 1.0},
        "breadth_internal_summary": {
            "NET NEW HIGH LOW": 42.0,
            "NET NEW HIGH LOW %": 1.2,
            "STAGE2 %": 23.0,
            "MCCLELLAN OSCILLATOR": 35.0,
            "MCCLELLAN SUMMATION": 1250.0,
            "ZWEIG BREADTH THRUST": 0.52,
            "ZWEIG THRUST FLAG": 1.0,
            "AD LINE": 100.0,
        },
        "high_vix_summary": {
            "VIX": 18.4,
            "VIX 252D PCTL": 42.0,
            "VIX PEAK": 28.5,
            "VIX PEAK DATE": "0521",
            "VIX PEAK RATIO %": -35.0,
            "VIX PEAK DAYS": 14.0,
            "SAFE HAVEN %": 3.2,
        },
        "metric_deltas": {"VIX": {"1W": -2.1}},
        "risk_on_ratio_summary": {"ABOVE MA COUNT": 3.0, "MA COUNT": 3.0, "REL 1M %": 2.4},
        "volatility_term_structure": {
            "VIX9D/VIX RATIO": 0.93,
            "RATIO": 0.88,
            "INVERSION FLAG": 0.0,
            "FULL BACKWARDATION FLAG": 0.0,
        },
        "credit_risk_proxy": {
            "HY OAS": 315.0,
            "HY OAS DELTA 5D BPS": -8.0,
            "HY OAS DELTA 21D BPS": -22.0,
            "HY OAS WIDENING 5D FLAG": 0.0,
            "HYG/LQD REL 1W %": 0.3,
            "CREDIT RISK-OFF FLAG": 0.0,
        },
        "style_pair_summary": [
            {"PAIR": "RSP/SPY", "REL 1M %": -1.8},
            {"PAIR": "QQQ/SPY", "REL 1M %": 1.3},
            {"PAIR": "MTUM/SPY", "REL 1M %": 2.1},
            {"PAIR": "VUG/VTV", "REL 1M %": 2.9},
        ],
        "defensive_cyclical_summary": {"REL 1M %": 1.5},
        "index_context_summary": {
            "SPY CLOSE": 612.45,
            "SPY DAY %": 0.4,
            "SPY 21EMA POSITION": "above",
            "SPY 50SMA %": 2.1,
            "SPY RALLY ATTEMPT DAY": 12.0,
            "SPY FTD FLAG": 1.0,
            "SPY FTD VALID FLAG": 1.0,
            "SPY FTD DATE": "0529",
            "SPY FTD AGE DAYS": 12.0,
            "SPY FTD GAIN %": 1.7,
            "SPY FTD ADVANCE RATIO": 0.68,
            "SPY DISTRIBUTION DAY COUNT": 2.0,
            "SPY BELOW 50SMA FLAG": 0.0,
            "QQQ CLOSE": 540.0,
            "QQQ DAY %": 0.2,
            "QQQ 21EMA POSITION": "inside",
            "QQQ 50SMA %": 1.0,
            "QQQ RALLY ATTEMPT DAY": 10.0,
            "QQQ FTD FLAG": 1.0,
            "QQQ FTD VALID FLAG": 1.0,
            "QQQ FTD DATE": "0529",
            "QQQ FTD AGE DAYS": 12.0,
            "QQQ FTD GAIN %": 2.0,
            "QQQ FTD ADVANCE RATIO": 0.68,
            "QQQ DISTRIBUTION DAY COUNT": 3.0,
            "QQQ BELOW 50SMA FLAG": 0.0,
        },
        "drawdown_summary": {"SPY DD 252D %": -1.8, "SPY T_DD": 14.0, "QQQ DD 252D %": -2.2, "QQQ T_DD": 16.0},
        "index_state_summary": {"SPY DISTRIBUTION DAY COUNT": 2.0, "QQQ DISTRIBUTION DAY COUNT": 3.0},
        "sector_leaders": [
            {"TICKER": "XLK", "RS": 92.0, "STRUCT RS": 88.0},
            {"TICKER": "XLI", "RS": 85.0, "STRUCT RS": 71.0},
        ],
        "sector_relative_strength": [
            {"TICKER": "XLK", "RANK DELTA 1W": 1.0},
            {"TICKER": "XLI", "RANK DELTA 1W": 3.0},
        ],
        "industry_leaders": [
            {"TICKER": "SMH", "RS": 95.0, "STRUCT RS": 90.0, "MAJOR STOCKS": "NVDA,AVGO,AMD"},
            {"TICKER": "XHB", "RS": 88.0, "STRUCT RS": 80.0, "MAJOR STOCKS": "DHI,LEN,PHM"},
        ],
    }


def test_market_context_renderer_outputs_fixed_sections_and_gate() -> None:
    previous = {
        **_summary(),
        "trade_date": "2026-06-03T00:00:00",
        "breadth_internal_summary": {"MCCLELLAN SUMMATION": 1000.0, "AD LINE": 90.0},
        "industry_leaders": [{"TICKER": "SMH", "RS": 92.0, "STRUCT RS": 87.0, "MAJOR STOCKS": "NVDA,AVGO,AMD"}],
        "index_state_summary": {"SPY DISTRIBUTION DAY COUNT": 3.0, "QQQ DISTRIBUTION DAY COUNT": 4.0},
    }
    context = MarketContextBuilder().build(_summary(), history_summaries=[previous])
    markdown = MarketContextMarkdownRenderer().render(context)

    assert markdown.startswith("# MARKET_CONTEXT | 2026-06-10 (Wed) | schema v1.0.1")
    for section in ["M_GATE", "INDEX", "BREADTH", "SENTIMENT", "STYLE", "SECTOR_RS", "INDUSTRY_RS", "CHANGES_1W"]:
        assert f"## {section}" in markdown
    assert "VERDICT: GO" in markdown
    assert "SPY: C=612.45" in markdown
    assert "FTD=Y(0529,+1.7%,ADV68%)" in markdown
    assert "RSP/SPY_1M=-1.8%" in markdown
    assert "1.XLK 92|88|+1" in markdown
    assert "## INDUSTRY_RS top8 (tactRS|structRS63|dRank1W|majors)" in markdown
    assert "1.SMH 95|90|+0|NVDA,AVGO,AMD" in markdown
    assert "NEW_IN_TOP8: XHB" in markdown
    assert "+ OAS -8bps; A20 +6pt; XLI rank +3" in markdown


def test_market_context_converts_oas_percent_level_to_bps() -> None:
    summary = _summary()
    summary["credit_risk_proxy"] = {
        **summary["credit_risk_proxy"],
        "HY OAS": 3.15,
    }

    markdown = MarketContextMarkdownRenderer().render(MarketContextBuilder().build(summary))

    assert "CREDIT: OAS=315 D5=-8 D21=-22" in markdown


def test_market_context_suppresses_industry_new_out_without_history() -> None:
    markdown = MarketContextMarkdownRenderer().render(MarketContextBuilder().build(_summary()))

    assert "1.SMH 95|90|NA|NVDA,AVGO,AMD" in markdown
    assert "NEW_IN_TOP8: NA(no_history)  OUT: NA(no_history)" in markdown
    assert "SMH(+8)" not in markdown


def test_market_context_industry_rank_delta_uses_full_prior_rank() -> None:
    current = _summary()
    current["industry_leaders"] = [
        {"TICKER": "SMH", "RS": 95.0, "STRUCT RS": 99.0, "MAJOR STOCKS": "NVDA,AVGO,AMD"},
        {"TICKER": "XHB", "RS": 88.0, "STRUCT RS": 98.0, "MAJOR STOCKS": "DHI,LEN,PHM"},
        {"TICKER": "CIBR", "RS": 85.0, "STRUCT RS": 97.0, "MAJOR STOCKS": "PANW,CRWD,FTNT"},
        {"TICKER": "SLX", "RS": 82.0, "STRUCT RS": 96.0, "MAJOR STOCKS": "NUE,STLD,X"},
        {"TICKER": "QTUM", "RS": 80.0, "STRUCT RS": 95.0, "MAJOR STOCKS": "NVDA,IBM,IONQ"},
        {"TICKER": "UFO", "RS": 78.0, "STRUCT RS": 94.0, "MAJOR STOCKS": "RKLB,IRDM,GSAT"},
        {"TICKER": "TAN", "RS": 76.0, "STRUCT RS": 93.0, "MAJOR STOCKS": "FSLR,ENPH,SEDG"},
        {"TICKER": "ICLN", "RS": 74.0, "STRUCT RS": 92.0, "MAJOR STOCKS": "FSLR,ENPH,PLUG"},
        {"TICKER": "IHI", "RS": 70.0, "STRUCT RS": 91.0, "MAJOR STOCKS": "ISRG,BSX,SYK"},
        {"TICKER": "ITB", "RS": 68.0, "STRUCT RS": 90.0, "MAJOR STOCKS": "DHI,LEN,PHM"},
        {"TICKER": "PEJ", "RS": 66.0, "STRUCT RS": 89.0, "MAJOR STOCKS": "BKNG,CMG,SBUX"},
        {"TICKER": "JETS", "RS": 64.0, "STRUCT RS": 88.0, "MAJOR STOCKS": "DAL,UAL,AAL"},
    ]
    previous = {
        **current,
        "trade_date": "2026-06-03T00:00:00",
        "industry_leaders": [
            {"TICKER": "SMH", "RS": 90.0, "STRUCT RS": 99.0, "MAJOR STOCKS": "NVDA,AVGO,AMD"},
            {"TICKER": "IHI", "RS": 80.0, "STRUCT RS": 98.0, "MAJOR STOCKS": "ISRG,BSX,SYK"},
            {"TICKER": "ITB", "RS": 78.0, "STRUCT RS": 97.0, "MAJOR STOCKS": "DHI,LEN,PHM"},
            {"TICKER": "PEJ", "RS": 75.0, "STRUCT RS": 96.0, "MAJOR STOCKS": "BKNG,CMG,SBUX"},
            {"TICKER": "JETS", "RS": 73.0, "STRUCT RS": 95.0, "MAJOR STOCKS": "DAL,UAL,AAL"},
            {"TICKER": "XHB", "RS": 70.0, "STRUCT RS": 94.0, "MAJOR STOCKS": "DHI,LEN,PHM"},
        ],
    }

    markdown = MarketContextMarkdownRenderer().render(MarketContextBuilder().build(current, history_summaries=[previous]))

    assert "1.SMH 95|99|+0|NVDA,AVGO,AMD" in markdown
    assert "2.XHB 88|98|+4|DHI,LEN,PHM" in markdown
    assert "NEW_IN_TOP8: CIBR(NA)" in markdown
    assert "OUT: IHI(-7), ITB(-7), PEJ(-7), JETS(-7)" in markdown


def test_market_context_industry_rank_delta_requires_struct_history() -> None:
    current = _summary()
    previous = {
        **current,
        "trade_date": "2026-06-03T00:00:00",
        "industry_leaders": [
            {"TICKER": "SMH", "RS": 92.0, "MAJOR STOCKS": "NVDA,AVGO,AMD"},
            {"TICKER": "XHB", "RS": 88.0, "MAJOR STOCKS": "DHI,LEN,PHM"},
        ],
    }

    markdown = MarketContextMarkdownRenderer().render(MarketContextBuilder().build(current, history_summaries=[previous]))

    assert "1.SMH 95|90|NA|NVDA,AVGO,AMD" in markdown
    assert "NEW_IN_TOP8: NA(no_struct_history)  OUT: NA(no_struct_history)" in markdown


def test_market_context_industry_majors_fall_back_to_config() -> None:
    summary = _summary()
    summary["industry_leaders"] = [{"TICKER": "SMH", "RS": 95.0, "STRUCT RS": 90.0}]
    config = MarketContextConfig(industry_major_stocks={"SMH": "NVDA,AVGO,AMD"})

    markdown = MarketContextMarkdownRenderer().render(MarketContextBuilder(config).build(summary))

    assert "1.SMH 95|90|NA|NVDA,AVGO,AMD" in markdown
