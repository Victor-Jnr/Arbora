# 035 — Local memory export

- **Date:** 2026-08-18
- **Commit subject:** Add local memory JSON export via CLI and desktop UI
- **Stage:** Stage 3

## Summary

Testers can export decrypted local memory (preferences, routines, history, audit) as JSON from the CLI or a desktop Memory dialog. Encryption key files are never included.

## Changes

- Added `export_memory_payload` and `memory_status_rows` in the memory store
- `arbora memory status` and `arbora memory export` (`--out`) plus `/memory export [path]`
- Desktop **Memory** dialog with Export JSON
- Regression tests in `tests/test_memory_export.py`

## Safety / permissions

- Export is read-only; no broker side effects
- Key material (`key.bin` / DPAPI wrap) is not written to the JSON
- Exported data stays local until the user moves the file
- `/wipe` still erases memory independently of export

## How to verify

```powershell
arbora memory status
arbora memory export --out memory.json
arbora-ui
# Memory → Export JSON
pytest tests/test_memory_export.py
```
