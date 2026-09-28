# 100 — Camera access inspect

- **Date:** 2026-09-28
- **Commit subject:** Inspect camera access behind the broker without per-app LastUsed dumps
- **Stage:** Stage 3

## Summary

Testers can ask whether camera access is allowed. Arbora reads the global ConsentStore webcam Value only — it does not dump LastUsed times or per-app grants. Screenshots stay `capture_screenshot`; “open camera” stays launch.

## Changes

- Desktop adapter action `inspect_camera`
- Planner journey for “camera access” / “is my camera allowed” / “webcam privacy”
- Enable / disable / screenshot / open-camera phrasing does not use this inspect
- Bundled workflow pack `inspect-camera`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Get-ChildItem on ConsentStore or return LastUsed / per-app keys
- Output that looks like a LastUsed dump or secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_camera
arbora --provider echo --goal "camera access"
```
