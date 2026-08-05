"""Encrypted local memory tests."""

from __future__ import annotations

import json
from pathlib import Path

from arbora.memory import LocalMemoryStore


def test_encrypted_roundtrip(tmp_path: Path):
    store = LocalMemoryStore(root=tmp_path, force_file_key=True)
    store.set("secret", "alpha-token-should-not-be-plaintext")
    assert store.encrypted_at_rest is True
    assert store.key_backend == "file"
    assert (tmp_path / "preferences.enc").exists()
    assert (tmp_path / "key.bin").exists()
    raw = (tmp_path / "preferences.enc").read_bytes()
    assert b"alpha-token-should-not-be-plaintext" not in raw

    store2 = LocalMemoryStore(root=tmp_path, force_file_key=True)
    assert store2.get("secret") == "alpha-token-should-not-be-plaintext"


def test_migrate_plaintext_json(tmp_path: Path):
    plain = tmp_path / "preferences.json"
    plain.write_text(json.dumps({"legacy": "value", "trusted_routines": []}), encoding="utf-8")
    store = LocalMemoryStore(root=tmp_path, force_file_key=True)
    assert store.get("legacy") == "value"
    assert (tmp_path / "preferences.enc").exists()
    assert not plain.exists()


def test_wipe_clears_ciphertext_and_key(tmp_path: Path):
    store = LocalMemoryStore(root=tmp_path, force_file_key=True)
    store.set("keep", "nope")
    store.wipe()
    assert store.get("keep") is None
    assert not (tmp_path / "preferences.enc").exists()
    # New key created for continued use after wipe.
    store.set("fresh", 1)
    assert store.get("fresh") == 1
