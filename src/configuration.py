from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "default.yaml"
YAML_SUFFIXES = (".yaml", ".yml")


def load_settings(path: str | Path | None = None) -> dict[str, Any]:
    """Load YAML configuration from disk, resolving includes and config directories."""
    config_path = Path(path).expanduser() if path is not None else DEFAULT_CONFIG_PATH
    return _load_config_path(config_path)


def _load_config_path(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config path does not exist: {config_path}")
    if config_path.is_dir():
        return _load_config_directory(config_path)
    return _load_config_file(config_path)


def _load_config_directory(config_dir: Path) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for child in sorted(config_dir.iterdir()):
        if child.is_file() and child.suffix.lower() in YAML_SUFFIXES:
            merged = _deep_merge(merged, _load_config_file(child))
    return merged


def _load_config_file(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Config file must contain a YAML mapping at the top level: {config_path}")

    includes = payload.pop("includes", ())
    if includes is None:
        includes = ()
    if isinstance(includes, (str, Path)):
        includes = [includes]

    merged: dict[str, Any] = {}
    for include in includes:
        include_path = Path(include)
        if not include_path.is_absolute():
            include_path = config_path.parent / include_path
        merged = _deep_merge(merged, _load_config_path(include_path))
    return _deep_merge(merged, payload)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result
