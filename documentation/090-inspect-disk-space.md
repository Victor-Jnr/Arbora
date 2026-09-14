# 090 — Logical disk free space inspect

- **Date:** 2026-09-14
- **Commit subject:** Inspect local disk free space behind the broker without formatting or chkdsk
- **Stage:** Stage 3

## Summary

Testers can ask how much disk is free. Arbora reads Size and FreeSpace for local fixed volumes only — it does not format, run chkdsk, or wipe a drive. Broader “diagnose disk space” still uses the existing diagnostic journey.

## Changes

- Desktop adapter action `inspect_disk_space`
- Planner journey for “free disk space” / “how much disk is free” / “inspect disk space”
- Diagnose / format / largest-folder phrasing does not use this inspect
- Bundled workflow pack `inspect-disk-space`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Format-Volume, Clear-Disk, or chkdsk
- Output that looks like a format/wipe command or secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k disk_space
arbora --provider echo --goal "free disk space"
```
