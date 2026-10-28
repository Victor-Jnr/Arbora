# 122 — Mouse Keys inspect

- **Date:** 2026-10-28
- **Commit subject:** Inspect Mouse Keys behind the broker without dumping pointer speed
- **Stage:** Stage 3

## Summary

Testers can ask whether Mouse Keys is on. Arbora reads MouseKeys Flags bit 0 only — it does not dump MaximumSpeed or call SystemParametersInfo. Toggle Keys stays `inspect_toggle_keys`.

## Changes

- Desktop adapter action `inspect_mouse_keys`
- Planner journey for “mouse keys” / “is mouse keys on”
- Enable / disable / Toggle Keys phrasing does not use this inspect
- Bundled workflow pack `inspect-mouse-keys`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not write Flags, call SystemParametersInfo, or dump MaximumSpeed
- Output that looks like an accessibility dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_mouse_keys
arbora --provider echo --goal "mouse keys"
```
