# 033 — Downloads folder preference

- **Date:** 2026-08-18
- **Commit subject:** Add downloads_folder user preference for organise journeys
- **Stage:** Stage 3

## Summary

Users can configure which folder Arbora organises and lists by default via an opt-in `downloads_folder` preference, instead of always using `~/Downloads`.

## Changes

- Added `downloads_folder` to `UserPreferences` with `resolved_downloads_folder()`
- Organise, default file-list, and fallback context plans use the configured root
- `arbora prefs set downloads_folder PATH` and banner/docs updates
- Regression tests for preference load and organise plan paths

## Safety / permissions

- Preference is explicit opt-in only
- Organise still previews before applying moves and records an undo batch
- Bundled workflow packs keep their static `~/Downloads` paths unless overridden by the user

## How to verify

```powershell
arbora prefs set downloads_folder C:\Users\you\Inbox
arbora --provider echo --goal "organise my downloads" --yes
pytest tests/test_preferences.py -k downloads
```
