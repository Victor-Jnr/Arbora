# 063 — Default browser inspect

- **Date:** 2026-08-29
- **Commit subject:** Inspect the default browser behind the broker without changing it
- **Stage:** Stage 3

## Summary

Testers can ask which browser is default and get a read-only http(s) UserChoice ProgId (mapped to a friendly name). The association Hash is not shown. The default is not changed.

## Changes

- Desktop adapter action `inspect_default_browser`
- Planner journey for “default browser” / “which browser”
- Does not steal “default printer” or “open https://… in chrome”
- Bundled workflow pack `inspect-default-browser`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the listing and does not query the registry
- Does not write UserChoice or StartMenuInternet
- Association Hash is not requested or printed

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k default_browser
arbora --provider echo --goal "what's my default browser"
```
