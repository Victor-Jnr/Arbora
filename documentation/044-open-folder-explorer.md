# 044 — Open folder in Explorer

- **Date:** 2026-08-20
- **Commit subject:** Open a folder in Explorer after a read-only listing
- **Stage:** Stage 3

## Summary

Testers can ask Arbora to open Downloads, Desktop, or another named folder in File Explorer. The plan lists the folder first, then opens a window. Nothing is moved or deleted.

## Changes

- Files adapter action `open_in_explorer` (Windows `os.startfile`, dry-run supported)
- Planner journey for “open … in explorer” / “open folder”
- Tests for missing path, dry-run, Downloads and Desktop targets

## Safety / permissions

- Listing is `read`; opening Explorer is `mutate` (shows a window) and still needs broker approval
- Not destructive; not auto-trusted

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py -k explorer
arbora --provider echo --goal "open downloads in explorer"
```
