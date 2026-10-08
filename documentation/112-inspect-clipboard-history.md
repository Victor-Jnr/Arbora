# 112 — Clipboard history inspect

- **Date:** 2026-10-08
- **Commit subject:** Inspect clipboard history behind the broker without dumping Win+V items
- **Stage:** Stage 3

## Summary

Testers can ask whether Windows clipboard history is on. Arbora reads EnableClipboardHistory only — it does not call Get-Clipboard or dump Win+V history items. Clipboard contents stay `inspect_clipboard`.

## Changes

- Desktop adapter action `inspect_clipboard_history`
- Planner journey for “clipboard history” / “is clipboard history on”
- Enable / disable / clear / save phrasing does not use this inspect
- Bundled workflow pack `inspect-clipboard-history`

## Safety / permissions

- Inspect is `read` — broker approval, not hard confirmation
- Dry-run describes the query and does not call PowerShell
- Does not read clipboard contents, history items, or write EnableClipboardHistory
- Output that looks like a clipboard dump or a secret is withheld

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k inspect_clipboard_history
arbora --provider echo --goal "clipboard history"
```
