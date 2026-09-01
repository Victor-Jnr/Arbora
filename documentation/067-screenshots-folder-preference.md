# 067 — Screenshots folder preference

- **Date:** 2026-09-01
- **Commit subject:** Add screenshots_folder user preference for capture output
- **Stage:** Stage 3

## Summary

Users can set where screenshot PNGs are written via an opt-in `screenshots_folder` preference. Unset, capture still defaults to `notes_folder/screenshots`. The screenshot journey reads the configured path on each run.

## Changes

- Added `screenshots_folder` to `UserPreferences` with `resolved_screenshots_folder()`
- `GoalPlanner` accepts `screenshots_root`; screenshot journey uses it for ensure_directory and capture paths
- `arbora prefs set screenshots_folder PATH` and `/prefs set screenshots_folder PATH`
- Regression tests for preference load, default-under-notes, and screenshot plan paths

## Safety / permissions

- Preference is explicit opt-in only
- Stored in encrypted local memory; cleared on `/wipe`
- Capture still goes through the permission broker; this plate does not add a new adapter action

## How to verify

```powershell
arbora prefs set screenshots_folder C:\Users\you\Pictures\Arbora
arbora --provider echo --goal "take a screenshot"
pytest tests/test_preferences.py -k screenshots
```
