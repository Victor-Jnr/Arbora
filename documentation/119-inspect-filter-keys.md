# 119 — Filter Keys inspect

- **Date:** 2026-10-12
- **Commit subject:** Inspect Filter Keys behind the broker without dumping bounce timings
- **Stage:** Stage 3

## Summary

Testers can ask whether Filter Keys is on. Arbora reads Keyboard Response Flags bit 0 only — it does not dump BounceTime or call SystemParametersInfo. Sticky Keys stays `inspect_sticky_keys`.

## Changes

- Desktop adapter action `inspect_filter_keys`
- Planner journey for “filter keys” / “is filter keys on”
- Enable / disable / Sticky Keys phrasing does not use this inspect
- Bundled workflow pack `inspect-filter-keys`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not write Flags, dump bounce timings, or call SystemParametersInfo
- Output that looks like an accessibility dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_filter_keys
arbora --provider echo --goal "filter keys"
```
