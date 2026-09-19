# 092 — Power plan inspect

- **Date:** 2026-09-20
- **Commit subject:** Inspect the active Windows power plan behind the broker without changing it
- **Stage:** Stage 3

## Summary

Testers can ask which power plan is active. Arbora reads the IsActive Win32_PowerPlan name only — it does not call powercfg /setactive or change sleep/hibernate settings.

## Changes

- Desktop adapter action `inspect_power_plan`
- Planner journey for “power plan” / “what power plan” / “inspect power plan”
- Set / change / hibernate phrasing does not use this inspect
- Bundled workflow pack `inspect-power-plan`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call powercfg /setactive, /change, or hibernate on
- Output that looks like a scheme-change command or secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k power_plan
arbora --provider echo --goal "power plan"
```
