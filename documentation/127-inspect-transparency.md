# 127 — Transparency inspect

- **Date:** 2026-11-01
- **Commit subject:** Inspect transparency effects behind the broker without changing the theme
- **Stage:** Stage 3

## Summary

Testers can ask whether transparency effects are on. Arbora reads EnableTransparency only — it does not dump AppsUseLightTheme or AccentColor. Dark/light theme stays `inspect_theme`.

## Changes

- Desktop adapter action `inspect_transparency`
- Planner journey for “transparency effects” / “is transparency on”
- Enable / disable / dark-mode phrasing does not use this inspect
- Bundled workflow pack `inspect-transparency`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not write EnableTransparency, dump AppsUseLightTheme, or dump AccentColor
- Output that looks like a theme dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_transparency
arbora --provider echo --goal "transparency effects"
```
