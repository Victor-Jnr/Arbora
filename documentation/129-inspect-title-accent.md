# 129 — Title-bar accent inspect

- **Date:** 2026-11-01
- **Commit subject:** Inspect title-bar accent behind the broker without dumping ColorizationColor
- **Stage:** Stage 3

## Summary

Testers can ask whether accent color is on title bars. Arbora reads DWM ColorPrevalence only — it does not dump ColorizationColor or Personalize AccentColor. Start and taskbar accent stays `inspect_start_accent`.

## Changes

- Desktop adapter action `inspect_title_accent`
- Planner journey for “accent on title bars” / “show accent color on title bar”
- Enable / disable / Start / taskbar phrasing does not use this inspect
- Bundled workflow pack `inspect-title-accent`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not write DWM ColorPrevalence, dump ColorizationColor, or dump AccentColor
- Output that looks like an accent dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_title_accent
arbora --provider echo --goal "accent on title bars"
```
