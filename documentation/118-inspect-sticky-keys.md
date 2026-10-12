# 118 — Sticky Keys inspect

- **Date:** 2026-10-12
- **Commit subject:** Inspect Sticky Keys behind the broker without changing accessibility flags
- **Stage:** Stage 3

## Summary

Testers can ask whether Sticky Keys is on. Arbora reads StickyKeys Flags bit 0 only — it does not dump FilterKeys or call SystemParametersInfo. Compact view stays `inspect_compact_view`.

## Changes

- Desktop adapter action `inspect_sticky_keys`
- Planner journey for “sticky keys” / “is sticky keys on”
- Enable / disable / Filter Keys phrasing does not use this inspect
- Bundled workflow pack `inspect-sticky-keys`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not write Flags, call SystemParametersInfo, or dump FilterKeys
- Output that looks like an accessibility dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_sticky_keys
arbora --provider echo --goal "sticky keys"
```
