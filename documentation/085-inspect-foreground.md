# 085 — Foreground window inspect and halt-on-failure

- **Date:** 2026-09-13
- **Commit subject:** Inspect the foreground window and halt a plan when a required step fails
- **Stage:** Stage 3

## Summary

Testers can ask which window is in front. Arbora returns title, process, and PID only. Plans can mark a step `halt_on_failure` so a failed verify does not continue into typing or other side effects.

## Changes

- Desktop adapter action `inspect_foreground`
- Planner journey for “foreground window” / “what's in front” / “which window is focused”
- `ToolStep.halt_on_failure` — remaining steps are skipped when that step fails
- Bundled workflow pack `inspect-foreground`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not SendKeys or SetForegroundWindow
- Halt-on-failure is opt-in per step; existing plans still continue after a failed step
- A denied halt_on_failure step also skips the rest of the plan
- Output that looks like a password or key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py tests/test_emergency_stop.py -k "foreground or halt_on_failure"
arbora --provider echo --goal "foreground window"
```
