# 028 — Briefs folder preference

- **Date:** 2026-08-17
- **Commit subject:** Add briefs_folder user preference for research output
- **Stage:** Stage 3

## Summary

Users can set where research briefs and snapshots are written via an opt-in `briefs_folder` preference. The research journey planner reads the configured path on each run.

## Changes

- Added `briefs_folder` to `UserPreferences` with `resolved_briefs_folder()`
- `GoalPlanner` accepts `briefs_root`; research journey uses it for ensure_directory, brief, and snapshot paths
- `arbora prefs set briefs_folder PATH` and `/prefs set briefs_folder PATH`
- Regression tests for preference load and research plan paths

## Safety / permissions

- Preference is explicit opt-in only
- Stored in encrypted local memory; cleared on `/wipe`

## How to verify

```powershell
arbora prefs set briefs_folder C:\Users\you\Briefs
arbora --provider echo --goal "research https://example.com" --yes
pytest tests/test_preferences.py -k briefs
```
