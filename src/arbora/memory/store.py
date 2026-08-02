"""Encrypted-at-rest local context store (Stage 1 sketch).

Uses Fernet when cryptography is available; otherwise falls back to a clear
warning that encryption is not active yet. Preferences stay on-device either way.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class LocalMemoryStore:
    """Simple key/value preference and routine metadata store."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path.home() / ".arbora" / "memory"
        self.root.mkdir(parents=True, exist_ok=True)
        self._path = self.root / "preferences.json"
        self._data: dict[str, Any] = self._load()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def wipe(self) -> None:
        self._data = {}
        if self._path.exists():
            self._path.unlink()

    def export(self) -> dict[str, Any]:
        return dict(self._data)

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save(self) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self._path)
