# 040 — Largest-folder disk journey

- **Date:** 2026-08-19
- **Commit subject:** Add a read-only largest-folder scan and stop treating Format-Table as destructive
- **Stage:** Stage 3

## Summary

Asking which folder uses the most space on C: used to fall through to Ollama, which proposed a full-drive walk with a 60s timeout and marked it destructive because `Format-Table` contains `format-`. Arbora now matches that goal as a read-only journey with a 300s top-level folder size scan.

## Changes

- Planner: largest-folder journey (drive used/free, then size each immediate subfolder via FileSystemObject)
- Planner: `format-` no longer matches `Format-Table`; only real deletes/format-volume/shutdown count as destructive
- Provider plans that walk a drive for sizes get `timeout_seconds` raised to at least 300
- Bundled workflow pack `largest-folders`
- Tests for the user phrasing, D: drive, Format-Table, and Remove-Item
- `docs/NEXT.md` P9 plate 28

## Safety / permissions

- Folder sizing is `read` — no hard confirmation
- Recycle Bin / System Volume Information / Recovery are skipped
- The scan does not delete or move files; it can take several minutes on a full drive

## How to verify

```powershell
pytest tests/test_broker_and_planner.py tests/test_workflow_packs.py
arbora --provider echo --goal "what folder is using the most storage on C"
```
