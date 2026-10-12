# 120 — High contrast inspect

- **Date:** 2026-10-12
- **Commit subject:** Inspect high contrast behind the broker without changing the theme
- **Stage:** Stage 3

## Summary

Testers can ask whether high contrast is on. Arbora reads HighContrast Flags bit 0 only — it does not dump DefaultScheme or write AppsUseLightTheme. Dark/light theme stays `inspect_theme`.

## Changes

- Desktop adapter action `inspect_high_contrast`
- Planner journey for “high contrast” / “is high contrast on”
- Enable / disable / dark-mode phrasing does not use this inspect
- Bundled workflow pack `inspect-high-contrast`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not write Flags, dump DefaultScheme, or change AppsUseLightTheme
- Output that looks like a theme dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_high_contrast
arbora --provider echo --goal "high contrast"
```
