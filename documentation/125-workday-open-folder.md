# 125 — Workday start opens the work folder

- **Date:** 2026-10-29
- **Commit subject:** Open the workday folder after writing the morning briefing
- **Stage:** Stage 3

## Summary

“Start my workday” now lists and opens the workday folder in Explorer after writing the morning briefing. Launching and focusing Notepad halt the plan if they fail. “Open my workday folder” stays the short list-then-open journey.

## Changes

- Workday start plan: `list_directory` + `open_in_explorer` after the briefing
- `halt_on_failure` on launch and focus
- Bundled workflow pack `start-workday`

## Safety / permissions

- `open_in_explorer` is `mutate` (opens a window). No deletes.
- Diagnose and Downloads-in-Explorer phrasing do not use this ritual
- Dry-run describes Explorer open and does not launch a window

## How to verify

```powershell
pytest tests/test_broker_and_planner.py tests/test_preferences.py tests/test_workflow_packs.py -k "workday or start_workday"
arbora --provider echo --goal "start my workday"
```
