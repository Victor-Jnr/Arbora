# 024 — Audit export

- **Date:** 2026-08-16
- **Commit subject:** Add audit export to JSON via CLI and desktop UI
- **Stage:** Stage 3

## Summary

Testers and reviewers can export the persisted audit log as JSON from the CLI or the desktop Audit dialog.

## Changes

- Added `export_audit_payload` helper in `audit_store.py`
- `arbora audit export` (+ `--out`, `--limit`) and `/audit export [path]`
- Desktop Audit dialog **Export JSON** button with save dialog
- Regression tests in `tests/test_audit_export.py`

## Safety / permissions

- Export is read-only; no broker side effects
- Exported data stays local until the user moves the file

## How to verify

```powershell
arbora audit export --out audit.json
arbora-ui
# Audit → Export JSON
pytest tests/test_audit_export.py
```
