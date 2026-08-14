# 019 — Desktop schedule management UX

- **Date:** 2026-08-13
- **Commit subject:** Add desktop Schedules dialog for trusted-routine triggers
- **Stage:** Stage 2

## Summary

The Tkinter desktop app now exposes a Schedules dialog to list, add, remove, and enable/disable trusted-routine time triggers without using the CLI.

## Changes

- Added **Schedules** toolbar button and management dialog in `arbora-ui`
- Add flow picks a trusted routine, time, optional weekdays, and dry-run vs live
- `format_schedule_list` helper for listbox rows
- Desktop chat tests cover schedule formatting and dialog smoke

## Safety / permissions

- UI only schedules existing trusted routines (same store as `arbora schedule`)
- Live runs require an explicit checkbox; default remains dry-run
- Broker and schedule runner safety rules unchanged

## How to verify

```powershell
arbora-ui
# Promote a routine, open Schedules, add 08:00 trigger, verify list updates
pytest tests/test_desktop_chat.py -k schedule
```
