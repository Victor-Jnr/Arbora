# 056 — Empty old Downloads

- **Date:** 2026-08-27
- **Commit subject:** Preview then delete old Downloads files with hard confirmation
- **Stage:** Stage 3

## Summary

Testers can list top-level files in the Downloads folder that are older than N days (default 30). Asking to delete them inspects first, then unlinks only those files after a fresh hard confirmation. Subfolders are never removed. Drive roots and the Windows directory are refused.

## Changes

- Files adapter: `inspect_old_files` (read) and `delete_old_files` (destructive)
- Planner journey for “old files in downloads” vs “delete downloads older than N days”
- Bundled workflow pack `inspect-old-downloads` (inspect only)

## Safety / permissions

- Inspect is `read`
- Delete is `destructive` — broker hard confirmation; not auto-trusted
- Top-level files only; directories stay
- Dry-run never unlinks files
- Does not empty all of Downloads — only files older than N days

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k "old_files or old_download"
arbora --provider echo --goal "old files in downloads"
arbora --provider echo --goal "delete downloads older than 30 days"
```
