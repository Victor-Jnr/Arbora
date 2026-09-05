# 074 — Installed apps inspect

- **Date:** 2026-09-05
- **Commit subject:** Inspect installed apps behind the broker without dumping Add/Remove
- **Stage:** Stage 3

## Summary

Testers can ask which apps are installed and get a capped read-only DisplayName (and publisher) list from the uninstall registry keys. Arbora does not open Add/Remove Programs, call Win32_Product, or uninstall anything.

## Changes

- Desktop adapter action `inspect_installed_apps`
- Planner journey for “installed apps” / “what programs are installed”
- Uninstall / Add-or-Remove phrasing does not use this inspect; startup apps stay on `inspect_startup`
- Bundled workflow pack `inspect-installed-apps`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the listing and does not query the registry
- Caps the listing (40 names); does not emit UninstallString
- Does not call Win32_Product, appwiz.cpl, or msiexec
- Output that looks like a password or key is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k installed_apps
arbora --provider echo --goal "installed apps"
```
