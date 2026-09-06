# 078 — Local username / computer name inspect

- **Date:** 2026-09-06
- **Commit subject:** Inspect local username and computer name behind the broker without domain creds
- **Stage:** Stage 3

## Summary

Testers can ask who they are signed in as and what this PC is called. Arbora returns the local username and computer name only — not domain credentials, SIDs, or password hashes.

## Changes

- Desktop adapter action `inspect_identity`
- Planner journey for “what's my username” / “computer name” / “what's this pc called”
- Named env-var inspect stays on `inspect_environment_variable`; net user / whoami /all do not use this inspect
- Bundled workflow pack `inspect-identity`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call whoami /all, net user, or cmdkey
- Output that looks like a password or key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k identity
arbora --provider echo --goal "what's my username"
```
