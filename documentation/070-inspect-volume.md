# 070 — Volume / mute inspect

- **Date:** 2026-09-04
- **Commit subject:** Inspect volume and mute behind the broker without changing them
- **Stage:** Stage 3

## Summary

Testers can ask for the speaker volume or whether sound is muted and get a read-only percent plus mute flag for the default playback device. Arbora does not change volume or mute.

## Changes

- Desktop adapter action `inspect_volume`
- Planner journey for “volume” / “what's my volume” / “am i muted”
- Set/mute/unmute phrasing does not use this inspect
- Bundled workflow pack `inspect-volume`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call Core Audio
- Does not call SetMasterVolumeLevelScalar, SetMute, or SendKeys volume keys
- Output that looks like a password or key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k volume
arbora --provider echo --goal "volume"
```
