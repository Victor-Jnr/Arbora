# 128 — Start/taskbar accent inspect

- **Date:** 2026-11-01
- **Commit subject:** Inspect Start and taskbar accent behind the broker without dumping AccentColor
- **Stage:** Stage 3

## Summary

Testers can ask whether accent color is on Start and the taskbar. Arbora reads Personalize ColorPrevalence only — it does not dump AccentColor or DWM ColorizationColor. Title-bar accent stays a later inspect.

## Changes

- Desktop adapter action `inspect_start_accent`
- Planner journey for “accent on start” / “show accent color on taskbar”
- Enable / disable / title-bar / dark-mode phrasing does not use this inspect
- Bundled workflow pack `inspect-start-accent`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not write ColorPrevalence, dump AccentColor, or dump ColorizationColor
- Output that looks like an accent dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_start_accent
arbora --provider echo --goal "accent on start"
```
