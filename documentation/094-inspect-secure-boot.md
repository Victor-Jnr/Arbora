# 094 — Secure Boot inspect

- **Date:** 2026-09-20
- **Commit subject:** Inspect Secure Boot behind the broker without changing firmware variables
- **Stage:** Stage 3

## Summary

Testers can ask whether Secure Boot is on. Arbora reads Confirm-SecureBootUEFI only — it does not call Set-SecureBootUEFI or dump firmware variables.

## Changes

- Desktop adapter action `inspect_secure_boot`
- Planner journey for “secure boot” / “is secure boot on” / “is secure boot enabled”
- Disable / enable / firmware-write phrasing does not use this inspect
- Bundled workflow pack `inspect-secure-boot`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Set-SecureBootUEFI or dump firmware variables
- Output that looks like a firmware write or secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k secure_boot
arbora --provider echo --goal "secure boot"
```
