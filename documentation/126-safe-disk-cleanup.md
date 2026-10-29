# 126 — Safe disk cleanup

- **Date:** 2026-10-29
- **Commit subject:** Offer a hard-confirmed disk cleanup plan without putting deletes in diagnose
- **Stage:** Stage 3

## Summary

Testers can approve a separate cleanup after a read-only diagnostic. “Free up disk space” inspects Recycle Bin and user TEMP, then empties them only with a fresh hard confirmation. “Free disk space” stays `inspect_disk_space`. Diagnose stays read-only.

## Changes

- Planner journey for “free up disk space” / “clean up disk space” / “safe disk cleanup”
- Diagnose / inspect-disk / empty-temp / Recycle Bin phrasing does not use this plan
- `arbora validate` dry-runs the cleanup repair with hard confirmation on the preview
- Bundled workflow pack `safe-disk-cleanup`

## Safety / permissions

- Deletes are `destructive` and need a fresh hard confirmation, including inside trusted routines
- Dry-run describes Recycle Bin empty and TEMP clean and does not delete
- Does not format volumes, run chkdsk, or delete old Downloads

## How to verify

```powershell
pytest tests/test_broker_and_planner.py tests/test_workflow_packs.py tests/test_validate.py -k "disk_cleanup or disk_space or mvp"
arbora --provider echo --goal "free up disk space"
arbora validate
```
