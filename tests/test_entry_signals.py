from __future__ import annotations

import pandas as pd

from src.data.tracking_db import connect_tracking_db
from src.pipeline import PlatformArtifacts
from src.scan.rules import ScanConfig
from src.signals.rules import EntrySignalConfig, evaluate_invalidation
from src.signals.runner import EntrySignalRunner


def test_entry_signal_config_uses_definition_keys_and_status_map() -> None:
    config = EntrySignalConfig.from_dict(
        {
            "signal_status_map": {
                "orderly_pullback_entry": "enabled",
                "disabled_signal": "disabled",
            },
            "default_selected_signal_names": [
                "orderly_pullback_entry",
                "disabled_signal",
            ],
            "definitions": {
                "orderly_pullback_entry": _definition_payload("Orderly Pullback Entry"),
                "disabled_signal": _definition_payload("Disabled Signal"),
            },
        }
    )

    definition = config.definition_for("orderly_pullback_entry")

    assert config.enabled_signal_names() == ("orderly_pullback_entry",)
    assert config.startup_selected_signal_names() == ("orderly_pullback_entry",)
    assert definition.display_name == "Orderly Pullback Entry"
    assert definition.pool.detection_window_days == 10
    assert definition.risk_reward.stop.reference == "low_since_detection"
    assert not config.context_guard.enabled


def test_entry_signal_config_loads_context_guard() -> None:
    config = EntrySignalConfig.from_dict(
        {
            "context_guard": {
                "enabled": True,
                "weak_market_score_threshold": 30.0,
                "cap_below_signal_detected": True,
                "earnings": {
                    "warning_field": "earnings_in_7d",
                    "today_field": "earnings_today",
                },
                "signal_overrides": {
                    "momentum_acceleration_entry": {
                        "weak_market_score_threshold": 40.0,
                    },
                    "early_cycle_recovery_entry": {
                        "weak_market_score_threshold": 20.0,
                    },
                },
            },
            "definitions": {
                "orderly_pullback_entry": _definition_payload("Orderly Pullback Entry"),
            },
        }
    )

    assert config.context_guard.enabled
    assert config.context_guard.weak_market_score_threshold == 30.0
    assert config.context_guard.earnings_warning_field == "earnings_in_7d"
    assert config.context_guard.earnings_today_field == "earnings_today"
    assert config.context_guard.weak_market_threshold_for("orderly_pullback_entry") == 30.0
    assert config.context_guard.weak_market_threshold_for("momentum_acceleration_entry") == 40.0
    assert config.context_guard.weak_market_threshold_for("early_cycle_recovery_entry") == 20.0


def test_entry_signal_runner_builds_pool_and_persists_evaluation(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "97 Club", "display_name": "97 Club"},
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Orderly Pullback",
                    "selected_scan_names": ["97 Club", "Pocket Pivot"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {
            "definitions": {
                "orderly_pullback_entry": _definition_payload("Orderly Pullback Entry"),
            }
        }
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=pd.DataFrame(
            {
                "close": [101.0],
                "open": [98.0],
                "high": [103.0],
                "low": [97.5],
                "ema21_close": [99.5],
                "sma50": [95.0],
                "rs21": [76.0],
                "atr": [4.0],
                "drawdown_from_20d_high_pct": [7.0],
                "volume_ma5_to_ma20_ratio": [0.72],
                "atr_21ema_zone": [0.35],
                "atr_50sma_zone": [1.6],
                "rolling_20d_close_high": [112.0],
                "ema21_slope_5d_pct": [0.24],
                "sma50_slope_10d_pct": [0.11],
                "volume_ratio_20d": [1.7],
                "dcr_percent": [78.0],
                "prev_high": [100.0],
                "pocket_pivot": [True],
                "ud_volume_ratio": [1.8],
                "close_crossed_above_ema21": [True],
                "high_52w": [120.0],
            },
            index=["AAA"],
        ),
        scan_hits=pd.DataFrame(
            [
                {"ticker": "AAA", "kind": "scan", "name": "97 Club"},
                {"ticker": "AAA", "kind": "scan", "name": "Pocket Pivot"},
            ]
        ),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(
        artifacts,
        ["orderly_pullback_entry"],
        root_dir=tmp_path,
    )

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Signal"] == "Orderly Pullback Entry"
    assert result.iloc[0]["Preset Sources"] == "Orderly Pullback"
    assert result.iloc[0]["Display Bucket"] == "Signal Detected"
    assert float(result.iloc[0]["Entry Strength"]) >= 50.0
    assert float(result.iloc[0]["R/R Ratio"]) > 1.0

    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        pool_row = conn.execute(
            """
            SELECT signal_name, ticker, pool_status, low_since_detection, high_since_detection
            FROM signal_pool_entry
            """
        ).fetchone()
        evaluation_row = conn.execute(
            """
            SELECT signal_name, ticker, signal_version, entry_strength, rr_ratio, stop_price, reward_target
            FROM signal_evaluation
            """
        ).fetchone()
    finally:
        conn.close()

    assert pool_row["signal_name"] == "orderly_pullback_entry"
    assert pool_row["ticker"] == "AAA"
    assert pool_row["pool_status"] == "active"
    assert float(pool_row["low_since_detection"]) == 97.5
    assert float(pool_row["high_since_detection"]) == 103.0
    assert evaluation_row["signal_name"] == "orderly_pullback_entry"
    assert evaluation_row["ticker"] == "AAA"
    assert evaluation_row["signal_version"] == "1.0"
    assert float(evaluation_row["entry_strength"]) >= 50.0
    assert float(evaluation_row["rr_ratio"]) > 1.0


def test_entry_signal_runner_syncs_same_day_saved_run_idempotently(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "97 Club", "display_name": "97 Club"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Orderly Pullback",
                    "selected_scan_names": ["97 Club"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {
            "definitions": {
                "orderly_pullback_entry": _definition_payload("Orderly Pullback Entry"),
            }
        }
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=pd.DataFrame(
            {
                "close": [101.0],
                "open": [98.0],
                "high": [103.0],
                "low": [97.5],
                "ema21_close": [99.5],
                "sma50": [95.0],
                "rs21": [76.0],
                "atr": [4.0],
                "drawdown_from_20d_high_pct": [7.0],
                "volume_ma5_to_ma20_ratio": [0.72],
                "atr_21ema_zone": [0.35],
                "atr_50sma_zone": [1.6],
                "rolling_20d_close_high": [112.0],
                "ema21_slope_5d_pct": [0.24],
                "sma50_slope_10d_pct": [0.11],
                "volume_ratio_20d": [1.7],
                "dcr_percent": [78.0],
                "prev_high": [100.0],
                "pocket_pivot": [True],
                "ud_volume_ratio": [1.8],
                "close_crossed_above_ema21": [True],
                "high_52w": [120.0],
            },
            index=["AAA"],
        ),
        scan_hits=pd.DataFrame([{"ticker": "AAA", "kind": "scan", "name": "97 Club"}]),
        trade_date="2026-04-24",
    )
    artifacts.artifact_origin = "same_day_saved_run"

    first = runner.sync_tracking(artifacts, root_dir=tmp_path)
    second = runner.sync_tracking(artifacts, root_dir=tmp_path)

    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        pool_rows = conn.execute(
            """
            SELECT ticker, latest_detected_date, detection_count
            FROM signal_pool_entry
            WHERE signal_name = ?
            """,
            ("orderly_pullback_entry",),
        ).fetchall()
    finally:
        conn.close()

    assert first.pool_inserted_count == 1
    assert second.pool_updated_count == 1
    assert len(pool_rows) == 1
    assert pool_rows[0]["ticker"] == "AAA"
    assert pool_rows[0]["latest_detected_date"] == "2026-04-24"
    assert int(pool_rows[0]["detection_count"]) == 1


def test_entry_signal_context_guard_caps_detected_signal(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "97 Club", "display_name": "97 Club"},
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Orderly Pullback",
                    "selected_scan_names": ["97 Club", "Pocket Pivot"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {
            "context_guard": {
                "enabled": True,
                "weak_market_score_threshold": 30.0,
                "cap_below_signal_detected": True,
                "earnings": {
                    "warning_field": "earnings_in_7d",
                    "today_field": "earnings_today",
                },
            },
            "definitions": {
                "orderly_pullback_entry": _definition_payload("Orderly Pullback Entry"),
            },
        }
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=pd.DataFrame(
            {
                "close": [101.0],
                "open": [98.0],
                "high": [103.0],
                "low": [97.5],
                "ema21_close": [99.5],
                "sma50": [95.0],
                "rs21": [76.0],
                "atr": [4.0],
                "drawdown_from_20d_high_pct": [7.0],
                "volume_ma5_to_ma20_ratio": [0.72],
                "atr_21ema_zone": [0.35],
                "atr_50sma_zone": [1.6],
                "rolling_20d_close_high": [112.0],
                "ema21_slope_5d_pct": [0.24],
                "sma50_slope_10d_pct": [0.11],
                "volume_ratio_20d": [1.7],
                "dcr_percent": [78.0],
                "prev_high": [100.0],
                "pocket_pivot": [True],
                "ud_volume_ratio": [1.8],
                "close_crossed_above_ema21": [True],
                "high_52w": [120.0],
                "market_score": [24.0],
                "earnings_in_7d": [True],
                "earnings_today": [False],
            },
            index=["AAA"],
        ),
        scan_hits=pd.DataFrame(
            [
                {"ticker": "AAA", "kind": "scan", "name": "97 Club"},
                {"ticker": "AAA", "kind": "scan", "name": "Pocket Pivot"},
            ]
        ),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(
        artifacts,
        ["orderly_pullback_entry"],
        root_dir=tmp_path,
    )

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Display Bucket"] == "Approaching"
    assert float(result.iloc[0]["Entry Strength"]) < 50.0
    assert "weak_market_warning" in str(result.iloc[0]["Timing Detail"])
    assert "earnings_warning" in str(result.iloc[0]["Timing Detail"])


def test_entry_signal_context_guard_uses_signal_specific_market_threshold(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "Momentum 97", "display_name": "Momentum 97"},
                {"scan_name": "4% bullish", "display_name": "4% bullish"},
                {"scan_name": "VCS 52 High", "display_name": "VCS 52 High"},
                {"scan_name": "PP Count", "display_name": "PP Count"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Momentum Ignition",
                    "selected_scan_names": ["Momentum 97", "4% bullish", "VCS 52 High", "PP Count"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {
            "context_guard": {
                "enabled": True,
                "weak_market_score_threshold": 30.0,
                "cap_below_signal_detected": True,
                "signal_overrides": {
                    "momentum_acceleration_entry": {
                        "weak_market_score_threshold": 40.0,
                    },
                },
            },
            "definitions": {
                "momentum_acceleration_entry": _momentum_definition_payload(),
            },
        }
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=pd.DataFrame(
            {
                "close": [102.0],
                "high": [103.0],
                "low": [100.0],
                "sma50": [92.0],
                "atr": [2.0],
                "rs21": [91.0],
                "vcs": [78.0],
                "weekly_return_rank": [98.0],
                "rel_volume": [2.0],
                "daily_change_pct": [4.5],
                "dcr_percent": [85.0],
                "dist_from_52w_high": [-5.0],
                "pp_count_window": [3.0],
                "market_score": [35.0],
                "hit_scans": ["Momentum 97, 4% bullish, VCS 52 High, PP Count"],
            },
            index=["AAA"],
        ),
        scan_hits=pd.DataFrame(
            [
                {"ticker": "AAA", "kind": "scan", "name": "Momentum 97"},
                {"ticker": "AAA", "kind": "scan", "name": "4% bullish"},
                {"ticker": "AAA", "kind": "scan", "name": "VCS 52 High"},
                {"ticker": "AAA", "kind": "scan", "name": "PP Count"},
            ]
        ),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(
        artifacts,
        ["momentum_acceleration_entry"],
        root_dir=tmp_path,
    )

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Display Bucket"] == "Approaching"
    assert float(result.iloc[0]["Entry Strength"]) < 55.0
    assert "weak_market_warning" in str(result.iloc[0]["Timing Detail"])


def test_entry_signal_runner_invalidates_broken_active_setup(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "97 Club", "display_name": "97 Club"},
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Orderly Pullback",
                    "selected_scan_names": ["97 Club", "Pocket Pivot"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {
            "definitions": {
                "orderly_pullback_entry": _definition_payload("Orderly Pullback Entry"),
            }
        }
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=pd.DataFrame(
            {
                "close": [90.0],
                "open": [91.0],
                "high": [92.0],
                "low": [89.0],
                "ema21_close": [92.5],
                "sma50": [95.0],
                "rs21": [35.0],
                "atr": [4.0],
                "drawdown_from_20d_high_pct": [21.0],
                "volume_ma5_to_ma20_ratio": [0.85],
                "atr_21ema_zone": [-0.6],
                "atr_50sma_zone": [-1.2],
                "rolling_20d_close_high": [110.0],
                "ema21_slope_5d_pct": [-0.1],
                "sma50_slope_10d_pct": [-0.05],
                "volume_ratio_20d": [0.8],
                "dcr_percent": [20.0],
                "prev_high": [93.0],
                "pocket_pivot": [False],
                "ud_volume_ratio": [0.7],
                "close_crossed_above_ema21": [False],
                "high_52w": [120.0],
            },
            index=["AAA"],
        ),
        scan_hits=pd.DataFrame(
            [
                {"ticker": "AAA", "kind": "scan", "name": "97 Club"},
                {"ticker": "AAA", "kind": "scan", "name": "Pocket Pivot"},
            ]
        ),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(
        artifacts,
        ["orderly_pullback_entry"],
        root_dir=tmp_path,
    )

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Pool Transition"] == "invalidated"
    assert float(result.iloc[0]["Entry Strength"]) == 0.0

    conn = connect_tracking_db(root_dir=tmp_path)
    try:
        pool_row = conn.execute(
            "SELECT pool_status, invalidated_reason FROM signal_pool_entry WHERE signal_name = ? AND ticker = ?",
            ("orderly_pullback_entry", "AAA"),
        ).fetchone()
        evaluation_count = conn.execute("SELECT COUNT(*) FROM signal_evaluation").fetchone()[0]
    finally:
        conn.close()

    assert pool_row["pool_status"] == "invalidated"
    assert pool_row["invalidated_reason"] == "close_below_sma50"
    assert evaluation_count == 0


def test_entry_signal_invalidation_supports_reference_multiplier() -> None:
    config = EntrySignalConfig.from_dict(
        {
            "definitions": {
                "pullback_resumption_entry": _pullback_definition_payload(),
            }
        }
    )
    definition = config.definition_for("pullback_resumption_entry")

    reason = evaluate_invalidation(definition, {"close": 96.0, "sma50": 100.0})

    assert reason == "close_below_sma50_x0p97"


def test_pullback_resumption_runner_scores_50sma_defense_depth_and_rr(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "50SMA Reclaim", "display_name": "50SMA Reclaim"},
                {"scan_name": "Pullback Quality scan", "display_name": "PB Quality"},
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "50SMA Defense",
                    "selected_scan_names": ["50SMA Reclaim", "Pullback Quality scan", "Pocket Pivot"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {
            "definitions": {
                "pullback_resumption_entry": _pullback_definition_payload(),
            }
        }
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=pd.DataFrame(
            {
                "close": [101.0],
                "open": [99.0],
                "high": [102.5],
                "low": [99.5],
                "ema21_close": [100.0],
                "sma50": [100.0],
                "rs21": [76.0],
                "atr": [2.0],
                "drawdown_from_20d_high_pct": [8.0],
                "volume_ma5_to_ma20_ratio": [0.70],
                "atr_21ema_zone": [0.5],
                "atr_50sma_zone": [0.5],
                "rolling_20d_close_high": [112.0],
                "sma50_slope_10d_pct": [0.12],
                "rel_volume": [1.7],
                "volume_ratio_20d": [1.4],
                "dcr_percent": [75.0],
                "pocket_pivot": [True],
                "ud_volume_ratio": [1.8],
                "close_crossed_above_sma50": [True],
                "close_crossed_above_ema21": [True],
                "high_52w": [120.0],
                "hit_scans": ["50SMA Reclaim, Pullback Quality scan, Pocket Pivot"],
            },
            index=["AAA"],
        ),
        scan_hits=pd.DataFrame(
            [
                {"ticker": "AAA", "kind": "scan", "name": "50SMA Reclaim"},
                {"ticker": "AAA", "kind": "scan", "name": "Pullback Quality scan"},
                {"ticker": "AAA", "kind": "scan", "name": "Pocket Pivot"},
            ]
        ),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(
        artifacts,
        ["pullback_resumption_entry"],
        root_dir=tmp_path,
    )

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Signal"] == "Pullback Resumption Entry"
    assert result.iloc[0]["Preset Sources"] == "50SMA Defense"
    assert result.iloc[0]["Display Bucket"] == "Signal Detected"
    assert float(result.iloc[0]["Setup Maturity"]) >= 75.0
    assert float(result.iloc[0]["R/R Ratio"]) >= 2.0


def test_momentum_acceleration_runner_scores_ignition_event_and_rr(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "Momentum 97", "display_name": "Momentum 97"},
                {"scan_name": "4% bullish", "display_name": "4% bullish"},
                {"scan_name": "VCS 52 High", "display_name": "VCS 52 High"},
                {"scan_name": "PP Count", "display_name": "PP Count"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Momentum Ignition",
                    "selected_scan_names": ["Momentum 97", "4% bullish", "VCS 52 High", "PP Count"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {
            "definitions": {
                "momentum_acceleration_entry": _momentum_definition_payload(),
            }
        }
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=pd.DataFrame(
            {
                "close": [102.0],
                "high": [103.0],
                "low": [100.0],
                "sma50": [92.0],
                "atr": [2.0],
                "rs21": [91.0],
                "vcs": [78.0],
                "weekly_return_rank": [98.0],
                "rel_volume": [2.0],
                "daily_change_pct": [4.5],
                "dcr_percent": [85.0],
                "dist_from_52w_high": [-5.0],
                "pp_count_window": [3.0],
                "hit_scans": ["Momentum 97, 4% bullish, VCS 52 High, PP Count"],
            },
            index=["AAA"],
        ),
        scan_hits=pd.DataFrame(
            [
                {"ticker": "AAA", "kind": "scan", "name": "Momentum 97"},
                {"ticker": "AAA", "kind": "scan", "name": "4% bullish"},
                {"ticker": "AAA", "kind": "scan", "name": "VCS 52 High"},
                {"ticker": "AAA", "kind": "scan", "name": "PP Count"},
            ]
        ),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(
        artifacts,
        ["momentum_acceleration_entry"],
        root_dir=tmp_path,
    )

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Signal"] == "Momentum Acceleration Entry"
    assert result.iloc[0]["Preset Sources"] == "Momentum Ignition"
    assert result.iloc[0]["Display Bucket"] == "Signal Detected"
    assert float(result.iloc[0]["R/R Ratio"]) >= 2.0
    assert float(result.iloc[0]["Risk In ATR"]) <= 2.0


def test_momentum_acceleration_climax_warning_caps_detected_signal(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "Momentum 97", "display_name": "Momentum 97"},
                {"scan_name": "4% bullish", "display_name": "4% bullish"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Momentum Ignition",
                    "selected_scan_names": ["Momentum 97", "4% bullish"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {
            "definitions": {
                "momentum_acceleration_entry": _momentum_definition_payload(),
            }
        }
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=pd.DataFrame(
            {
                "close": [102.0],
                "high": [103.0],
                "low": [100.0],
                "sma50": [92.0],
                "atr": [2.0],
                "rs21": [91.0],
                "vcs": [78.0],
                "weekly_return_rank": [98.0],
                "rel_volume": [5.5],
                "daily_change_pct": [8.5],
                "dcr_percent": [85.0],
                "dist_from_52w_high": [-0.5],
                "pp_count_window": [3.0],
                "hit_scans": ["Momentum 97, 4% bullish"],
            },
            index=["AAA"],
        ),
        scan_hits=pd.DataFrame(
            [
                {"ticker": "AAA", "kind": "scan", "name": "Momentum 97"},
                {"ticker": "AAA", "kind": "scan", "name": "4% bullish"},
            ]
        ),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(
        artifacts,
        ["momentum_acceleration_entry"],
        root_dir=tmp_path,
    )

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Display Bucket"] == "Approaching"
    assert float(result.iloc[0]["Entry Strength"]) < 55.0
    assert "climax_warning" in str(result.iloc[0]["Timing Detail"])


def test_saved_run_artifacts_preserve_entry_signal_evaluation_fields(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "Momentum 97", "display_name": "Momentum 97"},
                {"scan_name": "4% bullish", "display_name": "4% bullish"},
                {"scan_name": "VCS 52 High", "display_name": "VCS 52 High"},
                {"scan_name": "PP Count", "display_name": "PP Count"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Momentum Ignition",
                    "selected_scan_names": ["Momentum 97", "4% bullish", "VCS 52 High", "PP Count"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {"definitions": {"momentum_acceleration_entry": _momentum_definition_payload()}}
    )
    runner = EntrySignalRunner(signal_config, scan_config)

    full_snapshot = pd.DataFrame(
        {
            "close": [102.0],
            "high": [103.0],
            "low": [100.0],
            "sma50": [92.0],
            "atr": [2.0],
            "rs21": [91.0],
            "vcs": [78.0],
            "weekly_return_rank": [98.0],
            "rel_volume": [2.0],
            "daily_change_pct": [4.5],
            "dcr_percent": [85.0],
            "dist_from_52w_high": [-5.0],
            "pp_count_window": [3.0],
            "volume_ratio_20d": [1.6],
            "drawdown_from_20d_high_pct": [1.2],
            "atr_21ema_zone": [0.5],
            "hit_scans": ["Momentum 97, 4% bullish, VCS 52 High, PP Count"],
        },
        index=["AAA"],
    )
    seed_artifacts = _build_platform_artifacts(
        watchlist=full_snapshot,
        scan_hits=pd.DataFrame(
            [
                {"ticker": "AAA", "kind": "scan", "name": "Momentum 97"},
                {"ticker": "AAA", "kind": "scan", "name": "4% bullish"},
                {"ticker": "AAA", "kind": "scan", "name": "VCS 52 High"},
                {"ticker": "AAA", "kind": "scan", "name": "PP Count"},
            ]
        ),
        trade_date="2026-04-24",
    )
    runner.sync_tracking(seed_artifacts, root_dir=tmp_path)

    saved_run_watchlist = pd.DataFrame(
        {
            "vcs": [78.0],
            "pp_count_window": [3.0],
            "atr_21ema_zone": [0.5],
        },
        index=["AAA"],
    )
    saved_run_artifacts = PlatformArtifacts(
        snapshot=pd.DataFrame({"trade_date": ["2026-04-24"]}, index=["AAA"]),
        eligible_snapshot=full_snapshot.copy(),
        watchlist=saved_run_watchlist,
        duplicate_tickers=pd.DataFrame(),
        watchlist_cards=[],
        earnings_today=pd.DataFrame(),
        scan_hits=seed_artifacts.scan_hits,
        benchmark_history=pd.DataFrame(),
        vix_history=pd.DataFrame(),
        market_result=None,
        radar_result=None,
        used_sample_data=False,
        data_source_label="test",
        fetch_status=pd.DataFrame(),
        data_health_summary={},
        run_directory=None,
        universe_mode="test",
        resolved_symbols=["AAA"],
        universe_snapshot_path=None,
        artifact_origin="same_day_saved_run",
        entry_signal_watchlist=saved_run_watchlist.copy(),
    )

    result = runner.evaluate_active_pools(saved_run_artifacts, ["momentum_acceleration_entry"], root_dir=tmp_path)

    assert list(result["Ticker"]) == ["AAA"]
    assert float(result.iloc[0]["Close"]) == 102.0
    assert float(result.iloc[0]["RS21"]) == 91.0
    assert float(result.iloc[0]["R/R Ratio"]) >= 2.0
    assert float(result.iloc[0]["Risk In ATR"]) <= 2.0


def test_accumulation_breakout_runner_scores_breakout_and_rr(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "VCS 52 High", "display_name": "VCS 52 High"},
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
                {"scan_name": "Volume Accumulation", "display_name": "Volume Accumulation"},
                {"scan_name": "4% bullish", "display_name": "4% bullish"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Accumulation Breakout",
                    "selected_scan_names": ["VCS 52 High", "Pocket Pivot", "Volume Accumulation", "4% bullish"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {
            "definitions": {
                "accumulation_breakout_entry": _accumulation_breakout_definition_payload(),
            }
        }
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=pd.DataFrame(
            {
                "close": [101.0],
                "open": [98.0],
                "high": [102.0],
                "low": [99.0],
                "ema21_close": [99.0],
                "sma50": [92.0],
                "atr": [2.0],
                "rs21": [88.0],
                "vcs": [78.0],
                "rel_volume": [2.0],
                "volume_ratio_20d": [1.6],
                "dcr_percent": [82.0],
                "daily_change_pct": [3.8],
                "weekly_return_rank": [94.0],
                "quarterly_return_rank": [91.0],
                "rolling_20d_close_high": [100.0],
                "resistance_level_lookback": [100.0],
                "resistance_test_count": [3.0],
                "breakout_body_ratio": [0.7],
                "dist_from_52w_high": [-6.0],
                "high_52w": [118.0],
                "pp_count_window": [3.0],
                "pocket_pivot": [True],
                "three_weeks_tight": [True],
                "ema21_cloud_width": [1.2],
                "drawdown_from_20d_high_pct": [2.0],
                "hit_scans": ["VCS 52 High, Pocket Pivot, Volume Accumulation, 4% bullish"],
            },
            index=["AAA"],
        ),
        scan_hits=pd.DataFrame(
            [
                {"ticker": "AAA", "kind": "scan", "name": "VCS 52 High"},
                {"ticker": "AAA", "kind": "scan", "name": "Pocket Pivot"},
                {"ticker": "AAA", "kind": "scan", "name": "Volume Accumulation"},
                {"ticker": "AAA", "kind": "scan", "name": "4% bullish"},
            ]
        ),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(
        artifacts,
        ["accumulation_breakout_entry"],
        root_dir=tmp_path,
    )

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Signal"] == "Accumulation Breakout Entry"
    assert result.iloc[0]["Preset Sources"] == "Accumulation Breakout"
    assert result.iloc[0]["Display Bucket"] == "Signal Detected"
    assert float(result.iloc[0]["R/R Ratio"]) >= 2.0
    assert float(result.iloc[0]["Risk In ATR"]) <= 2.0
    assert "breakout_event" in str(result.iloc[0]["Timing Detail"])


def test_accumulation_breakout_climax_warning_caps_detected_signal(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "RS New High", "display_name": "RS New High"},
                {"scan_name": "4% bullish", "display_name": "4% bullish"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "RS Breakout Setup",
                    "selected_scan_names": ["RS New High", "4% bullish"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {
            "definitions": {
                "accumulation_breakout_entry": _accumulation_breakout_definition_payload(),
            }
        }
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=pd.DataFrame(
            {
                "close": [101.0],
                "open": [94.0],
                "high": [102.0],
                "low": [99.0],
                "ema21_close": [99.0],
                "sma50": [92.0],
                "atr": [2.0],
                "rs21": [88.0],
                "vcs": [78.0],
                "rel_volume": [5.8],
                "volume_ratio_20d": [2.8],
                "dcr_percent": [82.0],
                "daily_change_pct": [7.2],
                "weekly_return_rank": [94.0],
                "quarterly_return_rank": [91.0],
                "rolling_20d_close_high": [100.0],
                "resistance_level_lookback": [100.0],
                "resistance_test_count": [3.0],
                "breakout_body_ratio": [0.7],
                "dist_from_52w_high": [-0.4],
                "high_52w": [103.0],
                "pp_count_window": [3.0],
                "pocket_pivot": [True],
                "three_weeks_tight": [True],
                "ema21_cloud_width": [1.2],
                "drawdown_from_20d_high_pct": [2.0],
                "hit_scans": ["RS New High, 4% bullish"],
            },
            index=["AAA"],
        ),
        scan_hits=pd.DataFrame(
            [
                {"ticker": "AAA", "kind": "scan", "name": "RS New High"},
                {"ticker": "AAA", "kind": "scan", "name": "4% bullish"},
            ]
        ),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(
        artifacts,
        ["accumulation_breakout_entry"],
        root_dir=tmp_path,
    )

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Display Bucket"] == "Approaching"
    assert float(result.iloc[0]["Entry Strength"]) < 55.0
    assert "climax_warning" in str(result.iloc[0]["Timing Detail"])


def test_accumulation_breakout_risk_cap_blocks_detected_signal(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "VCS 52 High", "display_name": "VCS 52 High"},
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Accumulation Breakout",
                    "selected_scan_names": ["VCS 52 High", "Pocket Pivot"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {
            "definitions": {
                "accumulation_breakout_entry": _accumulation_breakout_definition_payload(),
            }
        }
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=pd.DataFrame(
            {
                "close": [110.0],
                "open": [108.0],
                "high": [111.0],
                "low": [100.0],
                "ema21_close": [99.0],
                "sma50": [92.0],
                "atr": [2.0],
                "rs21": [88.0],
                "vcs": [78.0],
                "rel_volume": [2.0],
                "volume_ratio_20d": [1.6],
                "dcr_percent": [82.0],
                "daily_change_pct": [3.8],
                "weekly_return_rank": [94.0],
                "quarterly_return_rank": [91.0],
                "rolling_20d_close_high": [100.0],
                "resistance_level_lookback": [100.0],
                "resistance_test_count": [3.0],
                "breakout_body_ratio": [0.7],
                "dist_from_52w_high": [-6.0],
                "high_52w": [130.0],
                "pp_count_window": [3.0],
                "pocket_pivot": [True],
                "three_weeks_tight": [True],
                "ema21_cloud_width": [1.2],
                "drawdown_from_20d_high_pct": [2.0],
                "hit_scans": ["VCS 52 High, Pocket Pivot"],
            },
            index=["AAA"],
        ),
        scan_hits=pd.DataFrame(
            [
                {"ticker": "AAA", "kind": "scan", "name": "VCS 52 High"},
                {"ticker": "AAA", "kind": "scan", "name": "Pocket Pivot"},
            ]
        ),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(
        artifacts,
        ["accumulation_breakout_entry"],
        root_dir=tmp_path,
    )

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Display Bucket"] == "Approaching"
    assert float(result.iloc[0]["Risk In ATR"]) > 2.0
    assert "risk_cap_reason" in str(result.iloc[0]["Timing Detail"])


def test_accumulation_breakout_invalidates_broken_setup(tmp_path) -> None:
    config = EntrySignalConfig.from_dict(
        {
            "definitions": {
                "accumulation_breakout_entry": _accumulation_breakout_definition_payload(),
            }
        }
    )
    definition = config.definition_for("accumulation_breakout_entry")

    reason = evaluate_invalidation(
        definition,
        {"close": 99.0, "sma50": 100.0, "rs21": 80.0, "weekly_return_rank": 90.0, "daily_change_pct": 0.0},
    )

    assert reason == "close_below_sma50"


def test_early_cycle_recovery_runner_scores_structure_reclaim_and_rr(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "Trend Reversal Setup", "display_name": "Trend Reversal Setup"},
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
                {"scan_name": "VCS 52 Low", "display_name": "VCS 52 Low"},
                {"scan_name": "Volume Accumulation", "display_name": "Volume Accumulation"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Early Cycle Recovery",
                    "selected_scan_names": ["Trend Reversal Setup", "Pocket Pivot", "VCS 52 Low", "Volume Accumulation"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {"definitions": {"early_cycle_recovery_entry": _early_cycle_recovery_definition_payload()}}
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=_early_cycle_recovery_watchlist(close=44.0, dcr_percent=78.0, rs21=62.0),
        scan_hits=pd.DataFrame(
            [
                {"ticker": "AAA", "kind": "scan", "name": "Trend Reversal Setup"},
                {"ticker": "AAA", "kind": "scan", "name": "Pocket Pivot"},
                {"ticker": "AAA", "kind": "scan", "name": "VCS 52 Low"},
                {"ticker": "AAA", "kind": "scan", "name": "Volume Accumulation"},
            ]
        ),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(artifacts, ["early_cycle_recovery_entry"], root_dir=tmp_path)

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Signal"] == "Early Cycle Recovery Entry"
    assert result.iloc[0]["Preset Sources"] == "Early Cycle Recovery"
    assert result.iloc[0]["Display Bucket"] == "Signal Detected"
    assert float(result.iloc[0]["R/R Ratio"]) >= 2.0
    assert "pivot_trigger" in str(result.iloc[0]["Timing Detail"])


def test_early_cycle_recovery_risk_cap_blocks_detected_signal(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [{"scan_name": "Trend Reversal Setup", "display_name": "Trend Reversal Setup"}],
            "watchlist_presets": [
                {
                    "preset_name": "Early Cycle Recovery",
                    "selected_scan_names": ["Trend Reversal Setup"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {"definitions": {"early_cycle_recovery_entry": _early_cycle_recovery_definition_payload()}}
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=_early_cycle_recovery_watchlist(close=50.0, dcr_percent=78.0, rs21=62.0),
        scan_hits=pd.DataFrame([{"ticker": "AAA", "kind": "scan", "name": "Trend Reversal Setup"}]),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(artifacts, ["early_cycle_recovery_entry"], root_dir=tmp_path)

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Display Bucket"] == "Approaching"
    assert float(result.iloc[0]["Risk In ATR"]) > 2.25
    assert "risk_cap_reason" in str(result.iloc[0]["Timing Detail"])


def test_early_cycle_recovery_low_dcr_caps_detected_signal(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [{"scan_name": "Trend Reversal Setup", "display_name": "Trend Reversal Setup"}],
            "watchlist_presets": [
                {
                    "preset_name": "Early Cycle Recovery",
                    "selected_scan_names": ["Trend Reversal Setup"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {"definitions": {"early_cycle_recovery_entry": _early_cycle_recovery_definition_payload()}}
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=_early_cycle_recovery_watchlist(close=44.0, dcr_percent=42.0, rs21=62.0),
        scan_hits=pd.DataFrame([{"ticker": "AAA", "kind": "scan", "name": "Trend Reversal Setup"}]),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(artifacts, ["early_cycle_recovery_entry"], root_dir=tmp_path)

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Display Bucket"] == "Approaching"
    assert "low_dcr_warning" in str(result.iloc[0]["Timing Detail"])


def test_early_cycle_recovery_invalidates_weak_rs() -> None:
    config = EntrySignalConfig.from_dict(
        {"definitions": {"early_cycle_recovery_entry": _early_cycle_recovery_definition_payload()}}
    )
    definition = config.definition_for("early_cycle_recovery_entry")

    reason = evaluate_invalidation(
        definition,
        {"close": 42.0, "sma50": 40.0, "rs21": 34.0, "daily_change_pct": 0.0},
    )

    assert reason == "rs21_below_35"


def test_power_gap_pullback_runner_scores_reclaim_and_rr(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [
                {"scan_name": "Pullback Quality scan", "display_name": "Pullback Quality scan"},
                {"scan_name": "21EMA Pattern H", "display_name": "21EMA Pattern H"},
                {"scan_name": "Reclaim scan", "display_name": "Reclaim scan"},
                {"scan_name": "Pocket Pivot", "display_name": "Pocket Pivot"},
            ],
            "watchlist_presets": [
                {
                    "preset_name": "Power Gap Pullback",
                    "selected_scan_names": ["Pullback Quality scan", "21EMA Pattern H", "Reclaim scan", "Pocket Pivot"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {"definitions": {"power_gap_pullback_entry": _power_gap_pullback_definition_payload()}}
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=_power_gap_pullback_watchlist(close=101.0, days_since_power_gap=6.0, dcr_percent=76.0, low=99.0),
        scan_hits=pd.DataFrame(
            [
                {"ticker": "AAA", "kind": "scan", "name": "Pullback Quality scan"},
                {"ticker": "AAA", "kind": "scan", "name": "21EMA Pattern H"},
                {"ticker": "AAA", "kind": "scan", "name": "Reclaim scan"},
                {"ticker": "AAA", "kind": "scan", "name": "Pocket Pivot"},
            ]
        ),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(artifacts, ["power_gap_pullback_entry"], root_dir=tmp_path)

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Signal"] == "Power Gap Pullback Entry"
    assert result.iloc[0]["Preset Sources"] == "Power Gap Pullback"
    assert result.iloc[0]["Display Bucket"] == "Signal Detected"
    assert float(result.iloc[0]["R/R Ratio"]) >= 2.0
    assert "reclaim_trigger" in str(result.iloc[0]["Timing Detail"])


def test_power_gap_pullback_gap_chase_caps_detected_signal(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [{"scan_name": "Reclaim scan", "display_name": "Reclaim scan"}],
            "watchlist_presets": [
                {
                    "preset_name": "Power Gap Pullback",
                    "selected_scan_names": ["Reclaim scan"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {"definitions": {"power_gap_pullback_entry": _power_gap_pullback_definition_payload()}}
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=_power_gap_pullback_watchlist(close=101.0, days_since_power_gap=1.0, dcr_percent=76.0, low=99.0),
        scan_hits=pd.DataFrame([{"ticker": "AAA", "kind": "scan", "name": "Reclaim scan"}]),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(artifacts, ["power_gap_pullback_entry"], root_dir=tmp_path)

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Display Bucket"] == "Approaching"
    assert "gap_chase_warning" in str(result.iloc[0]["Timing Detail"])


def test_power_gap_pullback_risk_cap_blocks_detected_signal(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [{"scan_name": "Reclaim scan", "display_name": "Reclaim scan"}],
            "watchlist_presets": [
                {
                    "preset_name": "Power Gap Pullback",
                    "selected_scan_names": ["Reclaim scan"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {"definitions": {"power_gap_pullback_entry": _power_gap_pullback_definition_payload()}}
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=_power_gap_pullback_watchlist(close=108.0, days_since_power_gap=6.0, dcr_percent=76.0, low=99.0),
        scan_hits=pd.DataFrame([{"ticker": "AAA", "kind": "scan", "name": "Reclaim scan"}]),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(artifacts, ["power_gap_pullback_entry"], root_dir=tmp_path)

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Display Bucket"] == "Approaching"
    assert float(result.iloc[0]["Risk In ATR"]) > 2.0
    assert "risk_cap_reason" in str(result.iloc[0]["Timing Detail"])


def test_power_gap_pullback_low_dcr_caps_detected_signal(tmp_path) -> None:
    scan_config = ScanConfig.from_dict(
        {
            "card_sections": [{"scan_name": "Reclaim scan", "display_name": "Reclaim scan"}],
            "watchlist_presets": [
                {
                    "preset_name": "Power Gap Pullback",
                    "selected_scan_names": ["Reclaim scan"],
                    "duplicate_threshold": 1,
                    "preset_status": "enabled",
                }
            ],
        }
    )
    signal_config = EntrySignalConfig.from_dict(
        {"definitions": {"power_gap_pullback_entry": _power_gap_pullback_definition_payload()}}
    )
    runner = EntrySignalRunner(signal_config, scan_config)
    artifacts = _build_platform_artifacts(
        watchlist=_power_gap_pullback_watchlist(close=101.0, days_since_power_gap=6.0, dcr_percent=42.0, low=99.0),
        scan_hits=pd.DataFrame([{"ticker": "AAA", "kind": "scan", "name": "Reclaim scan"}]),
        trade_date="2026-04-24",
    )

    result = runner.sync_and_evaluate(artifacts, ["power_gap_pullback_entry"], root_dir=tmp_path)

    assert list(result["Ticker"]) == ["AAA"]
    assert result.iloc[0]["Display Bucket"] == "Approaching"
    assert "low_dcr_warning" in str(result.iloc[0]["Timing Detail"])


def test_power_gap_pullback_invalidates_broken_setup() -> None:
    config = EntrySignalConfig.from_dict(
        {"definitions": {"power_gap_pullback_entry": _power_gap_pullback_definition_payload()}}
    )
    definition = config.definition_for("power_gap_pullback_entry")

    reason = evaluate_invalidation(
        definition,
        {"close": 99.0, "sma50": 100.0, "drawdown_from_20d_high_pct": 5.0, "rs21": 70.0, "days_since_power_gap": 6.0, "daily_change_pct": 0.0},
    )

    assert reason == "close_below_sma50"


def _definition_payload(display_name: str) -> dict[str, object]:
    return {
        "display_name": display_name,
        "signal_version": "1.0",
        "description": "test definition",
        "pool": {
            "preset_sources": ["Orderly Pullback", "Trend Pullback"],
            "detection_window_days": 10,
            "invalidation": [
                {"field": "close", "condition": "below", "reference": "sma50"},
                {"field": "drawdown_from_20d_high_pct", "condition": "above", "threshold": 20.0},
                {"field": "rs21", "condition": "below", "threshold": 40.0},
                {"field": "sma50_slope_10d_pct", "condition": "at_or_below", "threshold": 0.0},
            ],
            "snapshot_fields": [
                "close",
                "ema21_close",
                "sma50",
                "rs21",
                "atr",
                "drawdown_from_20d_high_pct",
                "volume_ma5_to_ma20_ratio",
                "atr_21ema_zone",
                "atr_50sma_zone",
                "rolling_20d_close_high",
                "high",
            ],
            "pool_tracking": ["low_since_detection", "high_since_detection"],
        },
        "setup_maturity": {
            "indicators": {
                "volume_exhaustion": {
                    "weight": 0.30,
                    "field": "volume_ma5_to_ma20_ratio",
                    "breakpoints": [[0.60, 100], [0.70, 80], [0.80, 55], [0.85, 35], [0.95, 10], [1.00, 0]],
                },
                "support_convergence": {
                    "weight": 0.25,
                    "field": "atr_21ema_zone",
                    "breakpoints": [[-1.25, 0], [-0.75, 40], [-0.50, 70], [-0.25, 95], [0.0, 100], [0.25, 95], [0.50, 70], [1.00, 0]],
                },
                "pullback_duration": {
                    "weight": 0.20,
                    "field": "_days_since_first_detected",
                    "breakpoints": [[1, 20], [2, 50], [3, 80], [4, 100], [5, 100], [6, 85], [7, 65], [8, 45], [9, 25], [10, 10]],
                },
                "trend_integrity": {
                    "weight": 0.15,
                    "components": {
                        "ema21_slope": {
                            "field": "ema21_slope_5d_pct",
                            "weight": 0.60,
                            "breakpoints": [[-0.05, 0], [0.00, 20], [0.10, 50], [0.20, 80], [0.30, 100]],
                        },
                        "sma50_slope": {
                            "field": "sma50_slope_10d_pct",
                            "weight": 0.40,
                            "breakpoints": [[-0.02, 0], [0.00, 20], [0.05, 50], [0.10, 80], [0.15, 100]],
                        },
                    },
                },
                "rs_resilience": {
                    "weight": 0.10,
                    "field": "_rs21_delta_from_detection",
                    "breakpoints": [[-20, 0], [-15, 25], [-10, 50], [-5, 75], [0, 100], [5, 100]],
                },
            }
        },
        "timing": {
            "indicators": {
                "ema_reclaim_event": {"weight": 0.30},
                "volume_confirmation": {
                    "weight": 0.25,
                    "field": "volume_ratio_20d",
                    "breakpoints": [[0.60, 5], [0.80, 15], [1.00, 40], [1.30, 70], [1.50, 90], [2.00, 95], [2.50, 80], [3.50, 50]],
                },
                "close_quality": {
                    "weight": 0.20,
                    "field": "dcr_percent",
                    "breakpoints": [[20, 5], [30, 10], [40, 25], [50, 40], [60, 60], [70, 80], [80, 100]],
                },
                "micro_structure_breakout": {"weight": 0.15},
                "demand_footprint": {"weight": 0.10},
            }
        },
        "risk_reward": {
            "stop": {
                "reference": "low_since_detection",
                "atr_buffer": 0.25,
                "min_distance_atr": 0.75,
                "structural_penalty": 0.80,
            },
            "reward": {
                "primary": "snapshot_rolling_20d_close_high",
                "secondary": "high_52w",
                "fallback": "measured_move",
            },
            "scoring": {
                "breakpoints": [[0.5, 5], [1.0, 25], [1.5, 50], [2.0, 70], [2.5, 85], [3.0, 95]],
            },
        },
        "entry_strength": {
            "weights": {"setup_maturity": 0.25, "timing": 0.40, "risk_reward": 0.35},
            "floor_gate": {"min_axis_threshold": 20, "capped_strength": 30},
        },
        "display": {
            "thresholds": {"signal_detected": 50, "approaching": 35, "tracking": 0},
        },
    }


def _pullback_definition_payload() -> dict[str, object]:
    return {
        "display_name": "Pullback Resumption Entry",
        "signal_version": "1.0",
        "description": "test pullback resumption definition",
        "pool": {
            "preset_sources": ["Pullback Trigger", "50SMA Defense", "Reclaim Trigger"],
            "detection_window_days": 7,
            "invalidation": [
                {"field": "close", "condition": "below", "reference": "sma50", "reference_multiplier": 0.97},
                {"field": "drawdown_from_20d_high_pct", "condition": "above", "threshold": 20.0},
                {"field": "rs21", "condition": "below", "threshold": 40.0},
            ],
            "snapshot_fields": [
                "close",
                "ema21_close",
                "sma50",
                "rs21",
                "atr",
                "drawdown_from_20d_high_pct",
                "volume_ma5_to_ma20_ratio",
                "atr_21ema_zone",
                "atr_50sma_zone",
                "rolling_20d_close_high",
                "high",
            ],
            "pool_tracking": ["low_since_detection", "high_since_detection"],
        },
        "setup_maturity": {
            "indicators": {
                "pullback_depth_rr_quality": {"weight": 0.35},
                "volume_dry_up": {
                    "weight": 0.25,
                    "field": "volume_ma5_to_ma20_ratio",
                    "breakpoints": [[0.60, 100], [0.70, 80], [0.80, 55], [0.85, 35], [0.95, 10], [1.00, 0]],
                },
                "rs_resilience": {
                    "weight": 0.20,
                    "field": "rs21",
                    "breakpoints": [[40, 0], [50, 25], [60, 55], [70, 80], [80, 100]],
                },
                "trend_health": {
                    "weight": 0.20,
                    "field": "sma50_slope_10d_pct",
                    "breakpoints": [[-0.05, 0], [0.00, 25], [0.05, 55], [0.10, 80], [0.20, 100]],
                },
            }
        },
        "timing": {
            "indicators": {
                "pattern_trigger": {"weight": 0.30},
                "ma_reclaim_event": {"weight": 0.25},
                "volume_confirmation": {
                    "weight": 0.25,
                    "field": "rel_volume",
                    "breakpoints": [[0.80, 10], [1.00, 35], [1.30, 65], [1.50, 85], [2.00, 100]],
                },
                "demand_footprint": {"weight": 0.20},
            }
        },
        "risk_reward": {
            "stop": {
                "reference": "depth_adaptive",
                "atr_buffer": 0.50,
                "min_distance_atr": 0.50,
                "structural_penalty": 0.85,
            },
            "reward": {
                "primary": "snapshot_rolling_20d_close_high",
                "secondary": "high_52w",
                "fallback": "measured_move",
            },
            "scoring": {
                "breakpoints": [[0.5, 5], [1.0, 25], [1.5, 50], [2.0, 70], [2.5, 85], [3.0, 95]],
            },
        },
        "entry_strength": {
            "weights": {"setup_maturity": 0.35, "timing": 0.40, "risk_reward": 0.25},
            "floor_gate": {"min_axis_threshold": 15, "capped_strength": 30},
        },
        "display": {
            "thresholds": {"signal_detected": 48, "approaching": 32, "tracking": 0},
        },
    }


def _momentum_definition_payload() -> dict[str, object]:
    return {
        "display_name": "Momentum Acceleration Entry",
        "signal_version": "1.0",
        "description": "test momentum acceleration definition",
        "pool": {
            "preset_sources": ["Momentum Ignition"],
            "detection_window_days": 3,
            "invalidation": [
                {"field": "daily_change_pct", "condition": "below", "threshold": -4.0},
                {"field": "close", "condition": "below", "reference": "sma50"},
                {"field": "weekly_return_rank", "condition": "below", "threshold": 80.0},
            ],
            "snapshot_fields": [
                "close",
                "high",
                "low",
                "atr",
                "rs21",
                "vcs",
                "weekly_return_rank",
                "rel_volume",
                "daily_change_pct",
                "dcr_percent",
                "dist_from_52w_high",
                "pp_count_window",
            ],
            "pool_tracking": ["low_since_detection", "high_since_detection"],
        },
        "setup_maturity": {
            "indicators": {
                "vcs_quality": {
                    "weight": 0.40,
                    "field": "vcs",
                    "breakpoints": [[35, 10], [45, 30], [55, 55], [65, 80], [75, 100]],
                },
                "pp_density": {
                    "weight": 0.30,
                    "field": "pp_count_window",
                    "breakpoints": [[0, 10], [1, 35], [2, 70], [3, 100]],
                },
                "momentum_rank": {
                    "weight": 0.30,
                    "field": "weekly_return_rank",
                    "breakpoints": [[80, 20], [90, 55], [97, 100]],
                },
            }
        },
        "timing": {
            "indicators": {
                "acceleration_event": {"weight": 0.35},
                "volume_confirmation": {
                    "weight": 0.30,
                    "field": "rel_volume",
                    "breakpoints": [[0.80, 10], [1.00, 40], [1.50, 75], [2.00, 100], [3.00, 90], [5.00, 65]],
                },
                "close_quality": {
                    "weight": 0.20,
                    "field": "dcr_percent",
                    "breakpoints": [[30, 5], [40, 15], [50, 35], [60, 60], [70, 80], [80, 100]],
                },
                "follow_through": {"weight": 0.15},
            }
        },
        "risk_reward": {
            "stop": {
                "reference": "acceleration_day_low",
                "atr_buffer": 0.25,
                "min_distance_atr": 0.25,
                "structural_penalty": 0.80,
            },
            "reward": {
                "primary": "rr_2x",
                "secondary": "momentum_8pct",
                "fallback": "measured_move",
            },
            "scoring": {
                "breakpoints": [[0.5, 5], [1.0, 25], [1.5, 50], [2.0, 70], [2.5, 85], [3.0, 95]],
            },
        },
        "entry_strength": {
            "weights": {"setup_maturity": 0.20, "timing": 0.45, "risk_reward": 0.35},
            "floor_gate": {"min_axis_threshold": 20, "capped_strength": 30},
        },
        "display": {
            "thresholds": {"signal_detected": 55, "approaching": 40, "tracking": 0},
        },
    }


def _accumulation_breakout_definition_payload() -> dict[str, object]:
    return {
        "display_name": "Accumulation Breakout Entry",
        "signal_version": "1.0",
        "description": "test accumulation breakout definition",
        "pool": {
            "preset_sources": ["Accumulation Breakout", "RS Breakout Setup"],
            "detection_window_days": 5,
            "invalidation": [
                {"field": "close", "condition": "below", "reference": "sma50"},
                {"field": "rs21", "condition": "below", "threshold": 45.0},
                {"field": "weekly_return_rank", "condition": "below", "threshold": 70.0},
                {"field": "daily_change_pct", "condition": "below", "threshold": -5.0},
            ],
            "snapshot_fields": [
                "close",
                "open",
                "high",
                "low",
                "atr",
                "ema21_close",
                "sma50",
                "rs21",
                "vcs",
                "rel_volume",
                "volume_ratio_20d",
                "dcr_percent",
                "daily_change_pct",
                "weekly_return_rank",
                "quarterly_return_rank",
                "rolling_20d_close_high",
                "resistance_level_lookback",
                "resistance_test_count",
                "breakout_body_ratio",
                "dist_from_52w_high",
                "high_52w",
                "pp_count_window",
                "pocket_pivot",
                "hit_scans",
            ],
            "pool_tracking": ["low_since_detection", "high_since_detection"],
        },
        "setup_maturity": {
            "indicators": {
                "vcs_quality": {
                    "weight": 0.25,
                    "field": "vcs",
                    "breakpoints": [[35, 10], [45, 30], [55, 55], [65, 80], [75, 100]],
                },
                "rs_leadership": {"weight": 0.25},
                "accumulation_quality": {"weight": 0.20},
                "base_tightness": {"weight": 0.15},
                "resistance_context": {"weight": 0.15},
            }
        },
        "timing": {
            "indicators": {
                "breakout_event": {"weight": 0.35},
                "volume_confirmation": {
                    "weight": 0.25,
                    "field": "rel_volume",
                    "breakpoints": [[0.80, 10], [1.00, 35], [1.30, 65], [1.50, 85], [2.50, 100], [5.00, 70]],
                },
                "close_quality": {
                    "weight": 0.20,
                    "field": "dcr_percent",
                    "breakpoints": [[30, 5], [40, 15], [50, 35], [60, 60], [70, 80], [80, 100]],
                },
                "follow_through": {"weight": 0.20},
            }
        },
        "risk_reward": {
            "stop": {
                "reference": "breakout_adaptive",
                "atr_buffer": 0.25,
                "min_distance_atr": 0.50,
                "structural_penalty": 0.80,
            },
            "reward": {
                "primary": "rr_2x",
                "secondary": "high_52w",
                "fallback": "measured_move",
            },
            "scoring": {
                "breakpoints": [[0.5, 5], [1.0, 25], [1.5, 50], [2.0, 70], [2.5, 85], [3.0, 95]],
            },
        },
        "entry_strength": {
            "weights": {"setup_maturity": 0.30, "timing": 0.35, "risk_reward": 0.35},
            "floor_gate": {"min_axis_threshold": 20, "capped_strength": 30},
        },
        "display": {
            "thresholds": {"signal_detected": 55, "approaching": 38, "tracking": 0},
        },
    }


def _early_cycle_recovery_definition_payload() -> dict[str, object]:
    return {
        "display_name": "Early Cycle Recovery Entry",
        "signal_version": "1.0",
        "description": "test early cycle recovery definition",
        "pool": {
            "preset_sources": ["Early Cycle Recovery", "Screening Thesis"],
            "detection_window_days": 8,
            "invalidation": [
                {"field": "rs21", "condition": "below", "threshold": 35.0},
                {"field": "daily_change_pct", "condition": "below", "threshold": -5.0},
                {"field": "close", "condition": "below", "reference": "sma50", "reference_multiplier": 0.95},
            ],
            "snapshot_fields": [
                "close",
                "open",
                "high",
                "low",
                "atr",
                "ema21_close",
                "sma50",
                "sma200",
                "rs21",
                "vcs",
                "rel_volume",
                "volume_ratio_20d",
                "dcr_percent",
                "daily_change_pct",
                "weekly_return_rank",
                "quarterly_return_rank",
                "dist_from_52w_low",
                "dist_from_52w_high",
                "atr_21ema_zone",
                "atr_50sma_zone",
                "close_crossed_above_ema21",
                "close_crossed_above_sma50",
                "sma50_slope_10d_pct",
                "structure_pivot_long_active",
                "structure_pivot_long_breakout_first_day",
                "structure_pivot_long_hl_price",
                "structure_pivot_1st_break",
                "structure_pivot_2nd_break",
                "ct_trendline_break",
                "pocket_pivot",
                "pp_count_window",
                "hit_scans",
            ],
            "pool_tracking": ["low_since_detection", "high_since_detection"],
        },
        "setup_maturity": {
            "indicators": {
                "structure_reversal_quality": {"weight": 0.35},
                "low_to_recovery_position": {"weight": 0.20},
                "accumulation_evidence": {"weight": 0.20},
                "trend_repair": {"weight": 0.15},
                "rs_recovery": {"weight": 0.10},
            }
        },
        "timing": {
            "indicators": {
                "pivot_trigger": {"weight": 0.35},
                "ma_reclaim": {"weight": 0.25},
                "volume_confirmation": {
                    "weight": 0.20,
                    "field": "rel_volume",
                    "breakpoints": [[0.80, 10], [1.00, 35], [1.30, 70], [1.80, 95], [3.00, 100], [5.00, 70]],
                },
                "close_quality": {
                    "weight": 0.20,
                    "field": "dcr_percent",
                    "breakpoints": [[30, 5], [40, 15], [50, 35], [65, 75], [80, 100]],
                },
            }
        },
        "risk_reward": {
            "stop": {
                "reference": "recovery_pivot_adaptive",
                "atr_buffer": 0.25,
                "min_distance_atr": 0.50,
                "structural_penalty": 0.80,
            },
            "reward": {
                "primary": "rr_2x",
                "secondary": "rolling_20d_close_high",
                "fallback": "measured_move",
            },
            "scoring": {
                "breakpoints": [[0.5, 5], [1.0, 25], [1.5, 50], [2.0, 70], [2.5, 85], [3.0, 95]],
            },
        },
        "entry_strength": {
            "weights": {"setup_maturity": 0.35, "timing": 0.35, "risk_reward": 0.30},
            "floor_gate": {"min_axis_threshold": 18, "capped_strength": 30},
        },
        "display": {"thresholds": {"signal_detected": 52, "approaching": 35, "tracking": 0}},
    }


def _early_cycle_recovery_watchlist(*, close: float, dcr_percent: float, rs21: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "close": [close],
            "open": [42.0],
            "high": [close + 1.0],
            "low": [41.5],
            "atr": [2.0],
            "ema21_close": [42.0],
            "sma50": [40.0],
            "sma200": [55.0],
            "rs21": [rs21],
            "vcs": [55.0],
            "rel_volume": [1.8],
            "volume_ratio_20d": [1.5],
            "dcr_percent": [dcr_percent],
            "daily_change_pct": [3.0],
            "weekly_return_rank": [78.0],
            "quarterly_return_rank": [72.0],
            "dist_from_52w_low": [22.0],
            "dist_from_52w_high": [-35.0],
            "atr_21ema_zone": [0.5],
            "atr_50sma_zone": [1.0],
            "close_crossed_above_ema21": [True],
            "close_crossed_above_sma50": [False],
            "sma50_slope_10d_pct": [-0.02],
            "structure_pivot_long_active": [True],
            "structure_pivot_long_breakout_first_day": [True],
            "structure_pivot_long_hl_price": [41.0],
            "structure_pivot_1st_break": [True],
            "structure_pivot_2nd_break": [True],
            "ct_trendline_break": [True],
            "pocket_pivot": [True],
            "pp_count_window": [3.0],
            "hit_scans": ["Trend Reversal Setup, Pocket Pivot, VCS 52 Low, Volume Accumulation"],
        },
        index=["AAA"],
    )


def _power_gap_pullback_definition_payload() -> dict[str, object]:
    return {
        "display_name": "Power Gap Pullback Entry",
        "signal_version": "1.0",
        "description": "test power gap pullback definition",
        "pool": {
            "preset_sources": ["Power Gap Pullback"],
            "detection_window_days": 10,
            "invalidation": [
                {"field": "close", "condition": "below", "reference": "sma50"},
                {"field": "drawdown_from_20d_high_pct", "condition": "above", "threshold": 18.0},
                {"field": "rs21", "condition": "below", "threshold": 45.0},
                {"field": "days_since_power_gap", "condition": "above", "threshold": 20.0},
                {"field": "daily_change_pct", "condition": "below", "threshold": -5.0},
            ],
            "snapshot_fields": [
                "close",
                "open",
                "high",
                "low",
                "atr",
                "ema21_close",
                "ema21_high",
                "ema21_low",
                "sma50",
                "rs21",
                "vcs",
                "rel_volume",
                "volume_ratio_20d",
                "volume_ma5_to_ma20_ratio",
                "dcr_percent",
                "daily_change_pct",
                "drawdown_from_20d_high_pct",
                "days_since_power_gap",
                "power_gap_up_pct",
                "ema21_low_pct",
                "atr_21ema_zone",
                "atr_low_to_ema21_high",
                "atr_low_to_ema21_low",
                "rolling_20d_close_high",
                "high_52w",
                "dist_from_52w_high",
                "pocket_pivot",
                "pp_count_window",
                "hit_scans",
            ],
            "pool_tracking": ["low_since_detection", "high_since_detection"],
        },
        "setup_maturity": {
            "indicators": {
                "gap_quality": {"weight": 0.25},
                "pullback_orderliness": {"weight": 0.30},
                "support_proximity": {"weight": 0.20},
                "rs_resilience": {"weight": 0.15},
                "accumulation_return": {"weight": 0.10},
            }
        },
        "timing": {
            "indicators": {
                "reclaim_trigger": {"weight": 0.35},
                "volume_reentry": {"weight": 0.25},
                "close_quality": {
                    "weight": 0.20,
                    "field": "dcr_percent",
                    "breakpoints": [[30, 5], [40, 15], [50, 35], [65, 75], [80, 100]],
                },
                "pullback_age": {"weight": 0.20},
            }
        },
        "risk_reward": {
            "stop": {
                "reference": "power_gap_pullback_adaptive",
                "atr_buffer": 0.25,
                "min_distance_atr": 0.50,
                "structural_penalty": 0.80,
            },
            "reward": {
                "primary": "rolling_20d_close_high",
                "secondary": "rr_2x",
                "fallback": "high_52w",
            },
            "scoring": {
                "breakpoints": [[0.5, 5], [1.0, 25], [1.5, 50], [2.0, 70], [2.5, 85], [3.0, 95]],
            },
        },
        "entry_strength": {
            "weights": {"setup_maturity": 0.35, "timing": 0.35, "risk_reward": 0.30},
            "floor_gate": {"min_axis_threshold": 18, "capped_strength": 30},
        },
        "display": {"thresholds": {"signal_detected": 52, "approaching": 35, "tracking": 0}},
    }


def _power_gap_pullback_watchlist(
    *,
    close: float,
    days_since_power_gap: float,
    dcr_percent: float,
    low: float,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "close": [close],
            "open": [99.0],
            "high": [close + 1.5],
            "low": [low],
            "atr": [2.0],
            "ema21_close": [100.0],
            "ema21_high": [101.0],
            "ema21_low": [99.0],
            "sma50": [95.0],
            "rs21": [76.0],
            "vcs": [72.0],
            "rel_volume": [1.7],
            "volume_ratio_20d": [1.4],
            "volume_ma5_to_ma20_ratio": [0.65],
            "dcr_percent": [dcr_percent],
            "daily_change_pct": [2.0],
            "drawdown_from_20d_high_pct": [6.0],
            "days_since_power_gap": [days_since_power_gap],
            "power_gap_up_pct": [8.0],
            "ema21_low_pct": [1.0],
            "atr_21ema_zone": [0.5],
            "atr_low_to_ema21_high": [0.4],
            "atr_low_to_ema21_low": [0.0],
            "rolling_20d_close_high": [112.0],
            "high_52w": [120.0],
            "dist_from_52w_high": [-10.0],
            "pocket_pivot": [True],
            "pp_count_window": [2.0],
            "hit_scans": ["Pullback Quality scan, 21EMA Pattern H, Reclaim scan, Volume Accumulation, Pocket Pivot"],
        },
        index=["AAA"],
    )


def _build_platform_artifacts(
    *,
    watchlist: pd.DataFrame,
    scan_hits: pd.DataFrame,
    trade_date: str,
) -> PlatformArtifacts:
    snapshot = pd.DataFrame({"trade_date": [trade_date]}, index=["AAA"])
    eligible_snapshot = watchlist.copy()
    return PlatformArtifacts(
        snapshot=snapshot,
        eligible_snapshot=eligible_snapshot,
        watchlist=watchlist,
        duplicate_tickers=pd.DataFrame(),
        watchlist_cards=[],
        earnings_today=pd.DataFrame(),
        scan_hits=scan_hits,
        benchmark_history=pd.DataFrame(),
        vix_history=pd.DataFrame(),
        market_result=None,
        radar_result=None,
        used_sample_data=False,
        data_source_label="test",
        fetch_status=pd.DataFrame(),
        data_health_summary={},
        run_directory=None,
        universe_mode="test",
        resolved_symbols=["AAA"],
        universe_snapshot_path=None,
        artifact_origin="pipeline_recomputed",
        entry_signal_watchlist=watchlist.copy(),
    )
