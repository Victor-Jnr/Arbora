# 020 — Persistent audit log

- **Date:** 2026-08-13
- **Commit subject:** Persist audit events in encrypted local memory across sessions
- **Stage:** Stage 2

## Summary

Audit events now survive application restarts. New events append to encrypted local memory (capped at 500) and reload when Arbora starts.

## Changes

- Added `src/arbora/core/audit_store.py` serialize/load helpers
- `AuditLog` accepts preloaded events and an `on_record` persistence hook
- `build_runtime` wires audit persistence through `LocalMemoryStore`
- Desktop audit dialog copy reflects persisted history
- Tests for cross-session load, trim cap, and memory wipe

## Safety / permissions

- Audit data stays local-first in the same encrypted memory store as routines
- `/wipe` clears persisted audit along with preferences and routines
- No change to broker authorization rules

## How to verify

```powershell
arbora --provider echo
# run a goal, exit, restart arbora, /audit — prior events should appear
pytest tests/test_audit_persistence.py
```
