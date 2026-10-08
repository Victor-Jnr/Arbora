# 113 — Nearby sharing inspect

- **Date:** 2026-10-08
- **Commit subject:** Inspect Nearby sharing behind the broker without listing nearby devices
- **Stage:** Stage 3

## Summary

Testers can ask whether Nearby sharing is off, limited to their devices, or open to everyone nearby. Arbora reads NearShareChannelUserAuthzPolicy only — it does not list nearby devices or toggle the radio. Bluetooth stays `inspect_bluetooth`.

## Changes

- Desktop adapter action `inspect_nearby_sharing`
- Planner journey for “nearby sharing” / “near share” / “is nearby sharing on”
- Enable / disable / turn on / turn off phrasing does not use this inspect
- Bundled workflow pack `inspect-nearby-sharing`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not enumerate nearby devices, dump MAC addresses, or write the CDP policy
- Output that looks like a device dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_nearby_sharing
arbora --provider echo --goal "nearby sharing"
```
