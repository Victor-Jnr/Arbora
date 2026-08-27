# 054 — Network / wifi inspect

- **Date:** 2026-08-24
- **Commit subject:** Inspect adapters and IPv4 behind the broker without secrets
- **Stage:** Stage 3

## Summary

Testers can ask for wifi/network status and get a read-only listing of adapters, IPv4 addresses, and connection profiles. Wi-Fi keys are never requested. The same inspect step is added to the broader diagnose journey.

## Changes

- Desktop adapter action `inspect_network`
- Planner journey for “wifi status” / “what’s my ip”
- Diagnose plans also include the inspect step
- Bundled workflow pack `inspect-network`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the listing and does not query adapters
- Output that looks like a Wi-Fi key is withheld
- Does not run `netsh wlan show profile key=clear` or change adapters

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k "network or wifi"
arbora --provider echo --goal "wifi status"
```
