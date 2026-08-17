# 029 — Windows voice input

- **Date:** 2026-08-17
- **Commit subject:** Add opt-in Windows voice goal entry in arbora-ui
- **Stage:** Stage 3

## Summary

`arbora-ui` now has a **Voice** button that listens for a spoken goal using Windows System.Speech (PowerShell). Recognized text fills the goal field for the usual plan→approve→execute flow.

## Changes

- Added `src/arbora/voice/windows.py` with `listen_once()` via System.Speech
- Desktop chat **Voice** button runs recognition in a background thread
- Regression tests mock PowerShell subprocess calls

## Safety / permissions

- Voice is opt-in per click — no always-on microphone
- Recognition uses the default Windows microphone device
- Spoken text is treated like typed goals; broker approval rules unchanged

## How to verify

```powershell
arbora-ui
# Click Voice, speak a goal (e.g. "start my workday"), then Plan
pytest tests/test_voice_windows.py
```
