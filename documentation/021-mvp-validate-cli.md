# 021 — MVP validate CLI

- **Date:** 2026-08-15
- **Commit subject:** Add arbora validate for Stage 2 MVP exit-criteria checks
- **Stage:** Stage 3

## Summary

Early testers can now run `arbora validate` to dry-run the five MVP exit criteria in one command: three priority journeys, trust/audit/revoke flow, and local-first memory defaults.

## Changes

- Added `src/arbora/cli/validate.py` with five automated checks
- `arbora validate` (+ `--json`, `--memory-dir`) returns exit code 0/1
- Banner mentions the new command
- Regression tests in `tests/test_validate.py`

## Safety / permissions

- All journey checks use dry-run only
- Trust check promotes and revokes inside an isolated memory directory
- No live side effects

## How to verify

```powershell
arbora validate
arbora validate --json
pytest tests/test_validate.py
```
