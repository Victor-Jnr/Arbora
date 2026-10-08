# 114 — Game Mode inspect

- **Date:** 2026-10-08
- **Commit subject:** Inspect Game Mode behind the broker without dumping Game DVR captures
- **Stage:** Stage 3

## Summary

Testers can ask whether Windows Game Mode is on. Arbora reads AutoGameModeEnabled (falling back to AllowAutoGameMode) only — it does not dump Game DVR captures or enable Game Mode. GPU stays `inspect_gpu`.

## Changes

- Desktop adapter action `inspect_game_mode`
- Planner journey for “game mode” / “is game mode on”
- Enable / disable / Game Bar / Xbox phrasing does not use this inspect
- Bundled workflow pack `inspect-game-mode`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not read Game DVR AppCaptureEnabled or write GameBar values
- Output that looks like a capture dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_game_mode
arbora --provider echo --goal "game mode"
```
