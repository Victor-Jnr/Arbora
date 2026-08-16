# 026 — Startup schedule runner

- **Date:** 2026-08-16
- **Commit subject:** Add opt-in startup schedule runner for arbora-ui
- **Stage:** Stage 3

## Summary

Users can opt in to running due trusted-routine schedules when `arbora-ui` starts. Results are logged in the chat pane; each schedule still respects its dry-run/live setting and trusted-routine safety rules.

## Changes

- Added `run_due_schedules_on_start` user preference
- `arbora prefs set run_schedules_on_start on|off` and `/prefs set run_schedules_on_start on`
- Desktop app runs due schedules in a background thread on startup when enabled
- Preference regression tests updated

## Safety / permissions

- Opt-in only — default is off
- Uses existing schedule runner (trusted match, no hard-confirmation plans)
- Schedules keep their per-entry dry-run default unless overridden at run time

## How to verify

```powershell
arbora prefs set run_schedules_on_start on
arbora-ui
# After promoting a routine and adding a due schedule, restart arbora-ui
pytest tests/test_preferences.py -k schedules
```
