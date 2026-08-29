# 062 — Startup apps inspect

- **Date:** 2026-08-29
- **Commit subject:** Inspect startup apps behind the broker without changing them
- **Stage:** Stage 3

## Summary

Testers can ask which apps start with Windows and get a read-only listing of HKCU/HKLM Run names plus the user Startup folder. Entries are not enabled, disabled, or deleted. Task Scheduler is not enumerated.

## Changes

- Desktop adapter action `inspect_startup`
- Planner journey for “startup apps” / “startup folder”
- Diagnose and workday plans stay unchanged
- Bundled workflow pack `inspect-startup`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the listing and does not query the registry
- Command lines that look like secrets are withheld
- Does not write Run keys, StartupApproved bits, or scheduled tasks

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k "startup"
arbora --provider echo --goal "startup apps"
```
