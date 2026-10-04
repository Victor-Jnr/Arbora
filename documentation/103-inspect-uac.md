# 103 — UAC inspect

- **Date:** 2026-10-04
- **Commit subject:** Inspect UAC behind the broker without changing EnableLUA
- **Stage:** Stage 3

## Summary

Testers can ask whether User Account Control is on. Arbora reads EnableLUA only — it does not dump ConsentPromptBehaviorAdmin or change UAC policy.

## Changes

- Desktop adapter action `inspect_uac`
- Planner journey for “uac” / “user account control” / “is uac on”
- Enable / disable / turn on / turn off phrasing does not use this inspect
- Bundled workflow pack `inspect-uac`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not read ConsentPromptBehaviorAdmin, FilterAdministratorToken, or write EnableLUA
- Output that looks like a UAC policy dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_uac
arbora --provider echo --goal "uac"
```
