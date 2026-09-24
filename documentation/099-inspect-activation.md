# 099 — Windows activation inspect

- **Date:** 2026-09-24
- **Commit subject:** Inspect Windows activation status behind the broker without a product key
- **Stage:** Stage 3

## Summary

Testers can ask whether Windows is activated. Arbora reads SoftwareLicensingProduct LicenseStatus and Name only — it never returns a product key and does not call slmgr. “windows version” stays `inspect_windows_version`.

## Changes

- Desktop adapter action `inspect_activation`
- Planner journey for “windows activation” / “is windows activated” / “is windows licensed”
- Product-key / slmgr / activate-windows phrasing does not use this inspect
- Bundled workflow pack `inspect-activation`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call slmgr, /ipk, or /ato, and does not write PartialProductKey
- Output that looks like a product key, OA3 dump, or secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k activation
arbora --provider echo --goal "windows activation"
```
