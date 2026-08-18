# 034 — Save-note journey

- **Date:** 2026-08-18
- **Commit subject:** Add save-note journey with notes_folder preference
- **Stage:** Stage 3

## Summary

Testers can ask Arbora to save a local note. Notes go to an opt-in `notes_folder` (default `~/ArboraNotes`) as a timestamped text file after plan approval.

## Changes

- Added `notes_folder` to `UserPreferences` with `resolved_notes_folder()`
- Planner matches “save a note” / “jot down” and writes via the files adapter
- `arbora prefs set notes_folder PATH` and banner/docs updates
- Regression tests for preference, phrasing, and live write

## Safety / permissions

- Preference is explicit opt-in only
- Write is mutate-class and still goes through the permission broker
- Filenames are timestamped so existing notes are not overwritten
- Notes stay local; nothing is uploaded

## How to verify

```powershell
arbora prefs set notes_folder C:\Users\you\Notes
arbora --provider echo --goal "save a note about buying milk" --yes --execute
pytest tests/test_preferences.py -k notes
```
