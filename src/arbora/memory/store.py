"""Encrypted-at-rest local context store.

Preferences and trusted-routine metadata are sealed with Fernet. On Windows the
Fernet key is wrapped with DPAPI. Plaintext `preferences.json` from earlier
prototypes is migrated automatically into `preferences.enc`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from arbora.memory.crypto import MemoryCrypto


class LocalMemoryStore:
    """Encrypted key/value preference and routine metadata store."""

    def __init__(self, root: Path | None = None, *, force_file_key: bool = False) -> None:
        self.root = root or Path.home() / ".arbora" / "memory"
        self.root.mkdir(parents=True, exist_ok=True)
        self._plain_path = self.root / "preferences.json"
        self._enc_path = self.root / "preferences.enc"
        self._crypto = MemoryCrypto(self.root, force_file_key=force_file_key)
        self._data: dict[str, Any] = self._load()

    @property
    def encrypted_at_rest(self) -> bool:
        return self._crypto.encrypted_at_rest

    @property
    def key_backend(self) -> str:
        return self._crypto.key_backend

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def wipe(self) -> None:
        """Erase stored memory (keeps the application; rotates to a fresh key)."""
        use_file_key = self._crypto.key_backend == "file"
        self._data = {}
        for path in (self._enc_path, self._plain_path):
            if path.exists():
                path.unlink()
        self._crypto.wipe_key()
        # Recreate crypto/key so subsequent writes work in the same process.
        self._crypto = MemoryCrypto(self.root, force_file_key=use_file_key)

    def export(self) -> dict[str, Any]:
        return dict(self._data)

    def _load(self) -> dict[str, Any]:
        if self._enc_path.exists():
            token = self._enc_path.read_bytes()
            if not token:
                return {}
            raw = self._crypto.decrypt(token)
            try:
                data = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return {}
            return data if isinstance(data, dict) else {}

        if self._plain_path.exists():
            try:
                data = json.loads(self._plain_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
            if not isinstance(data, dict):
                data = {}
            self._data = data
            self._save()
            try:
                self._plain_path.unlink()
            except OSError:
                pass
            return data

        return {}

    def _save(self) -> None:
        payload = json.dumps(self._data, indent=2, sort_keys=True).encode("utf-8")
        token = self._crypto.encrypt(payload)
        tmp = self._enc_path.with_suffix(".tmp")
        tmp.write_bytes(token)
        os.replace(tmp, self._enc_path)
        if self._plain_path.exists():
            try:
                self._plain_path.unlink()
            except OSError:
                pass


def export_memory_payload(memory: LocalMemoryStore) -> dict[str, Any]:
    """JSON-serialisable dump of local memory. Encryption keys are never included."""
    data = memory.export()
    return {
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "encrypted_at_rest": memory.encrypted_at_rest,
        "key_backend": memory.key_backend,
        "keys": sorted(data),
        "data": data,
    }


def memory_status_rows(memory: LocalMemoryStore) -> list[str]:
    data = memory.export()
    key_list = ", ".join(sorted(data)) if data else "none"
    return [
        f"root = {memory.root}",
        f"encrypted_at_rest = {str(memory.encrypted_at_rest).lower()}",
        f"key_backend = {memory.key_backend}",
        f"keys = {len(data)} ({key_list})",
    ]

