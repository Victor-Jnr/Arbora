# 095 — TPM inspect

- **Date:** 2026-09-20
- **Commit subject:** Inspect TPM present/ready/enabled flags behind the broker without owner auth
- **Stage:** Stage 3

## Summary

Testers can ask whether a TPM is present and ready. Arbora reads Get-Tpm present/ready/enabled/activated flags only — it does not return owner auth or recovery material, and does not clear the TPM.

## Changes

- Desktop adapter action `inspect_tpm`
- Planner journey for “tpm status” / “is tpm ready” / “trusted platform module”
- Clear / initialize / recovery phrasing does not use this inspect
- Bundled workflow pack `inspect-tpm`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Clear-Tpm, Initialize-Tpm, or return owner auth / recovery passwords
- Output that looks like owner auth, recovery material, or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_tpm
arbora --provider echo --goal "tpm status"
```
