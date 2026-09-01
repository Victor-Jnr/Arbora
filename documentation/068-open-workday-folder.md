# 068 — Open workday folder in Explorer

- **Date:** 2026-09-01
- **Commit subject:** Open the workday folder in Explorer as a named journey
- **Stage:** Stage 3

## Summary

Testers can ask Arbora to open the workday folder in File Explorer without running the full start-workday ritual. The plan lists the folder first, then opens a window. The path follows the opt-in `workday_folder` preference.

## Changes

- Planner named journey for “open my workday folder” / “open workday in explorer”
- `_folder_path_from_goal` resolves `workday` to the configured workday root
- Bundled workflow pack `open-workday-folder`
- Tests: explorer vs start-workday, preference path, pack match

## Safety / permissions

- Listing is `read`; opening Explorer is `mutate` (shows a window) and still needs broker approval
- Not destructive; does not launch the workday setup plan
- Start/end workday phrasing is unchanged

## How to verify

```powershell
pytest tests/test_broker_and_planner.py tests/test_preferences.py tests/test_workflow_packs.py -k "workday"
arbora --provider echo --goal "open my workday folder"
```
