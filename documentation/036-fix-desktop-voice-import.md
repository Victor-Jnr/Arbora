# 036 — Fix desktop voice import

- **Date:** 2026-08-18
- **Commit subject:** Import Windows voice helpers in arbora-ui
- **Stage:** Stage 3

## Summary

Clicking **Voice** in `arbora-ui` crashed with `NameError` because `voice_input_available` and `listen_once` were used without being imported.

## Changes

- Imported `listen_once` and `voice_input_available` in `apps/desktop_chat/app.py`
- Added a regression test that the desktop module exposes those helpers

## Safety / permissions

- None — import-only fix; voice remains opt-in per click and still fills the goal field without auto-running

## How to verify

```powershell
arbora-ui
# Click Voice — should listen instead of raising NameError
pytest tests/test_desktop_chat.py -k voice
```
