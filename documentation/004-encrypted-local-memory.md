# 004 — Encrypted local memory

- **Date:** 2026-08-05
- **Commit subject:** Encrypt local memory at rest with Fernet and DPAPI key wrap
- **Stage:** Stage 1

## Summary

Personal preferences and trusted-routine metadata are now stored encrypted on disk. Fernet seals the payload; on Windows the Fernet key is wrapped with DPAPI so a copied key file is useless on another machine/user.

## Changes

- Added `memory/crypto.py` (Fernet + Windows DPAPI / file-key fallback)
- Reworked `LocalMemoryStore` to write `preferences.enc` instead of plaintext JSON
- Auto-migrate legacy `preferences.json` into encrypted form
- CLI `/memory` status and `/wipe` to erase local memory
- Added `cryptography` dependency
- Tests for roundtrip, migration, and wipe

## Safety / permissions

- Memory remains local-first; encryption-at-rest does not replace endpoint security
- Wipe removes ciphertext and rotates the key without removing the application

## How to verify

```powershell
pip install -e ".[dev]"
pytest
arbora --provider echo
# then: /memory
```
