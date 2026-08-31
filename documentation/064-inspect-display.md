# 064 — Display / resolution inspect

- **Date:** 2026-08-31
- **Commit subject:** Inspect attached displays and resolutions behind the broker
- **Stage:** Stage 3

## Summary

Testers can ask for screen or monitor resolution and get a read-only listing of attached displays (bounds, primary flag, working area). Display mode, DPI, and wallpaper are not changed.

## Changes

- Desktop adapter action `inspect_display`
- Planner journey for “screen resolution” / “how many monitors”
- Does not steal screenshot or diagnose journeys
- Bundled workflow pack `inspect-display`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the listing and does not query screens
- Does not call ChangeDisplaySettings / SetDisplayConfig
- Output that looks like a password or key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k display
arbora --provider echo --goal "screen resolution"
```
