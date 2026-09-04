# 072 — Idle time inspect

- **Date:** 2026-09-04
- **Commit subject:** Inspect last-input idle time behind the broker without injecting input
- **Stage:** Stage 3

## Summary

Testers can ask how long the PC has been idle and get a read-only last-input duration. Arbora does not inject keys or mouse events, and does not change power settings.

## Changes

- Desktop adapter action `inspect_idle`
- Planner journey for “idle time” / “how long have i been idle”
- Bundled workflow pack `inspect-idle`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call GetLastInputInfo
- Does not call BlockInput, SendInput, mouse_event, or keybd_event
- Output that looks like a password or key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k idle
arbora --provider echo --goal "idle time"
```
