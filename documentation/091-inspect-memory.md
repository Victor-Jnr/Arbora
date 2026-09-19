# 091 — Physical RAM inspect

- **Date:** 2026-09-20
- **Commit subject:** Inspect physical RAM free and total behind the broker without dumping processes
- **Stage:** Stage 3

## Summary

Testers can ask how much RAM is free. Arbora reads TotalVisibleMemorySize and FreePhysicalMemory only — it does not dump processes or working-set lists. Broader “memory usage” still uses the existing diagnostic journey.

## Changes

- Desktop adapter action `inspect_memory`
- Planner journey for “how much ram” / “inspect memory” / “free ram”
- Diagnose / process-dump phrasing does not use this inspect
- Bundled workflow pack `inspect-memory`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Get-Process or list working sets
- Output that looks like a process dump or secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k memory
arbora --provider echo --goal "how much ram"
```
