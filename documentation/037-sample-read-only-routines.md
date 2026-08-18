# 037 — Sample read-only trusted routines

- **Date:** 2026-08-19
- **Commit subject:** Seed read-only sample trusted routines on first run
- **Stage:** Stage 3

## Summary

Trusted routines stay empty until a plan is promoted — that is intentional. First-run testers now get two **read-only** samples (`list-downloads`, `disk-diagnose`) so Routines is not a blank dialog. Mutate and hard-confirmation journeys are never auto-trusted.

## Changes

- Added `src/arbora/core/sample_routines.py` with a one-shot seed flag in local memory
- `PermissionBroker.promote_plan` records trust without executing
- CLI and `arbora-ui` pass `seed_samples=True` into `build_runtime`
- Regression tests in `tests/test_sample_routines.py`

## Safety / permissions

- Samples are inspect-only (`Sensitivity.READ`)
- Existing user routines are never overwritten
- Users can revoke samples; the seed flag prevents them from coming back until `/wipe`
- Hard-confirmation classes still apply if a later matching plan adds them

## How to verify

```powershell
arbora-ui
# Routines → list-downloads and disk-diagnose
arbora --provider echo
/routines
pytest tests/test_sample_routines.py
```
