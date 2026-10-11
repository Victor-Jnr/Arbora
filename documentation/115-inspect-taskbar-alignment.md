# 115 — Taskbar alignment inspect

- **Date:** 2026-10-11
- **Commit subject:** Inspect taskbar alignment behind the broker without moving the taskbar
- **Stage:** Stage 3

## Summary

Testers can ask whether the Windows 11 taskbar is left or center aligned. Arbora reads TaskbarAl only — it does not dump TaskbarSize or write Explorer Advanced. Hidden files stay `inspect_hidden_files`.

## Changes

- Desktop adapter action `inspect_taskbar_alignment`
- Planner journey for “taskbar alignment” / “is the taskbar centered”
- Move / hide / center-the-taskbar phrasing does not use this inspect
- Bundled workflow pack `inspect-taskbar-alignment`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not read TaskbarSize, write TaskbarAl, or dump SuperHidden
- Output that looks like a taskbar dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_taskbar_alignment
arbora --provider echo --goal "taskbar alignment"
```
