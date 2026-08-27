# 055 — Save clipboard to notes

- **Date:** 2026-08-27
- **Commit subject:** Save clipboard text to notes after refusing secrets
- **Stage:** Stage 3

## Summary

Testers can ask Arbora to save clipboard text into the notes folder as a timestamped file. Empty clipboards, images, file lists, and password/token-like text are refused. Inspect-only clipboard requests stay read-only.

## Changes

- Desktop adapter action `save_clipboard_text` (`path`)
- Planner journey for “save clipboard to notes”
- Bundled workflow pack `save-clipboard-note`

## Safety / permissions

- Save is `mutate` — broker approval, not hard confirmation
- Dry-run describes the write and does not read or create the file
- Secret-like text is never written
- Does not change the clipboard

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k "clipboard"
arbora --provider echo --goal "save clipboard to notes"
```
