# 098 — Airplane mode inspect

- **Date:** 2026-09-24
- **Commit subject:** Inspect airplane mode behind the broker without toggling radios
- **Stage:** Stage 3

## Summary

Testers can ask whether airplane mode is on. Arbora reads RadioManagement SystemRadioState only — it does not enable or disable radios.

## Changes

- Desktop adapter action `inspect_airplane`
- Planner journey for “airplane mode” / “flight mode” / “is airplane mode on”
- Enable / disable / turn-on / turn-off phrasing does not use this inspect; wifi status stays `inspect_network`
- Bundled workflow pack `inspect-airplane`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Set-NetAdapter or netsh wlan set
- Output that looks like a radio toggle or secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k airplane
arbora --provider echo --goal "airplane mode"
```
