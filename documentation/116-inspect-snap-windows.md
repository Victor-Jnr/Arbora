# 116 — Snap windows inspect

- **Date:** 2026-10-11
- **Commit subject:** Inspect Snap windows behind the broker without changing snap layouts
- **Stage:** Stage 3

## Summary

Testers can ask whether Snap windows is on. Arbora reads WindowArrangementActive only — it does not write snap layouts or change display mode. Attached displays stay `inspect_display`.

## Changes

- Desktop adapter action `inspect_snap_windows`
- Planner journey for “snap windows” / “snap assist” / “is snap on”
- Enable / disable / screenshot phrasing does not use this inspect
- Bundled workflow pack `inspect-snap-windows`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call SetDisplayConfig, write WindowArrangementActive, or dump snap layouts
- Output that looks like a display-mode dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_snap_windows
arbora --provider echo --goal "snap windows"
```
