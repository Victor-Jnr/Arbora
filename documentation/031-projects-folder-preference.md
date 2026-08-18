# 031 — Projects folder preference

- **Date:** 2026-08-18
- **Commit subject:** Add projects_folder user preference for dev setup
- **Stage:** Stage 3

## Summary

Users can configure where Arbora ensures a projects folder during the developer setup journey via an opt-in `projects_folder` preference.

## Changes

- Added `projects_folder` to `UserPreferences` with `resolved_projects_folder()`
- `GoalPlanner` uses `projects_root` in dev setup; workday shutdown respects `workday_root`
- `arbora prefs set projects_folder PATH` and banner/docs updates
- Regression tests for preference load and dev setup plan paths

## Safety / permissions

- Preference is explicit opt-in only
- Dev setup still only ensures a directory — no auto clone/install

## How to verify

```powershell
arbora prefs set projects_folder C:\Users\you\Projects
arbora --provider echo --goal "set up a project" --yes
pytest tests/test_preferences.py -k projects
```
