# 050 — Clipboard inspect

- **Date:** 2026-08-22
- **Commit subject:** Inspect the clipboard without dumping secrets
- **Stage:** Stage 3

## Summary

Testers can ask Arbora what is on the Windows clipboard. The default report is type and length only. An explicit “show clipboard text” request may include a short preview, but password/token-like content is still withheld.

## Changes

- Desktop adapter action `inspect_clipboard` (`reveal`)
- Planner journey for “inspect clipboard” vs “show clipboard text”
- Bundled workflow pack `inspect-clipboard` (metadata only)
- Secret heuristic withholds passwords, tokens, and keys from the step output

## Safety / permissions

- Inspect is `read` — no hard confirmation
- Does not write the clipboard
- Secrets are never included in the adapter output, even with `reveal`

## How to verify

```powershell
pytest tests/test_adapters_hardening.py tests/test_broker_and_planner.py tests/test_workflow_packs.py -k clipboard
arbora --provider echo --goal "inspect clipboard"
```
