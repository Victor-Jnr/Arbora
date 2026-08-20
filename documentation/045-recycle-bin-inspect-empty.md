# 045 — Recycle Bin inspect and empty

- **Date:** 2026-08-20
- **Commit subject:** Inspect the Recycle Bin before emptying it with hard confirmation
- **Stage:** Stage 3

## Summary

Asking what is in the Recycle Bin is a read-only listing. Asking to empty it lists first, then offers a destructive empty step that still needs a fresh hard confirmation. This is the “preview then dangerous action” pattern testers already know from organise-downloads.

## Changes

- Files adapter: `inspect_recycle_bin` (read) and `empty_recycle_bin` (destructive)
- Planner journey for “recycle bin” vs “empty the recycle bin”
- Tests for dry-run, read-only inspect, and hard-confirm empty

## Safety / permissions

- Inspect is `read`
- Empty is `destructive` — broker hard confirmation; not auto-trusted
- Dry-run never calls `Clear-RecycleBin`

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py -k recycle
arbora --provider echo --goal "what's in the recycle bin"
arbora --provider echo --goal "empty the recycle bin"
```
