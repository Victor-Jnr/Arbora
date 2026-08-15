# 022 — Opt-in user preferences

- **Date:** 2026-08-15
- **Commit subject:** Add opt-in user preferences in encrypted local memory
- **Stage:** Stage 3

## Summary

Users can now set explicit defaults in encrypted local memory: dry-run mode, preferred provider, and workday folder. Preferences are opt-in only — nothing is inferred silently.

## Changes

- Added `src/arbora/preferences/` store with `UserPreferences`
- `arbora prefs list|set` and interactive `/prefs` commands
- `build_runtime` applies saved provider and workday folder to the planner
- Desktop UI reads dry-run and provider defaults on startup
- Regression tests in `tests/test_preferences.py`

## Safety / permissions

- Preferences are stored in the same encrypted memory store as routines
- `/wipe` clears preferences with everything else
- Cloud provider still requires explicit API key configuration

## How to verify

```powershell
arbora prefs set dry_run on
arbora prefs set workday_folder C:\Users\you\Work
arbora prefs list
pytest tests/test_preferences.py
```
