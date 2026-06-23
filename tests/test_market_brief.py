from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from src.cli import oratek
from src.dashboard.market_brief import MarketBriefBuilder


def _summary() -> dict[str, object]:
    sectors = [
        {
            "TICKER": f"S{index}",
            "NAME": f"Sector {index}",
            "REL 1M %": 2.0 if index < 7 else -2.0,
            "RANK 1M": float(index + 1),
            "RANK DELTA 1W": 1.0 if index % 2 == 0 else -1.0,
        }
        for index in range(11)
    ]
    return {
        "trade_date": "2026-06-18",
        "score": 54.12,
        "label": "Neutral",
        "score_1d_ago": 62.22,
        "score_1w_ago": 48.32,
        "score_1m_ago": 59.35,
        "score_3m_ago": 30.4,
        "component_scores": {
            "pct_above_sma20": 51.58,
            "pct_above_sma50": 64.21,
            "pct_above_sma200": 70.53,
            "pct_sma50_gt_sma200": 67.37,
            "pct_positive_1m": 67.37,
            "pct_positive_3m": 70.53,
            "pct_2w_high": 0.0,
            "safe_haven_score": 37.01,
            "vix_score": 42.8,
        },
        "breadth_summary": {
            "pct_above_sma20": 52.63,
            "pct_above_sma50": 73.68,
            "pct_above_sma200": 84.21,
            "pct_sma50_gt_sma200": 78.95,
        },
        "breadth_momentum_summary": {
            "A20": 52.632,
            "A20 DELTA 1D": -13.23,
            "A20 DELTA 5D": 21.053,
            "A20 DELTA 10D": -15.789,
            "A20 MOMENTUM FLAG": -1.0,
        },
        "breadth_internal_summary": {
            "UNIVERSE COUNT": 2265.0,
            "ADVANCE RATIO": 0.634,
            "NET NEW HIGH LOW": 51.0,
            "NET NEW HIGH LOW %": 2.26,
            "ZWEIG BREADTH THRUST": 0.51,
            "MCCLELLAN OSCILLATOR": 0.0,
            "STAGE2 %": 46.7,
        },
        "participation_summary": {
            "pct_positive_1w": 73.68,
            "pct_positive_1m": 78.95,
            "pct_positive_3m": 84.21,
        },
        "metric_deltas": {
            "pct_above_sma20": {"1D": -31.579, "1W": 21.053},
            "pct_above_sma50": {"1D": -10.526, "1W": 0.0},
            "pct_above_sma200": {"1D": -10.526, "1W": 5.263},
            "pct_sma50_gt_sma200": {"1D": 0.0, "1W": 0.0},
            "pct_positive_1m": {"1D": -10.526, "1W": 31.579},
            "pct_positive_3m": {"1D": 0.0, "1W": 10.526},
            "pct_2w_high": {"1D": -26.316, "1W": -10.526},
            "safe_haven_score": {"1D": -4.337, "1W": -11.051},
            "vix_score": {"1D": -10.15, "1W": 18.9},
        },
        "high_vix_summary": {"S2W HIGH %": 0.0, "VIX": 18.44},
        "volatility_term_structure": {
            "VIX": 18.44,
            "VIX3M": 20.62,
            "FRONT INVERSION FLAG": 1.0,
        },
        "credit_risk_proxy": {
            "HYG/LQD REL 1M %": -0.784,
            "HYG/IEF REL 1M %": -0.347,
            "CREDIT RISK-OFF FLAG": 1.0,
            "HY OAS DELTA 5D BPS": -9.0,
            "HY OAS DELTA 21D BPS": -17.0,
        },
        "index_state_summary": {
            "SPY RALLY ATTEMPT DAY": 6.0,
            "SPY FTD FLAG": 0.0,
            "SPY DISTRIBUTION DAY COUNT": 7.0,
            "SPY UNDER PRESSURE FLAG": 1.0,
            "QQQ RALLY ATTEMPT DAY": 5.0,
            "QQQ FTD FLAG": 0.0,
            "QQQ DISTRIBUTION DAY COUNT": 6.0,
            "QQQ UNDER PRESSURE FLAG": 1.0,
        },
        "drawdown_summary": {"SPY DD 252D %": -1.689},
        "index_context_summary": {
            "SPY DAY %": 0.78,
            "SPY 50SMA %": 2.34,
            "SPY PRICE DATE": "2026-06-18",
            "SPY ACC DAYS 10D": 2.0,
            "SPY DIST DAYS 10D": 4.0,
            "QQQ DAY %": -1.01,
            "QQQ 50SMA %": 4.64,
            "QQQ PRICE DATE": "2026-06-17",
            "QQQ ACC DAYS 10D": 1.0,
            "QQQ DIST DAYS 10D": 4.0,
        },
        "defensive_cyclical_summary": {"REL 1W %": 2.244, "REL 1M %": -0.826, "REL 3M %": 8.369},
        "sector_relative_strength": sectors,
        "industry_leaders": [
            {"TICKER": "LOW", "NAME": "Low", "STRUCT RS": 70.0, "RS": 80.0, "52W HIGH": "-8.0%"},
            {"TICKER": "TOP", "NAME": "Top", "STRUCT RS": 100.0, "RS": 92.0, "52W HIGH": "-3.0%"},
        ],
        "market_snapshot": [{"TICKER": f"M{index}"} for index in range(19)],
        "series_as_of": {"SPY": "2026-06-18", "QQQ": "2026-06-17", "^VIX": "2026-06-18"},
    }


def test_market_brief_matches_proposed_regime_and_attribution_contract() -> None:
    payload = MarketBriefBuilder().build(
        _summary(),
        history_summaries=[{"score": 48.0}, {"score": 62.0}],
    ).to_dict()

    assert payload["schema_version"] == "market_brief.v1"
    assert payload["document_type"] == "market_summary"
    assert payload["regime_layers"]["trend_structure"]["score"] == pytest.approx(85.154)
    momentum_layer = payload["regime_layers"]["momentum_participation"]
    assert momentum_layer["internals_health"]["score"] == pytest.approx(57.46)
    assert momentum_layer["score"] == pytest.approx(63.598)
    assert payload["regime_layers"]["volatility_stress"]["score"] == pytest.approx(45.318)
    assert payload["regime_layers"]["credit"]["score"] == pytest.approx(67.945)
    assert payload["regime_layers"]["leadership"]["score"] == pytest.approx(72.193, abs=0.01)
    assert payload["regime_verdict"]["alignment"] == "diverging"
    assert payload["regime_verdict"]["posture"] == "cautious_hold"
    assert payload["index_cycle_state"]["market_rollup"] == "uptrend_under_distribution_pressure"
    assert {item["id"] for item in payload["divergence_flags"]} == {
        "credit_flag_vs_oas_trend",
        "spy_vs_qqq_temp",
        "early_defensive_rotation",
    }
    assert payload["score_distance"]["to_positive"] == pytest.approx(5.88)
    assert payload["score_distance"]["to_negative"] == pytest.approx(-14.12)
    assert payload["score_attribution"]["delta_contribution_1d_total"] == pytest.approx(-8.1, abs=0.01)
    assert payload["score_attribution"]["delta_contribution_1d_reconciliation_error"] == pytest.approx(0.0, abs=0.01)
    assert payload["leadership_map"]["industry_top5"][0]["ticker"] == "TOP"


def test_term_health_uses_aligned_ratio_when_latest_vix3m_close_is_unavailable() -> None:
    summary = _summary()
    summary["volatility_term_structure"] = {
        "RATIO": 0.838,
        "VIX": 17.28,
        "INVERSION FLAG": 0.0,
    }

    payload = MarketBriefBuilder().build(summary).to_dict()
    volatility = payload["regime_layers"]["volatility_stress"]
    term_driver = next(item for item in volatility["drivers"] if item["field"] == "derived.term_health")

    assert term_driver["value"] == pytest.approx(82.4)
    assert volatility["score"] == pytest.approx(54.07)
    assert not any(
        item["block"] == "regime_layers.volatility_stress"
        for item in payload["data_quality"]["missing_blocks"]
    )


def test_market_brief_reports_missing_derived_layer_input() -> None:
    summary = _summary()
    summary["volatility_term_structure"] = {"VIX": 17.28}

    payload = MarketBriefBuilder().build(summary).to_dict()

    assert payload["regime_layers"]["volatility_stress"]["score"] is None
    assert {
        "block": "regime_layers.volatility_stress",
        "reason": "one or more required derived inputs were unavailable",
    } in payload["data_quality"]["missing_blocks"]


def test_market_brief_marks_missing_internals_as_null_and_reduces_confidence() -> None:
    summary = _summary()
    summary["breadth_internal_summary"] = {}
    payload = MarketBriefBuilder().build(summary).to_dict()

    assert payload["breadth_internal_summary"] is None
    assert payload["raw_reference"]["breadth_internal_summary"] == {}
    assert payload["data_quality"]["breadth_internal_available"] is False
    assert payload["data_quality"]["breadth_universe_n"] == 19
    assert payload["data_quality"]["overall_confidence"] == "medium"
    assert payload["data_quality"]["max_staleness_days"] == 1
    assert payload["headline"]["score_percentile_252d"] is None


def test_structure_vs_internals_uses_broad_internal_health() -> None:
    summary = _summary()
    summary["breadth_internal_summary"] = {
        "UNIVERSE COUNT": 2000.0,
        "ADVANCE RATIO": 0.30,
        "NET NEW HIGH LOW": -100.0,
        "NET NEW HIGH LOW %": -5.0,
        "ZWEIG BREADTH THRUST": 0.35,
        "MCCLELLAN OSCILLATOR": -50.0,
        "STAGE2 %": 20.0,
    }

    payload = MarketBriefBuilder().build(summary).to_dict()
    flag = next(item for item in payload["divergence_flags"] if item["id"] == "structure_vs_internals")

    assert flag["severity"] == "high"
    assert "ADV RATIO=0.3" in flag["note"]
    assert "NET NEW H/L=-100" in flag["note"]


def test_etf_proxy_divergence_is_informational_when_broad_internals_are_healthy() -> None:
    summary = _summary()
    summary["breadth_momentum_summary"]["A20 DELTA 1D"] = -20.0

    payload = MarketBriefBuilder().build(summary).to_dict()
    flags = {item["id"]: item for item in payload["divergence_flags"]}

    assert "structure_vs_internals" not in flags
    assert flags["etf_proxy_vs_broad_internals"]["severity"] == "info"


def test_market_report_input_writer_emits_only_dated_market_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    market = SimpleNamespace(
        trade_date=pd.Timestamp("2026-06-18"),
        score=54.12,
        label="Neutral",
        score_1d_ago=52.0,
        score_1w_ago=50.0,
        score_1m_ago=48.0,
        score_3m_ago=45.0,
        series_as_of={"SPY": "2026-06-18"},
    )
    result = SimpleNamespace(market_result=market, radar_result=SimpleNamespace())
    context = SimpleNamespace(
        service_output_dir=tmp_path,
        settings={"market": {}},
    )
    monkeypatch.setattr(oratek, "_enrich_index_absorb_inputs", lambda *args, **kwargs: None)

    output = oratek.write_market_report_input(context, result)

    expected = tmp_path / "market_report_input" / "market_summary_20260618.json"
    assert output == {"summary_path": expected}
    assert expected.exists()
    assert not (expected.parent / "latest.json").exists()
    assert not list(expected.parent.glob("*.md"))
    assert json.loads(expected.read_text(encoding="utf-8"))["schema_version"] == "market_brief.v1"


def test_blended_market_service_uses_default_universe_when_symbols_are_omitted(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeService:
        def run(self, **kwargs):
            captured.update(kwargs)
            return "result"

    monkeypatch.setattr(oratek, "MarketService", SimpleNamespace(from_config=lambda *args, **kwargs: FakeService()))
    monkeypatch.setattr(oratek, "_resolve_default_universe_symbols", lambda context: (["AAA", "BBB"], "cached", None))
    args = SimpleNamespace(symbols=[], symbols_file=None, as_of="2026-06-18", refresh_missing=False, force_refresh=False)
    context = SimpleNamespace(
        settings={"market": {"calculation_mode": "blended"}},
        config_path=Path("config/default.yaml"),
        module_output_store=None,
    )

    result = oratek._run_market_service(args, context, write_outputs=False)

    assert result == "result"
    assert captured["stock_symbols"] == ["AAA", "BBB"]
