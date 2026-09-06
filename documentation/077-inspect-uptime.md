# 077 — Uptime inspect

- **Date:** 2026-09-06
- **Commit subject:** Inspect system uptime behind the broker without shutting down
- **Stage:** Stage 3

## Summary

Testers can ask how long the PC has been on and get read-only uptime plus last boot time. Arbora does not shut down or restart the machine.

## Changes

- Desktop adapter action `inspect_uptime`
- Planner journey for “uptime” / “last boot” / “how long has the pc been on”
- Shutdown/restart phrasing does not use this inspect; idle stays on `inspect_idle`
- Bundled workflow pack `inspect-uptime`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call WMI
- Does not call Shutdown-Computer, Restart-Computer, or Stop-Computer
- Output that looks like a password or key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k uptime
arbora --provider echo --goal "uptime"
```
