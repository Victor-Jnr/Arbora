# 032 — Recent goal history

- **Date:** 2026-08-18
- **Commit subject:** Add recent goal history in encrypted local memory
- **Stage:** Stage 3

## Summary

Arbora now remembers recent chat goals locally (up to 20) so testers can reuse common requests from the CLI or desktop UI.

## Changes

- Added `src/arbora/memory/goal_history.py` record/list helpers
- Interactive CLI `/history` and automatic recording when a goal is planned
- Desktop **History** button opens a picker that refills the goal field
- Regression tests in `tests/test_goal_history.py`

## Safety / permissions

- History stays in encrypted local memory; cleared on `/wipe`
- Slash commands are not recorded
- History does not auto-run goals — user still plans and approves

## How to verify

```powershell
arbora --provider echo
# enter a goal, then /history
arbora-ui
# History → pick a prior goal → Plan
pytest tests/test_goal_history.py
```
