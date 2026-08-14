# 018 — Scheduled trusted routines

- **Date:** 2026-08-13
- **Commit subject:** Add scheduled trusted routines with arbora schedule CLI
- **Stage:** Stage 2

## Summary

Trusted routines can now fire on optional daily time triggers. Schedules only run goals that still match the stored trusted fingerprint, default to dry-run, and refuse hard-confirmation plans.

## Changes

- Added `src/arbora/schedules/` store, runner, and due-time checks
- Added `arbora schedule` subcommands: `list`, `add`, `remove`, `run-due`, `list-routines`
- Interactive CLI `/schedules` lists saved triggers
- Tests for parse, due logic, trusted match, and CLI smoke

## Safety / permissions

- Schedules reference trusted routine ids only — no free-form unsupervised goals
- Plan fingerprint must still match the trusted routine or the run is skipped
- Hard-confirmation steps block scheduled execution
- Default schedule mode is dry-run; `--execute` required for live runs

## How to verify

```powershell
arbora --provider echo --yes --promote list-downloads --goal "list files in ~/Downloads"
arbora schedule list-routines
arbora schedule add ROUTINE_ID 08:00 --days mon,fri
arbora schedule run-due --force SCHEDULE_ID
pytest tests/test_schedules.py
```
