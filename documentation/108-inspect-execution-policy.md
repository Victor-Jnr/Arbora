# 108 — PowerShell execution policy inspect

- **Date:** 2026-10-05
- **Commit subject:** Inspect PowerShell execution policy behind the broker without Set-ExecutionPolicy
- **Stage:** Stage 3

## Summary

Testers can ask what the PowerShell execution policy is. Arbora reads Get-ExecutionPolicy scopes only — it does not call Set-ExecutionPolicy or change Bypass/Unrestricted. Developer Mode stays `inspect_developer_mode`.

## Changes

- Desktop adapter action `inspect_execution_policy`
- Planner journey for “execution policy” / “powershell execution policy” / “get-executionpolicy”
- Set / change phrasing does not use this inspect
- Bundled workflow pack `inspect-execution-policy`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Set-ExecutionPolicy or dump encoded commands
- Output that looks like a policy change or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_execution_policy
arbora --provider echo --goal "execution policy"
```
