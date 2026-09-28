# 101 — Microphone access inspect

- **Date:** 2026-09-28
- **Commit subject:** Inspect microphone access behind the broker without listening or per-app dumps
- **Stage:** Stage 3

## Summary

Testers can ask whether microphone access is allowed. Arbora reads the global ConsentStore microphone Value only — it does not listen, dump LastUsed times, or list per-app grants. Volume and default playback device stay their own inspects.

## Changes

- Desktop adapter action `inspect_microphone`
- Planner journey for “microphone access” / “is my microphone allowed” / “mic privacy”
- Enable / disable / mute / listen phrasing does not use this inspect
- Bundled workflow pack `inspect-microphone`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not capture audio, call Get-ChildItem on ConsentStore, or return LastUsed / per-app keys
- Output that looks like a LastUsed dump or secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k microphone
arbora --provider echo --goal "microphone access"
```
