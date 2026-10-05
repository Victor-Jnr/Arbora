# 107 — Developer Mode inspect

- **Date:** 2026-10-05
- **Commit subject:** Inspect Developer Mode behind the broker without enabling sideloading
- **Stage:** Stage 3

## Summary

Testers can ask whether Windows Developer Mode is on. Arbora reads AllowDevelopmentWithoutDevLicense only — it does not dump sideload lists or enable Developer Mode. Project scaffold stays the existing `dev setup` journey.

## Changes

- Desktop adapter action `inspect_developer_mode`
- Planner journey for “developer mode” / “dev mode” / “is developer mode on”
- Enable / disable / turn on / turn off phrasing does not use this inspect
- Bundled workflow pack `inspect-developer-mode`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not read AllowAllTrustedApps, dump sideload packages, or write AppModelUnlock
- Output that looks like a sideload dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_developer_mode
arbora --provider echo --goal "developer mode"
```
