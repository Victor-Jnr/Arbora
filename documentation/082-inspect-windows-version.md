# 082 — Windows version inspect

- **Date:** 2026-09-12
- **Commit subject:** Inspect Windows version and build behind the broker without a product key
- **Stage:** Stage 3

## Summary

Testers can ask which Windows version this PC is running. Arbora returns Caption, Version, Build, and architecture only — never a product key or DigitalProductId.

## Changes

- Desktop adapter action `inspect_windows_version`
- Planner journey for “windows version” / “what version of windows” / “os build”
- Windows Update and product-key phrasing do not use this inspect
- Bundled workflow pack `inspect-windows-version`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not query ProductKey, OA3xOriginalProductKey, or DigitalProductId
- Output that looks like a password or product key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k "windows_version or windows version"
arbora --provider echo --goal "windows version"
```
