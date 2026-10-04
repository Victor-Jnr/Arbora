# 104 — SmartScreen inspect

- **Date:** 2026-10-04
- **Commit subject:** Inspect SmartScreen behind the broker without dumping URL lists
- **Stage:** Stage 3

## Summary

Testers can ask whether Windows SmartScreen is on. Arbora reads Explorer SmartScreenEnabled only — it does not dump URL lists or Defender preferences. Defender stays `inspect_defender`.

## Changes

- Desktop adapter action `inspect_smartscreen`
- Planner journey for “smartscreen” / “smart screen” / “is smartscreen on”
- Enable / disable / turn on / turn off phrasing does not use this inspect
- Bundled workflow pack `inspect-smartscreen`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not call Get-MpPreference, dump FilterList / URLs, or write SmartScreenEnabled
- Output that looks like a URL list or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_smartscreen
arbora --provider echo --goal "smartscreen"
```
