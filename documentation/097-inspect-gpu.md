# 097 — GPU inspect

- **Date:** 2026-09-24
- **Commit subject:** Inspect GPU name and status behind the broker without device IDs or mode changes
- **Stage:** Stage 3

## Summary

Testers can ask which graphics adapter is installed. Arbora reads Win32_VideoController name and Status only — it does not dump PNPDeviceID and does not change display mode. Screen resolution stays `inspect_display`.

## Changes

- Desktop adapter action `inspect_gpu`
- Planner journey for “gpu status” / “graphics card” / “which gpu”
- Resolution / monitor / display-mode phrasing does not use this inspect
- Bundled workflow pack `inspect-gpu`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call SetDisplayConfig or ChangeDisplaySettings, and does not dump PNPDeviceID
- Output that looks like a device-ID dump, display-mode write, or secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_gpu
arbora --provider echo --goal "gpu status"
```
