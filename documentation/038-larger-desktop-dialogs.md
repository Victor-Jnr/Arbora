# 038 — Larger desktop Trust dialogs

- **Date:** 2026-08-19
- **Commit subject:** Enlarge arbora-ui dialogs so action buttons stay visible
- **Stage:** Stage 3

## Summary

Audit, Memory, Routines, Schedules, Setup, History, and related modals were too short for typical Windows scaling, hiding Close/Export buttons. They now open larger, with a matching minimum size.

## Changes

- Added `configure_dialog` helper (geometry + minsize + resizable)
- Enlarged Setup, History, Routines, Schedules, Audit, Memory, and name/add-schedule prompts
- Tests assert Audit/Memory dialog minsize

## Safety / permissions

- None — layout only; broker behaviour unchanged

## How to verify

```powershell
arbora-ui
# Audit, Memory, Routines — buttons at the bottom should be visible
pytest tests/test_desktop_chat.py -k dialog
```
