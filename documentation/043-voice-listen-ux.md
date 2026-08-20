# 043 — Voice listen UX polish

- **Date:** 2026-08-20
- **Commit subject:** Polish desktop voice listen so it cannot double-fire and shows confidence
- **Stage:** Stage 3

## Summary

The Voice button already filled the goal field without auto-running a plan, but a second click could start another listener and recognition ignored Windows UI culture. Listening now disables the button, uses the current UI culture, and logs confidence so testers can edit before Plan.

## Changes

- `listen_once` uses CurrentUICulture, silence timeouts, and optional confidence on stdout
- Desktop Voice button shows Listening… and ignores extra clicks until the listen finishes
- Transcript reminds testers that Plan is not auto-run

## Safety / permissions

- Still opt-in per click — no always-on microphone
- Spoken text still only fills the goal field; broker approval is unchanged

## How to verify

```powershell
pytest tests/test_voice_windows.py tests/test_desktop_chat.py
arbora-ui
# Click Voice once, speak, confirm the field fills and Plan is not auto-run
```
