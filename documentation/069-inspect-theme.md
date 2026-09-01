# 069 — Dark / light theme inspect

- **Date:** 2026-09-01
- **Commit subject:** Inspect the Windows light/dark theme behind the broker without changing it
- **Stage:** Stage 3

## Summary

Testers can ask whether Windows is in dark or light mode and get a read-only report of app and system chrome settings. Arbora does not change the theme, accent color, or wallpaper.

## Changes

- Desktop adapter action `inspect_theme`
- Planner journey for “dark mode” / “what's my theme”
- Set/change phrasing does not use this inspect
- Bundled workflow pack `inspect-theme`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call Get-ItemProperty
- Does not run Set-ItemProperty, SystemParametersInfo, or open personalization settings
- Output that looks like a password or key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k theme
arbora --provider echo --goal "dark mode"
```
