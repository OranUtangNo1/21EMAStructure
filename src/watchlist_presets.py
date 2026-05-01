from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.configuration import load_settings
from src.scan.rules import DuplicateRuleConfig, ScanConfig, WatchlistPresetConfig
from src.ui_preferences import UserPreferenceStore


WATCHLIST_PRESET_GROUP = "watchlist_presets"
WATCHLIST_PRESET_KIND = "watchlist_controls"
WATCHLIST_PRESET_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class ResolvedWatchlistPreset:
    preset_name: str
    source: str
    config: WatchlistPresetConfig


def load_watchlist_preset_configs(
    config_path: str,
    scan_config: ScanConfig | None = None,
) -> tuple[ResolvedWatchlistPreset, ...]:
    resolved_scan_config = scan_config or ScanConfig.from_dict(load_settings(config_path).get("scan", {}))
    builtins = [
        ResolvedWatchlistPreset(
            preset_name=preset.preset_name,
            source="Built-in",
            config=preset,
        )
        for preset in resolved_scan_config.watchlist_presets
        if preset.export_enabled
    ]
    customs = _load_custom_watchlist_preset_configs(config_path, resolved_scan_config)
    return tuple([*builtins, *customs])


def watchlist_preference_namespace(config_path: str) -> str:
    return str(Path(config_path).expanduser().resolve(strict=False))


def load_user_preference_store(config_path: str) -> UserPreferenceStore:
    settings = load_settings(config_path)
    app_settings = settings.get("app", {}) if isinstance(settings.get("app", {}), dict) else {}
    root = Path(__file__).resolve().parents[1]
    configured_path = str(app_settings.get("user_preferences_path", "")).strip()
    if configured_path:
        preference_path = Path(configured_path).expanduser()
        if not preference_path.is_absolute():
            preference_path = root / preference_path
    else:
        cache_dir = Path(str(app_settings.get("cache_dir", "data_cache"))).expanduser()
        if not cache_dir.is_absolute():
            cache_dir = root / cache_dir
        preference_path = cache_dir / "user_preferences.yaml"
    return UserPreferenceStore(preference_path)


def _load_custom_watchlist_preset_configs(
    config_path: str,
    scan_config: ScanConfig,
) -> list[ResolvedWatchlistPreset]:
    preference_store = load_user_preference_store(config_path)
    raw_presets = preference_store.load_collection(WATCHLIST_PRESET_GROUP, watchlist_preference_namespace(config_path))
    available_scan_names = {section.scan_name for section in scan_config.card_sections}
    available_annotation_names = {section.filter_name for section in scan_config.annotation_filters}
    presets: list[ResolvedWatchlistPreset] = []
    for raw_name, raw_record in raw_presets.items():
        preset_name = str(raw_name).strip()
        if not preset_name:
            continue
        payload = _read_watchlist_preset_payload(raw_record)
        if payload is None:
            continue
        selected_scan_names = tuple(
            name for name in (str(value).strip() for value in payload.get("selected_scan_names", [])) if name in available_scan_names
        )
        if not selected_scan_names:
            continue
        selected_annotation_filters = tuple(
            name
            for name in (str(value).strip() for value in payload.get("selected_annotation_filters", []))
            if name in available_annotation_names
        )
        selected_duplicate_subfilters = tuple(
            name for name in (str(value).strip() for value in payload.get("selected_duplicate_subfilters", [])) if name
        )
        try:
            duplicate_threshold = int(payload.get("duplicate_threshold", scan_config.duplicate_min_count))
        except (TypeError, ValueError):
            duplicate_threshold = int(scan_config.duplicate_min_count)
        duplicate_threshold = max(1, min(duplicate_threshold, max(1, len(selected_scan_names))))
        try:
            duplicate_rule = DuplicateRuleConfig.from_dict(
                payload.get("duplicate_rule"),
                default_min_count=duplicate_threshold,
            )
        except ValueError:
            continue
        presets.append(
            ResolvedWatchlistPreset(
                preset_name=preset_name,
                source="Custom",
                config=WatchlistPresetConfig(
                    preset_name=preset_name,
                    selected_scan_names=selected_scan_names,
                    selected_annotation_filters=selected_annotation_filters,
                    selected_duplicate_subfilters=selected_duplicate_subfilters,
                    duplicate_threshold=duplicate_threshold,
                    duplicate_rule=duplicate_rule,
                    preset_status="enabled",
                ),
            )
        )
    return presets


def _read_watchlist_preset_payload(record: object) -> dict[str, object] | None:
    if not isinstance(record, dict):
        return None
    if any(key in record for key in ("schema_version", "kind", "values")):
        schema_version = record.get("schema_version")
        if schema_version not in (None, 1, 2):
            return None
        kind = str(record.get("kind", WATCHLIST_PRESET_KIND)).strip()
        if kind not in {WATCHLIST_PRESET_KIND, "watchlist_preset"}:
            return None
        values = record.get("values", {})
        return values if isinstance(values, dict) else None
    return record
