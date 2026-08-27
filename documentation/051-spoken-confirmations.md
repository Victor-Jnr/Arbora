# 051 — Opt-in spoken confirmations

- **Date:** 2026-08-22
- **Commit subject:** Add opt-in spoken plan read-back behind the broker
- **Stage:** Stage 3

## Summary

Testers can ask Arbora to read a short confirmation aloud, or opt in via `spoken_confirmations` so each plan prepends a TTS read-back. Speech still goes through the permission broker. The microphone is not opened.

## Changes

- `speak_text` helper (System.Speech synthesizer) and desktop adapter action
- Planner journey for “read this back: …”
- Opt-in preference `spoken_confirmations` prepends a speak step to other plans
- Bundled workflow pack `speak-confirmation`

## Safety / permissions

- Speak is `mutate` — broker approval, not hard confirmation
- Dry-run prints the phrase and does not play audio
- No always-on microphone; this is output only

## How to verify

```powershell
pytest tests/test_voice_windows.py tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_preferences.py tests/test_workflow_packs.py -k "speak or spoken or confirmation"
arbora --provider echo --goal "read this back: start my workday"
arbora prefs set spoken_confirmations on
```
