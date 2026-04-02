from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


class UserPreferenceStore:
    """Persist page-scoped user setup with config-specific namespaces."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load_group(self, group: str, namespace: str) -> dict[str, Any]:
        payload = self._load_payload()
        groups = payload.get("groups", {})
        group_state = groups.get(group, {})
        value = group_state.get(namespace, {})
        return deepcopy(value) if isinstance(value, dict) else {}

    def save_group(self, group: str, namespace: str, values: dict[str, Any]) -> None:
        payload = self._load_payload()
        payload.setdefault("version", 1)
        groups = payload.setdefault("groups", {})
        group_state = groups.setdefault(group, {})
        normalized_values = self._normalize_values(values)
        if group_state.get(namespace) == normalized_values:
            return
        group_state[namespace] = normalized_values
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=False)

    def _load_payload(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "groups": {}}
        with self.path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        if not isinstance(payload, dict):
            return {"version": 1, "groups": {}}
        groups = payload.get("groups")
        if not isinstance(groups, dict):
            payload["groups"] = {}
        return payload

    def _normalize_values(self, values: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in values.items():
            normalized[str(key)] = self._normalize_value(value)
        return normalized

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._normalize_value(child) for key, child in value.items()}
        if isinstance(value, tuple):
            return [self._normalize_value(item) for item in value]
        if isinstance(value, list):
            return [self._normalize_value(item) for item in value]
        if isinstance(value, Path):
            return str(value)
        return value
