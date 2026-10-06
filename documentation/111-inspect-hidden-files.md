# 111 — Explorer hidden files inspect

- **Date:** 2026-10-06
- **Commit subject:** Inspect Explorer hidden files behind the broker without SuperHidden writes
- **Stage:** Stage 3

## Summary

Testers can ask whether hidden files and extensions are shown. Arbora reads Explorer Advanced Hidden and HideFileExt only — it does not write SuperHidden or list folder contents. Filename search stays `search_by_name`.

## Changes

- Desktop adapter action `inspect_hidden_files`
- Planner journey for “hidden files” / “are hidden files shown” / “are file extensions hidden”
- Show / hide / find phrasing does not use this inspect
- Bundled workflow pack `inspect-hidden-files`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not read SuperHidden, call Get-ChildItem, or write Explorer Advanced
- Output that looks like a SuperHidden dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_hidden_files
arbora --provider echo --goal "hidden files"
```
