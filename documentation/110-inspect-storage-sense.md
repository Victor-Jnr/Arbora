# 110 — Storage Sense inspect

- **Date:** 2026-10-06
- **Commit subject:** Inspect Storage Sense behind the broker without running cleanup
- **Stage:** Stage 3

## Summary

Testers can ask whether Storage Sense is on. Arbora reads StoragePolicy 01 only — it does not dump cleanup ages or run cleanmgr. Disk free space stays `inspect_disk_space`. Temp stays `inspect_user_temp`.

## Changes

- Desktop adapter action `inspect_storage_sense`
- Planner journey for “storage sense” / “is storage sense on”
- Enable / disable / run phrasing does not use this inspect
- Bundled workflow pack `inspect-storage-sense`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not dump cleanup ages, call cleanmgr, or write StoragePolicy
- Output that looks like a cleanup dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_storage_sense
arbora --provider echo --goal "storage sense"
```
