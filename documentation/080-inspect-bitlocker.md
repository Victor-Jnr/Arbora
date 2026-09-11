# 080 — BitLocker status inspect

- **Date:** 2026-09-11
- **Commit subject:** Inspect BitLocker status behind the broker without recovery keys
- **Stage:** Stage 3

## Summary

Testers can ask whether the drive is encrypted. Arbora returns mount point, volume status, protection status, and encryption percentage only — never RecoveryPassword, KeyProtector, or unlock.

## Changes

- Desktop adapter action `inspect_bitlocker`
- Planner journey for “bitlocker” / “is the drive encrypted” / “disk encryption status”
- Unlock / recovery-key phrasing does not use this inspect
- Bundled workflow pack `inspect-bitlocker`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Unlock-BitLocker, Enable-BitLocker, or Disable-BitLocker
- Output that looks like a password, recovery key, or key protector is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k bitlocker
arbora --provider echo --goal "bitlocker"
```
