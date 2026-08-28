# 060 — Printer inspect

- **Date:** 2026-08-28
- **Commit subject:** Inspect installed printers behind the broker without print jobs
- **Stage:** Stage 3

## Summary

Testers can ask for printer status or the default printer and get a read-only listing of installed printers (name, default flag, status, port). Print jobs are not enumerated. Driver paths and secret-like output are withheld.

## Changes

- Desktop adapter action `inspect_printers`
- Planner journey for “printer status” / “default printer”
- Diagnose plans stay battery/network-focused and do not auto-add printers
- Bundled workflow pack `inspect-printers`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the listing and does not query WMI
- Output that looks like a password or key is withheld
- Does not send jobs, pause queues, or change the default printer

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k "printer"
arbora --provider echo --goal "printer status"
```
