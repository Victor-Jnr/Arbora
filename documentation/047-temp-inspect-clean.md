# 047 — Temp inspect and clean

- **Date:** 2026-08-21
- **Commit subject:** Inspect user TEMP before deleting top-level files with hard confirmation
- **Stage:** Stage 3

## Summary

Asking what is in TEMP is a read-only listing of top-level files in the user `%TEMP%` folder. Asking to clean it inspects first, then deletes those files only after a fresh hard confirmation. Subfolders are never removed.

## Changes

- Files adapter: `inspect_user_temp` (read) and `clean_user_temp` (destructive)
- Planner journey for “what’s in temp” vs “empty temp”
- Bundled workflow pack `inspect-temp`
- Refuses the Windows directory if `TEMP` points there

## Safety / permissions

- Inspect is `read`
- Clean is `destructive` — broker hard confirmation; not auto-trusted
- Only the current user’s TEMP; only top-level files; directories stay
- Dry-run never unlinks files

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k temp
arbora --provider echo --goal "what's in temp"
arbora --provider echo --goal "empty temp"
```
