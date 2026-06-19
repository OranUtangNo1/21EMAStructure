from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd


MODULE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True, slots=True)
class ModuleOutputRecord:
    module: str
    date_key: str
    path: Path
    metadata_path: Path
    row_count: int


@dataclass(frozen=True, slots=True)
class ModuleOutputStore:
    """Date-keyed local artifact store for modular scan, preset, market, and RS outputs."""

    root_dir: str | Path = "data_runs/service_outputs"

    def __post_init__(self) -> None:
        Path(self.root_dir).mkdir(parents=True, exist_ok=True)

    def save_frame(
        self,
        module: str,
        date_key: str | date | datetime | pd.Timestamp,
        frame: pd.DataFrame,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> ModuleOutputRecord:
        module_name = self.normalize_module(module)
        normalized_date_key = self.normalize_date_key(date_key)
        module_dir = self.module_dir(module_name)
        module_dir.mkdir(parents=True, exist_ok=True)

        output_path = module_dir / f"{normalized_date_key}.csv"
        metadata_path = module_dir / f"{normalized_date_key}.json"
        payload = frame.copy() if frame is not None else pd.DataFrame()
        payload.to_csv(output_path, index=False)
        metadata_payload = {
            "module": module_name,
            "date_key": normalized_date_key,
            "row_count": int(len(payload)),
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            **(metadata or {}),
        }
        metadata_path.write_text(json.dumps(metadata_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        return ModuleOutputRecord(
            module=module_name,
            date_key=normalized_date_key,
            path=output_path,
            metadata_path=metadata_path,
            row_count=int(len(payload)),
        )

    def load_frame(self, module: str, date_key: str | date | datetime | pd.Timestamp) -> pd.DataFrame:
        path = self.frame_path(module, date_key)
        if not path.exists():
            return pd.DataFrame()
        frame = pd.read_csv(path)
        if "date_key" in frame.columns:
            frame["date_key"] = frame["date_key"].astype(str)
        return frame

    def save_json(
        self,
        module: str,
        date_key: str | date | datetime | pd.Timestamp,
        payload: dict[str, Any],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> ModuleOutputRecord:
        module_name = self.normalize_module(module)
        normalized_date_key = self.normalize_date_key(date_key)
        module_dir = self.module_dir(module_name)
        module_dir.mkdir(parents=True, exist_ok=True)

        output_path = module_dir / f"{normalized_date_key}.json"
        metadata_path = module_dir / f"{normalized_date_key}.meta.json"
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        metadata_payload = {
            "module": module_name,
            "date_key": normalized_date_key,
            "row_count": 1,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            **(metadata or {}),
        }
        metadata_path.write_text(json.dumps(metadata_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        return ModuleOutputRecord(
            module=module_name,
            date_key=normalized_date_key,
            path=output_path,
            metadata_path=metadata_path,
            row_count=1,
        )

    def load_json(self, module: str, date_key: str | date | datetime | pd.Timestamp) -> dict[str, Any]:
        path = self.json_path(module, date_key)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def load_metadata(self, module: str, date_key: str | date | datetime | pd.Timestamp) -> dict[str, Any]:
        frame_metadata = self.metadata_path(module, date_key)
        json_metadata = self.json_metadata_path(module, date_key)
        path = frame_metadata if frame_metadata.exists() else json_metadata
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def exists(self, module: str, date_key: str | date | datetime | pd.Timestamp) -> bool:
        return self.frame_path(module, date_key).exists() or self.json_path(module, date_key).exists()

    def list_date_keys(self, module: str) -> list[str]:
        module_dir = self.module_dir(module)
        if not module_dir.exists():
            return []
        date_keys = {
            path.stem
            for path in module_dir.iterdir()
            if path.is_file() and path.suffix in {".csv", ".json"} and not path.name.endswith(".meta.json")
        }
        return sorted(date_keys)

    def latest_date_key(self, module: str) -> str | None:
        date_keys = self.list_date_keys(module)
        return date_keys[-1] if date_keys else None

    def latest_frame(self, module: str) -> pd.DataFrame:
        date_key = self.latest_date_key(module)
        return pd.DataFrame() if date_key is None else self.load_frame(module, date_key)

    def frame_path(self, module: str, date_key: str | date | datetime | pd.Timestamp) -> Path:
        return self.module_dir(module) / f"{self.normalize_date_key(date_key)}.csv"

    def json_path(self, module: str, date_key: str | date | datetime | pd.Timestamp) -> Path:
        return self.module_dir(module) / f"{self.normalize_date_key(date_key)}.json"

    def metadata_path(self, module: str, date_key: str | date | datetime | pd.Timestamp) -> Path:
        return self.module_dir(module) / f"{self.normalize_date_key(date_key)}.json"

    def json_metadata_path(self, module: str, date_key: str | date | datetime | pd.Timestamp) -> Path:
        return self.module_dir(module) / f"{self.normalize_date_key(date_key)}.meta.json"

    def module_dir(self, module: str) -> Path:
        return Path(self.root_dir) / self.normalize_module(module)

    def normalize_module(self, module: str) -> str:
        value = str(module).strip()
        if not value or not MODULE_NAME_PATTERN.match(value):
            raise ValueError(f"Invalid module name: {module}")
        return value

    def normalize_date_key(self, value: str | date | datetime | pd.Timestamp) -> str:
        if isinstance(value, str):
            text = value.strip()
            if re.fullmatch(r"\d{8}", text):
                return text
            parsed = pd.to_datetime(text, errors="coerce")
        else:
            parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            raise ValueError(f"Invalid date key: {value}")
        return pd.Timestamp(parsed).strftime("%Y%m%d")
