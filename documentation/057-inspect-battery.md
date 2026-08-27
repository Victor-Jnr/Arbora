# 057 — Battery / power inspect

- **Date:** 2026-08-27
- **Commit subject:** Inspect battery and power status behind the broker without secrets
- **Stage:** Stage 3

## Summary

Testers can ask for battery or power status and get a read-only charge, charging-state, and chassis listing. Serials and `powercfg` reports are not used. The same inspect step is added to the broader diagnose journey.

## Changes

- Desktop adapter action `inspect_battery`
- Planner journey for “battery status” / “how much battery”
- Diagnose plans also include the inspect step
- Bundled workflow pack `inspect-battery`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the listing and does not query WMI
- Output that looks like a password or key is withheld
- Does not change power plans or write battery reports

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k "battery or wifi"
arbora --provider echo --goal "battery status"
```
