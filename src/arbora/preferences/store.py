"""Serialize opt-in user preferences to/from encrypted local memory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arbora.memory.store import LocalMemoryStore

MEMORY_KEY = "user_preferences"

VALID_PROVIDERS = frozenset({"", "ollama", "echo", "openai", "cloud"})


@dataclass
class UserPreferences:
    """Explicit user defaults — never inferred without opt-in."""

    dry_run_default: bool = True
    provider: str = ""
    workday_folder: str = ""

    def resolved_workday_folder(self) -> Path:
        if self.workday_folder.strip():
            return Path(self.workday_folder).expanduser()
        return Path.home() / "ArboraWorkday"


def preferences_to_dict(prefs: UserPreferences) -> dict[str, Any]:
    return {
        "dry_run_default": prefs.dry_run_default,
        "provider": prefs.provider,
        "workday_folder": prefs.workday_folder,
    }


def preferences_from_dict(raw: dict[str, Any] | None) -> UserPreferences:
    if not raw:
        return UserPreferences()
    provider = str(raw.get("provider", "")).strip().lower()
    if provider == "cloud":
        provider = "openai"
    if provider not in VALID_PROVIDERS:
        provider = ""
    return UserPreferences(
        dry_run_default=bool(raw.get("dry_run_default", True)),
        provider=provider,
        workday_folder=str(raw.get("workday_folder", "")),
    )


def load_preferences(memory: LocalMemoryStore) -> UserPreferences:
    raw = memory.get(MEMORY_KEY)
    return preferences_from_dict(raw if isinstance(raw, dict) else None)


def save_preferences(memory: LocalMemoryStore, prefs: UserPreferences) -> None:
    memory.set(MEMORY_KEY, preferences_to_dict(prefs))


def set_preference(memory: LocalMemoryStore, key: str, value: str) -> UserPreferences:
    prefs = load_preferences(memory)
    normalized = key.strip().lower().replace("-", "_")
    if normalized in {"dry_run", "dry_run_default"}:
        prefs.dry_run_default = value.strip().lower() in {"1", "true", "on", "yes", "y"}
    elif normalized == "provider":
        choice = value.strip().lower()
        if choice == "cloud":
            choice = "openai"
        if choice not in VALID_PROVIDERS:
            raise ValueError(f"Unknown provider '{value}'. Use ollama, echo, openai, or empty to clear.")
        prefs.provider = choice
    elif normalized in {"workday_folder", "workday_root", "workday"}:
        prefs.workday_folder = value.strip()
    else:
        raise ValueError(f"Unknown preference '{key}'. Use dry_run, provider, or workday_folder.")
    save_preferences(memory, prefs)
    return prefs


def preference_rows(prefs: UserPreferences) -> list[str]:
    provider = prefs.provider or "(env default)"
    workday = str(prefs.resolved_workday_folder())
    dry = "on" if prefs.dry_run_default else "off"
    return [
        f"dry_run_default = {dry}",
        f"provider = {provider}",
        f"workday_folder = {workday}",
    ]
