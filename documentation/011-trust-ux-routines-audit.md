# 011 — Trust UX for routines and audit

- **Date:** 2026-08-08
- **Commit subject:** Add trusted-routine revoke and audit dialogs to desktop UI
- **Stage:** Stage 2

## Summary

The desktop UI now opens dedicated dialogs for trusted routines (inspect + revoke with confirm) and the session audit log, instead of dumping into the transcript only.

## Changes

- Routines dialog: list, detail, revoke selected, persist after revoke
- Audit dialog: timestamped events with payload details
- Tests for dialog contents and revoke path
- Marked P0#3 done in NEXT

## Safety / permissions

- Revoke requires an explicit yes confirmation
- No broker bypass; revoke still records `routine_revoked` in the audit log

## How to verify

```powershell
arbora-ui
# Promote a routine, then Routines → Revoke selected
# Audit → view recent events
pytest tests/test_desktop_chat.py
```
