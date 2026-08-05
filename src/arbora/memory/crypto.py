"""Local encryption helpers for Arbora memory.

Data is sealed with Fernet. The Fernet key is wrapped with Windows DPAPI when
available so the key file is useless if copied to another machine/user. On
non-Windows (and in tests), the key is stored as a local file under the memory
root with restrictive permissions.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class MemoryCryptoError(RuntimeError):
    """Raised when memory encryption or key handling fails."""


def _dpapi_protect(raw: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    in_buf = ctypes.create_string_buffer(raw)
    blob_in = DATA_BLOB(len(raw), ctypes.cast(in_buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    if not crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        "ArboraMemoryKey",
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    ):
        raise MemoryCryptoError("CryptProtectData failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def _dpapi_unprotect(wrapped: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    in_buf = ctypes.create_string_buffer(wrapped)
    blob_in = DATA_BLOB(len(wrapped), ctypes.cast(in_buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    ):
        raise MemoryCryptoError("CryptUnprotectData failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


class MemoryCrypto:
    """Owns the Fernet key for a memory root directory."""

    def __init__(self, root: Path, *, force_file_key: bool = False) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        env_force = os.environ.get("ARBORA_MEMORY_FILE_KEY", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        self._use_dpapi = sys.platform == "win32" and not force_file_key and not env_force
        self._key_path = self.root / ("key.dpapi" if self._use_dpapi else "key.bin")
        self._fernet = Fernet(self._load_or_create_key())

    @property
    def encrypted_at_rest(self) -> bool:
        return True

    @property
    def key_backend(self) -> str:
        return "dpapi" if self._use_dpapi else "file"

    def encrypt(self, plaintext: bytes) -> bytes:
        return self._fernet.encrypt(plaintext)

    def decrypt(self, token: bytes) -> bytes:
        try:
            return self._fernet.decrypt(token)
        except InvalidToken as exc:
            raise MemoryCryptoError("Failed to decrypt memory (wrong key or corrupt data)") from exc

    def wipe_key(self) -> None:
        if self._key_path.exists():
            self._key_path.unlink()

    def _load_or_create_key(self) -> bytes:
        if self._key_path.exists():
            wrapped = self._key_path.read_bytes()
            if self._use_dpapi:
                return _dpapi_unprotect(wrapped)
            return wrapped

        key = Fernet.generate_key()
        payload = _dpapi_protect(key) if self._use_dpapi else key
        self._write_private(self._key_path, payload)
        return key

    @staticmethod
    def _write_private(path: Path, data: bytes) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        try:
            if os.name != "nt":
                os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, path)
        try:
            if os.name != "nt":
                os.chmod(path, 0o600)
        except OSError:
            pass
