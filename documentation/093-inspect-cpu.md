# 093 — CPU load inspect

- **Date:** 2026-09-20
- **Commit subject:** Inspect CPU name, cores, and load behind the broker without dumping processes
- **Stage:** Stage 3

## Summary

Testers can ask how busy the CPU is. Arbora reads Win32_Processor name, logical processor count, and LoadPercentage only — it does not dump processes or change affinity. Broader “slow PC” still uses the existing diagnostic journey.

## Changes

- Desktop adapter action `inspect_cpu`
- Planner journey for “cpu load” / “cpu usage” / “inspect cpu”
- Diagnose / slow-PC / affinity phrasing does not use this inspect
- Bundled workflow pack `inspect-cpu`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Get-Process, Set-Process, or change processor affinity
- Output that looks like a process dump, affinity change, or secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_cpu
arbora --provider echo --goal "cpu load"
```
