# 076 — Environment variable inspect by name

- **Date:** 2026-09-06
- **Commit subject:** Inspect a named environment variable behind the broker without dumping Env:
- **Stage:** Stage 3

## Summary

Testers can ask for one named process environment variable (for example PATH or TEMP) and get a truncated read-only value. Arbora never lists the whole environment and skips secret-like names.

## Changes

- Desktop adapter action `inspect_environment_variable`
- Planner journey for “environment variable PATH” / “env var TEMP” / `$env:USERPROFILE`
- Dump/set/unset phrasing does not use this inspect
- Bundled workflow pack `inspect-env-var` (PATH)

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the read and does not call PowerShell
- Does not call Get-ChildItem Env:, `[Environment]::GetEnvironmentVariables`, or setx
- Names that look like secrets are refused before any read
- Values that look like passwords or keys are withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k environment_variable
arbora --provider echo --goal "environment variable PATH"
```
