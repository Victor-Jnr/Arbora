# 121 — Toggle Keys inspect

- **Date:** 2026-10-28
- **Commit subject:** Inspect Toggle Keys behind the broker without changing accessibility flags
- **Stage:** Stage 3

## Summary

Testers can ask whether Toggle Keys is on. Arbora reads ToggleKeys Flags bit 0 only — it does not dump StickyKeys or call SystemParametersInfo. Sticky Keys stays `inspect_sticky_keys`.

## Changes

- Desktop adapter action `inspect_toggle_keys`
- Planner journey for “toggle keys” / “is toggle keys on”
- Enable / disable / Sticky Keys phrasing does not use this inspect
- Bundled workflow pack `inspect-toggle-keys`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not write Flags, call SystemParametersInfo, or dump StickyKeys
- Output that looks like an accessibility dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_toggle_keys
arbora --provider echo --goal "toggle keys"
```
