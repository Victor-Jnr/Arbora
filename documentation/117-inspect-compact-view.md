# 117 — Explorer compact view inspect

- **Date:** 2026-10-11
- **Commit subject:** Inspect Explorer compact view behind the broker without SuperHidden writes
- **Stage:** Stage 3

## Summary

Testers can ask whether File Explorer compact view is on. Arbora reads UseCompactMode only — it does not write SuperHidden or change hidden-files settings. Hidden files stay `inspect_hidden_files`.

## Changes

- Desktop adapter action `inspect_compact_view`
- Planner journey for “compact view” / “explorer compact” / “is compact mode on”
- Enable / disable / hidden-files phrasing does not use this inspect
- Bundled workflow pack `inspect-compact-view`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not read SuperHidden, HideFileExt, or write UseCompactMode
- Output that looks like a SuperHidden dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_compact_view
arbora --provider echo --goal "compact view"
```
