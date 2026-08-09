# 012 — Emergency stop for in-flight plans

- **Date:** 2026-08-09
- **Commit subject:** Add emergency stop for in-flight plan execution
- **Stage:** Stage 2

## Summary

The permission broker now honours an emergency stop between steps, and the desktop UI exposes a Stop control while Approve & run is in flight.

## Changes

- Broker: `request_stop` / `clear_stop` / `is_executing`; skip remaining steps and audit `plan_stopped`
- Desktop UI: background execution + danger-styled Stop button
- Stopped plans do not promote to trusted routines
- Tests for skip + no-promote behaviour

## Safety / permissions

- Stop is fail-closed for remaining steps (recorded as skipped, not executed)
- Does not interrupt a single adapter call already in progress; halt is between steps

## How to verify

```powershell
pytest tests/test_emergency_stop.py
arbora-ui
# Plan a multi-step goal → Approve & run → Stop
```
