# 102 — Location access inspect

- **Date:** 2026-09-28
- **Commit subject:** Inspect location access behind the broker without GPS or per-app dumps
- **Stage:** Stage 3

## Summary

Testers can ask whether location access is allowed. Arbora reads the global ConsentStore location Value only — it does not return GPS coordinates or dump per-app grants. Time zone stays `inspect_timezone`.

## Changes

- Desktop adapter action `inspect_location`
- Planner journey for “location access” / “location services” / “is location on”
- Enable / disable / GPS / “where am I” phrasing does not use this inspect
- Bundled workflow pack `inspect-location`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not query GPS, call Get-ChildItem on ConsentStore, or return LastUsed / per-app keys
- Output that looks like coordinates, a LastUsed dump, or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_location
arbora --provider echo --goal "location access"
```
