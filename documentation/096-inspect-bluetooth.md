# 096 — Bluetooth radio inspect

- **Date:** 2026-09-20
- **Commit subject:** Inspect Bluetooth adapter status behind the broker without MAC or pairing dumps
- **Stage:** Stage 3

## Summary

Testers can ask whether Bluetooth is on. Arbora reads Get-NetAdapter name and Status for Bluetooth adapters only — it does not dump MAC addresses or paired devices, and does not enable or disable the radio.

## Changes

- Desktop adapter action `inspect_bluetooth`
- Planner journey for “bluetooth status” / “is bluetooth on” / “bluetooth radio”
- Disable / pair / MAC phrasing does not use this inspect; wifi status stays `inspect_network`
- Bundled workflow pack `inspect-bluetooth`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Disable-NetAdapter / Enable-NetAdapter or dump MAC / pairing lists
- Output that looks like a MAC dump, pairing list, or secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k bluetooth
arbora --provider echo --goal "bluetooth status"
```
