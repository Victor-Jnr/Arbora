# 089 — Defender status inspect

- **Date:** 2026-09-14
- **Commit subject:** Inspect Defender on/off status behind the broker without scanning or disabling
- **Stage:** Stage 3

## Summary

Testers can ask whether Microsoft Defender is on. Arbora reads enabled flags and the antivirus signature date only — it does not dump threats, change preferences, or start a scan.

## Changes

- Desktop adapter action `inspect_defender`
- Planner journey for “defender status” / “is defender on” / “real-time protection”
- Disable / scan / threat phrasing does not use this inspect
- Bundled workflow pack `inspect-defender`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Set-MpPreference, Start-MpScan, Get-MpThreat, or disable Defender
- Output that looks like a threat dump, quarantine list, or secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k defender
arbora --provider echo --goal "defender status"
```
