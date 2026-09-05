# 073 — Default audio device inspect

- **Date:** 2026-09-05
- **Commit subject:** Inspect the default audio device behind the broker without changing it
- **Stage:** Stage 3

## Summary

Testers can ask which speakers or playback device Windows is using and get a read-only friendly name for the default Core Audio endpoint. Arbora does not change the default device or volume.

## Changes

- Desktop adapter action `inspect_audio_device`
- Planner journey for “audio device” / “what's my speaker” / “playback device”
- Set/switch phrasing does not use this inspect; volume/mute stays on `inspect_volume`
- Bundled workflow pack `inspect-audio-device`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call Core Audio
- Does not call SetDefaultEndpoint, PolicyConfig, or IPropertyStore.SetValue
- Output that looks like a password or key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k audio_device
arbora --provider echo --goal "audio device"
```
