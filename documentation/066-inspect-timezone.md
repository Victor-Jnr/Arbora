# 066 — Time zone / locale inspect

- **Date:** 2026-08-31
- **Commit subject:** Inspect the time zone and locale behind the broker without changing them
- **Stage:** Stage 3

## Summary

Testers can ask for the time zone or locale and get a read-only Id, UTC offset, user culture, and system locale. Arbora does not change the clock, timezone, or regional format.

## Changes

- Desktop adapter action `inspect_timezone`
- Planner journey for “time zone” / “what's my locale”
- Set/change phrasing does not use this inspect
- Bundled workflow pack `inspect-timezone`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call Get-TimeZone
- Does not run tzutil /s, Set-TimeZone, Set-Culture, or Set-WinSystemLocale
- Output that looks like a password or key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k timezone
arbora --provider echo --goal "time zone"
```
