# 007 — Tkinter desktop chat

- **Date:** 2026-08-07
- **Commit subject:** Add Tkinter desktop chat UI
- **Stage:** Stage 1

## Summary

Arbora now has a native Tkinter window for the plan → approve → execute loop, reusing the same broker runtime as the CLI (trusted routines, hard confirmations, dry-run, providers).

## Changes

- Added `apps/desktop_chat` Tkinter app (`arbora-ui` / `python -m apps.desktop_chat`)
- Forest/ink visual chrome with brand-forward header
- Provider selector, dry-run toggle, promote-after-success, routines/audit views
- Console script and package discovery for `apps*`
- Smoke test for app construction

## Safety / permissions

- Same permission broker path as CLI
- Hard-confirmation dialog for sensitive step classes

## How to verify

```powershell
pip install -e ".[dev]"
pytest
arbora-ui
```
