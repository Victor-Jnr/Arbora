# 071 — Wallpaper path inspect

- **Date:** 2026-09-04
- **Commit subject:** Inspect the desktop wallpaper path behind the broker without changing it
- **Stage:** Stage 3

## Summary

Testers can ask for the desktop wallpaper and get a read-only path plus fill/fit/center/tile style. Arbora does not change the wallpaper or open personalization settings.

## Changes

- Desktop adapter action `inspect_wallpaper`
- Planner journey for “wallpaper” / “desktop background”
- Set/change phrasing does not use this inspect
- Bundled workflow pack `inspect-wallpaper`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call Get-ItemProperty
- Does not run Set-ItemProperty, SystemParametersInfo SPI_SETDESKWALLPAPER, or dump image bytes
- Output that looks like a password or key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k wallpaper
arbora --provider echo --goal "wallpaper"
```
