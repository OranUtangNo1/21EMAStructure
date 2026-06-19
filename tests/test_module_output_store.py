from __future__ import annotations

import json

import pandas as pd
import pytest

from src.services.module_output_store import ModuleOutputStore


def test_module_output_store_saves_and_loads_frame_by_date_key(tmp_path) -> None:
    store = ModuleOutputStore(tmp_path)
    frame = pd.DataFrame(
        [
            {"date_key": "20260313", "ticker": "AAA", "scan_name": "scan_a", "passed": True},
            {"date_key": "20260313", "ticker": "BBB", "scan_name": "scan_a", "passed": False},
        ]
    )

    record = store.save_frame("scan", "2026-03-13", frame, metadata={"ticker_count": 2})
    loaded = store.load_frame("scan", "20260313")
    metadata = store.load_metadata("scan", "2026-03-13")

    assert record.path == tmp_path / "scan" / "20260313.csv"
    assert record.metadata_path == tmp_path / "scan" / "20260313.json"
    assert record.row_count == 2
    assert loaded.to_dict("records") == frame.to_dict("records")
    assert metadata["module"] == "scan"
    assert metadata["date_key"] == "20260313"
    assert metadata["row_count"] == 2
    assert metadata["ticker_count"] == 2


def test_module_output_store_latest_and_exists(tmp_path) -> None:
    store = ModuleOutputStore(tmp_path)
    store.save_frame("preset", "2026-03-12", pd.DataFrame([{"ticker": "AAA"}]))
    store.save_frame("preset", "2026-03-13", pd.DataFrame([{"ticker": "BBB"}]))

    assert store.exists("preset", pd.Timestamp("2026-03-12"))
    assert not store.exists("preset", "2026-03-11")
    assert store.list_date_keys("preset") == ["20260312", "20260313"]
    assert store.latest_date_key("preset") == "20260313"
    assert store.latest_frame("preset").to_dict("records") == [{"ticker": "BBB"}]


def test_module_output_store_saves_json_payloads(tmp_path) -> None:
    store = ModuleOutputStore(tmp_path)
    payload = {"date_key": "20260313", "market_label": "neutral", "score": 51.5}

    record = store.save_json("market", "2026-03-13", payload, metadata={"source": "unit"})

    assert record.path == tmp_path / "market" / "20260313.json"
    assert record.metadata_path == tmp_path / "market" / "20260313.meta.json"
    assert store.load_json("market", "20260313") == payload
    assert json.loads(record.metadata_path.read_text(encoding="utf-8"))["source"] == "unit"


def test_module_output_store_rejects_unsafe_module_names(tmp_path) -> None:
    store = ModuleOutputStore(tmp_path)

    with pytest.raises(ValueError):
        store.save_frame("../scan", "2026-03-13", pd.DataFrame())


def test_module_output_store_rejects_invalid_date_keys(tmp_path) -> None:
    store = ModuleOutputStore(tmp_path)

    with pytest.raises(ValueError):
        store.save_frame("scan", "not-a-date", pd.DataFrame())
